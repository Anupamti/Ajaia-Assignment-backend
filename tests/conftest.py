import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import bootstrap_seed_users
from app.db import Base, get_db
from app.main import app
from app.models import User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    bootstrap_seed_users(session)
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Not used as a context manager: that would trigger the startup event,
    # which connects to the real (Postgres) engine instead of the test DB.
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def users(db_session):
    return {u.name: u for u in db_session.query(User).all()}


def login_as(client: TestClient, user_id: int) -> TestClient:
    resp = client.post("/api/auth/login", json={"user_id": str(user_id)})
    assert resp.status_code == 200
    return client
