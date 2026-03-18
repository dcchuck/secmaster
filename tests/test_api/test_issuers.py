from datetime import date

from app.models.issuer import Issuer, IssuerNameHistory
from app.models.classification import IssuerClassificationHistory


def test_list_issuers(client, session):
    issuer = Issuer(legal_name="Acme Corp", country_incorporation="US")
    session.add(issuer)
    session.commit()

    response = client.get("/api/v1/issuers")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["legal_name"] == "Acme Corp"


def test_get_issuer_by_id(client, session):
    issuer = Issuer(legal_name="Acme Corp")
    session.add(issuer)
    session.commit()

    response = client.get(f"/api/v1/issuers/{issuer.issuer_id}")
    assert response.status_code == 200
    assert response.json()["legal_name"] == "Acme Corp"


def test_get_issuer_not_found(client):
    response = client.get("/api/v1/issuers/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_issuer_history(client, session):
    issuer = Issuer(legal_name="New Name Corp")
    session.add(issuer)
    session.commit()

    name1 = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Old Name Inc",
        effective_start_date=date(2018, 1, 1),
        effective_end_date=date(2022, 1, 1),
        source="test",
    )
    name2 = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="New Name Corp",
        effective_start_date=date(2022, 1, 1),
        source="test",
    )
    session.add_all([name1, name2])
    session.commit()

    response = client.get(f"/api/v1/issuers/{issuer.issuer_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data["name_history"]) == 2


def test_get_issuer_history_as_of(client, session):
    issuer = Issuer(legal_name="New Name Corp")
    session.add(issuer)
    session.commit()

    name1 = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="Old Name Inc",
        effective_start_date=date(2018, 1, 1),
        effective_end_date=date(2022, 1, 1),
        source="test",
    )
    name2 = IssuerNameHistory(
        issuer_id=issuer.issuer_id,
        name="New Name Corp",
        effective_start_date=date(2022, 1, 1),
        source="test",
    )
    session.add_all([name1, name2])
    session.commit()

    response = client.get(
        f"/api/v1/issuers/{issuer.issuer_id}/history",
        params={"as_of": "2020-06-15"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["name_history"]) == 1
    assert data["name_history"][0]["name"] == "Old Name Inc"
