# Fidelity Ingestor Design

## Overview

A two-part system for ingesting microcap stock data from Fidelity into secmaster:

1. **Fidelity Scraper** — a local Playwright CLI tool that logs into Fidelity, navigates the stock screener, and downloads XLSX files to a local inbox directory.
2. **Fidelity Ingestor** — a server-side component that reads XLSX files from the inbox, parses BasicFacts data, and creates point-in-time records in the secmaster database.

These are separate commands (`mise run scrape:fidelity` and `mise run ingest:fidelity`) that communicate through a filesystem inbox convention.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Scraper location | In secmaster repo (`tools/fidelity-scraper/`) | Co-locates data contract with producer; single repo to maintain |
| Data scope | Security master fields only (BasicFacts sheet) | Focused on what we have models for today |
| File transport | Local inbox directory now, object storage later | Start simple; ingestor reads from configurable path |
| Duplicate handling | Always insert with point-in-time history | Core product purpose: track and quantify change over time |
| Scrape vs ingest | Two separate commands | Composable; inspect before ingesting; re-ingest without re-scraping |
| Scraper port strategy | Faithful port from batcave | Battle-tested selectors and timing; don't reinvent what works |
| File tracking | `ingestion_log` DB table with sha256 dedup | Scales to thousands of files; queryable history |

## Architecture

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Fidelity Scraper   │  XLSX   │   data/inbox/    │  reads   │   Fidelity      │
│  (Playwright CLI)   │ ──────► │   fidelity/      │ ◄────── │   Ingestor      │
│                     │         │                  │         │                 │
│  mise run           │         │  timestamped     │         │  mise run       │
│    scrape:fidelity  │         │  batch files     │         │    ingest:fidelity│
└─────────────────────┘         └──────────────────┘         └────────┬────────┘
                                                                      │
                                                              ┌───────▼────────┐
                                                              │   PostgreSQL   │
                                                              │                │
                                                              │  ingestion_log │
                                                              │  issuer        │
                                                              │  security      │
                                                              │  listing       │
                                                              │  *_history     │
                                                              └────────────────┘
```

## Component 1: Fidelity Scraper

Faithful port of batcave's `fidelity_automation/` into `tools/fidelity-scraper/`.

### Modules

**`tools/fidelity-scraper/auth.py`** — from batcave's `context.py`
- Persistent session via `fidelity_auth.json` (stored in project root, gitignored)
- Opens visible Chromium browser for manual login + MFA
- 24-hour session validity, prompts re-login when expired
- Anti-automation-detection flags preserved

**`tools/fidelity-scraper/scraper.py`** — from batcave's `pages/research.py`
- Navigate to stock screener, apply microcap filter
- Paginate through results in 500-item batches
- Select all → download modal → pick BasicFacts sheet → download XLSX
- Write to `data/inbox/fidelity/` with timestamped filenames
- Progress output to terminal (batch N of M, items downloaded)

**`tools/fidelity-scraper/cli.py`** — entrypoint
- `mise run scrape:fidelity` → authenticate (reuse session or prompt login) → scrape → report summary
- Flags: `--headless=false` (default, required for MFA), `--dry-run` (navigate but don't download)

### What we are NOT porting
- Fixed income pages (not in scope)
- Portfolio page (was just for auth verification)
- batcave's job system / WebSocket updates
- Excel parsing logic from `microcap.py` — moves into the ingestor's `transform()`

### Dependencies
- `playwright` added to project (scraper only, not the server)

## Component 2: Fidelity Ingestor

### `ingestion_log` Table

```python
class IngestionLog(SQLModel, table=True):
    __tablename__ = "ingestion_log"
    id: UUID                    # PK
    vendor_name: str            # "fidelity"
    filename: str               # "microcap_stocks_batch_001_20260320_143022.xlsx"
    file_hash: str              # sha256 — dedup key
    file_size_bytes: int
    scrape_date: date           # extracted from filename timestamp
    status: str                 # "pending", "completed", "failed"
    records_fetched: int | None # rows parsed from file
    records_created: int | None # new entities created
    records_updated: int | None # history records appended
    error_details: str | None   # if status="failed"
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
```

Key behaviors:
- Dedup on `file_hash` — same file never processed twice, even if renamed
- Status lifecycle: `pending` → `completed` or `failed`
- Failed files can be retried by deleting the log entry or adding a `mise run ingest:retry` command

### FidelityIngestor Implementation

```python
class FidelityIngestor(BaseIngestor):
    vendor_name = "fidelity"

    def __init__(self, session: Session, inbox_path: str = "data/inbox/fidelity"):
        super().__init__(session)
        self.inbox_path = Path(inbox_path)

    def fetch(self) -> list[RawRecord]:
        # Scan inbox for XLSX files
        # Hash each, check ingestion_log, skip already-processed
        # Parse BasicFacts sheet from each unprocessed file
        # Create pending ingestion_log entries
        # Return flat list of row dicts with scrape_date attached

    def transform(self, raw: list[RawRecord]) -> list[SQLModel]:
        # For each row: resolve/create Issuer → Security → Listing chain
        # Compare against existing records, append history only on change
        # Return all new/updated model instances

    def run(self) -> IngestResult:
        # Override to add per-file status tracking
        # Update ingestion_log entries to completed/failed
        # Report: X files processed, Y created, Z updated, N failed
