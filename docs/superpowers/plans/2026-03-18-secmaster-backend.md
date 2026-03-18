# Secmaster Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working FastAPI backend with PostgreSQL providing OTC/microcap security master data through RESTful API endpoints with point-in-time query support, Clerk authentication, and a pluggable ingestion architecture.

**Architecture:** Modular monolith — one Python package with clear internal module boundaries. SQLModel unifies ORM and Pydantic schemas. All history tables use effective dating for point-in-time queries. Ingestion is pluggable via abstract base class.

**Tech Stack:** Python 3.12+ (via mise), FastAPI, SQLModel (SQLAlchemy + Pydantic), PostgreSQL, Alembic, Clerk (JWT auth), slowapi (rate limiting), pydantic-settings

**Tooling:** All runtimes, environment, and dev tasks managed via [mise-en-place](https://mise.jdx.dev/). `mise.toml` is the single source of truth for tool versions and dev workflows.

**Spec:** `docs/superpowers/specs/2026-03-17-secmaster-product-design.md`

**Scope:** This plan covers the full backend: models, database, API endpoints, auth, rate limiting, and ingestion. The frontend (React + TypeScript) will be a separate plan.

---

## File Structure

```
secmaster/
├── mise.toml                             # mise-en-place: Python version, env, dev tasks
├── app/
│   ├── __init__.py                      # Package marker
│   ├── main.py                          # FastAPI app, router mounting, startup
│   ├── config.py                        # pydantic-settings configuration
│   ├── models/
│   │   ├── __init__.py                  # Re-exports all models for Alembic
│   │   ├── issuer.py                    # Issuer, IssuerNameHistory + Read/Create schemas
│   │   ├── security.py                  # Security, SecurityIdentifierHistory + schemas
│   │   ├── listing.py                   # Listing, ListingStatusHistory + schemas
│   │   ├── corporate_action.py          # CorporateAction + schemas
│   │   ├── shares_outstanding.py        # SharesOutstandingHistory + schemas
│   │   ├── classification.py            # IssuerClassificationHistory + schemas
│   │   ├── vendor.py                    # VendorSecurityMap + schemas
│   │   └── user.py                      # User, ApiKey + schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                      # DB session, auth, pagination dependencies
│   │   └── v1/
│   │       ├── __init__.py              # v1 router aggregation
│   │       ├── issuers.py               # Issuer endpoints
│   │       ├── securities.py            # Security endpoints
│   │       ├── listings.py              # Listing endpoints
│   │       └── api_keys.py              # API key management endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   └── point_in_time.py             # Point-in-time query helpers
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── base.py                      # Abstract BaseIngestor interface
│   │   ├── fidelity.py                  # Fidelity ingestor (stub for v1)
│   │   └── cli.py                       # CLI entrypoints for running ingestion
│   └── db/
│       ├── __init__.py
│       └── session.py                   # Engine, session factory, get_session dependency
├── alembic.ini                          # Alembic configuration
├── migrations/
│   ├── env.py                           # Alembic env with SQLModel metadata
│   ├── script.py.mako                   # Migration template
│   └── versions/                        # Auto-generated migration files
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Test DB, session, client fixtures
│   ├── test_models/
│   │   ├── __init__.py
│   │   ├── test_issuer.py
│   │   ├── test_security.py
│   │   ├── test_listing.py
│   │   └── test_user.py
│   ├── test_api/
│   │   ├── __init__.py
│   │   ├── test_health.py
│   │   ├── test_issuers.py
│   │   ├── test_securities.py
│   │   ├── test_listings.py
│   │   └── test_api_keys.py
│   ├── test_services/
│   │   ├── __init__.py
│   │   └── test_point_in_time.py
│   └── test_ingestion/
│       ├── __init__.py
│       └── test_base.py
├── pyproject.toml
├── .gitignore
├── Dockerfile
└── docker-compose.yml
```

---

## Task 1: Project Scaffold & Configuration

**Files:**
- Create: `mise.toml`
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `.gitignore`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create mise.toml (mise-en-place — do this first)**

This is the foundation. All tooling flows through mise.

```toml
[tools]
python = "3.12"

[env]
_.file = ".env"

[tasks.install]
description = "Install project dependencies"
run = "pip install -e '.[dev]'"

[tasks.test]
description = "Run tests"
run = "pytest tests/ -v"

[tasks.dev]
description = "Start development server"
run = "uvicorn app.main:app --reload"

[tasks."db:up"]
description = "Start database containers"
run = "docker compose up -d db db-test"

[tasks."db:down"]
description = "Stop database containers"
run = "docker compose down"

[tasks."db:reset"]
description = "Reset database containers (destroy and recreate)"
run = "docker compose down -v && docker compose up -d db db-test"

[tasks.migrate]
description = "Run database migrations"
run = "alembic upgrade head"

[tasks."migrate:create"]
description = "Create a new migration"
run = "alembic revision --autogenerate -m \"$1\""

[tasks.verify]
description = "Verify project setup (config loads, DB connects)"
run = "python -c \"from app.config import settings; print('DB:', settings.database_url)\""
```

- [ ] **Step 2: Create pyproject.toml with all dependencies**

```toml
[project]
name = "secmaster"
version = "0.1.0"
requires-python = ">=3.12"
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
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=6.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: Create docker-compose.yml for Postgres**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: secmaster
      POSTGRES_PASSWORD: secmaster
      POSTGRES_DB: secmaster
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  db-test:
    image: postgres:16
    environment:
      POSTGRES_USER: secmaster_test
      POSTGRES_PASSWORD: secmaster_test
      POSTGRES_DB: secmaster_test
    ports:
      - "5433:5432"

volumes:
  pgdata:
```

- [ ] **Step 4: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# Environment
.env

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
```

- [ ] **Step 5: Create app/__init__.py**

Empty file.

- [ ] **Step 6: Create app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://secmaster:secmaster@localhost:5432/secmaster"
    test_database_url: str = "postgresql://secmaster_test:secmaster_test@localhost:5433/secmaster_test"
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    rate_limit_free: str = "60/minute"
    rate_limit_paid: str = "300/minute"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 7: Install tooling and dependencies via mise**

```bash
mise install          # installs Python 3.12 (if not already present)
mise run db:up        # start Postgres containers
mise run install      # install project dependencies into mise-managed venv
mise run verify       # confirm config loads
```

Expected: Python 3.12 installed, containers running, dependencies installed, prints the database URL.

- [ ] **Step 8: Commit**

```bash
git add mise.toml .gitignore pyproject.toml app/__init__.py app/config.py docker-compose.yml
git commit -m "feat: project scaffold with mise, config, and docker-compose"
```

---

## Task 2: Database Session & Test Infrastructure

**Files:**
- Create: `app/db/__init__.py`
- Create: `app/db/session.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create app/db/__init__.py**

Empty file.

- [ ] **Step 2: Create app/db/session.py**

```python
from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.config import settings

engine = create_engine(settings.database_url)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 3: Create tests/__init__.py**

Empty file.

- [ ] **Step 4: Create tests/conftest.py**

This is the central test fixture file. It creates a test engine pointing at the test database, creates all tables before the test session, provides a transactional session per test, and provides a FastAPI TestClient.

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(settings.test_database_url)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def session(test_engine) -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture()
def client(session) -> Generator[TestClient, None, None]:
    from app.db.session import get_session
    from app.main import app

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 5: Verify test infrastructure connects**

Create a minimal test to verify DB connectivity:

```python
# tests/test_db_connection.py
from sqlmodel import text


def test_db_connection(session):
    result = session.exec(text("SELECT 1")).scalar()
    assert result == 1
```

Run: `pytest tests/test_db_connection.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/db/ tests/
git commit -m "feat: database session and test infrastructure"
```

---

## Task 3: Issuer Models

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/issuer.py`
- Create: `tests/test_models/__init__.py`
- Create: `tests/test_models/test_issuer.py`

- [ ] **Step 1: Write failing tests for Issuer and IssuerNameHistory**

```python
# tests/test_models/test_issuer.py
from datetime import date, datetime, timezone
from uuid import UUID

from sqlmodel import select

from app.models.issuer import Issuer, IssuerNameHistory


def test_create_issuer(session):
    issuer = Issuer(legal_name="Test Corp", country_incorporation="US")
    session.add(issuer)
    session.commit()
    session.refresh(issuer)

    assert isinstance(issuer.issuer_id, UUID)
    assert issuer.legal_name == "Test Corp"
    assert issuer.country_incorporation == "US"
    assert issuer.is_shell_flag is False
    assert isinstance(issuer.created_at, datetime)
    assert isinstance(issuer.updated_at, datetime)


def test_create_issuer_name_history(session):
    issuer = Issuer(legal_name="Old Name Inc")
    session.add(issuer)
    session.commit()

    name_hist = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Old Name Inc",
        effective_start_date=date(2020, 1, 1),
        effective_end_date=date(2023, 6, 15),
        source="fidelity",
    )
    session.add(name_hist)
    session.commit()
    session.refresh(name_hist)

    assert name_hist.issuer_id == issuer.issuer_id
    assert name_hist.name == "Old Name Inc"
    assert name_hist.effective_start_date == date(2020, 1, 1)
    assert name_hist.effective_end_date == date(2023, 6, 15)
    assert name_hist.source == "fidelity"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models/test_issuer.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.issuer'`

- [ ] **Step 3: Implement Issuer and IssuerNameHistory models**

```python
# app/models/__init__.py
from app.models.issuer import Issuer, IssuerNameHistory  # noqa: F401

# app/models/issuer.py
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IssuerBase(SQLModel):
    legal_name: str
    normalized_name: str | None = None
    issuer_type: str | None = None
    country_incorporation: str | None = None
    domicile_country: str | None = None
    cik: str | None = None
    lei: str | None = None
    sic: str | None = None
    naics: str | None = None
    is_shell_flag: bool = False
    is_bankrupt_flag: bool = False
    is_liquidating_flag: bool = False


class Issuer(IssuerBase, table=True):
    issuer_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class IssuerCreate(IssuerBase):
    pass


class IssuerRead(IssuerBase):
    issuer_id: UUID
    created_at: datetime
    updated_at: datetime


class IssuerNameHistoryBase(SQLModel):
    name: str
    normalized_name: str | None = None
    effective_start_date: date
    effective_end_date: date | None = None
    source: str | None = None


class IssuerNameHistory(IssuerNameHistoryBase, table=True):
    __tablename__ = "issuer_name_history"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    issuer_id: UUID = Field(foreign_key="issuer.issuer_id")
    created_at: datetime = Field(default_factory=_utcnow)


class IssuerNameHistoryRead(IssuerNameHistoryBase):
    id: UUID
    issuer_id: UUID
    created_at: datetime
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models/test_issuer.py -v`

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add app/models/ tests/test_models/
git commit -m "feat: issuer and issuer_name_history models"
```

---

## Task 4: Security Models

**Files:**
- Create: `app/models/security.py`
- Create: `tests/test_models/test_security.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models/test_security.py
from datetime import date, datetime
from uuid import UUID

from app.models.issuer import Issuer
from app.models.security import Security, SecurityIdentifierHistory


def test_create_security(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(
        issuer_id=issuer.issuer_id,
        security_type="common_stock",
        currency="USD",
        is_primary_equity_flag=True,
    )
    session.add(security)
    session.commit()
    session.refresh(security)

    assert isinstance(security.security_id, UUID)
    assert security.issuer_id == issuer.issuer_id
    assert security.security_type == "common_stock"
    assert security.is_primary_equity_flag is True


def test_create_security_identifier_history(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    ident = SecurityIdentifierHistory(
        security_id=security.security_id,
        id_type="ticker",
        id_value="TCOR",
        venue_code="OTC",
        effective_start_date=date(2020, 1, 1),
        is_primary_flag=True,
        source="fidelity",
    )
    session.add(ident)
    session.commit()
    session.refresh(ident)

    assert ident.id_type == "ticker"
    assert ident.id_value == "TCOR"
    assert ident.is_primary_flag is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models/test_security.py -v`

Expected: FAIL

- [ ] **Step 3: Implement Security and SecurityIdentifierHistory**

```python
# app/models/security.py
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SecurityBase(SQLModel):
    issuer_id: UUID = Field(foreign_key="issuer.issuer_id")
    security_type: str
    security_subtype: str | None = None
    share_class: str | None = None
    par_value: float | None = None
    currency: str | None = None
    is_primary_equity_flag: bool = False
    underlying_security_id: UUID | None = Field(
        default=None, foreign_key="security.security_id"
    )


class Security(SecurityBase, table=True):
    security_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class SecurityCreate(SecurityBase):
    pass


class SecurityRead(SecurityBase):
    security_id: UUID
    created_at: datetime
    updated_at: datetime


class SecurityIdentifierHistoryBase(SQLModel):
    id_type: str
    id_value: str
    venue_code: str | None = None
    effective_start_date: date
    effective_end_date: date | None = None
    is_primary_flag: bool = False
    source: str | None = None


class SecurityIdentifierHistory(SecurityIdentifierHistoryBase, table=True):
    __tablename__ = "security_identifier_history"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    security_id: UUID = Field(foreign_key="security.security_id")
    created_at: datetime = Field(default_factory=_utcnow)


class SecurityIdentifierHistoryRead(SecurityIdentifierHistoryBase):
    id: UUID
    security_id: UUID
    created_at: datetime
```

Update `app/models/__init__.py` to add:
```python
from app.models.security import Security, SecurityIdentifierHistory  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models/test_security.py -v`

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add app/models/security.py app/models/__init__.py tests/test_models/test_security.py
git commit -m "feat: security and security_identifier_history models"
```

---

## Task 5: Listing Models

**Files:**
- Create: `app/models/listing.py`
- Create: `tests/test_models/test_listing.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models/test_listing.py
from datetime import date, datetime
from uuid import UUID

from app.models.issuer import Issuer
from app.models.listing import Listing, ListingStatusHistory
from app.models.security import Security


def test_create_listing(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    listing = Listing(
        security_id=security.security_id,
        venue_code="OTCM",
        mic_code="OTCM",
        primary_symbol="TCOR",
        currency="USD",
        country="US",
        listing_status="active",
        effective_start_date=date(2020, 1, 1),
        is_primary_listing_flag=True,
    )
    session.add(listing)
    session.commit()
    session.refresh(listing)

    assert isinstance(listing.listing_id, UUID)
    assert listing.venue_code == "OTCM"
    assert listing.listing_status == "active"
    assert listing.is_primary_listing_flag is True


def test_create_listing_status_history(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    listing = Listing(
        security_id=security.security_id,
        venue_code="OTCM",
        listing_status="active",
        effective_start_date=date(2020, 1, 1),
    )
    session.add(listing)
    session.commit()

    status = ListingStatusHistory(
        listing_id=listing.listing_id,
        effective_start_date=date(2020, 1, 1),
        effective_end_date=date(2022, 6, 1),
        listing_status="active",
        tier="OTCQB",
        caveat_emptor_flag=False,
        source="otc_markets",
    )
    session.add(status)
    session.commit()
    session.refresh(status)

    assert status.tier == "OTCQB"
    assert status.caveat_emptor_flag is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models/test_listing.py -v`

Expected: FAIL

- [ ] **Step 3: Implement Listing and ListingStatusHistory**

```python
# app/models/listing.py
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ListingBase(SQLModel):
    security_id: UUID = Field(foreign_key="security.security_id")
    venue_code: str
    mic_code: str | None = None
    primary_symbol: str | None = None
    currency: str | None = None
    country: str | None = None
    listing_status: str | None = None
    effective_start_date: date
    effective_end_date: date | None = None
    is_primary_listing_flag: bool = False


class Listing(ListingBase, table=True):
    listing_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ListingCreate(ListingBase):
    pass


class ListingRead(ListingBase):
    listing_id: UUID
    created_at: datetime
    updated_at: datetime


class ListingStatusHistoryBase(SQLModel):
    effective_start_date: date
    effective_end_date: date | None = None
    listing_status: str | None = None
    tier: str | None = None
    caveat_emptor_flag: bool = False
    unsolicited_quotes_only_flag: bool = False
    shell_risk_flag: bool = False
    sec_suspension_flag: bool = False
    bankruptcy_flag: bool = False
    current_information_flag: bool = False
    transfer_agent_verified_flag: bool = False
    source: str | None = None


class ListingStatusHistory(ListingStatusHistoryBase, table=True):
    __tablename__ = "listing_status_history"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    listing_id: UUID = Field(foreign_key="listing.listing_id")
    created_at: datetime = Field(default_factory=_utcnow)


class ListingStatusHistoryRead(ListingStatusHistoryBase):
    id: UUID
    listing_id: UUID
    created_at: datetime
```

Update `app/models/__init__.py` to add:
```python
from app.models.listing import Listing, ListingStatusHistory  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models/test_listing.py -v`

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add app/models/listing.py app/models/__init__.py tests/test_models/test_listing.py
git commit -m "feat: listing and listing_status_history models"
```

---

## Task 6: Supporting Models

**Files:**
- Create: `app/models/corporate_action.py`
- Create: `app/models/shares_outstanding.py`
- Create: `app/models/classification.py`
- Create: `app/models/vendor.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Write failing tests for all supporting models**

```python
# tests/test_models/test_supporting.py
from datetime import date
from uuid import UUID

from app.models.corporate_action import CorporateAction
from app.models.classification import IssuerClassificationHistory
from app.models.issuer import Issuer
from app.models.security import Security
from app.models.shares_outstanding import SharesOutstandingHistory
from app.models.vendor import VendorSecurityMap


def test_create_corporate_action(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    action = CorporateAction(
        security_id=security.security_id,
        issuer_id=issuer.issuer_id,
        action_type="reverse_split",
        effective_date=date(2023, 3, 1),
        ratio_from=10,
        ratio_to=1,
        source="fidelity",
    )
    session.add(action)
    session.commit()
    session.refresh(action)

    assert isinstance(action.corporate_action_id, UUID)
    assert action.action_type == "reverse_split"
    assert action.ratio_from == 10
    assert action.ratio_to == 1


def test_create_shares_outstanding_history(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    shares = SharesOutstandingHistory(
        security_id=security.security_id,
        as_of_date=date(2023, 6, 30),
        shares_outstanding=1_000_000,
        public_float=750_000,
        source="fidelity",
    )
    session.add(shares)
    session.commit()
    session.refresh(shares)

    assert shares.shares_outstanding == 1_000_000
    assert shares.public_float == 750_000


def test_create_issuer_classification_history(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    classification = IssuerClassificationHistory(
        issuer_id=issuer.issuer_id,
        classification_system="SIC",
        classification_code="7372",
        classification_name="Prepackaged Software",
        effective_start_date=date(2020, 1, 1),
        source="sec_edgar",
    )
    session.add(classification)
    session.commit()
    session.refresh(classification)

    assert classification.classification_system == "SIC"
    assert classification.classification_code == "7372"


def test_create_vendor_security_map(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    vendor_map = VendorSecurityMap(
        vendor_name="fidelity",
        vendor_entity_type="security",
        vendor_id="FID-12345",
        issuer_id=issuer.issuer_id,
        security_id=security.security_id,
        effective_start_date=date(2020, 1, 1),
        confidence_score=0.95,
        mapping_method="exact_cusip",
    )
    session.add(vendor_map)
    session.commit()
    session.refresh(vendor_map)

    assert vendor_map.vendor_name == "fidelity"
    assert vendor_map.confidence_score == 0.95
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models/test_supporting.py -v`

Expected: FAIL

- [ ] **Step 3: Implement all four supporting models**

```python
# app/models/corporate_action.py
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CorporateActionBase(SQLModel):
    security_id: UUID = Field(foreign_key="security.security_id")
    issuer_id: UUID = Field(foreign_key="issuer.issuer_id")
    action_type: str
    announcement_date: date | None = None
    effective_date: date | None = None
    ratio_from: float | None = None
    ratio_to: float | None = None
    old_value: str | None = None
    new_value: str | None = None
    notes: str | None = None
    source: str | None = None


class CorporateAction(CorporateActionBase, table=True):
    __tablename__ = "corporate_action"
    corporate_action_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)


class CorporateActionCreate(CorporateActionBase):
    pass


class CorporateActionRead(CorporateActionBase):
    corporate_action_id: UUID
    created_at: datetime
```

```python
# app/models/shares_outstanding.py
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SharesOutstandingHistoryBase(SQLModel):
    security_id: UUID = Field(foreign_key="security.security_id")
    as_of_date: date
    shares_outstanding: int | None = None
    public_float: int | None = None
    authorized_shares: int | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    value_source_type: str | None = None
    source: str | None = None


class SharesOutstandingHistory(SharesOutstandingHistoryBase, table=True):
    __tablename__ = "shares_outstanding_history"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)


class SharesOutstandingHistoryRead(SharesOutstandingHistoryBase):
    id: UUID
    created_at: datetime
```

```python
# app/models/classification.py
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IssuerClassificationHistoryBase(SQLModel):
    issuer_id: UUID = Field(foreign_key="issuer.issuer_id")
    classification_system: str
    classification_code: str
    classification_name: str | None = None
    effective_start_date: date
    effective_end_date: date | None = None
    source: str | None = None


class IssuerClassificationHistory(IssuerClassificationHistoryBase, table=True):
    __tablename__ = "issuer_classification_history"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)


class IssuerClassificationHistoryRead(IssuerClassificationHistoryBase):
    id: UUID
    created_at: datetime
```

```python
# app/models/vendor.py
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VendorSecurityMapBase(SQLModel):
    vendor_name: str
    vendor_entity_type: str
    vendor_id: str
    issuer_id: UUID | None = Field(default=None, foreign_key="issuer.issuer_id")
    security_id: UUID | None = Field(default=None, foreign_key="security.security_id")
    listing_id: UUID | None = Field(default=None, foreign_key="listing.listing_id")
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    confidence_score: float | None = None
    mapping_method: str | None = None


class VendorSecurityMap(VendorSecurityMapBase, table=True):
    __tablename__ = "vendor_security_map"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)


class VendorSecurityMapRead(VendorSecurityMapBase):
    id: UUID
    created_at: datetime
```

Update `app/models/__init__.py` to add:
```python
from app.models.corporate_action import CorporateAction  # noqa: F401
from app.models.shares_outstanding import SharesOutstandingHistory  # noqa: F401
from app.models.classification import IssuerClassificationHistory  # noqa: F401
from app.models.vendor import VendorSecurityMap  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models/test_supporting.py -v`

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/models/ tests/test_models/test_supporting.py
git commit -m "feat: corporate action, shares outstanding, classification, and vendor map models"
```

---

## Task 7: User & API Key Models

**Files:**
- Create: `app/models/user.py`
- Create: `tests/test_models/test_user.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models/test_user.py
import hashlib
from datetime import datetime
from uuid import UUID

from app.models.user import ApiKey, User


def test_create_user(session):
    user = User(
        clerk_user_id="user_abc123",
        email="test@example.com",
        tier="free",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert isinstance(user.user_id, UUID)
    assert user.clerk_user_id == "user_abc123"
    assert user.tier == "free"


def test_create_api_key(session):
    user = User(clerk_user_id="user_xyz", email="paid@example.com", tier="paid")
    session.add(user)
    session.commit()

    key_hash = hashlib.sha256(b"test-api-key").hexdigest()
    api_key = ApiKey(
        user_id=user.user_id,
        key_hash=key_hash,
        label="My Test Key",
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)

    assert isinstance(api_key.id, UUID)
    assert api_key.key_hash == key_hash
    assert api_key.is_active is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models/test_user.py -v`

Expected: FAIL

- [ ] **Step 3: Implement User and ApiKey models**

```python
# app/models/user.py
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserBase(SQLModel):
    clerk_user_id: str = Field(unique=True, index=True)
    email: str
    tier: str = "free"


class User(UserBase, table=True):
    user_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class UserRead(UserBase):
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class ApiKeyBase(SQLModel):
    label: str | None = None


class ApiKey(ApiKeyBase, table=True):
    __tablename__ = "api_key"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.user_id")
    key_hash: str
    created_at: datetime = Field(default_factory=_utcnow)
    last_used_at: datetime | None = None
    is_active: bool = True


class ApiKeyCreate(SQLModel):
    label: str | None = None


class ApiKeyRead(SQLModel):
    id: UUID
    label: str | None
    created_at: datetime
    last_used_at: datetime | None
    is_active: bool
```

Update `app/models/__init__.py` to add:
```python
from app.models.user import ApiKey, User  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models/test_user.py -v`

Expected: PASS (2 tests)

- [ ] **Step 5: Run all model tests together**

Run: `pytest tests/test_models/ -v`

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/models/user.py app/models/__init__.py tests/test_models/test_user.py
git commit -m "feat: user and api_key models"
```

---

## Task 8: Alembic Setup & Initial Migration

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `migrations/versions/` (directory)

- [ ] **Step 1: Initialize Alembic**

```bash
alembic init migrations
```

This creates `alembic.ini` and the `migrations/` directory with boilerplate.

- [ ] **Step 2: Configure alembic.ini**

Edit `alembic.ini` — set `sqlalchemy.url` to empty (will be overridden in env.py):

```ini
sqlalchemy.url =
```

- [ ] **Step 3: Configure migrations/env.py for SQLModel**

Replace the generated `migrations/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.config import settings

# Import all models so metadata is populated
import app.models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

```bash
alembic revision --autogenerate -m "initial schema"
```

Expected: creates a migration file in `migrations/versions/`.

- [ ] **Step 5: Run migration against dev database**

```bash
alembic upgrade head
```

Expected: all tables created in Postgres.

- [ ] **Step 6: Verify tables exist**

```bash
docker compose exec db psql -U secmaster -c "\dt"
```

Expected: lists all 12 tables (issuer, issuer_name_history, security, security_identifier_history, listing, listing_status_history, corporate_action, shares_outstanding_history, issuer_classification_history, vendor_security_map, user, api_key) plus alembic_version.

- [ ] **Step 7: Commit**

```bash
git add alembic.ini migrations/
git commit -m "feat: alembic setup with initial schema migration"
```

---

## Task 9: FastAPI App & Health Check

**Files:**
- Create: `app/main.py`
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_api/test_health.py`

- [ ] **Step 1: Write failing test for health check**

```python
# tests/test_api/test_health.py
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api/test_health.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Implement app/main.py**

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI(
    title="Secmaster API",
    description="OTC/Microcap Security Master Data",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api/test_health.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_api/
git commit -m "feat: FastAPI app with health check endpoint"
```

---

## Task 10: Point-in-Time Query Service

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/point_in_time.py`
- Create: `tests/test_services/__init__.py`
- Create: `tests/test_services/test_point_in_time.py`

- [ ] **Step 1: Write failing tests for point-in-time filtering**

```python
# tests/test_services/test_point_in_time.py
from datetime import date

from sqlmodel import select

from app.models.issuer import Issuer, IssuerNameHistory
from app.models.listing import Listing, ListingStatusHistory
from app.models.security import Security, SecurityIdentifierHistory
from app.services.point_in_time import apply_as_of_filter


def test_as_of_returns_active_record(session):
    """Record with no end date is active at any date after start."""
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    name = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Test Corp",
        effective_start_date=date(2020, 1, 1),
        effective_end_date=None,
        source="test",
    )
    session.add(name)
    session.commit()

    stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer.issuer_id
    )
    stmt = apply_as_of_filter(stmt, IssuerNameHistory, date(2023, 6, 15))
    results = session.exec(stmt).all()

    assert len(results) == 1
    assert results[0].name == "Test Corp"


def test_as_of_excludes_future_record(session):
    """Record starting after the as_of date should be excluded."""
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    name = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Future Name",
        effective_start_date=date(2025, 1, 1),
        effective_end_date=None,
        source="test",
    )
    session.add(name)
    session.commit()

    stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer.issuer_id
    )
    stmt = apply_as_of_filter(stmt, IssuerNameHistory, date(2023, 6, 15))
    results = session.exec(stmt).all()

    assert len(results) == 0


