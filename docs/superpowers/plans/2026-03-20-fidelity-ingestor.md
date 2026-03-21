# Fidelity Ingestor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-part system — a local Playwright scraper and a file-based ingestor — that downloads microcap stock data from Fidelity and creates point-in-time records in secmaster's database.

**Architecture:** The scraper (`tools/fidelity_scraper/`) downloads XLS files to `data/inbox/fidelity/`. The ingestor (`app/ingestion/fidelity.py`) scans the inbox, deduplicates via `ingestion_log` table, parses "Basic Facts" sheets, and creates/updates Issuer → Security → Listing entity chains with point-in-time history records. Each file is processed in its own DB transaction.

**Tech Stack:** Python 3.12, Playwright (async), xlrd (XLS reading), openpyxl (test fixture generation), SQLModel, Alembic, PostgreSQL, mise

**Spec:** `docs/superpowers/specs/2026-03-20-fidelity-ingestor-design.md`

### Important: Fidelity File Format

Fidelity downloads are **CDFV2 (old .xls format)**, not modern .xlsx. The `file` command shows `CDFV2 Microsoft Excel`. Use `xlrd` to read them (not openpyxl). The sheet name is `"Basic Facts"` (with a space). Actual columns:

```
Symbol, Company Name, Security Price, Volume (90 Day Avg), Market Capitalization,
Dividend Yield, Company Headquarters Location, Sector, Industry, Optionable
```

Market Capitalization values are strings like `"$2.83B"`, `"$156.69M"`. Test fixtures use openpyxl (.xlsx) for simplicity — the `fetch()` implementation detects format and uses the appropriate reader.

---

## File Structure

### New Files
| File | Responsibility |
|---|---|
| `app/models/ingestion_log.py` | `IngestionLog` SQLModel table |
| `app/ingestion/fidelity.py` | `FidelityIngestor` — fetch, transform, resolve, run (replaces stub) |
| `tools/fidelity_scraper/__init__.py` | Package init |
| `tools/fidelity_scraper/auth.py` | Playwright session management, cookie persistence |
| `tools/fidelity_scraper/scraper.py` | Stock screener automation, pagination, download |
| `tools/fidelity_scraper/cli.py` | CLI entrypoint with `asyncio.run()` wrapper |
| `tools/fidelity_scraper/__main__.py` | Allows `python -m tools.fidelity_scraper` |
| `tests/test_ingestion/test_fidelity.py` | Unit + integration tests for ingestor |
| `tests/fixtures/fidelity/sample_basicfacts.xlsx` | Test fixture XLSX (openpyxl format for tests) |

### Modified Files
| File | Change |
|---|---|
| `pyproject.toml` | Add `playwright`, `xlrd`, `openpyxl` dependencies |
| `mise.toml` | Add `scrape:fidelity` and `ingest:fidelity` tasks |
| `.gitignore` | Add `data/`, `fidelity_auth.json`, `tmp_downloads/` |
| `app/models/__init__.py` | Import `IngestionLog` |
| `app/ingestion/cli.py` | Pass `inbox_path` to `FidelityIngestor` constructor |

---

## Task 1: Project Setup — Dependencies, Gitignore, Mise Tasks

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Modify: `mise.toml`

- [ ] **Step 1: Add dependencies to pyproject.toml**

In `pyproject.toml`, add `playwright`, `xlrd`, and `openpyxl` to the dependencies list:

```python
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlmodel>=0.0.22",
    "psycopg2-binary>=2.9",
    "alembic>=1.14",
    "pydantic-settings>=2.7",
    "slowapi>=0.1.9",
    "PyJWT[crypto]>=2.9",
    "httpx>=0.28",
    "playwright>=1.40",
    "xlrd>=2.0",
    "openpyxl>=3.1",
]
```

Note: `xlrd` reads Fidelity's CDFV2 .xls files. `openpyxl` is used for generating test fixtures and for reading any .xlsx files.

- [ ] **Step 2: Add gitignore entries**

Append to `.gitignore`:

```
# Fidelity scraper
data/
fidelity_auth.json
tmp_downloads/
```

- [ ] **Step 3: Add mise tasks**

Append to `mise.toml`:

```toml
[tasks."scrape:fidelity"]
description = "Scrape microcap data from Fidelity stock screener"
run = "python -m tools.fidelity_scraper.cli"

[tasks."ingest:fidelity"]
description = "Ingest Fidelity XLSX files from data/inbox/fidelity/"
run = "python -m app.ingestion.cli fidelity"
```

- [ ] **Step 4: Install dependencies**

Run: `pip install -e '.[dev]'`
Expected: Successfully installs playwright, xlrd, and openpyxl

- [ ] **Step 5: Install Playwright browsers**

Run: `playwright install chromium`
Expected: Downloads Chromium browser binary

- [ ] **Step 6: Create inbox directory structure**

