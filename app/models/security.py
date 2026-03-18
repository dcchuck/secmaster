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