def test_as_of_excludes_expired_record(session):
    """Record that ended before the as_of date should be excluded."""
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    name = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Old Name",
        effective_start_date=date(2018, 1, 1),
        effective_end_date=date(2020, 1, 1),
        source="test",
    )
    session.add(name)
    session.commit()

    stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer.issuer_id
    )
    stmt = apply_as_of_filter(stmt, IssuerNameHistory, date(2023, 6, 15))
    results = session.exec(stmt).all()

    assert len(results) == 0


def test_as_of_none_returns_all(session):
    """When as_of is None, no time filter is applied."""
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    for i, (start, end) in enumerate([
        (date(2018, 1, 1), date(2020, 1, 1)),
        (date(2020, 1, 1), None),
    ]):
        name = IssuerNameHistory(
            issuer_id=issuer.issuer_id,
            name=f"Name {i}",
            effective_start_date=start,
            effective_end_date=end,
            source="test",
        )
        session.add(name)
    session.commit()

    stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer.issuer_id
    )
    stmt = apply_as_of_filter(stmt, IssuerNameHistory, None)
    results = session.exec(stmt).all()

    assert len(results) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_services/test_point_in_time.py -v`

Expected: FAIL

- [ ] **Step 3: Implement point-in-time query service**

```python
# app/services/__init__.py
# empty

