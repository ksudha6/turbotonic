from __future__ import annotations

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
    email: str | None = None,
) -> User:
    # Resolves the UserRepository bound to the test connection through the
    # dependency override the conftest installed, so seeded users land in the
    # same in-transaction DB the endpoints read from.
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


async def _login_as(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    username: str,
) -> None:
    monkeypatch.setenv("DEV_AUTH", "1")
    resp = await client.post("/api/v1/auth/dev-login", json={"username": username})
    assert resp.status_code == 200, resp.text


# --- list users ---


async def test_list_users_returns_403_when_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/users/")
    assert resp.status_code == 403


async def test_list_users_returns_403_for_non_admin(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="erin",
        display_name="Erin SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "erin")
    resp = await client.get("/api/v1/users/")
    assert resp.status_code == 403


async def test_list_users_as_admin_returns_all(
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
        username="bob",
        display_name="Bob SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _seed_user(
        client,
        username="carol",
        display_name="Carol PM",
        role=UserRole.PROCUREMENT_MANAGER,
        status=UserStatus.PENDING,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.get("/api/v1/users/")
    assert resp.status_code == 200
    body = resp.json()
    usernames = [u["username"] for u in body["users"]]
    assert usernames == ["alice", "bob", "carol"]


async def test_list_users_filters_by_status(
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
        username="pending-pat",
        display_name="Pending Pat",
        role=UserRole.SM,
        status=UserStatus.PENDING,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.get("/api/v1/users/?status=PENDING")
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()["users"]]
    assert usernames == ["pending-pat"]


async def test_list_users_filters_by_role(
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
        username="bob",
        display_name="Bob SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.get("/api/v1/users/?role=SM")
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()["users"]]
    assert usernames == ["bob"]


async def test_list_users_filters_compose_status_and_role(
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
        username="bob-active-sm",
        display_name="Bob Active SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _seed_user(
        client,
        username="carol-pending-sm",
        display_name="Carol Pending SM",
        role=UserRole.SM,
        status=UserStatus.PENDING,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.get("/api/v1/users/?status=ACTIVE&role=SM")
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()["users"]]
    assert usernames == ["bob-active-sm"]


async def test_list_users_rejects_invalid_status(
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
    resp = await client.get("/api/v1/users/?status=BOGUS")
    assert resp.status_code == 422


# --- get user ---


async def test_get_user_returns_403_for_non_admin(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    erin = await _seed_user(
        client,
        username="erin",
        display_name="Erin SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "erin")
    resp = await client.get(f"/api/v1/users/{erin.id}")
    assert resp.status_code == 403


async def test_get_user_returns_404_on_unknown(
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
    resp = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_get_user_as_admin_returns_user(
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
        email="bob@example.com",
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.get(f"/api/v1/users/{bob.id}")
    assert resp.status_code == 200
    assert resp.json() == {
        "user": {
            "id": bob.id,
            "username": "bob",
            "display_name": "Bob SM",
            "role": "SM",
            "status": "ACTIVE",
            "vendor_id": None,
            "email": "bob@example.com",
            "brand_ids": [],
        }
    }


# --- patch user ---


async def test_patch_user_updates_display_name(
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
        email="bob@example.com",
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.patch(
        f"/api/v1/users/{bob.id}", json={"display_name": "Robert SM"}
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["display_name"] == "Robert SM"
    # Re-fetch confirms persistence and that other fields are untouched.
    refetch = await client.get(f"/api/v1/users/{bob.id}")
    assert refetch.json()["user"] == {
        "id": bob.id,
        "username": "bob",
        "display_name": "Robert SM",
        "role": "SM",
        "status": "ACTIVE",
        "vendor_id": None,
        "email": "bob@example.com",
        "brand_ids": [],
    }


async def test_patch_user_updates_email(
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
    resp = await client.patch(
        f"/api/v1/users/{bob.id}", json={"email": "bob@example.com"}
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "bob@example.com"


async def test_patch_user_clears_email_with_null(
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
        email="bob@example.com",
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.patch(f"/api/v1/users/{bob.id}", json={"email": None})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] is None


async def test_patch_user_rejects_empty_display_name(
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
    resp = await client.patch(f"/api/v1/users/{bob.id}", json={"display_name": ""})
    assert resp.status_code == 422


async def test_patch_user_rejects_whitespace_display_name(
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
    resp = await client.patch(
        f"/api/v1/users/{bob.id}", json={"display_name": "   "}
    )
    assert resp.status_code == 422


async def test_patch_user_returns_404_on_unknown(
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
    resp = await client.patch(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        json={"display_name": "Ghost"},
    )
    assert resp.status_code == 404


async def test_patch_user_returns_403_for_non_admin(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    erin = await _seed_user(
        client,
        username="erin",
        display_name="Erin SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "erin")
    resp = await client.patch(
        f"/api/v1/users/{erin.id}", json={"display_name": "Erin Smith"}
    )
    assert resp.status_code == 403


# --- deactivate user ---


async def test_deactivate_user_active_to_inactive(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # Two admins so the last-admin guard does not preempt the test target.
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
    assert resp.json()["user"]["status"] == "INACTIVE"


async def test_deactivate_user_pending_to_inactive(
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
    resp = await client.post(f"/api/v1/users/{pat.id}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["user"]["status"] == "INACTIVE"


async def test_deactivate_user_returns_409_on_already_inactive(
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
    resp = await client.post(f"/api/v1/users/{inactive.id}/deactivate")
    assert resp.status_code == 409
    assert "already" in resp.json()["detail"].lower()


async def test_deactivate_user_returns_409_on_self_deactivate(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # Two admins so self-deactivate (not last-admin) is the guard that fires.
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
        display_name="Alice2 Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{alice.id}/deactivate")
    assert resp.status_code == 409
    assert "yourself" in resp.json()["detail"].lower()


async def test_deactivate_user_returns_409_on_last_active_admin(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # Single ACTIVE admin; trying to deactivate them (themselves) trips the
    # last-admin guard before the self-deactivate guard.
    alice = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    # A PENDING admin does not count toward the active pool.
    await _seed_user(
        client,
        username="pending-admin",
        display_name="Pending Admin",
        role=UserRole.ADMIN,
        status=UserStatus.PENDING,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{alice.id}/deactivate")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "cannot deactivate the last active admin"


async def test_deactivate_user_succeeds_with_two_active_admins(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    other_admin = await _seed_user(
        client,
        username="alice2",
        display_name="Alice2 Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{other_admin.id}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["user"]["status"] == "INACTIVE"


async def test_deactivate_user_returns_403_for_non_admin(
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
        display_name="Target SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "erin")
    resp = await client.post(f"/api/v1/users/{target.id}/deactivate")
    assert resp.status_code == 403


async def test_deactivate_user_returns_404_on_unknown(
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
        "/api/v1/users/00000000-0000-0000-0000-000000000000/deactivate"
    )
    assert resp.status_code == 404


# --- reactivate user ---


async def test_reactivate_user_inactive_to_active(
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
    resp = await client.post(f"/api/v1/users/{inactive.id}/reactivate")
    assert resp.status_code == 200
    assert resp.json()["user"]["status"] == "ACTIVE"


async def test_reactivate_user_returns_409_on_already_active(
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
    resp = await client.post(f"/api/v1/users/{bob.id}/reactivate")
    assert resp.status_code == 409


async def test_reactivate_user_returns_409_on_pending(
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
    resp = await client.post(f"/api/v1/users/{pat.id}/reactivate")
    assert resp.status_code == 409


async def test_reactivate_user_returns_403_for_non_admin(
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
        display_name="Target SM",
        role=UserRole.SM,
        status=UserStatus.INACTIVE,
    )
    await _login_as(client, monkeypatch, "erin")
    resp = await client.post(f"/api/v1/users/{target.id}/reactivate")
    assert resp.status_code == 403


async def test_reactivate_user_returns_404_on_unknown(
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
        "/api/v1/users/00000000-0000-0000-0000-000000000000/reactivate"
    )
    assert resp.status_code == 404


# --- invite endpoint route-ordering smoke test ---


async def test_invite_route_still_distinct_from_user_id_route(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # POST /api/v1/users/invite must not be swallowed by /{user_id}/...
    # patterns. This guards against regressions from new routes registered
    # ahead of /invite.
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(
        "/api/v1/users/invite",
        json={
            "username": "newcomer",
            "display_name": "Newcomer",
            "role": "SM",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "newcomer"
    assert resp.json()["user"]["status"] == "PENDING"
