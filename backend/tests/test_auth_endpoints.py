from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.domain.user import User, UserRole, UserStatus

pytestmark = pytest.mark.asyncio


# --- Helper to create a user directly in the DB via API ---

async def _bootstrap(client: AsyncClient) -> dict:
    """Bootstrap the first admin user. Returns the user dict."""
    with patch("src.routers.auth.create_registration_options") as mock_reg_opts:
        mock_reg_opts.return_value = ({"mock": "options"}, b"test-challenge")
        resp = await client.post("/api/v1/auth/bootstrap", json={
            "username": "admin", "display_name": "Admin User",
        })
    assert resp.status_code == 200
    return resp.json()


async def _register_verify(client: AsyncClient, username: str) -> dict:
    """Complete registration verification with mocked WebAuthn."""
    with patch("src.routers.auth.verify_registration") as mock_verify:
        mock_verify.return_value = ("cred-id-123", b"public-key-bytes", 0)
        with patch("src.routers.auth._read_challenge_cookie") as mock_challenge:
            mock_challenge.return_value = b"test-challenge"
            resp = await client.post("/api/v1/auth/register/verify", json={
                "username": username,
                "credential": {"mock": "credential"},
            })
    assert resp.status_code == 200
    return resp.json()


# --- Tests ---

async def test_me_without_session_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_bootstrap_creates_admin(client: AsyncClient):
    result = await _bootstrap(client)
    user = result["user"]
    assert user["role"] == "ADMIN"
    assert user["status"] == "PENDING"
    assert user["username"] == "admin"


async def test_bootstrap_returns_409_when_users_exist(client: AsyncClient):
    await _bootstrap(client)
    resp = await client.post("/api/v1/auth/bootstrap", json={
        "username": "admin2", "display_name": "Admin 2",
    })
    assert resp.status_code == 409


async def test_register_verify_activates_user_and_sets_session(client: AsyncClient):
    await _bootstrap(client)
    result = await _register_verify(client, "admin")
    user = result["user"]
    assert user["status"] == "ACTIVE"
    assert user["role"] == "ADMIN"


async def test_register_options_unknown_user_returns_404(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register/options", json={"username": "nobody"})
    assert resp.status_code == 404


async def test_logout_clears_session(client: AsyncClient):
    await _bootstrap(client)
    await _register_verify(client, "admin")
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # After logout, me should return 401
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_invite_requires_admin(client: AsyncClient):
    # No session - should get 403
    resp = await client.post("/api/v1/users/invite", json={
        "username": "newuser", "display_name": "New", "role": "SM",
    })
    assert resp.status_code == 403


async def test_login_options_pending_user_returns_403(client: AsyncClient):
    await _bootstrap(client)
    resp = await client.post("/api/v1/auth/login/options", json={"username": "admin"})
    assert resp.status_code == 403
    assert "pending" in resp.json()["detail"].lower()