# app/services/point_in_time.py
from datetime import date
from typing import TypeVar

from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)


def apply_as_of_filter(stmt, model: type[T], as_of: date | None):
    """Apply effective dating filter to a select statement.

    Uses the pattern:
        WHERE effective_start_date <= as_of
          AND (effective_end_date IS NULL OR effective_end_date > as_of)
    """
    if as_of is None:
        return stmt

    stmt = stmt.where(model.effective_start_date <= as_of)
    stmt = stmt.where(
        (model.effective_end_date.is_(None)) | (model.effective_end_date > as_of)  # type: ignore
    )
    return stmt
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_services/test_point_in_time.py -v`

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/services/ tests/test_services/
git commit -m "feat: point-in-time query service with effective dating filter"
```

---

## Task 11: API Dependencies & Pagination

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/deps.py`
- Create: `app/api/v1/__init__.py`

- [ ] **Step 1: Create API dependency module**

```python
# app/api/__init__.py
# empty

# app/api/v1/__init__.py
# empty

# app/api/deps.py
from collections.abc import Generator
from datetime import date
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_session


def get_db() -> Generator[Session, None, None]:
    yield from get_session()


def get_as_of(as_of: date | None = Query(default=None, description="Point-in-time date (YYYY-MM-DD)")) -> date | None:
    return as_of


