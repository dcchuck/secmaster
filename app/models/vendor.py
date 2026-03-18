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
