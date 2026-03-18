from datetime import date, datetime, timezone
from uuid import UUID

from sqlmodel import select

from app.models.issuer import Issuer, IssuerNameHistory


def test_create_issuer(session):
    issuer = Issuer(legal_name="Test Corp", country_incorporation="US")
    session.add(issuer)
    session.commit()
    session.refresh(issuer)

    assert isinstance(issuer.issuer_id, UUID)
    assert issuer.legal_name == "Test Corp"
    assert issuer.country_incorporation == "US"
    assert issuer.is_shell_flag is False
    assert isinstance(issuer.created_at, datetime)
    assert isinstance(issuer.updated_at, datetime)


def test_create_issuer_name_history(session):
    issuer = Issuer(legal_name="Old Name Inc")
    session.add(issuer)
    session.commit()

    name_hist = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Old Name Inc",
        effective_start_date=date(2020, 1, 1),
        effective_end_date=date(2023, 6, 15),
        source="fidelity",
    )
    session.add(name_hist)
    session.commit()
    session.refresh(name_hist)

    assert name_hist.issuer_id == issuer.issuer_id
    assert name_hist.name == "Old Name Inc"
    assert name_hist.effective_start_date == date(2020, 1, 1)
    assert name_hist.effective_end_date == date(2023, 6, 15)
    assert name_hist.source == "fidelity"