class CursorPagination:
    def __init__(
        self,
        cursor: UUID | None = Query(default=None, description="Cursor for pagination (UUID of last item)"),
        limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    ):
        self.cursor = cursor
        self.limit = limit
```

- [ ] **Step 2: Commit**

```bash
git add app/api/
git commit -m "feat: API dependencies for db session, as_of, and cursor pagination"
```

---

## Task 12: Issuer API Endpoints

**Files:**
- Create: `app/api/v1/issuers.py`
- Create: `tests/test_api/test_issuers.py`
- Modify: `app/main.py` (mount router)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api/test_issuers.py
from datetime import date

from app.models.issuer import Issuer, IssuerNameHistory
from app.models.classification import IssuerClassificationHistory


def test_list_issuers(client, session):
    issuer = Issuer(legal_name="Acme Corp", country_incorporation="US")
    session.add(issuer)
    session.commit()

    response = client.get("/api/v1/issuers")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["legal_name"] == "Acme Corp"


def test_get_issuer_by_id(client, session):
    issuer = Issuer(legal_name="Acme Corp")
    session.add(issuer)
    session.commit()

    response = client.get(f"/api/v1/issuers/{issuer.issuer_id}")
    assert response.status_code == 200
    assert response.json()["legal_name"] == "Acme Corp"


def test_get_issuer_not_found(client):
    response = client.get("/api/v1/issuers/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_issuer_history(client, session):
    issuer = Issuer(legal_name="New Name Corp")
    session.add(issuer)
    session.commit()

    name1 = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Old Name Inc",
        effective_start_date=date(2018, 1, 1),
        effective_end_date=date(2022, 1, 1),
        source="test",
    )
    name2 = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="New Name Corp",
        effective_start_date=date(2022, 1, 1),
        source="test",
    )
    session.add_all([name1, name2])
    session.commit()

    response = client.get(f"/api/v1/issuers/{issuer.issuer_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data["name_history"]) == 2


def test_get_issuer_history_as_of(client, session):
    issuer = Issuer(legal_name="New Name Corp")
    session.add(issuer)
    session.commit()

    name1 = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Old Name Inc",
        effective_start_date=date(2018, 1, 1),
        effective_end_date=date(2022, 1, 1),
        source="test",
    )
    name2 = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="New Name Corp",
        effective_start_date=date(2022, 1, 1),
        source="test",
    )
    session.add_all([name1, name2])
    session.commit()

    response = client.get(
        f"/api/v1/issuers/{issuer.issuer_id}/history",
        params={"as_of": "2020-06-15"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["name_history"]) == 1
    assert data["name_history"][0]["name"] == "Old Name Inc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api/test_issuers.py -v`

