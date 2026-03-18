from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


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


@pytest.fixture()
def client(session) -> Generator[TestClient, None, None]:
    from app.db.session import get_session
    from app.main import app

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
