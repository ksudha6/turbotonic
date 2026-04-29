from __future__ import annotations

import re
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.domain.user import User, UserRole, UserStatus

pytestmark = pytest.mark.asyncio

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


async def _bootstrap_admin(client: AsyncClient) -> dict:
    with patch("src.routers.auth.create_registration_options") as mock_reg_opts:
        mock_reg_opts.return_value = ({"mock": "options"}, b"test-challenge")
        resp = await client.post(
            "/api/v1/auth/bootstrap",
            json={"username": "admin", "display_name": "Admin User"},
        )
    assert resp.status_code == 200
    return resp.json()


async def _register_admin(client: AsyncClient, token: str) -> dict:
    with patch("src.routers.auth.verify_registration") as mock_verify:
        mock_verify.return_value = ("cred-id-bootstrap", b"public-key", 0)
        with patch("src.routers.auth._read_challenge_cookie") as mock_challenge:
            mock_challenge.return_value = b"test-challenge"
            resp = await client.post(
                "/api/v1/auth/register/verify",
                json={"token": token, "credential": {"mock": "credential"}},
            )
    assert resp.status_code == 200
    return resp.json()


async def _seed_pending(
    client: AsyncClient,
    *,
    username: str,
    role: UserRole,
    vendor_id: str | None = None,
) -> User:
    # Drives a PENDING user via the dependency-overridden repo so the seeded
    # row is in the same in-transaction DB the endpoints read from. Avoids
    # going through /invite (which itself is exercised by other tests here).
    from src.main import app
    from src.routers.auth import get_user_repo as auth_get_user_repo

    override = app.dependency_overrides[auth_get_user_repo]
    async for repo in override():
        user = User.invite(
            username=username,
            display_name=f"{username} display",
            role=role,
            vendor_id=vendor_id,
        )
        await repo.save(user)
        return user
    raise RuntimeError("override did not yield a repo")


# --- bootstrap returns invite_token ---


async def test_bootstrap_returns_invite_token(client: AsyncClient):
    body = await _bootstrap_admin(client)
    assert "invite_token" in body
    assert UUID_PATTERN.match(body["invite_token"])
    # The user dict itself does NOT carry the token. The token is a secret
    # and only escapes at the moment of invite/bootstrap.
    assert "invite_token" not in body["user"]


# --- invite returns invite_token ---


async def test_invite_returns_invite_token(client: AsyncClient):
    bootstrap_resp = await _bootstrap_admin(client)
    await _register_admin(client, bootstrap_resp["invite_token"])
    invite_resp = await client.post(
        "/api/v1/users/invite",
        json={"username": "newcomer", "display_name": "Newcomer", "role": "SM"},
    )
    assert invite_resp.status_code == 200
    body = invite_resp.json()
    assert "invite_token" in body
    assert UUID_PATTERN.match(body["invite_token"])
    assert "invite_token" not in body["user"]


# --- register/options keyed on token ---


async def test_register_options_with_valid_token_returns_options(client: AsyncClient):
    bootstrap_resp = await _bootstrap_admin(client)
    token = bootstrap_resp["invite_token"]
    with patch("src.routers.auth.create_registration_options") as mock_reg_opts:
        mock_reg_opts.return_value = ({"mock": "options"}, b"test-challenge")
        resp = await client.post(
            "/api/v1/auth/register/options", json={"token": token}
        )
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "admin"


async def test_register_options_unknown_token_returns_404(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register/options",
        json={"token": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404


async def test_register_options_username_no_longer_accepted(client: AsyncClient):
    # Sending {"username": ...} with no token must be rejected by pydantic
    # validation (422), not silently fall through to a username lookup. This
    # locks the legacy path closed.
    resp = await client.post(
        "/api/v1/auth/register/options", json={"username": "admin"}
    )
    assert resp.status_code == 422


# --- register/verify keyed on token, clears it ---


async def test_register_verify_clears_invite_token(client: AsyncClient):
    bootstrap_resp = await _bootstrap_admin(client)
    token = bootstrap_resp["invite_token"]
    await _register_admin(client, token)

    # The token must be unusable on a second call. The router should look up
    # by token, find nothing (cleared), and 404.
    with patch("src.routers.auth.verify_registration") as mock_verify:
        mock_verify.return_value = ("cred-id-other", b"public-key", 0)
        with patch("src.routers.auth._read_challenge_cookie") as mock_challenge:
            mock_challenge.return_value = b"test-challenge"
            resp = await client.post(
                "/api/v1/auth/register/verify",
                json={"token": token, "credential": {"mock": "credential"}},
            )
    assert resp.status_code == 404


async def test_register_verify_unknown_token_returns_404(client: AsyncClient):
    with patch("src.routers.auth._read_challenge_cookie") as mock_challenge:
        mock_challenge.return_value = b"test-challenge"
        resp = await client.post(
            "/api/v1/auth/register/verify",
            json={
                "token": "00000000-0000-0000-0000-000000000000",
                "credential": {"mock": "credential"},
            },
        )
    assert resp.status_code == 404


async def test_register_verify_missing_token_returns_400(client: AsyncClient):
    with patch("src.routers.auth._read_challenge_cookie") as mock_challenge:
        mock_challenge.return_value = b"test-challenge"
        resp = await client.post(
            "/api/v1/auth/register/verify",
            json={"credential": {"mock": "credential"}},
        )
    assert resp.status_code == 400
    assert "token" in resp.json()["detail"].lower()


# --- second invitee can register with their own token ---


async def test_invitee_registers_via_their_own_token(client: AsyncClient):
    bootstrap_resp = await _bootstrap_admin(client)
    await _register_admin(client, bootstrap_resp["invite_token"])

    # ADMIN invites a new SM user; the response carries that user's own token.
    invite_resp = await client.post(
        "/api/v1/users/invite",
        json={"username": "sm-1", "display_name": "SM One", "role": "SM"},
    )
    assert invite_resp.status_code == 200
    sm_token = invite_resp.json()["invite_token"]
    assert sm_token != bootstrap_resp["invite_token"]

    # The invitee opens the link, register/options succeeds with their token.
    with patch("src.routers.auth.create_registration_options") as mock_reg_opts:
        mock_reg_opts.return_value = ({"mock": "options"}, b"test-challenge")
        opts_resp = await client.post(
            "/api/v1/auth/register/options", json={"token": sm_token}
        )
    assert opts_resp.status_code == 200
    assert opts_resp.json()["user"]["username"] == "sm-1"


# --- domain unit: User.activate clears the token ---


async def test_domain_activate_clears_invite_token():
    user = User.invite(
        username="alice",
        display_name="Alice",
        role=UserRole.SM,
    )
    assert user.invite_token is not None
    assert UUID_PATTERN.match(user.invite_token)
    user.activate()
    assert user.status is UserStatus.ACTIVE
    assert user.invite_token is None


async def test_domain_create_has_no_invite_token():
    # Active-from-start users (test fixtures, dev-login seeding) do not get
    # a token because they bypass the registration handshake entirely.
    user = User.create(
        username="dev",
        display_name="Dev",
        role=UserRole.ADMIN,
    )
    assert user.invite_token is None
