from fastapi.testclient import TestClient
from sqlmodel import select

from app.models.user import User


def test_unauthenticated_request_returns_401(session):
    """When auth is required and no token/key is provided, return 401."""
    from app.api.deps import get_db
    from app.main import app

    def get_session_override():
        yield session

    app.dependency_overrides[get_db] = get_session_override
    with TestClient(app) as raw_client:
        response = raw_client.get("/api/v1/issuers")
    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_authenticated_request_creates_user(client, session):
    """First authenticated request auto-creates a user record."""
    response = client.get("/api/v1/issuers")
    assert response.status_code == 200

    users = session.exec(
        select(User).where(User.clerk_user_id == "test_clerk_user")
    ).all()
    assert len(users) == 1
    assert users[0].tier == "free"
