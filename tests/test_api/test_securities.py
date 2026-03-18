from datetime import date

from app.models.corporate_action import CorporateAction
from app.models.issuer import Issuer
from app.models.security import Security, SecurityIdentifierHistory
from app.models.shares_outstanding import SharesOutstandingHistory


def test_list_securities(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock", currency="USD")
    session.add(sec)
    session.commit()

    response = client.get("/api/v1/securities")
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_get_security_by_id(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    response = client.get(f"/api/v1/securities/{sec.security_id}")
    assert response.status_code == 200
    assert response.json()["security_type"] == "common_stock"


def test_get_security_identifiers(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    ident = SecurityIdentifierHistory(
        security_id=sec.security_id,
        id_type="ticker",
        id_value="TCOR",
        effective_start_date=date(2020, 1, 1),
        source="test",
    )
    session.add(ident)
    session.commit()

    response = client.get(f"/api/v1/securities/{sec.security_id}/identifiers")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["id_value"] == "TCOR"


def test_get_security_actions(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    action = CorporateAction(
        security_id=sec.security_id,
        issuer_id=issuer.issuer_id,
        action_type="reverse_split",
        effective_date=date(2023, 3, 1),
        ratio_from=10,
        ratio_to=1,
        source="test",
    )
    session.add(action)
    session.commit()

    response = client.get(f"/api/v1/securities/{sec.security_id}/actions")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["action_type"] == "reverse_split"


def test_get_security_shares_outstanding(client, session):
    issuer = Issuer(legal_name="Test Corp")
    session.add(issuer)
    session.commit()

    sec = Security(issuer_id=issuer.issuer_id, security_type="common_stock")
    session.add(sec)
    session.commit()

    shares = SharesOutstandingHistory(
        security_id=sec.security_id,
        as_of_date=date(2023, 6, 30),
        shares_outstanding=1_000_000,
        source="test",
    )
    session.add(shares)
    session.commit()

    response = client.get(f"/api/v1/securities/{sec.security_id}/shares-outstanding")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["shares_outstanding"] == 1_000_000
