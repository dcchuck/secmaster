from datetime import date

from sqlmodel import select

from app.models.issuer import Issuer, IssuerNameHistory
from app.services.point_in_time import apply_as_of_filter


def test_as_of_returns_active_record(session):
    """Record with no end date is active at any date after start."""
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    name = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Test Corp",
        effective_start_date=date(2020, 1, 1),
        effective_end_date=None,
        source="test",
    )
    session.add(name)
    session.commit()

    stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer.issuer_id
    )
    stmt = apply_as_of_filter(stmt, IssuerNameHistory, date(2023, 6, 15))
    results = session.exec(stmt).all()

    assert len(results) == 1
    assert results[0].name == "Test Corp"


def test_as_of_excludes_future_record(session):
    """Record starting after the as_of date should be excluded."""
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    name = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Future Name",
        effective_start_date=date(2025, 1, 1),
        effective_end_date=None,
        source="test",
    )
    session.add(name)
    session.commit()

    stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer.issuer_id
    )
    stmt = apply_as_of_filter(stmt, IssuerNameHistory, date(2023, 6, 15))
    results = session.exec(stmt).all()

    assert len(results) == 0


def test_as_of_excludes_expired_record(session):
    """Record that ended before the as_of date should be excluded."""
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    name = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Old Name",
        effective_start_date=date(2018, 1, 1),
        effective_end_date=date(2020, 1, 1),
        source="test",
    )
    session.add(name)
    session.commit()

    stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer.issuer_id
    )
    stmt = apply_as_of_filter(stmt, IssuerNameHistory, date(2023, 6, 15))
    results = session.exec(stmt).all()

    assert len(results) == 0


def test_as_of_none_returns_all(session):
    """When as_of is None, no time filter is applied."""
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    for i, (start, end) in enumerate([
        (date(2018, 1, 1), date(2020, 1, 1)),
        (date(2020, 1, 1), None),
    ]):
        name = IssuerNameHistory(
            issuer_id=issuer.issuer_id,
            name=f"Name {i}",
            effective_start_date=start,
            effective_end_date=end,
            source="test",
        )
        session.add(name)
    session.commit()

    stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer.issuer_id
    )
    stmt = apply_as_of_filter(stmt, IssuerNameHistory, None)
    results = session.exec(stmt).all()

    assert len(results) == 2
