from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.domain.user import User, UserRole, UserStatus

pytestmark = pytest.mark.asyncio


async def _seed_user(
    client: AsyncClient,
    *,
    username: str,
    display_name: str,
    role: UserRole,
    status: UserStatus,
    vendor_id: str | None = None,
) -> User:
    from src.main import app
    from src.routers.auth import get_user_repo as auth_get_user_repo

    override = app.dependency_overrides[auth_get_user_repo]
    async for repo in override():
        if status is UserStatus.ACTIVE:
            user = User.create(
                username=username,
                display_name=display_name,
                role=role,
                vendor_id=vendor_id,
            )
        else:
            user = User.invite(
                username=username,
                display_name=display_name,
                role=role,
                vendor_id=vendor_id,
            )
            if status is UserStatus.INACTIVE:
                user.deactivate()
        await repo.save(user)
        return user
    raise RuntimeError("override did not yield a repo")


async def _seed_active_user_with_credential(
    client: AsyncClient,
    *,
    username: str,
    display_name: str,
    role: UserRole,
) -> User:
    # Seeds an ACTIVE user and parks one webauthn_credentials row so the
    # reset-credentials handler has something to delete. Goes through the
    # repo directly to avoid the bootstrap → register-verify dance.
    from src.main import app
    from src.routers.auth import get_user_repo as auth_get_user_repo

    override = app.dependency_overrides[auth_get_user_repo]
    async for repo in override():
        user = User.create(
            username=username,
            display_name=display_name,
            role=role,
        )
        await repo.save(user)
        await repo.save_credential(
            credential_id=f"cred-{username}",
            user_id=user.id,
            public_key=b"public-key-bytes",
            sign_count=0,
        )
        return user
    raise RuntimeError("override did not yield a repo")


async def _credentials_for(client: AsyncClient, user_id: str) -> list:
    from src.main import app
    from src.routers.auth import get_user_repo as auth_get_user_repo

    override = app.dependency_overrides[auth_get_user_repo]
    async for repo in override():
        return await repo.get_credentials_by_user_id(user_id)
    raise RuntimeError("override did not yield a repo")


async def _login_as(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    username: str,
) -> None:
    monkeypatch.setenv("DEV_AUTH", "1")
    resp = await client.post("/api/v1/auth/dev-login", json={"username": username})
    assert resp.status_code == 200, resp.text


# --- reset-credentials ---