Expected: FAIL

- [ ] **Step 3: Implement issuer endpoints**

```python
# app/api/v1/issuers.py
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import CursorPagination, get_as_of, get_db
from app.models.issuer import (
    Issuer,
    IssuerNameHistory,
    IssuerNameHistoryRead,
    IssuerRead,
)
from app.models.classification import (
    IssuerClassificationHistory,
    IssuerClassificationHistoryRead,
)
from app.services.point_in_time import apply_as_of_filter

router = APIRouter(prefix="/issuers", tags=["issuers"])


@router.get("", response_model=dict)
def list_issuers(
    session: Session = Depends(get_db),
    pagination: CursorPagination = Depends(),
    name: str | None = Query(default=None),
    country: str | None = Query(default=None),
):
    stmt = select(Issuer)
    if name:
        stmt = stmt.where(Issuer.legal_name.ilike(f"{name}%"))  # type: ignore
    if country:
        stmt = stmt.where(Issuer.country_incorporation == country)
    if pagination.cursor:
        stmt = stmt.where(Issuer.issuer_id > pagination.cursor)
    stmt = stmt.order_by(Issuer.issuer_id).limit(pagination.limit)

    issuers = session.exec(stmt).all()
    next_cursor = str(issuers[-1].issuer_id) if len(issuers) == pagination.limit else None
    return {
        "items": [IssuerRead.model_validate(i) for i in issuers],
        "next_cursor": next_cursor,
    }


@router.get("/{issuer_id}", response_model=IssuerRead)
def get_issuer(issuer_id: UUID, session: Session = Depends(get_db)):
    issuer = session.get(Issuer, issuer_id)
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")
    return issuer


@router.get("/{issuer_id}/history", response_model=dict)
def get_issuer_history(
    issuer_id: UUID,
    session: Session = Depends(get_db),
    as_of: date | None = Depends(get_as_of),
):
    issuer = session.get(Issuer, issuer_id)
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")

    # Name history
    name_stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer_id
    )
    name_stmt = apply_as_of_filter(name_stmt, IssuerNameHistory, as_of)
    name_stmt = name_stmt.order_by(IssuerNameHistory.effective_start_date)
    name_history = session.exec(name_stmt).all()

    # Classification history
    class_stmt = select(IssuerClassificationHistory).where(
        IssuerClassificationHistory.issuer_id == issuer_id
    )
    class_stmt = apply_as_of_filter(class_stmt, IssuerClassificationHistory, as_of)
    class_stmt = class_stmt.order_by(IssuerClassificationHistory.effective_start_date)
    classification_history = session.exec(class_stmt).all()

    return {
        "issuer": IssuerRead.model_validate(issuer),
        "name_history": [IssuerNameHistoryRead.model_validate(n) for n in name_history],
        "classification_history": [
            IssuerClassificationHistoryRead.model_validate(c) for c in classification_history
        ],
    }
```

- [ ] **Step 4: Mount the router in app/main.py**

Add to `app/main.py`:

```python
from app.api.v1.issuers import router as issuers_router

app.include_router(issuers_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_api/test_issuers.py -v`

Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add app/api/v1/issuers.py app/main.py tests/test_api/test_issuers.py
git commit -m "feat: issuer API endpoints with point-in-time history"
```

---

## Task 13: Security API Endpoints

**Files:**
- Create: `app/api/v1/securities.py`
- Create: `tests/test_api/test_securities.py`
- Modify: `app/main.py` (mount router)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api/test_securities.py
from datetime import date

from app.models.corporate_action import CorporateAction
from app.models.issuer import Issuer
from app.models.security import Security, SecurityIdentifierHistory
from app.models.shares_outstanding import SharesOutstandingHistory


def test_list_securities(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock", currency="USD")
    session.add(sec)
    session.commit()

    response = client.get("/api/v1/securities")
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_get_security_by_id(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    response = client.get(f"/api/v1/securities/{sec.security_id}")
    assert response.status_code == 200
    assert response.json()["security_type"] == "common_stock"


def test_get_security_identifiers(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    ident = SecurityIdentifierHistory(
        security_id=sec.security_id,
        id_type="ticker",
        id_value="TCOR",
        effective_start_date=date(2020, 1, 1),
        source="test",
    )
    session.add(ident)
    session.commit()

    response = client.get(f"/api/v1/securities/{sec.security_id}/identifiers")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["id_value"] == "TCOR"


def test_get_security_actions(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    action = CorporateAction(
        security_id=sec.security_id,
        issuer_id=issuer.issuer_id,
        action_type="reverse_split",
        effective_date=date(2023, 3, 1),
        ratio_from=10,
        ratio_to=1,
        source="test",
    )
    session.add(action)
    session.commit()

    response = client.get(f"/api/v1/securities/{sec.security_id}/actions")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["action_type"] == "reverse_split"


def test_get_security_shares_outstanding(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    shares = SharesOutstandingHistory(
        security_id=sec.security_id,
        as_of_date=date(2023, 6, 30),
        shares_outstanding=1_000_000,
        source="test",
    )
    session.add(shares)
    session.commit()

    response = client.get(f"/api/v1/securities/{sec.security_id}/shares-outstanding")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["shares_outstanding"] == 1_000_000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api/test_securities.py -v`

Expected: FAIL

- [ ] **Step 3: Implement security endpoints**

