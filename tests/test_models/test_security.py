from datetime import date, datetime
from uuid import UUID

from app.models.issuer import Issuer
from app.models.security import Security, SecurityIdentifierHistory


def test_create_security(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(
        issuer_id=issuer.issuer_id,
        security_type="common_stock",
        currency="USD",
        is_primary_equity_flag=True,
    )
    session.add(security)
    session.commit()
    session.refresh(security)

    assert isinstance(security.security_id, UUID)
    assert security.issuer_id == issuer.issuer_id
    assert security.security_type == "common_stock"
    assert security.is_primary_equity_flag is True


def test_create_security_identifier_history(session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    security = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(security)
    session.commit()

    ident = SecurityIdentifierHistory(
        security_id=security.security_id,
        id_type="ticker",
        id_value="TCOR",
        venue_code="OTC",
        effective_start_date=date(2020, 1, 1),
        is_primary_flag=True,
        source="fidelity",
    )
    session.add(ident)
    session.commit()
    session.refresh(ident)

    assert ident.id_type == "ticker"
    assert ident.id_value == "TCOR"
    assert ident.is_primary_flag is True