async def test_reset_credentials_active_to_pending_with_new_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    # Second admin so the last-active-admin guard does not fire on Bob.
    await _seed_user(
        client,
        username="alice2",
        display_name="Alice2",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    bob = await _seed_active_user_with_credential(
        client, username="bob", display_name="Bob SM", role=UserRole.SM
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{bob.id}/reset-credentials")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["status"] == "PENDING"
    assert body["invite_token"]
    # Credentials gone.
    assert await _credentials_for(client, bob.id) == []


async def test_reset_credentials_inactive_to_pending(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    inactive = await _seed_user(
        client,
        username="ian",
        display_name="Ian Inactive",
        role=UserRole.SM,
        status=UserStatus.INACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{inactive.id}/reset-credentials")
    assert resp.status_code == 200
    assert resp.json()["user"]["status"] == "PENDING"


async def test_reset_credentials_returns_409_on_already_pending(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    pat = await _seed_user(
        client,
        username="pat",
        display_name="Pending Pat",
        role=UserRole.SM,
        status=UserStatus.PENDING,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{pat.id}/reset-credentials")
    assert resp.status_code == 409
    assert "already" in resp.json()["detail"].lower()


async def test_reset_credentials_returns_409_on_last_active_admin_self(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    alice = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    # PENDING admin does not count toward the active pool — confirms the iter
    # 095 active-only count rule applies here too.
    await _seed_user(
        client,
        username="pending-admin",
        display_name="Pending Admin",
        role=UserRole.ADMIN,
        status=UserStatus.PENDING,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{alice.id}/reset-credentials")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "cannot reset credentials for the last active admin"


async def test_reset_credentials_self_succeeds_with_two_active_admins(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    alice = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _seed_user(
        client,
        username="alice2",
        display_name="Alice2",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{alice.id}/reset-credentials")
    assert resp.status_code == 200
    assert resp.json()["user"]["status"] == "PENDING"
    # Calling session is now bound to a PENDING user — middleware rejects.
    me_resp = await client.get("/api/v1/auth/me")
    assert me_resp.status_code == 401


async def test_reset_credentials_returns_403_for_non_admin(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    erin = await _seed_user(
        client,
        username="erin",
        display_name="Erin SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    target = await _seed_user(
        client,
        username="target",
        display_name="Target",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "erin")
    resp = await client.post(f"/api/v1/users/{target.id}/reset-credentials")
    assert resp.status_code == 403


async def test_reset_credentials_returns_404_on_unknown(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(
        "/api/v1/users/00000000-0000-0000-0000-000000000000/reset-credentials"
    )
    assert resp.status_code == 404


async def test_reset_credentials_breaks_login_until_re_register(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _seed_user(
        client,
        username="alice2",
        display_name="Alice2",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    bob = await _seed_active_user_with_credential(
        client, username="bob", display_name="Bob SM", role=UserRole.SM
    )
    await _login_as(client, monkeypatch, "alice")
    await client.post(f"/api/v1/users/{bob.id}/reset-credentials")

    # login/options on a PENDING user returns 403 (iter-030 status guard
    # fires before the credential-count check). Login is broken by status,
    # not by credential absence — both are downstream of reset.
    resp = await client.post("/api/v1/auth/login/options", json={"username": "bob"})
    assert resp.status_code == 403
    assert "pending" in resp.json()["detail"].lower()


async def test_reset_credentials_new_token_unlocks_register_options(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _seed_user(
        client,
        username="alice2",
        display_name="Alice2",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    bob = await _seed_active_user_with_credential(
        client, username="bob", display_name="Bob SM", role=UserRole.SM
    )
    await _login_as(client, monkeypatch, "alice")
    reset_resp = await client.post(f"/api/v1/users/{bob.id}/reset-credentials")
    new_token = reset_resp.json()["invite_token"]

    with patch("src.routers.auth.create_registration_options") as mock_reg_opts:
        mock_reg_opts.return_value = ({"mock": "options"}, b"test-challenge")
        opts_resp = await client.post(
            "/api/v1/auth/register/options", json={"token": new_token}
        )
    assert opts_resp.status_code == 200
    assert opts_resp.json()["user"]["username"] == "bob"


# --- reissue-invite ---


async def test_reissue_invite_pending_returns_new_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    pat = await _seed_user(
        client,
        username="pat",
        display_name="Pending Pat",
        role=UserRole.SM,
        status=UserStatus.PENDING,
    )
    original_token = pat.invite_token
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{pat.id}/reissue-invite")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["status"] == "PENDING"
    assert body["invite_token"] != original_token


async def test_reissue_invite_invalidates_old_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    pat = await _seed_user(
        client,
        username="pat",
        display_name="Pending Pat",
        role=UserRole.SM,
        status=UserStatus.PENDING,
    )
    old_token = pat.invite_token
    await _login_as(client, monkeypatch, "alice")
    await client.post(f"/api/v1/users/{pat.id}/reissue-invite")

    # Old token no longer resolves to the user.
    resp = await client.post(
        "/api/v1/auth/register/options", json={"token": old_token}
    )
    assert resp.status_code == 404


async def test_reissue_invite_new_token_works(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    pat = await _seed_user(
        client,
        username="pat",
        display_name="Pending Pat",
        role=UserRole.SM,
        status=UserStatus.PENDING,
    )
    await _login_as(client, monkeypatch, "alice")
    reissue_resp = await client.post(f"/api/v1/users/{pat.id}/reissue-invite")
    new_token = reissue_resp.json()["invite_token"]

    with patch("src.routers.auth.create_registration_options") as mock_reg_opts:
        mock_reg_opts.return_value = ({"mock": "options"}, b"test-challenge")
        opts_resp = await client.post(
            "/api/v1/auth/register/options", json={"token": new_token}
        )
    assert opts_resp.status_code == 200


async def test_reissue_invite_returns_409_on_active(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    bob = await _seed_user(
        client,
        username="bob",
        display_name="Bob SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{bob.id}/reissue-invite")
    assert resp.status_code == 409


async def test_reissue_invite_returns_409_on_inactive(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    inactive = await _seed_user(
        client,
        username="ian",
        display_name="Ian Inactive",
        role=UserRole.SM,
        status=UserStatus.INACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{inactive.id}/reissue-invite")
    assert resp.status_code == 409


async def test_reissue_invite_returns_403_for_non_admin(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    erin = await _seed_user(
        client,
        username="erin",
        display_name="Erin SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    target = await _seed_user(
        client,
        username="pat",
        display_name="Pending Pat",
        role=UserRole.SM,
        status=UserStatus.PENDING,
    )
    await _login_as(client, monkeypatch, "erin")
    resp = await client.post(f"/api/v1/users/{target.id}/reissue-invite")
    assert resp.status_code == 403


async def test_reissue_invite_returns_404_on_unknown(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(
        "/api/v1/users/00000000-0000-0000-0000-000000000000/reissue-invite"
    )
    assert resp.status_code == 404


# --- domain unit tests ---


async def test_domain_reset_credentials_active_to_pending_allocates_token():
    user = User.create(username="alice", display_name="Alice", role=UserRole.SM)
    assert user.status is UserStatus.ACTIVE
    assert user.invite_token is None
    user.reset_credentials()
    assert user.status is UserStatus.PENDING
    assert user.invite_token is not None


async def test_domain_reset_credentials_inactive_to_pending():
    user = User.invite(username="alice", display_name="Alice", role=UserRole.SM)
    user.deactivate()
    assert user.status is UserStatus.INACTIVE
    user.reset_credentials()
    assert user.status is UserStatus.PENDING
    assert user.invite_token is not None


async def test_domain_reset_credentials_rejects_pending():
    user = User.invite(username="alice", display_name="Alice", role=UserRole.SM)
    with pytest.raises(ValueError, match="already PENDING"):
        user.reset_credentials()


async def test_domain_reissue_invite_rotates_token():
    user = User.invite(username="alice", display_name="Alice", role=UserRole.SM)
    original = user.invite_token
    user.reissue_invite()
    assert user.invite_token != original
    assert user.status is UserStatus.PENDING


async def test_domain_reissue_invite_rejects_active():
    user = User.create(username="alice", display_name="Alice", role=UserRole.SM)
    with pytest.raises(ValueError, match="only PENDING"):
        user.reissue_invite()


async def test_domain_reissue_invite_rejects_inactive():
    user = User.invite(username="alice", display_name="Alice", role=UserRole.SM)
    user.deactivate()
    with pytest.raises(ValueError, match="only PENDING"):
        user.reissue_invite()
