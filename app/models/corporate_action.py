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
