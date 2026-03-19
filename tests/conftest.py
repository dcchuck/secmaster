from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import settings
from app.models.user import User


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(settings.test_database_url)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def session(test_engine) -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(autouse=True)
def mock_auth_user(session):
    """Create a test user and override auth dependency to return it.

    Resets tier to 'free' each test to avoid cross-test contamination.
    """
    user = session.exec(
        select(User).where(User.clerk_user_id == "test_clerk_user")
    ).first()
    if not user:
        user = User(clerk_user_id="test_clerk_user", email="test@test.com", tier="free")
        session.add(user)
        session.commit()
        session.refresh(user)
    elif user.tier != "free":
        user.tier = "free"
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@pytest.fixture()
def client(session, mock_auth_user) -> Generator[TestClient, None, None]:
    from app.api.deps import get_current_user, get_db
    from app.main import app

    def get_db_override():
        yield session

    def get_auth_override():
        return mock_auth_user

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = get_auth_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
