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
