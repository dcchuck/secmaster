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