```

Override `run()` rather than changing `BaseIngestor` — keeps the base class clean for other vendors.

### Data Flow

For each XLSX file:

1. Scan inbox, hash each file (sha256), skip any already in `ingestion_log`
2. Parse BasicFacts sheet — each row is one stock with: Symbol, Company Name, Sector, Industry, Market Cap, and identifiers (CUSIP etc.)
3. For each row, resolve or create the entity chain:

```
Symbol "ACME" from file scraped 2026-03-20
│
├─► Issuer: find by normalized name or create new
│   └─► IssuerNameHistory: if name differs from latest record, end-date old, insert new
│   └─► IssuerClassificationHistory: if sector/industry changed, end-date old, insert new
│
├─► Security: find by issuer + type "common_equity" or create new
│   └─► SecurityIdentifierHistory: for each identifier (ticker, CUSIP, etc.)
│       if value changed, end-date old, insert new
│
├─► Listing: find by security + venue or create new
│   └─► ListingStatusHistory: end-date old, insert new snapshot
│
└─► VendorSecurityMap: link Fidelity's symbol back to our entities
```

### Point-in-Time Rules

- `effective_start_date` = scrape date (the date the XLSX was downloaded, embedded in filename)
- When a value changes: set `effective_end_date` on the previous record to scrape date, insert new record with open-ended end date (`NULL`)
- When a value hasn't changed: no new record — the existing open-ended record remains valid
- When a ticker disappears from a scrape: do NOT end-date it (absence from one scrape doesn't mean delisted — could be a filter/pagination issue)

### Entity Matching Strategy

- Primary match key: ticker symbol via `VendorSecurityMap` (vendor_name="fidelity", vendor_id=symbol)
- First-time tickers: create full Issuer → Security → Listing chain
- Known tickers: walk the existing chain, compare fields, append history only on change

## Error Handling

- **File-level isolation** — if one XLSX fails to parse or ingest, mark it `failed` in `ingestion_log`, continue to next file. One bad batch doesn't block the rest.
- **Row-level errors** — if a single row fails to transform (e.g., missing required field), log it in `error_details`, skip that row, continue. Track count in `IngestResult.errors`.
- **Database transaction** — each file gets its own transaction. Commit on success, rollback on failure. No partial file ingestions.
- **Scraper errors** — Playwright timeouts, missing selectors, download failures: log to stderr, continue to next batch if possible. Best-effort — whatever files land in inbox get ingested.

## Testing Strategy

- **Unit tests for transform logic** — feed known RawRecords, assert correct model instances with correct point-in-time dates. No database needed.
- **Integration tests for the full pipeline** — drop a sample XLSX in a temp inbox directory, run the ingestor against test Postgres, assert entities and history records exist with correct dates.
- **Sample fixture** — create a small XLSX with ~5 stocks in BasicFacts format, commit to `tests/fixtures/fidelity/`. Avoids needing real Fidelity data in tests.
- **No scraper tests** — browser automation against a live third-party site isn't reliably testable. The scraper is tested by running it.

## Future: Object Storage Migration

When ready to move from local inbox to S3/R2:
- Change `inbox_path` config to an S3 URI
- Add a storage read layer (boto3) in `fetch()`
- `ingestion_log` and all transform/load logic stays identical
- Scraper uploads to S3 instead of writing locally
