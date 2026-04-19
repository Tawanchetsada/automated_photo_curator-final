"""
tests/test_auth.py — Integration tests for /auth and /profile/me endpoints.

All tests use an in-memory SQLite database and never load real ML models.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login, register_user


# ── /auth/register ────────────────────────────────────────────────────────────
async def test_register_success(client: AsyncClient) -> None:
    """POST /auth/register with valid payload → 201 with user fields."""
    resp = await register_user(client)
    assert resp.status_code == 201
    body = resp.json()
    assert "user_id" in body
    assert body["username"] == "testuser"
    assert body["email"] == "test@test.com"


async def test_register_duplicate_username(client: AsyncClient) -> None:
    """Registering the same username twice → second call returns 400."""
    await register_user(client, username="dupuser", email="first@test.com")
    resp = await register_user(client, username="dupuser", email="other@test.com")
    assert resp.status_code == 400


# ── /auth/login ───────────────────────────────────────────────────────────────
async def test_login_success(client: AsyncClient) -> None:
    """Register then login with correct credentials → 200 with access_token."""
    await register_user(client)
    resp = await client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient) -> None:
    """Login with wrong password → 401."""
    await register_user(client)
    resp = await client.post(
        "/auth/login",
        data={"username": "testuser", "password": "wrong"},
    )
    assert resp.status_code == 401


# ── /profile/me ───────────────────────────────────────────────────────────────
async def test_get_profile_requires_auth(client: AsyncClient) -> None:
    """GET /profile/me without a token → 401."""
    resp = await client.get("/profile/me")
    assert resp.status_code == 401


async def test_get_profile_success(client: AsyncClient) -> None:
    """GET /profile/me with a valid token → 200 with profile fields."""
    token = await register_and_login(client)
    resp = await client.get(
        "/profile/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "testuser"
    assert body["email"] == "test@test.com"
    assert "has_selfie" in body
    assert "created_at" in body
