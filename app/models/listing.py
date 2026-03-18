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