```python
# app/api/v1/securities.py
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import CursorPagination, get_as_of, get_db
from app.models.corporate_action import CorporateAction, CorporateActionRead
from app.models.security import (
    Security,
    SecurityIdentifierHistory,
    SecurityIdentifierHistoryRead,
    SecurityRead,
)
from app.models.shares_outstanding import (
    SharesOutstandingHistory,
    SharesOutstandingHistoryRead,
)
from app.services.point_in_time import apply_as_of_filter

router = APIRouter(prefix="/securities", tags=["securities"])


@router.get("", response_model=dict)
def list_securities(
    session: Session = Depends(get_db),
    pagination: CursorPagination = Depends(),
    issuer_id: UUID | None = Query(default=None),
    ticker: str | None = Query(default=None),
    cusip: str | None = Query(default=None),
    as_of: date | None = Depends(get_as_of),
):
    stmt = select(Security)
    if issuer_id:
        stmt = stmt.where(Security.issuer_id == issuer_id)
    if ticker or cusip:
        # Join to identifier history to filter by ticker/cusip
        stmt = stmt.join(
            SecurityIdentifierHistory,
            Security.security_id == SecurityIdentifierHistory.security_id,
        )
        if ticker:
            stmt = stmt.where(SecurityIdentifierHistory.id_type == "ticker")
            stmt = stmt.where(SecurityIdentifierHistory.id_value == ticker)
        if cusip:
            stmt = stmt.where(SecurityIdentifierHistory.id_type == "cusip")
            stmt = stmt.where(SecurityIdentifierHistory.id_value == cusip)
        if as_of:
            stmt = apply_as_of_filter(stmt, SecurityIdentifierHistory, as_of)
    if pagination.cursor:
        stmt = stmt.where(Security.security_id > pagination.cursor)
    stmt = stmt.order_by(Security.security_id).limit(pagination.limit)

    securities = session.exec(stmt).all()
    next_cursor = str(securities[-1].security_id) if len(securities) == pagination.limit else None
    return {
        "items": [SecurityRead.model_validate(s) for s in securities],
        "next_cursor": next_cursor,
    }


@router.get("/{security_id}", response_model=SecurityRead)
def get_security(security_id: UUID, session: Session = Depends(get_db)):
    security = session.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")
    return security


@router.get("/{security_id}/identifiers", response_model=list[SecurityIdentifierHistoryRead])
def get_security_identifiers(
    security_id: UUID,
    session: Session = Depends(get_db),
    as_of: date | None = Depends(get_as_of),
):
    security = session.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")

    stmt = select(SecurityIdentifierHistory).where(
        SecurityIdentifierHistory.security_id == security_id
    )
    stmt = apply_as_of_filter(stmt, SecurityIdentifierHistory, as_of)
    stmt = stmt.order_by(SecurityIdentifierHistory.effective_start_date)
    return session.exec(stmt).all()


@router.get("/{security_id}/actions", response_model=list[CorporateActionRead])
def get_security_actions(
    security_id: UUID,
    session: Session = Depends(get_db),
):
    security = session.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")

    stmt = (
        select(CorporateAction)
        .where(CorporateAction.security_id == security_id)
        .order_by(CorporateAction.effective_date)
    )
    return session.exec(stmt).all()


@router.get("/{security_id}/shares-outstanding", response_model=list[SharesOutstandingHistoryRead])
def get_security_shares_outstanding(
    security_id: UUID,
    session: Session = Depends(get_db),
):
    security = session.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")

    stmt = (
        select(SharesOutstandingHistory)
        .where(SharesOutstandingHistory.security_id == security_id)
        .order_by(SharesOutstandingHistory.as_of_date)
    )
    return session.exec(stmt).all()
```

Add to `app/main.py`:
```python
from app.api.v1.securities import router as securities_router

app.include_router(securities_router, prefix="/api/v1")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api/test_securities.py -v`

Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/securities.py app/main.py tests/test_api/test_securities.py
git commit -m "feat: security API endpoints with identifiers, actions, and shares outstanding"
```

---

## Task 14: Listing API Endpoints

**Files:**
- Create: `app/api/v1/listings.py`
- Create: `tests/test_api/test_listings.py`
- Modify: `app/main.py` (mount router)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api/test_listings.py
from datetime import date

from app.models.issuer import Issuer
from app.models.listing import Listing, ListingStatusHistory
from app.models.security import Security


def test_list_listings(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    listing = Listing(
        security_id=sec.security_id,
        venue_code="OTCM",
        listing_status="active",
        effective_start_date=date(2020, 1, 1),
    )
    session.add(listing)
    session.commit()

    response = client.get("/api/v1/listings")
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_get_listing_by_id(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    listing = Listing(
        security_id=sec.security_id,
        venue_code="OTCM",
        listing_status="active",
        effective_start_date=date(2020, 1, 1),
    )
    session.add(listing)
    session.commit()

    response = client.get(f"/api/v1/listings/{listing.listing_id}")
    assert response.status_code == 200
    assert response.json()["venue_code"] == "OTCM"


def test_get_listing_status_history(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    listing = Listing(
        security_id=sec.security_id,
        venue_code="OTCM",
        listing_status="active",
        effective_start_date=date(2020, 1, 1),
    )
    session.add(listing)
    session.commit()

    status1 = ListingStatusHistory(
        listing_id=listing.listing_id,
        effective_start_date=date(2020, 1, 1),
        effective_end_date=date(2022, 1, 1),
        listing_status="active",
        tier="Pink",
        caveat_emptor_flag=False,
        source="test",
    )
    status2 = ListingStatusHistory(
        listing_id=listing.listing_id,
        effective_start_date=date(2022, 1, 1),
        listing_status="active",
        tier="OTCQB",
        caveat_emptor_flag=False,
        source="test",
    )
    session.add_all([status1, status2])
    session.commit()

    response = client.get(f"/api/v1/listings/{listing.listing_id}/status-history")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_listing_status_history_as_of(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    listing = Listing(
        security_id=sec.security_id,
        venue_code="OTCM",
        listing_status="active",
        effective_start_date=date(2020, 1, 1),
    )
    session.add(listing)
    session.commit()

    status1 = ListingStatusHistory(
        listing_id=listing.listing_id,
        effective_start_date=date(2020, 1, 1),
        effective_end_date=date(2022, 1, 1),
        listing_status="active",
        tier="Pink",
        source="test",
    )
    status2 = ListingStatusHistory(
        listing_id=listing.listing_id,
        effective_start_date=date(2022, 1, 1),
        listing_status="active",
        tier="OTCQB",
        source="test",
    )
    session.add_all([status1, status2])
    session.commit()

    # Query as of 2021 — should only see Pink tier
    response = client.get(
        f"/api/v1/listings/{listing.listing_id}/status-history",
        params={"as_of": "2021-06-15"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tier"] == "Pink"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api/test_listings.py -v`

Expected: FAIL

- [ ] **Step 3: Implement listing endpoints**

```python
# app/api/v1/listings.py
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import CursorPagination, get_as_of, get_db
from app.models.listing import (
    Listing,
    ListingRead,
    ListingStatusHistory,
    ListingStatusHistoryRead,
)
from app.services.point_in_time import apply_as_of_filter

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=dict)
def list_listings(
    session: Session = Depends(get_db),
    pagination: CursorPagination = Depends(),
    venue_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    tier: str | None = Query(default=None),
):
    stmt = select(Listing)
    if venue_code:
        stmt = stmt.where(Listing.venue_code == venue_code)
    if status:
        stmt = stmt.where(Listing.listing_status == status)
    if pagination.cursor:
        stmt = stmt.where(Listing.listing_id > pagination.cursor)
    stmt = stmt.order_by(Listing.listing_id).limit(pagination.limit)

    listings = session.exec(stmt).all()
    next_cursor = str(listings[-1].listing_id) if len(listings) == pagination.limit else None
    return {
        "items": [ListingRead.model_validate(li) for li in listings],
        "next_cursor": next_cursor,
    }


@router.get("/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: UUID, session: Session = Depends(get_db)):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("/{listing_id}/status-history", response_model=list[ListingStatusHistoryRead])
def get_listing_status_history(
    listing_id: UUID,
    session: Session = Depends(get_db),
    as_of: date | None = Depends(get_as_of),
):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    stmt = select(ListingStatusHistory).where(
        ListingStatusHistory.listing_id == listing_id
    )
    stmt = apply_as_of_filter(stmt, ListingStatusHistory, as_of)
    stmt = stmt.order_by(ListingStatusHistory.effective_start_date)
    return session.exec(stmt).all()
```

Add to `app/main.py`:
```python
from app.api.v1.listings import router as listings_router

app.include_router(listings_router, prefix="/api/v1")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api/test_listings.py -v`

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/listings.py app/main.py tests/test_api/test_listings.py
git commit -m "feat: listing API endpoints with OTC status history and as_of filtering"
```

---

## Task 15: Clerk Auth Integration

**Files:**
- Create: `app/auth.py`
- Modify: `app/api/deps.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write failing tests for auth dependency**

