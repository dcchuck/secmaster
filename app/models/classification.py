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
