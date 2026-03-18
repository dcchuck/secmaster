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
