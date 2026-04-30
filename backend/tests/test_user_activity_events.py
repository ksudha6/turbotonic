from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.activity import ActivityEvent, EntityType
from src.domain.user import User, UserRole, UserStatus

pytestmark = pytest.mark.asyncio


# Reuses the same dev-login + dependency-override harness as test_user_management.py.
# A separate _seed_user lives here rather than importing from the sibling test
# file because pytest does not export module-level helpers between test files
# without packaging them under tests/, and the shape is small enough that
# duplication is cheaper than an indirection.


async def _seed_user(
    client: AsyncClient,
    *,
    username: str,
    display_name: str,
    role: UserRole,
    status: UserStatus,
    vendor_id: str | None = None,
    email: str | None = None,
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
                email=email,
            )
        else:
            user = User.invite(
                username=username,
                display_name=display_name,
                role=role,
                vendor_id=vendor_id,
                email=email,
            )
            if status is UserStatus.INACTIVE:
                user.deactivate()
        await repo.save(user)
        return user
    raise RuntimeError("override did not yield a repo")


async def _activity_rows_for(client: AsyncClient, user_id: str) -> list:
    # Reads activity_log rows scoped to the USER aggregate via the same
    # dependency-overridden repo the routers use, so the test sees the rows
    # written inside the same in-transaction connection.
    from src.main import app
    from src.routers.auth import get_activity_repo as auth_get_activity_repo

    override = app.dependency_overrides[auth_get_activity_repo]
    async for repo in override():
        return await repo.list_for_entity(EntityType.USER, user_id)
    raise RuntimeError("override did not yield a repo")


async def _login_as(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    username: str,
) -> None:
    monkeypatch.setenv("DEV_AUTH", "1")
    resp = await client.post("/api/v1/auth/dev-login", json={"username": username})
    assert resp.status_code == 200, resp.text


# --- happy paths: one row per success ---


async def test_patch_user_emits_user_updated(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    alice = await _seed_user(
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
    resp = await client.patch(
        f"/api/v1/users/{bob.id}", json={"display_name": "Robert SM"}
    )
    assert resp.status_code == 200

    rows = await _activity_rows_for(client, bob.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type is EntityType.USER
    assert row.entity_id == bob.id
    assert row.event is ActivityEvent.USER_UPDATED
    assert row.actor_id == alice.id
    assert "bob" in (row.detail or "")


async def test_deactivate_emits_user_deactivated(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    alice = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    # Second admin so the last-active-admin guard does not preempt Bob.
    await _seed_user(
        client,
        username="alice2",
        display_name="Alice2 Admin",
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
    resp = await client.post(f"/api/v1/users/{bob.id}/deactivate")
    assert resp.status_code == 200

    rows = await _activity_rows_for(client, bob.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type is EntityType.USER
    assert row.entity_id == bob.id
    assert row.event is ActivityEvent.USER_DEACTIVATED
    assert row.actor_id == alice.id
    assert "bob" in (row.detail or "")


async def test_reactivate_emits_user_reactivated(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    alice = await _seed_user(
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
    resp = await client.post(f"/api/v1/users/{inactive.id}/reactivate")
    assert resp.status_code == 200

    rows = await _activity_rows_for(client, inactive.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type is EntityType.USER
    assert row.entity_id == inactive.id
    assert row.event is ActivityEvent.USER_REACTIVATED
    assert row.actor_id == alice.id
    assert "ian" in (row.detail or "")


async def test_reset_credentials_emits_user_credentials_reset(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    alice = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    # Second admin so resetting Bob does not trip the last-active-admin guard.
    await _seed_user(
        client,
        username="alice2",
        display_name="Alice2 Admin",
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
    resp = await client.post(f"/api/v1/users/{bob.id}/reset-credentials")
    assert resp.status_code == 200

    rows = await _activity_rows_for(client, bob.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type is EntityType.USER
    assert row.entity_id == bob.id
    assert row.event is ActivityEvent.USER_CREDENTIALS_RESET
    assert row.actor_id == alice.id
    assert "bob" in (row.detail or "")


async def test_reissue_invite_emits_user_invite_reissued(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    alice = await _seed_user(
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
    resp = await client.post(f"/api/v1/users/{pat.id}/reissue-invite")
    assert resp.status_code == 200

    rows = await _activity_rows_for(client, pat.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type is EntityType.USER
    assert row.entity_id == pat.id
    assert row.event is ActivityEvent.USER_INVITE_REISSUED
    assert row.actor_id == alice.id
    assert "pat" in (row.detail or "")


# --- negative paths: 409 emits zero rows ---


async def test_failed_deactivate_last_admin_does_not_emit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # Single ACTIVE admin trying to deactivate themselves trips the
    # last-active-admin guard. The guard runs before the activity append, so
    # no row should land on the target.
    alice = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{alice.id}/deactivate")
    assert resp.status_code == 409

    rows = await _activity_rows_for(client, alice.id)
    assert rows == []


async def test_failed_reset_credentials_on_pending_does_not_emit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # PENDING users cannot be reset (use reissue-invite). The 409 path runs
    # before the activity append, so no row should land on the target.
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

    rows = await _activity_rows_for(client, pat.id)
    assert rows == []
