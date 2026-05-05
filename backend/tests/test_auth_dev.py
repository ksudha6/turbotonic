from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.auth.session import COOKIE_NAME
from src.domain.user import User, UserRole, UserStatus
from src.domain.vendor import Vendor, VendorType

pytestmark = pytest.mark.asyncio


# Resolve the UserRepository bound to the test connection via the dependency
# override the conftest installed. This mirrors how the real handler resolves
# its repo, so seeded users land in the same in-transaction DB the endpoint
# reads from.
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


async def _seed_vendor(client: AsyncClient) -> str:
    # Returns the vendor id of a freshly inserted ACTIVE vendor so tests that
    # need a VENDOR-role user can satisfy the users.vendor_id FK constraint.
    from src.main import app
    from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo

    override = app.dependency_overrides[vendor_get_vendor_repo]
    async for repo in override():
        vendor = Vendor.create(
            name="Carol Vendor Co",
            country="US",
            vendor_type=VendorType.PROCUREMENT,
        )
        await repo.save(vendor)
        return vendor.id
    raise RuntimeError("vendor override did not yield a repo")


# --- /api/v1/auth/dev-login ---


async def test_dev_login_returns_404_when_dev_auth_unset(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("DEV_AUTH", raising=False)
    resp = await client.post("/api/v1/auth/dev-login", json={"username": "alice"})
    assert resp.status_code == 404


async def test_dev_login_returns_404_when_dev_auth_not_one(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DEV_AUTH", "0")
    resp = await client.post("/api/v1/auth/dev-login", json={"username": "alice"})
    assert resp.status_code == 404


async def test_dev_login_creates_session_for_active_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DEV_AUTH", "1")
    alice = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    expected_user = {
        "id": alice.id,
        "username": "alice",
        "display_name": "Alice Admin",
        "role": "ADMIN",
        "status": "ACTIVE",
        "vendor_id": None,
        "email": None,
        "brand_ids": [],
    }

    resp = await client.post("/api/v1/auth/dev-login", json={"username": "alice"})

    assert resp.status_code == 200
    assert resp.json() == {"user": expected_user}
    assert COOKIE_NAME in resp.cookies

    # Session cookie now resolves to alice on /me.
    me_resp = await client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json() == {"user": expected_user}


async def test_dev_login_rejects_unknown_username(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DEV_AUTH", "1")
    resp = await client.post("/api/v1/auth/dev-login", json={"username": "ghost"})
    assert resp.status_code == 404


async def test_dev_login_rejects_inactive_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DEV_AUTH", "1")
    await _seed_user(
        client,
        username="pending-pat",
        display_name="Pending Pat",
        role=UserRole.SM,
        status=UserStatus.PENDING,
    )
    resp = await client.post(
        "/api/v1/auth/dev-login", json={"username": "pending-pat"}
    )
    assert resp.status_code == 404


# --- /api/v1/auth/dev-users ---


async def test_dev_users_returns_404_when_flag_unset(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("DEV_AUTH", raising=False)
    resp = await client.get("/api/v1/auth/dev-users")
    assert resp.status_code == 404


async def test_dev_users_lists_active_users_alphabetically(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DEV_AUTH", "1")

    vendor_id = await _seed_vendor(client)

    # Seed deliberately out of alphabetical order to prove the endpoint sorts.
    seeded = [
        ("frank", "Frank FM", UserRole.FREIGHT_MANAGER, UserStatus.ACTIVE, None),
        ("alice", "Alice Admin", UserRole.ADMIN, UserStatus.ACTIVE, None),
        ("dave", "Dave Lab", UserRole.QUALITY_LAB, UserStatus.ACTIVE, None),
        ("bob", "Bob Procurement", UserRole.PROCUREMENT_MANAGER, UserStatus.ACTIVE, None),
        ("erin", "Erin SM", UserRole.SM, UserStatus.ACTIVE, None),
        # Pending user is excluded from the list.
        ("ghost", "Ghost Pending", UserRole.SM, UserStatus.PENDING, None),
        # Vendor users are included alongside SM/ADMIN.
        ("carol", "Carol Vendor", UserRole.VENDOR, UserStatus.ACTIVE, vendor_id),
    ]
    for username, display_name, role, status, vendor_id in seeded:
        await _seed_user(
            client,
            username=username,
            display_name=display_name,
            role=role,
            status=status,
            vendor_id=vendor_id,
        )

    resp = await client.get("/api/v1/auth/dev-users")
    assert resp.status_code == 200
    body = resp.json()
    assert body == [
        {"username": "alice", "display_name": "Alice Admin", "role": "ADMIN"},
        {"username": "bob", "display_name": "Bob Procurement", "role": "PROCUREMENT_MANAGER"},
        {"username": "carol", "display_name": "Carol Vendor", "role": "VENDOR"},
        {"username": "dave", "display_name": "Dave Lab", "role": "QUALITY_LAB"},
        {"username": "erin", "display_name": "Erin SM", "role": "SM"},
        {"username": "frank", "display_name": "Frank FM", "role": "FREIGHT_MANAGER"},
    ]
