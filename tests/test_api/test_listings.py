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

    response = client.get(
        f"/api/v1/listings/{listing.listing_id}/status-history",
        params={"as_of": "2021-06-15"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tier"] == "Pink"