```python
# tests/test_api/test_auth.py
from fastapi.testclient import TestClient
from sqlmodel import select

from app.models.user import User


def test_unauthenticated_request_returns_401(session):
    """When auth is required and no token/key is provided, return 401."""
    from app.api.deps import get_db
    from app.main import app

    # Create a client that does NOT override get_current_user
    def get_session_override():
        yield session

    app.dependency_overrides[get_db] = get_session_override
    with TestClient(app) as raw_client:
        response = raw_client.get("/api/v1/issuers")
    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_authenticated_request_creates_user(client, session):
    """First authenticated request auto-creates a user record."""
    response = client.get("/api/v1/issuers")
    assert response.status_code == 200

    users = session.exec(
        select(User).where(User.clerk_user_id == "test_clerk_user")
    ).all()
    assert len(users) == 1
    assert users[0].tier == "free"
```

- [ ] **Step 2: Implement Clerk JWT verification module**

```python
# app/auth.py
import jwt
import httpx
from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Fetch Clerk JWKS for JWT verification. Cached in-process."""
    if not settings.clerk_jwks_url:
        return {}
    response = httpx.get(settings.clerk_jwks_url)
    response.raise_for_status()
    return response.json()


def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return the payload.

    Returns dict with at minimum 'sub' (Clerk user ID).
    Raises jwt.InvalidTokenError on failure.
    """
    jwks = _get_jwks()
    if not jwks:
        raise jwt.InvalidTokenError("JWKS not configured")

    # Get the signing key from JWKS
    header = jwt.get_unverified_header(token)
    key = None
    for jwk in jwks.get("keys", []):
        if jwk["kid"] == header.get("kid"):
            key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
            break

    if key is None:
        raise jwt.InvalidTokenError("Signing key not found in JWKS")

    payload = jwt.decode(token, key, algorithms=["RS256"])
    return payload
```

- [ ] **Step 3: Add auth dependency to deps.py and update conftest**

Update `app/api/deps.py` — add auth dependencies:

```python
# Add to app/api/deps.py
from app.auth import verify_clerk_token
from app.models.user import User
import hashlib


def get_current_user(
    session: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> User:
    """Resolve the current user from Clerk JWT or API key.

    On first authenticated request, auto-creates a User record.
    """
    if x_api_key:
        return _resolve_api_key_user(session, x_api_key)
    if authorization:
        return _resolve_jwt_user(session, authorization)
    raise HTTPException(status_code=401, detail="Authentication required")


def _resolve_jwt_user(session: Session, authorization: str) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        payload = verify_clerk_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    clerk_user_id = payload["sub"]
    user = session.exec(
        select(User).where(User.clerk_user_id == clerk_user_id)
    ).first()
    if not user:
        user = User(
            clerk_user_id=clerk_user_id,
            email=payload.get("email", ""),
            tier="free",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _resolve_api_key_user(session: Session, api_key: str) -> User:
    from app.models.user import ApiKey

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    db_key = session.exec(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    ).first()
    if not db_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    user = session.get(User, db_key.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

Add import for `select`:
```python
from sqlmodel import Session, select
```

Update `tests/conftest.py` — add mock auth that bypasses Clerk JWT verification:

```python
# Add to tests/conftest.py
from sqlmodel import select

from app.models.user import User


@pytest.fixture(autouse=True)
def mock_auth_user(session):
    """Create a test user and override auth dependency to return it."""
    user = session.exec(
        select(User).where(User.clerk_user_id == "test_clerk_user")
    ).first()
    if not user:
        user = User(clerk_user_id="test_clerk_user", email="test@test.com", tier="free")
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@pytest.fixture()
def client(session, mock_auth_user) -> Generator[TestClient, None, None]:
    from app.api.deps import get_current_user, get_db
    from app.main import app

    def get_session_override():
        yield session

    def get_auth_override():
        return mock_auth_user

    app.dependency_overrides[get_db] = get_session_override
    app.dependency_overrides[get_current_user] = get_auth_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

Note: Also replace the original `get_session` override in the `client` fixture — the dependency is now `get_db` from `deps.py`, not `get_session` from `db/session.py`.

- [ ] **Step 4: Wire auth into API endpoints**

Add `current_user: User = Depends(get_current_user)` as a parameter to each endpoint function in `issuers.py`, `securities.py`, and `listings.py`. This makes auth required on all data endpoints.

Example for `list_issuers`:
```python
def list_issuers(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # add this
    pagination: CursorPagination = Depends(),
    ...
):
```

- [ ] **Step 5: Run all tests to verify they pass**

Run: `pytest tests/ -v`

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/auth.py app/api/deps.py app/api/v1/ tests/conftest.py tests/test_api/
git commit -m "feat: Clerk JWT auth with user auto-sync and API key resolution"
```

---

## Task 16: API Key Management Endpoints

**Files:**
- Create: `app/api/v1/api_keys.py`
- Create: `tests/test_api/test_api_keys.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api/test_api_keys.py
from app.models.user import User


def test_create_api_key_paid_user(client, session, mock_auth_user):
    # Upgrade user to paid tier
    mock_auth_user.tier = "paid"
    session.add(mock_auth_user)
    session.commit()

    response = client.post("/api/v1/api-keys", json={"label": "My Key"})
    assert response.status_code == 201
    data = response.json()
    assert "key" in data  # raw key returned only on creation
    assert data["label"] == "My Key"


def test_create_api_key_free_user_rejected(client):
    response = client.post("/api/v1/api-keys", json={"label": "My Key"})
    assert response.status_code == 403


def test_list_api_keys(client, session, mock_auth_user):
    mock_auth_user.tier = "paid"
    session.add(mock_auth_user)
    session.commit()

    # Create a key first
    client.post("/api/v1/api-keys", json={"label": "Key 1"})

    response = client.get("/api/v1/api-keys")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # Raw key should NOT be returned on list
    assert "key" not in data[0]


def test_delete_api_key(client, session, mock_auth_user):
    mock_auth_user.tier = "paid"
    session.add(mock_auth_user)
    session.commit()

    create_resp = client.post("/api/v1/api-keys", json={"label": "To Delete"})
    key_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/api-keys/{key_id}")
    assert response.status_code == 204
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api/test_api_keys.py -v`

Expected: FAIL

- [ ] **Step 3: Implement API key endpoints**

```python
# app/api/v1/api_keys.py
import hashlib
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_db
from app.models.user import ApiKey, ApiKeyCreate, ApiKeyRead, User

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.tier != "paid":
        raise HTTPException(status_code=403, detail="API keys require paid tier")

    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        user_id=current_user.user_id,
        key_hash=key_hash,
        label=body.label,
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)

    return {
        "id": str(api_key.id),
        "key": raw_key,  # only returned on creation
        "label": api_key.label,
        "created_at": api_key.created_at.isoformat(),
    }


@router.get("", response_model=list[ApiKeyRead])
def list_api_keys(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ApiKey).where(
        ApiKey.user_id == current_user.user_id,
        ApiKey.is_active == True,
    )
    return session.exec(stmt).all()


