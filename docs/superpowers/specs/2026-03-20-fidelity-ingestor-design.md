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

### Async Note

The batcave scraper uses `async_playwright` with async/await throughout. The secmaster codebase is synchronous. The scraper CLI entrypoint wraps the async code with `asyncio.run()`. Async does **not** leak into the ingestion path — the ingestor remains fully synchronous.

### Dependencies

Added to `pyproject.toml`:
- `playwright` — scraper only (browser automation)
- `openpyxl` — XLSX parsing in the ingestor's `fetch()`/`transform()`

Both are main dependencies (not optional extras) since they're used in the core workflow.

### .gitignore Additions

```
data/
fidelity_auth.json
```

`data/inbox/fidelity/` contains downloaded XLSX files (large, ephemeral). `fidelity_auth.json` contains Fidelity session cookies (sensitive).

### mise Task Definitions

```toml
[tasks."scrape:fidelity"]
description = "Scrape microcap data from Fidelity stock screener"
run = "python -m tools.fidelity_scraper.cli"

[tasks."ingest:fidelity"]
description = "Ingest Fidelity XLSX files from data/inbox/fidelity/"
run = "python -m app.ingestion.cli fidelity"
```

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
    updated_at: datetime
```

Key behaviors:
- Dedup on `file_hash` — same file never processed twice, even if renamed
- Status lifecycle: `pending` → `completed` or `failed`
- Failed files can be retried by deleting the log entry or adding a `mise run ingest:retry` command
- Requires an Alembic migration (`mise run migrate:create` → `mise run migrate`) to create the table

### FidelityIngestor Implementation

The Fidelity ingestor overrides `run()` to manage per-file transaction boundaries and ingestion log tracking. It does **not** use the base class `load()` method, since `BaseIngestor.load()` does a single `session.commit()` which conflicts with per-file transaction isolation.

`transform()` stays pure — it converts raw dicts to domain objects without DB access. Entity resolution and change detection (which require DB reads) live in a separate `_resolve_and_persist()` method called from `run()`. This keeps `transform()` unit-testable without a database.

```python
class FidelityIngestor(BaseIngestor):
    vendor_name = "fidelity"

    def __init__(self, session: Session, inbox_path: str = "data/inbox/fidelity"):
        super().__init__(session)
        self.inbox_path = Path(inbox_path)

    def fetch(self) -> dict[str, list[RawRecord]]:
        # Scan inbox for XLSX files
        # Hash each, check ingestion_log, skip already-processed
        # Parse BasicFacts sheet from each unprocessed file
        # Return rows grouped by filename so run() can process per-file transactions
        # e.g. {"batch_001_20260320.xlsx": [row1, row2, ...], ...}

    def transform(self, raw: list[RawRecord]) -> list[SQLModel]:
        # Pure transformation: raw dicts → canonical domain objects
        # No DB access — maps XLSX columns to model fields
        # Returns Issuer, Security, Listing, *History instances

    def _resolve_and_persist(self, records: list[SQLModel], scrape_date: date) -> tuple[int, int]:
        # Entity resolution: find existing via VendorSecurityMap or create new
        # Change detection: compare against current open-ended history records
        # Point-in-time: end-date old records, insert new only on change
        # Returns (created_count, updated_count)

    def run(self) -> IngestResult:
        # For each unprocessed file in inbox:
        #   1. Create pending ingestion_log entry
        #   2. Parse file → fetch() for that file's rows
        #   3. Transform rows → transform()
        #   4. Resolve and persist → _resolve_and_persist()
        #   5. Commit transaction on success, rollback on failure
        #   6. Update ingestion_log entry (completed/failed)
        # Aggregate results across all files
```

Overrides `run()` and bypasses `load()` — keeps the base class clean for other vendors that fit the simpler flow.

### Filename Convention

The scraper writes files with the pattern:

```
microcap_stocks_batch_NNN_YYYYMMDD_HHMMSS.xlsx
```

Example: `microcap_stocks_batch_001_20260320_143022.xlsx`

The ingestor extracts `scrape_date` by parsing the `YYYYMMDD` portion from the filename using:

```python
# Match _YYYYMMDD_HHMMSS.xlsx at end of filename
match = re.search(r'_(\d{8})_\d{6}\.xlsx$', filename)
scrape_date = date(int(match[1][:4]), int(match[1][4:6]), int(match[1][6:8]))
```

This date becomes the `effective_start_date` for all point-in-time records created from that file.

### Classification Field Mapping

Fidelity provides free-text Sector and Industry values (e.g., "Technology", "Software - Application"). These map to `IssuerClassificationHistory` as **two separate records per issuer**:

| Fidelity Field | `classification_system` | `classification_code` | `classification_name` |
|---|---|---|---|
| Sector | `fidelity_sector` | Normalized lowercase (e.g., `technology`) | Raw Fidelity text (e.g., `Technology`) |
| Industry | `fidelity_industry` | Normalized lowercase (e.g., `software_application`) | Raw Fidelity text (e.g., `Software - Application`) |

Change detection compares `classification_code` values against the current open-ended record for each system. A sector change and an industry change are tracked independently.

### VendorSecurityMap Usage

One `VendorSecurityMap` row per ticker, pointing to all three entity levels:

| Field | Value |
|---|---|
| `vendor_name` | `"fidelity"` |
| `vendor_entity_type` | `"stock"` |
| `vendor_id` | Ticker symbol (e.g., `"ACME"`) |
| `issuer_id` | FK to resolved Issuer |
| `security_id` | FK to resolved Security |
| `listing_id` | FK to resolved Listing |
| `mapping_method` | `"ticker_match"` for first creation, `"vendor_map_lookup"` for subsequent |
| `confidence_score` | `1.0` (direct match from Fidelity's own data) |

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
│       (two records: one for fidelity_sector, one for fidelity_industry)
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
