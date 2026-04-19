"""
tests/conftest.py — Shared pytest fixtures for all test modules.

Uses an in-memory SQLite database (StaticPool) so every test gets a fresh,
isolated schema without touching the real data/app.db file.
The FastAPI get_db dependency is overridden to yield the test session.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# ── In-memory test database ───────────────────────────────────────────────────
_TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture()
def test_db():
    """
    Create a brand-new in-memory SQLite database for each test.
    StaticPool ensures all connections share the same in-memory store
    (required for SQLite ':memory:' to work across sessions).
    """
    engine = create_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    db = TestSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
async def client(test_db):
    """
    httpx AsyncClient wired to the FastAPI app with the test DB injected.
    Clears dependency overrides after each test.
    """
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Reusable request helpers ──────────────────────────────────────────────────
_SELFIE = ("test.jpg", b"fakejpeg", "image/jpeg")


async def register_user(
    client: AsyncClient,
    username: str = "testuser",
    email: str = "test@test.com",
    password: str = "testpass",
) -> dict:
    resp = await client.post(
        "/auth/register",
        data={"username": username, "email": email, "password": password},
        files={"selfie": _SELFIE},
    )
    return resp


async def login_user(
    client: AsyncClient,
    username: str = "testuser",
    password: str = "testpass",
) -> str:
    resp = await client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    return resp.json()["access_token"]


async def register_and_login(
    client: AsyncClient,
    username: str = "testuser",
    email: str = "test@test.com",
    password: str = "testpass",
) -> str:
    await register_user(client, username, email, password)
    return await login_user(client, username, password)