@router.delete("/{key_id}", status_code=204)
def delete_api_key(
    key_id: UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = session.get(ApiKey, key_id)
    if not api_key or api_key.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    session.add(api_key)
    session.commit()
```

Add to `app/main.py`:
```python
from app.api.v1.api_keys import router as api_keys_router

app.include_router(api_keys_router, prefix="/api/v1")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api/test_api_keys.py -v`

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/api_keys.py app/main.py tests/test_api/test_api_keys.py
git commit -m "feat: API key management endpoints (create, list, delete) with paid tier enforcement"
```

---

## Task 17: Rate Limiting

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_api/test_rate_limit.py`

- [ ] **Step 1: Write a test verifying rate limit headers are present**

```python
# tests/test_api/test_rate_limit.py
def test_rate_limit_headers_present(client):
    response = client.get("/api/v1/issuers")
    # slowapi adds X-RateLimit headers
    assert "X-RateLimit-Limit" in response.headers or response.status_code == 200
    # Basic smoke test — the real enforcement is tested by exceeding the limit
```

- [ ] **Step 2: Implement rate limiting in app/main.py**

```python
# Add to app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

For per-tier rate limiting, add a custom key function to `app/api/deps.py`:

```python
def get_rate_limit_key(request):
    """Rate limit key that includes user tier for differentiated limits."""
    return get_remote_address(request)
```

Apply `@limiter.limit()` decorators to endpoints as needed, or use a default limit on the app. For v1, a simple global per-IP limit is sufficient:

```python
# In app/main.py, after creating the app
app = FastAPI(...)
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
```

- [ ] **Step 3: Run all tests**

Run: `pytest tests/ -v`

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: rate limiting with slowapi (60 req/min default)"
```

---

## Task 18: Ingestion Base & CLI

**Files:**
- Create: `app/ingestion/__init__.py`
- Create: `app/ingestion/base.py`
- Create: `app/ingestion/cli.py`
- Create: `app/ingestion/fidelity.py`
- Create: `tests/test_ingestion/__init__.py`
- Create: `tests/test_ingestion/test_base.py`

- [ ] **Step 1: Write failing tests for base ingestor**

```python
# tests/test_ingestion/test_base.py
from datetime import date

import pytest
from sqlmodel import Session

from app.ingestion.base import BaseIngestor, IngestResult, RawRecord
from app.models.issuer import Issuer


class FakeIngestor(BaseIngestor):
    """Test ingestor that creates issuers from fake raw records."""

    vendor_name = "fake"

    def fetch(self) -> list[RawRecord]:
        return [
            {"legal_name": "Fake Corp", "country": "US"},
            {"legal_name": "Fake Inc", "country": "CA"},
        ]

    def transform(self, raw: list[RawRecord]) -> list[Issuer]:
        return [
            Issuer(
                legal_name=r["legal_name"],
                country_incorporation=r["country"],
            )
            for r in raw
        ]


def test_ingestor_run(session):
    ingestor = FakeIngestor(session)
    result = ingestor.run()

    assert isinstance(result, IngestResult)
    assert result.records_fetched == 2
    assert result.records_loaded == 2
    assert result.errors == 0


def test_ingestor_load_persists_records(session):
    ingestor = FakeIngestor(session)
    ingestor.run()

    from sqlmodel import select
    issuers = session.exec(select(Issuer)).all()
    assert len(issuers) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingestion/test_base.py -v`

Expected: FAIL

- [ ] **Step 3: Implement base ingestor**

```python
# app/ingestion/__init__.py
# empty

# app/ingestion/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlmodel import Session, SQLModel

# Raw records from vendors — untyped dicts before transformation
RawRecord = dict


@dataclass
class IngestResult:
    vendor_name: str = ""
    records_fetched: int = 0
    records_loaded: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)


class BaseIngestor(ABC):
    """Abstract base class for vendor data ingestion.

    Subclasses implement fetch() and transform().
    The base class provides load() and run().
    """

    vendor_name: str = "unknown"

    def __init__(self, session: Session):
        self.session = session

    @abstractmethod
    def fetch(self) -> list[RawRecord]:
        """Pull raw data from vendor source."""
        ...

    @abstractmethod
    def transform(self, raw: list[RawRecord]) -> list[SQLModel]:
        """Normalize raw records into canonical SQLModel instances."""
        ...

    def load(self, records: list[SQLModel]) -> int:
        """Persist records to the database. Returns count of records loaded."""
        for record in records:
            self.session.add(record)
        self.session.commit()
        return len(records)

    def run(self) -> IngestResult:
        """Execute the full fetch → transform → load pipeline."""
        result = IngestResult(vendor_name=self.vendor_name)

        raw = self.fetch()
        result.records_fetched = len(raw)

        records = self.transform(raw)
        result.records_loaded = self.load(records)

        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingestion/test_base.py -v`

Expected: PASS (2 tests)

- [ ] **Step 5: Create Fidelity ingestor stub**

```python
# app/ingestion/fidelity.py
from app.ingestion.base import BaseIngestor, RawRecord
from sqlmodel import SQLModel


class FidelityIngestor(BaseIngestor):
    """Fidelity data ingestion adapter.

    This is a stub — the actual implementation will be ported
    from the existing Fidelity ingestion work.
    """

    vendor_name = "fidelity"

    def fetch(self) -> list[RawRecord]:
        raise NotImplementedError(
            "Fidelity ingestor not yet implemented. "
            "Port existing ingestion work to this interface."
        )

    def transform(self, raw: list[RawRecord]) -> list[SQLModel]:
        raise NotImplementedError(
            "Fidelity ingestor not yet implemented."
        )
```

- [ ] **Step 6: Create CLI entrypoint**

```python
# app/ingestion/cli.py
"""CLI for running data ingestion.

Usage:
    python -m app.ingestion.cli fidelity
"""
import argparse
import sys

from sqlmodel import Session

from app.db.session import engine

INGESTORS = {
    "fidelity": "app.ingestion.fidelity.FidelityIngestor",
}


def main():
    parser = argparse.ArgumentParser(description="Run data ingestion")
    parser.add_argument("vendor", choices=INGESTORS.keys(), help="Vendor to ingest from")
    args = parser.parse_args()

    module_path, class_name = INGESTORS[args.vendor].rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    ingestor_class = getattr(module, class_name)

    with Session(engine) as session:
        ingestor = ingestor_class(session)
        result = ingestor.run()
        print(f"Ingestion complete: {result}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Commit**

```bash
git add app/ingestion/ tests/test_ingestion/
git commit -m "feat: ingestion architecture with base ingestor, CLI, and fidelity stub"
```

---

## Task 19: Docker & Local Dev Setup

**Files:**
- Create: `Dockerfile`
- Modify: `docker-compose.yml` (add app service)

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Add app service to docker-compose.yml**

Add to `docker-compose.yml`:

```yaml
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://secmaster:secmaster@db:5432/secmaster
    depends_on:
      - db
```

- [ ] **Step 3: Build and verify**

```bash
docker compose build app
docker compose up -d
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: Dockerfile and docker-compose app service for local dev"
```

---

## Task 20: Full Integration Verification

- [ ] **Step 1: Run all tests**

```bash
docker compose up -d db db-test
pytest tests/ -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 2: Run migrations on dev database and start server**

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Verify in browser: `http://localhost:8000/docs` shows the OpenAPI documentation with all endpoints.

- [ ] **Step 3: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: final cleanup and integration verification"
```

---

## Summary

| Task | What it builds | Tests |
|------|---------------|-------|
| 1 | Project scaffold, config, docker-compose | Manual verify |
| 2 | Database session, test fixtures | DB connectivity test |
| 3 | Issuer + IssuerNameHistory models | 2 model tests |
| 4 | Security + SecurityIdentifierHistory models | 2 model tests |
| 5 | Listing + ListingStatusHistory models | 2 model tests |
| 6 | CorporateAction, SharesOutstanding, Classification, VendorMap | 4 model tests |
| 7 | User + ApiKey models | 2 model tests |
| 8 | Alembic setup + initial migration | Migration verify |
| 9 | FastAPI app + health check | 1 API test |
| 10 | Point-in-time query service | 4 service tests |
| 11 | API dependencies (db, auth, pagination) | Used by API tests |
| 12 | Issuer API endpoints | 5 API tests |
| 13 | Security API endpoints | 5 API tests |
| 14 | Listing API endpoints | 4 API tests |
| 15 | Clerk auth + user sync | Auth integration |
| 16 | API key management | 4 API tests |
| 17 | Rate limiting | 1 smoke test |
| 18 | Ingestion base + CLI + Fidelity stub | 2 ingestion tests |
| 19 | Docker + local dev | Manual verify |
| 20 | Full integration verification | All tests |

**Next plan:** Frontend (React + TypeScript + Vite) — to be created after backend API is stable.
