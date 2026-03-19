from app.models.user import User


def test_create_api_key_paid_user(client, session, mock_auth_user):
    # Upgrade user to paid tier
    mock_auth_user.tier = "paid"
    session.add(mock_auth_user)
    session.commit()

    response = client.post("/api/v1/api-keys", json={"label": "My Key"})
    assert response.status_code == 201
    data = response.json()
    assert "key" in data  # raw key returned only on creation
    assert data["label"] == "My Key"


def test_create_api_key_free_user_rejected(client):
    response = client.post("/api/v1/api-keys", json={"label": "My Key"})
    assert response.status_code == 403


def test_list_api_keys(client, session, mock_auth_user):
    mock_auth_user.tier = "paid"
    session.add(mock_auth_user)
    session.commit()

    # Create a key first
    client.post("/api/v1/api-keys", json={"label": "Key 1"})

    response = client.get("/api/v1/api-keys")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # Raw key should NOT be returned on list
    assert "key" not in data[0]


def test_delete_api_key(client, session, mock_auth_user):
    mock_auth_user.tier = "paid"
    session.add(mock_auth_user)
    session.commit()

    create_resp = client.post("/api/v1/api-keys", json={"label": "To Delete"})
    key_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/api-keys/{key_id}")
    assert response.status_code == 204
