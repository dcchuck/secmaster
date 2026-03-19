from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import CursorPagination, get_as_of, get_current_user, get_db
from app.models.user import User
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
    current_user: User = Depends(get_current_user),
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
def get_listing(listing_id: UUID, session: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("/{listing_id}/status-history", response_model=list[ListingStatusHistoryRead])
def get_listing_status_history(
    listing_id: UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