Run: `mkdir -p data/inbox/fidelity`
Expected: Directory created (gitignored, won't be committed)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore mise.toml
git commit -m "Add Fidelity ingestor dependencies, gitignore, mise tasks"
```

---

## Task 2: IngestionLog Model + Migration

**Files:**
- Create: `app/models/ingestion_log.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Create the IngestionLog model**

Create `app/models/ingestion_log.py`:

```python
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestionLog(SQLModel, table=True):
    __tablename__ = "ingestion_log"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    vendor_name: str
    filename: str
    file_hash: str = Field(index=True)
    file_size_bytes: int
    scrape_date: date
    status: str = "pending"
    records_fetched: int | None = None
    records_created: int | None = None
    records_updated: int | None = None
    error_details: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
```

- [ ] **Step 2: Register in models __init__**

Add to `app/models/__init__.py`:

```python
from app.models.ingestion_log import IngestionLog  # noqa: F401
```

- [ ] **Step 3: Generate Alembic migration**

Run: `alembic revision --autogenerate -m "add ingestion_log table"`
Expected: New migration file created in `migrations/versions/`

- [ ] **Step 4: Verify migration SQL looks correct**

Read the generated migration file. Confirm it creates `ingestion_log` table with all columns and an index on `file_hash`.

- [ ] **Step 5: Apply migration to dev database**

Run: `mise run db:up && mise run migrate`
Expected: Migration applies cleanly

- [ ] **Step 6: Commit**

```bash
git add app/models/ingestion_log.py app/models/__init__.py migrations/versions/
git commit -m "Add ingestion_log model and migration"
```

---

## Task 3: Test Fixture — Sample XLSX

**Files:**
- Create: `tests/fixtures/fidelity/sample_basicfacts.xlsx`

- [ ] **Step 1: Create test fixture XLSX**

Write a Python script (run once, don't commit the script) to generate the fixture. Uses the **real** Fidelity column layout with all 10 columns from the "Basic Facts" sheet:

```python
import openpyxl

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Basic Facts"  # Note: space in sheet name, matching real Fidelity format

# Headers matching Fidelity's actual Basic Facts sheet
headers = [
    "Symbol", "Company Name", "Security Price", "Volume (90 Day Avg)",
    "Market Capitalization", "Dividend Yield", "Company Headquarters Location",
    "Sector", "Industry", "Optionable",
]
ws.append(headers)

# 5 test stocks with realistic data
ws.append(["ACME", "Acme Corporation", 22.37, 2313650, "$150.50M", None, "United States of America", "Technology", "Software - Application", "Yes (Option Chain)"])
ws.append(["BGFV", "Big 5 Sporting Goods Corp", 8.52, 500000, "$85.20M", 3.5, "United States of America", "Consumer Discretionary", "Specialty Retail", "Yes (Option Chain)"])
ws.append(["CATO", "The Cato Corporation", 15.60, 250000, "$320.10M", 6.2, "United States of America", "Consumer Discretionary", "Apparel Retail", "No"])
ws.append(["DMRC", "Digimarc Corporation", 25.10, 150000, "$210.70M", None, "United States of America", "Technology", "Software - Infrastructure", "Yes (Option Chain)"])
ws.append(["EDUC", "Educational Development Corp", 1.23, 50000, "$12.30M", None, "United States of America", "Communication Services", "Publishing", "No"])

wb.save("tests/fixtures/fidelity/sample_basicfacts.xlsx")
```

Run: `mkdir -p tests/fixtures/fidelity && python -c "<the script above>"`
Expected: XLSX file created with 5 rows of test data in "Basic Facts" sheet

- [ ] **Step 2: Verify fixture is readable**

```bash
python -c "
import openpyxl
wb = openpyxl.load_workbook('tests/fixtures/fidelity/sample_basicfacts.xlsx')
print('Sheets:', wb.sheetnames)
ws = wb['Basic Facts']
for row in ws.iter_rows(values_only=True):
    print(row)
"
```

Expected: Prints `Sheets: ['Basic Facts']` then header row + 5 data rows

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/fidelity/
git commit -m "Add sample Fidelity Basic Facts XLSX test fixture"
```

---

## Task 4: FidelityIngestor — fetch()

**Files:**
- Modify: `app/ingestion/fidelity.py`
- Create: `tests/test_ingestion/test_fidelity.py`

- [ ] **Step 1: Write failing test for fetch — skips already-processed files**

Create `tests/test_ingestion/test_fidelity.py`:

```python
import hashlib
import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.ingestion.fidelity import FidelityIngestor
from app.models.ingestion_log import IngestionLog


@pytest.fixture
def inbox_dir(tmp_path):
    """Create a temp inbox with the sample fixture copied in."""
    inbox = tmp_path / "inbox" / "fidelity"
    inbox.mkdir(parents=True)
    fixture = Path("tests/fixtures/fidelity/sample_basicfacts.xlsx")
    dest = inbox / "microcap_stocks_batch_001_20260320_143022.xlsx"
    shutil.copy(fixture, dest)
    return inbox


def test_fetch_returns_rows_grouped_by_file(session, inbox_dir):
    ingestor = FidelityIngestor(session, inbox_path=str(inbox_dir))
    result = ingestor.fetch()

    assert len(result) == 1  # one file
    filename = list(result.keys())[0]
    assert "batch_001" in filename
    rows = result[filename]
    assert len(rows) == 5  # 5 stocks in fixture
    assert rows[0]["Symbol"] == "ACME"
    assert rows[0]["_scrape_date"] == date(2026, 3, 20)


def test_fetch_skips_already_processed_file(session, inbox_dir):
    """If a file's hash is already in ingestion_log, fetch() skips it."""
    fixture_path = inbox_dir / "microcap_stocks_batch_001_20260320_143022.xlsx"
    file_hash = hashlib.sha256(fixture_path.read_bytes()).hexdigest()

    log_entry = IngestionLog(
        vendor_name="fidelity",
        filename=fixture_path.name,
        file_hash=file_hash,
        file_size_bytes=fixture_path.stat().st_size,
        scrape_date=date(2026, 3, 20),
        status="completed",
    )
    session.add(log_entry)
    session.commit()

    ingestor = FidelityIngestor(session, inbox_path=str(inbox_dir))
    result = ingestor.fetch()

    assert len(result) == 0  # file was already processed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingestion/test_fidelity.py -v`
Expected: FAIL — `FidelityIngestor` still raises `NotImplementedError`

- [ ] **Step 3: Implement fetch()**

Replace `app/ingestion/fidelity.py`. Key design note: `fetch()` returns `dict[str, list[RawRecord]]` (grouped by filename) instead of `list[RawRecord]`. This breaks the `BaseIngestor` abstract signature intentionally — FidelityIngestor overrides `run()` and never calls `BaseIngestor.run()`, so the base class never sees this return type. A type: ignore comment documents this.

The implementation auto-detects XLS vs XLSX format. Real Fidelity files are CDFV2 .xls (read with `xlrd`). Test fixtures are .xlsx (read with `openpyxl`). Invalid symbols (timestamps, disclaimers) are filtered out using the same regex from batcave's `microcap.py`.

```python
import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Any

import openpyxl
import xlrd
from sqlmodel import Session, SQLModel, select

from app.ingestion.base import BaseIngestor, IngestResult, RawRecord
from app.models.ingestion_log import IngestionLog

# Junk rows Fidelity includes at the bottom of sheets
_INVALID_SYMBOL_RE = re.compile(
    r"^\d{2}:\d{2}|AS OF|All data is|Data and information|Quotes delayed"
)


def _parse_scrape_date(filename: str) -> date:
    """Extract scrape date from filename like microcap_stocks_batch_001_20260320_143022.xlsx"""
    match = re.search(r"_(\d{8})_\d{6}\.xlsx$", filename)
    if not match:
        raise ValueError(f"Cannot parse scrape date from filename: {filename}")
    d = match.group(1)
    return date(int(d[:4]), int(d[4:6]), int(d[6:8]))


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_basic_facts_sheet(file_path: Path) -> list[dict[str, Any]]:
    """Read the 'Basic Facts' sheet from an XLS or XLSX file.

    Auto-detects format: CDFV2 .xls (real Fidelity) → xlrd, OOXML .xlsx (test fixtures) → openpyxl.
    """
    header = file_path.read_bytes()[:8]
    is_xls = header[:4] == b"\xd0\xcf\x11\xe0"  # CDFV2 magic bytes

    sheet_name = "Basic Facts"

    if is_xls:
        wb = xlrd.open_workbook(str(file_path))
        if sheet_name not in wb.sheet_names():
            return []
        ws = wb.sheet_by_name(sheet_name)
        headers = [str(ws.cell_value(0, c)).strip() for c in range(ws.ncols)]
        rows = []
        for r in range(1, ws.nrows):
            row = {headers[c]: ws.cell_value(r, c) for c in range(ws.ncols)}
            rows.append(row)
        return rows
    else:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        if sheet_name not in wb.sheetnames:
            wb.close()
            return []
        ws = wb[sheet_name]
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h).strip() for h in next(rows_iter)]
        rows = [dict(zip(headers, row)) for row in rows_iter]
        wb.close()
        return rows


def _is_valid_symbol(symbol: str) -> bool:
    """Filter out junk rows (timestamps, disclaimers) from Fidelity data."""
    if not symbol or len(symbol) > 10:
        return False
    if _INVALID_SYMBOL_RE.search(symbol):
        return False
    return True


class FidelityIngestor(BaseIngestor):
    """Fidelity data ingestion — reads XLS/XLSX files from inbox directory."""

    vendor_name = "fidelity"

    def __init__(self, session: Session, inbox_path: str = "data/inbox/fidelity"):
        super().__init__(session)
        self.inbox_path = Path(inbox_path)

    def fetch(self) -> dict[str, list[RawRecord]]:  # type: ignore[override]
        """Scan inbox for unprocessed XLS/XLSX files, parse Basic Facts sheets.

        Returns rows grouped by filename so run() can process per-file transactions.
        Overrides BaseIngestor.fetch() return type — FidelityIngestor uses its own run().
        """
        result: dict[str, list[RawRecord]] = {}

        if not self.inbox_path.exists():
            return result

        for file_path in sorted(self.inbox_path.glob("*.xlsx")):
            fhash = _file_hash(file_path)

            # Check if already processed
            existing = self.session.exec(
                select(IngestionLog).where(IngestionLog.file_hash == fhash)
            ).first()
            if existing:
                continue

            try:
                scrape_date = _parse_scrape_date(file_path.name)
            except ValueError:
                continue

            rows = _read_basic_facts_sheet(file_path)
            if not rows:
                continue

            file_rows = []
            for row in rows:
                symbol = str(row.get("Symbol", "")).strip()
                if not _is_valid_symbol(symbol):
                    continue
                row["_scrape_date"] = scrape_date
                row["_filename"] = file_path.name
                row["_file_hash"] = fhash
                row["_file_size"] = file_path.stat().st_size
                file_rows.append(row)

            if file_rows:
                result[file_path.name] = file_rows

        return result

    def transform(self, raw: list[RawRecord]) -> list[SQLModel]:
        raise NotImplementedError("Transform not yet implemented")

    def run(self) -> IngestResult:
        raise NotImplementedError("Run not yet implemented")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingestion/test_fidelity.py -v`
Expected: Both `test_fetch_returns_rows_grouped_by_file` and `test_fetch_skips_already_processed_file` PASS

- [ ] **Step 5: Commit**

```bash
git add app/ingestion/fidelity.py tests/test_ingestion/test_fidelity.py
git commit -m "Implement FidelityIngestor.fetch() with inbox scanning and dedup"
```

---

## Task 5: FidelityIngestor — transform()

**Files:**
- Modify: `app/ingestion/fidelity.py`
- Modify: `tests/test_ingestion/test_fidelity.py`

`transform()` is pure — it converts raw dicts to domain objects without touching the DB. It returns a list of `TickerBundle` dataclasses (one per ticker) so that `_resolve_and_persist()` doesn't need to re-group by ticker.

- [ ] **Step 1: Write failing tests for transform**

Add to `tests/test_ingestion/test_fidelity.py`:

```python
from app.models.issuer import Issuer
from app.models.security import Security
from app.models.listing import Listing, ListingStatusHistory
from app.models.classification import IssuerClassificationHistory


def _make_raw_record(**overrides):
    """Helper to create a raw record dict as fetch() would produce."""
    defaults = {
        "Symbol": "ACME",
        "Company Name": "Acme Corporation",
        "Security Price": 22.37,
        "Volume (90 Day Avg)": 2313650,
        "Market Capitalization": "$150.50M",
        "Dividend Yield": None,
        "Company Headquarters Location": "United States of America",
        "Sector": "Technology",
        "Industry": "Software - Application",
        "Optionable": "Yes (Option Chain)",
        "_scrape_date": date(2026, 3, 20),
        "_filename": "batch_001_20260320_143022.xlsx",
        "_file_hash": "abc123",
        "_file_size": 1000,
    }
    defaults.update(overrides)
    return defaults


def test_transform_creates_ticker_bundles(session):
    ingestor = FidelityIngestor(session, inbox_path="/dev/null")
    raw = [_make_raw_record()]
    bundles = ingestor.transform(raw)

    assert len(bundles) == 1
    bundle = bundles[0]
    assert bundle.symbol == "ACME"
    assert isinstance(bundle.issuer, Issuer)
    assert bundle.issuer.legal_name == "Acme Corporation"
    assert bundle.issuer.normalized_name == "acme corporation"


def test_transform_creates_security_and_listing(session):
    ingestor = FidelityIngestor(session, inbox_path="/dev/null")
    raw = [_make_raw_record()]
    bundles = ingestor.transform(raw)
    bundle = bundles[0]

    assert bundle.security.security_type == "common_equity"
    assert bundle.security.is_primary_equity_flag is True

    assert bundle.listing.primary_symbol == "ACME"
    assert bundle.listing.venue_code == "fidelity_screener"


def test_transform_creates_classification_records(session):
    ingestor = FidelityIngestor(session, inbox_path="/dev/null")
    raw = [_make_raw_record()]
    bundles = ingestor.transform(raw)
    bundle = bundles[0]

    assert len(bundle.classifications) == 2  # sector + industry

    sector = next(c for c in bundle.classifications if c.classification_system == "fidelity_sector")
    assert sector.classification_code == "technology"
    assert sector.classification_name == "Technology"

    industry = next(c for c in bundle.classifications if c.classification_system == "fidelity_industry")
    assert industry.classification_code == "software_application"
    assert industry.classification_name == "Software - Application"


def test_transform_creates_listing_status_history(session):
    ingestor = FidelityIngestor(session, inbox_path="/dev/null")
    raw = [_make_raw_record()]
    bundles = ingestor.transform(raw)
    bundle = bundles[0]

    assert bundle.listing_status is not None
    assert bundle.listing_status.listing_status == "active"
    assert bundle.listing_status.effective_start_date == date(2026, 3, 20)


def test_transform_handles_multiple_records(session):
    ingestor = FidelityIngestor(session, inbox_path="/dev/null")
    raw = [
        _make_raw_record(Symbol="ACME", **{"Company Name": "Acme Corp"}),
        _make_raw_record(Symbol="BGFV", **{"Company Name": "Big 5 Sporting"}),
    ]
    bundles = ingestor.transform(raw)
    assert len(bundles) == 2
    assert bundles[0].symbol == "ACME"
    assert bundles[1].symbol == "BGFV"


def test_transform_skips_rows_with_missing_symbol(session):
    ingestor = FidelityIngestor(session, inbox_path="/dev/null")
    raw = [
        _make_raw_record(Symbol="ACME"),
        _make_raw_record(Symbol=""),
        _make_raw_record(Symbol=None),
    ]
    bundles = ingestor.transform(raw)
    assert len(bundles) == 1  # only ACME
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingestion/test_fidelity.py::test_transform_creates_ticker_bundles -v`
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement TickerBundle and transform()**

Add to `app/ingestion/fidelity.py`:

```python
import re as _re_module
from dataclasses import dataclass, field

from app.models.issuer import Issuer
from app.models.security import Security, SecurityIdentifierHistory
from app.models.listing import Listing, ListingStatusHistory
from app.models.classification import IssuerClassificationHistory
from app.models.vendor import VendorSecurityMap


def _normalize_code(text: str) -> str:
    """Normalize free text to a classification code: lowercase, replace non-alnum with underscore."""
    return _re_module.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


@dataclass
class TickerBundle:
    """All domain objects for a single ticker, produced by transform()."""
    symbol: str
    scrape_date: date
    issuer: Issuer
    security: Security
    listing: Listing
    listing_status: ListingStatusHistory
    classifications: list[IssuerClassificationHistory] = field(default_factory=list)
    identifiers: list[SecurityIdentifierHistory] = field(default_factory=list)
    vendor_map: VendorSecurityMap | None = None
```

The `transform()` method on `FidelityIngestor`:

```python
    def transform(self, raw: list[RawRecord]) -> list[TickerBundle]:  # type: ignore[override]
        """Pure transformation: raw dicts → TickerBundle objects. No DB access.

        Each bundle groups all entities for one ticker. Row-level errors are
        logged and skipped — one bad row does not fail the whole batch.
        """
        bundles: list[TickerBundle] = []

        for row in raw:
            try:
                symbol = str(row.get("Symbol") or "").strip()
                company_name = str(row.get("Company Name") or "").strip()
                sector = str(row.get("Sector") or "").strip()
                industry = str(row.get("Industry") or "").strip()
                scrape_date = row["_scrape_date"]

                if not symbol or not company_name:
                    continue

                # Issuer
                issuer = Issuer(
                    legal_name=company_name,
                    normalized_name=company_name.lower(),
                )

                # Security
                security = Security(
                    issuer_id=issuer.issuer_id,
                    security_type="common_equity",
                    is_primary_equity_flag=True,
                    currency="USD",
                )

                # Listing
                listing = Listing(
                    security_id=security.security_id,
                    venue_code="fidelity_screener",
                    primary_symbol=symbol,
                    currency="USD",
                    country="US",
                    listing_status="active",
                    effective_start_date=scrape_date,
                    is_primary_listing_flag=True,
                )

                # ListingStatusHistory
                listing_status = ListingStatusHistory(
                    listing_id=listing.listing_id,
                    listing_status="active",
                    effective_start_date=scrape_date,
                    source="fidelity",
                )

                # Classifications
                classifications = []
                if sector:
                    classifications.append(IssuerClassificationHistory(
                        issuer_id=issuer.issuer_id,
                        classification_system="fidelity_sector",
                        classification_code=_normalize_code(sector),
                        classification_name=sector,
                        effective_start_date=scrape_date,
                        source="fidelity",
                    ))
                if industry:
                    classifications.append(IssuerClassificationHistory(
                        issuer_id=issuer.issuer_id,
                        classification_system="fidelity_industry",
                        classification_code=_normalize_code(industry),
                        classification_name=industry,
                        effective_start_date=scrape_date,
                        source="fidelity",
                    ))

                # SecurityIdentifierHistory — ticker
                identifiers = [SecurityIdentifierHistory(
                    security_id=security.security_id,
                    id_type="ticker",
                    id_value=symbol,
                    effective_start_date=scrape_date,
                    is_primary_flag=True,
                    source="fidelity",
                )]

                # VendorSecurityMap
                vendor_map = VendorSecurityMap(
                    vendor_name="fidelity",
                    vendor_entity_type="stock",
                    vendor_id=symbol,
                    issuer_id=issuer.issuer_id,
                    security_id=security.security_id,
                    listing_id=listing.listing_id,
                    mapping_method="ticker_match",
                    confidence_score=1.0,
                    effective_start_date=scrape_date,
                )

                bundles.append(TickerBundle(
                    symbol=symbol,
                    scrape_date=scrape_date,
                    issuer=issuer,
                    security=security,
                    listing=listing,
                    listing_status=listing_status,
                    classifications=classifications,
                    identifiers=identifiers,
                    vendor_map=vendor_map,
                ))

            except Exception as e:
                # Row-level error: skip this row, continue processing
                import logging
                logging.getLogger(__name__).warning(
                    f"Skipping row {row.get('Symbol', '?')}: {e}"
                )

        return bundles
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingestion/test_fidelity.py -k "transform" -v`
Expected: All 6 transform tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/ingestion/fidelity.py tests/test_ingestion/test_fidelity.py
git commit -m "Implement FidelityIngestor.transform() with TickerBundle grouping"
```

---

## Task 6: FidelityIngestor — _resolve_and_persist()

**Files:**
- Modify: `app/ingestion/fidelity.py`
- Modify: `tests/test_ingestion/test_fidelity.py`

With `TickerBundle`, the resolution logic is clean — no need to re-group records.

- [ ] **Step 1: Write failing test for entity resolution — new ticker creates full chain**

Add to `tests/test_ingestion/test_fidelity.py`:

```python
from app.models.vendor import VendorSecurityMap
from app.models.security import SecurityIdentifierHistory


def test_resolve_and_persist_new_ticker(session, inbox_dir):
    """First time seeing a ticker creates Issuer + Security + Listing + history records."""
    ingestor = FidelityIngestor(session, inbox_path=str(inbox_dir))
    raw = [_make_raw_record()]
    bundles = ingestor.transform(raw)

    created, updated = ingestor._resolve_and_persist(bundles, date(2026, 3, 20))

    assert created == 1  # one new ticker
    assert updated == 0

    # Verify VendorSecurityMap exists
    vsm = session.exec(
        select(VendorSecurityMap).where(
            VendorSecurityMap.vendor_name == "fidelity",
            VendorSecurityMap.vendor_id == "ACME",
        )
    ).first()
    assert vsm is not None
    assert vsm.issuer_id is not None
    assert vsm.security_id is not None
    assert vsm.listing_id is not None
```

- [ ] **Step 2: Write failing test for change detection — same data no new history**

```python
def test_resolve_and_persist_no_change_no_new_history(session, inbox_dir):
    """Re-ingesting identical data should not create new history records."""
    ingestor = FidelityIngestor(session, inbox_path=str(inbox_dir))
    raw = [_make_raw_record()]

    # First ingestion
    bundles1 = ingestor.transform(raw)
    ingestor._resolve_and_persist(bundles1, date(2026, 3, 20))
    session.commit()

    # Second ingestion with same data, different date
    bundles2 = ingestor.transform(raw)
    created, updated = ingestor._resolve_and_persist(bundles2, date(2026, 3, 21))

    assert created == 0  # no new entities
    assert updated == 0  # no changes to detect
```

- [ ] **Step 3: Write failing test for change detection — sector change creates new history**

```python
def test_resolve_and_persist_sector_change_creates_history(session, inbox_dir):
    """When sector changes, old record gets end-dated and new one created."""
    ingestor = FidelityIngestor(session, inbox_path=str(inbox_dir))

    # First ingestion
    raw1 = [_make_raw_record(Sector="Technology")]
    bundles1 = ingestor.transform(raw1)
    ingestor._resolve_and_persist(bundles1, date(2026, 3, 20))
    session.commit()

    # Second ingestion with changed sector
    raw2 = [_make_raw_record(Sector="Health Care")]
    bundles2 = ingestor.transform(raw2)
    _, updated = ingestor._resolve_and_persist(bundles2, date(2026, 3, 25))
    session.commit()

    assert updated > 0

    # Old record should be end-dated
    classifications = session.exec(
        select(IssuerClassificationHistory).where(
            IssuerClassificationHistory.classification_system == "fidelity_sector"
        )
    ).all()

    assert len(classifications) == 2
    old = next(c for c in classifications if c.classification_code == "technology")
    new = next(c for c in classifications if c.classification_code == "health_care")
    assert old.effective_end_date == date(2026, 3, 25)
    assert new.effective_end_date is None
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `pytest tests/test_ingestion/test_fidelity.py -k "resolve" -v`
Expected: FAIL — `_resolve_and_persist` not implemented

- [ ] **Step 5: Implement _resolve_and_persist()**

Add to `FidelityIngestor` in `app/ingestion/fidelity.py`:

```python
    def _resolve_and_persist(self, bundles: list[TickerBundle], scrape_date: date) -> tuple[int, int]:
        """Entity resolution with point-in-time change detection.

        For each TickerBundle:
        - Look up existing VendorSecurityMap by (vendor_name="fidelity", vendor_id=symbol)
        - If not found: persist all new entities
        - If found: compare current history records against new values, append only on change

        Returns (tickers_created, fields_updated).
        """
        created = 0
        updated = 0

        for bundle in bundles:
            existing_map = self.session.exec(
                select(VendorSecurityMap).where(
                    VendorSecurityMap.vendor_name == "fidelity",
                    VendorSecurityMap.vendor_id == bundle.symbol,
                )
            ).first()

            if not existing_map:
                # New ticker — persist everything
                self.session.add(bundle.issuer)
                self.session.add(bundle.security)
                self.session.add(bundle.listing)
                self.session.add(bundle.listing_status)
                for c in bundle.classifications:
                    self.session.add(c)
                for i in bundle.identifiers:
                    self.session.add(i)
                self.session.add(bundle.vendor_map)
                created += 1
            else:
                # Existing ticker — check for changes

                # Name change
                existing_issuer = self.session.get(Issuer, existing_map.issuer_id)
                if existing_issuer and existing_issuer.legal_name != bundle.issuer.legal_name:
                    from app.models.issuer import IssuerNameHistory
                    self.session.add(IssuerNameHistory(
                        issuer_id=existing_map.issuer_id,
                        name=bundle.issuer.legal_name,
                        normalized_name=bundle.issuer.normalized_name,
                        effective_start_date=scrape_date,
                        source="fidelity",
                    ))
                    existing_issuer.legal_name = bundle.issuer.legal_name
                    existing_issuer.normalized_name = bundle.issuer.normalized_name
                    self.session.add(existing_issuer)
                    updated += 1

                # Classification changes
                for new_class in bundle.classifications:
                    current = self.session.exec(
                        select(IssuerClassificationHistory).where(
                            IssuerClassificationHistory.issuer_id == existing_map.issuer_id,
                            IssuerClassificationHistory.classification_system == new_class.classification_system,
                            IssuerClassificationHistory.effective_end_date.is_(None),  # type: ignore
                        )
                    ).first()

                    if current and current.classification_code != new_class.classification_code:
                        current.effective_end_date = scrape_date
                        self.session.add(current)
                        new_class.issuer_id = existing_map.issuer_id
                        self.session.add(new_class)
                        updated += 1

                # Identifier changes
                for new_id in bundle.identifiers:
                    current = self.session.exec(
                        select(SecurityIdentifierHistory).where(
                            SecurityIdentifierHistory.security_id == existing_map.security_id,
                            SecurityIdentifierHistory.id_type == new_id.id_type,
                            SecurityIdentifierHistory.effective_end_date.is_(None),  # type: ignore
                        )
                    ).first()

                    if current and current.id_value != new_id.id_value:
                        current.effective_end_date = scrape_date
                        self.session.add(current)
                        new_id.security_id = existing_map.security_id
                        self.session.add(new_id)
                        updated += 1

        return created, updated
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_ingestion/test_fidelity.py -k "resolve" -v`
Expected: All 3 resolve tests PASS

- [ ] **Step 7: Commit**

```bash
git add app/ingestion/fidelity.py tests/test_ingestion/test_fidelity.py
git commit -m "Implement _resolve_and_persist() with point-in-time change detection"
```

---

## Task 7: FidelityIngestor — run()

**Files:**
- Modify: `app/ingestion/fidelity.py`
- Modify: `tests/test_ingestion/test_fidelity.py`

- [ ] **Step 1: Write failing integration test for full run**

Add to `tests/test_ingestion/test_fidelity.py`:

```python
def test_run_full_pipeline(session, inbox_dir):
    """End-to-end: drop XLSX in inbox, run ingestor, verify DB state."""
    ingestor = FidelityIngestor(session, inbox_path=str(inbox_dir))
    result = ingestor.run()

    assert result.vendor_name == "fidelity"
    assert result.records_fetched == 5
    assert result.errors == 0

    # Verify ingestion_log entry
    log = session.exec(
        select(IngestionLog).where(IngestionLog.vendor_name == "fidelity")
    ).first()
    assert log is not None
    assert log.status == "completed"
    assert log.records_fetched == 5

    # Verify entities created
    issuers = session.exec(select(Issuer)).all()
    # Filter to only our test issuers (conftest creates a test user too)
    fidelity_maps = session.exec(
        select(VendorSecurityMap).where(VendorSecurityMap.vendor_name == "fidelity")
    ).all()
    assert len(fidelity_maps) == 5


def test_run_skips_already_processed(session, inbox_dir):
    """Running twice doesn't re-process the same file."""
    ingestor = FidelityIngestor(session, inbox_path=str(inbox_dir))

    result1 = ingestor.run()
    assert result1.records_fetched == 5

    result2 = ingestor.run()
    assert result2.records_fetched == 0  # no new files
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingestion/test_fidelity.py::test_run_full_pipeline -v`
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement run()**

Replace the `run()` method on `FidelityIngestor`. Uses local variables for log entry state to survive rollback:

```python
    def run(self) -> IngestResult:
        """Execute per-file fetch → transform → resolve pipeline with ingestion_log tracking."""
        from datetime import datetime, timezone

        result = IngestResult(vendor_name=self.vendor_name)
        files_by_name = self.fetch()
        total_fetched = sum(len(rows) for rows in files_by_name.values())
        result.records_fetched = total_fetched

        for filename, rows in files_by_name.items():
            scrape_date = rows[0]["_scrape_date"]
            file_hash = rows[0]["_file_hash"]
            file_size = rows[0]["_file_size"]
            started_at = datetime.now(timezone.utc)

            # Create pending log entry
            log_entry = IngestionLog(
                vendor_name=self.vendor_name,
                filename=filename,
                file_hash=file_hash,
                file_size_bytes=file_size,
                scrape_date=scrape_date,
                status="pending",
                records_fetched=len(rows),
                started_at=started_at,
            )
            self.session.add(log_entry)
            self.session.flush()

            try:
                bundles = self.transform(rows)
                created, updated = self._resolve_and_persist(bundles, scrape_date)

                log_entry.status = "completed"
                log_entry.records_created = created
                log_entry.records_updated = updated
                log_entry.completed_at = datetime.now(timezone.utc)
                log_entry.updated_at = datetime.now(timezone.utc)
                self.session.add(log_entry)
                self.session.commit()

                result.records_loaded += created

            except Exception as e:
                self.session.rollback()
                # Re-create log entry after rollback (original was lost)
                failed_entry = IngestionLog(
                    vendor_name=self.vendor_name,
                    filename=filename,
                    file_hash=file_hash,
                    file_size_bytes=file_size,
                    scrape_date=scrape_date,
                    status="failed",
                    records_fetched=len(rows),
                    error_details=str(e),
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                )
                self.session.add(failed_entry)
                self.session.commit()

                result.errors += 1
                result.error_details.append(f"{filename}: {e}")

        return result
```

- [ ] **Step 4: Run all fidelity tests**

Run: `pytest tests/test_ingestion/test_fidelity.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `pytest tests/ -v`
Expected: All existing tests still PASS

- [ ] **Step 6: Commit**

```bash
git add app/ingestion/fidelity.py tests/test_ingestion/test_fidelity.py
git commit -m "Implement FidelityIngestor.run() with per-file transactions and ingestion_log"
```

---

## Task 8: CLI Integration — Pass inbox_path

**Files:**
- Modify: `app/ingestion/cli.py`

- [ ] **Step 1: Update CLI to pass inbox_path**

Modify `app/ingestion/cli.py` to accept an optional `--inbox` argument:

```python
"""CLI for running data ingestion.

Usage:
    python -m app.ingestion.cli fidelity
    python -m app.ingestion.cli fidelity --inbox /path/to/inbox
"""
import argparse

from sqlmodel import Session

from app.db.session import engine

INGESTORS = {
    "fidelity": "app.ingestion.fidelity.FidelityIngestor",
}


def main():
    parser = argparse.ArgumentParser(description="Run data ingestion")
    parser.add_argument("vendor", choices=INGESTORS.keys(), help="Vendor to ingest from")
    parser.add_argument("--inbox", default=None, help="Override inbox directory path")
    args = parser.parse_args()

    module_path, class_name = INGESTORS[args.vendor].rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    ingestor_class = getattr(module, class_name)

    with Session(engine) as session:
        kwargs = {}
        if args.inbox:
            kwargs["inbox_path"] = args.inbox
        ingestor = ingestor_class(session, **kwargs)
        result = ingestor.run()
        print(f"Ingestion complete: {result}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI help works**

Run: `python -m app.ingestion.cli --help`
Expected: Shows usage with `--inbox` option

- [ ] **Step 3: Commit**

```bash
git add app/ingestion/cli.py
git commit -m "Add --inbox flag to ingestion CLI"
```

---

## Task 9: Port Fidelity Scraper — Auth Module

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/fidelity_scraper/__init__.py`
- Create: `tools/fidelity_scraper/auth.py`

- [ ] **Step 1: Create package structure**

Create `tools/__init__.py` and `tools/fidelity_scraper/__init__.py` as empty files.

- [ ] **Step 2: Port auth.py from batcave**

Create `tools/fidelity_scraper/auth.py`. Faithful port of `batcave/backend/fidelity_automation/context.py`. Deliberate simplification: session length is hardcoded to 24 hours (batcave had a configurable `.fidelity_session_length` file — dropped for simplicity).

```python
"""Fidelity session management — persistent cookies with manual MFA login."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

STORAGE_STATE_FILE = "fidelity_auth.json"
PORTFOLIO_URL = "https://digital.fidelity.com/ftgw/digital/portfolio/summary"
SESSION_HOURS = 24


@asynccontextmanager
async def authenticated_context():
    """Yields an authenticated Playwright browser context.

    Reuses saved session cookies if still valid (< 24 hours old).
    Otherwise opens a visible browser for manual login + MFA.
    """
    storage_path = Path(STORAGE_STATE_FILE)
    needs_auth = True

    if storage_path.exists():
        age = datetime.now() - datetime.fromtimestamp(storage_path.stat().st_mtime)
        if age < timedelta(hours=SESSION_HOURS):
            needs_auth = False

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            downloads_path="tmp_downloads",
        )

        context = await browser.new_context(
            storage_state=(
                STORAGE_STATE_FILE if not needs_auth and storage_path.exists() else None
            ),
            accept_downloads=True,
        )
        page = await context.new_page()

        # Test authentication by going to portfolio
        await page.goto(PORTFOLIO_URL)

        if "login" in page.url:
            print("Authentication required. Please log in manually...")
            await page.wait_for_url(PORTFOLIO_URL, timeout=300000)  # 5 min
            await context.storage_state(path=STORAGE_STATE_FILE)
            print("Authentication successful! Session saved.")

        try:
            await page.close()
            yield context
        finally:
            await browser.close()
```

- [ ] **Step 3: Commit**

```bash
git add tools/__init__.py tools/fidelity_scraper/__init__.py tools/fidelity_scraper/auth.py
git commit -m "Port Fidelity auth module from batcave"
```

---

## Task 10: Port Fidelity Scraper — Scraper Module

**Files:**
- Create: `tools/fidelity_scraper/scraper.py`

- [ ] **Step 1: Port scraper.py from batcave**

Create `tools/fidelity_scraper/scraper.py`. This is a faithful port of `batcave/backend/fidelity_automation/pages/research.py` — the `StockScreenerPage` class with all its methods (~890 lines). Port it verbatim except for these two changes:

**Change 1: Constructor default** (line 10 of batcave):
```python
# batcave:
def __init__(self, context, downloads_dir="downloads"):
# secmaster:
def __init__(self, context, downloads_dir="data/inbox/fidelity"):
```

**Change 2: Destination path in `click_download_results()`** (line 684 of batcave):
```python
# batcave:
destination_path = self.downloads_dir / "microcap-data" / expected_filename
# secmaster:
destination_path = self.downloads_dir / expected_filename
```

And remove the corresponding `destination_path.parent.mkdir(exist_ok=True)` line since `downloads_dir` is created by the CLI.

Keep ALL selectors, timing, pagination logic, error handling, and print statements exactly as-is. The selectors and timing are battle-tested against Fidelity's actual UI.

- [ ] **Step 2: Commit**

```bash
git add tools/fidelity_scraper/scraper.py
git commit -m "Port Fidelity stock screener automation from batcave"
```

---

## Task 11: Port Fidelity Scraper — CLI Entrypoint

**Files:**
- Create: `tools/fidelity_scraper/cli.py`
- Create: `tools/fidelity_scraper/__main__.py`

- [ ] **Step 1: Create CLI entrypoint**

Create `tools/fidelity_scraper/cli.py`:

```python
"""Fidelity scraper CLI — downloads microcap stock data to inbox.

Usage:
    python -m tools.fidelity_scraper.cli
    python -m tools.fidelity_scraper.cli --dry-run
    python -m tools.fidelity_scraper.cli --max-batches 2
"""

import argparse
import asyncio
from pathlib import Path


async def run_scraper(max_batches: int | None = None, dry_run: bool = False):
    from tools.fidelity_scraper.auth import authenticated_context
    from tools.fidelity_scraper.scraper import StockScreenerPage

    inbox_dir = "data/inbox/fidelity"
    Path(inbox_dir).mkdir(parents=True, exist_ok=True)

    async with authenticated_context() as context:
        screener = StockScreenerPage(context, downloads_dir=inbox_dir)

        if dry_run:
            page = await screener.filter_microcap_stocks()
            start, end, total = await screener.parse_results_header(page)
            print(f"Dry run: found {total} microcap stocks")
            print(f"Would download ~{(total + 499) // 500} batches")
            return

        downloads = await screener.download_all_microcap_stocks(
            max_batches=max_batches
        )
        print(f"\nDownloaded {len(downloads)} files to {inbox_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Scrape Fidelity microcap data")
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Limit number of batches (for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Navigate and count results without downloading",
    )
    args = parser.parse_args()

    asyncio.run(run_scraper(max_batches=args.max_batches, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `tools/fidelity_scraper/__main__.py`**

```python
from tools.fidelity_scraper.cli import main

main()
```

This allows `python -m tools.fidelity_scraper` to work.

- [ ] **Step 3: Verify CLI help works**

Run: `python -m tools.fidelity_scraper --help`
Expected: Shows usage with `--max-batches` and `--dry-run` flags

- [ ] **Step 4: Commit**

```bash
git add tools/fidelity_scraper/cli.py tools/fidelity_scraper/__main__.py
git commit -m "Add Fidelity scraper CLI with dry-run and batch limit options"
```

---

## Task 12: Final Integration Test + Verify Full Suite

**Files:**
- Modify: `tests/test_ingestion/test_fidelity.py`

- [ ] **Step 1: Add test for file-level error isolation**

Add to `tests/test_ingestion/test_fidelity.py`:

```python
def test_run_continues_after_bad_file(session, tmp_path):
    """A corrupt file shouldn't prevent processing other files."""
    inbox = tmp_path / "inbox" / "fidelity"
    inbox.mkdir(parents=True)

    # Good file (sorted first alphabetically)
    fixture = Path("tests/fixtures/fidelity/sample_basicfacts.xlsx")
    shutil.copy(fixture, inbox / "microcap_stocks_batch_001_20260320_143022.xlsx")

    # Bad file (not a real XLSX, sorted second)
    bad_file = inbox / "microcap_stocks_batch_002_20260320_143023.xlsx"
    bad_file.write_bytes(b"not a real xlsx file")

    ingestor = FidelityIngestor(session, inbox_path=str(inbox))
    result = ingestor.run()

    # Good file should succeed
    assert result.records_fetched == 5  # from good file only (bad file fails in fetch)

    # At least the good file should have been processed
    logs = session.exec(
        select(IngestionLog).where(IngestionLog.vendor_name == "fidelity")
    ).all()
    completed = [log for log in logs if log.status == "completed"]
    assert len(completed) >= 1
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS (existing + new fidelity tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_ingestion/test_fidelity.py
git commit -m "Add error isolation integration test for Fidelity ingestor"
```

- [ ] **Step 4: Run the ingestor CLI to verify it works end-to-end**

Run: `mise run db:up && mise run migrate && mise run ingest:fidelity`
Expected: "Ingestion complete" with 0 records (empty inbox, but no errors)

- [ ] **Step 5: Final commit — update NEXT_STEPS.md**

Update `NEXT_STEPS.md` to mark the Fidelity Ingestor section as done, noting what's implemented and that the scraper requires manual testing with a real Fidelity account.

```bash
git add NEXT_STEPS.md
git commit -m "Mark Fidelity ingestor as implemented in NEXT_STEPS"
```
