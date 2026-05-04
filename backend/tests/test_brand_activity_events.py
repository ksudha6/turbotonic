from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.activity import ActivityEvent, EntityType, TargetRole
from src.domain.user import User, UserRole, UserStatus
from src.domain.vendor import Vendor, VendorType

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BRAND_BASE: dict = {
    "name": "Event Brand",
    "legal_name": "Event Brand Legal",
    "address": "123 Event St",
    "country": "US",
    "tax_id": "",
}


async def _seed_user(
    client: AsyncClient,
    *,
    username: str,
    display_name: str,
    role: UserRole,
) -> User:
    from src.main import app
    from src.routers.auth import get_user_repo as auth_get_user_repo

    override = app.dependency_overrides[auth_get_user_repo]
    async for repo in override():
        user = User.create(username=username, display_name=display_name, role=role)
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


async def _activity_rows_for_brand(client: AsyncClient, brand_id: str) -> list:
    from src.main import app
    from src.routers.brands import get_activity_repo_for_brands as brands_get_activity_repo

    override = app.dependency_overrides[brands_get_activity_repo]
    async for repo in override():
        return await repo.list_for_entity(EntityType.BRAND, brand_id)
    raise RuntimeError("override did not yield a repo")


async def _make_vendor_direct(client: AsyncClient, name: str = "Event Vendor") -> dict:
    from src.main import app
    from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo

    override = app.dependency_overrides[vendor_get_vendor_repo]
    async for repo in override():
        vendor = Vendor.create(name=name, country="US", vendor_type=VendorType.PROCUREMENT)
        await repo.save(vendor)
        return {"id": vendor.id, "name": vendor.name}
    raise RuntimeError("override did not yield a repo")


# ---------------------------------------------------------------------------
# Event assertions
# ---------------------------------------------------------------------------


async def test_brand_created_event(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await _seed_user(client, username="admin_ev_create", display_name="Admin", role=UserRole.ADMIN)
    await _login_as(client, monkeypatch, "admin_ev_create")

    resp = await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Create Event Brand"})
    assert resp.status_code == 201
    brand_id = resp.json()["id"]

    rows = await _activity_rows_for_brand(client, brand_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type is EntityType.BRAND
    assert row.entity_id == brand_id
    assert row.event is ActivityEvent.BRAND_CREATED
    assert row.target_role is TargetRole.ADMIN
    assert row.actor_id == admin.id


async def test_brand_updated_event(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await _seed_user(client, username="admin_ev_update", display_name="Admin", role=UserRole.ADMIN)
    await _login_as(client, monkeypatch, "admin_ev_update")

    resp = await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Update Event Brand"})
    brand_id = resp.json()["id"]

    await client.patch(f"/api/v1/brands/{brand_id}", json={"legal_name": "Updated Legal"})

    rows = await _activity_rows_for_brand(client, brand_id)
    events = [r.event for r in rows]
    assert ActivityEvent.BRAND_UPDATED in events

    updated_row = next(r for r in rows if r.event is ActivityEvent.BRAND_UPDATED)
    assert updated_row.target_role is TargetRole.ADMIN
    assert updated_row.entity_type is EntityType.BRAND
    assert updated_row.actor_id == admin.id


async def test_brand_deactivated_event(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await _seed_user(client, username="admin_ev_deact", display_name="Admin", role=UserRole.ADMIN)
    await _login_as(client, monkeypatch, "admin_ev_deact")

    resp = await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Deactivate Event Brand"})
    brand_id = resp.json()["id"]

    await client.post(f"/api/v1/brands/{brand_id}/deactivate")

    rows = await _activity_rows_for_brand(client, brand_id)
    events = [r.event for r in rows]
    assert ActivityEvent.BRAND_DEACTIVATED in events

    deact_row = next(r for r in rows if r.event is ActivityEvent.BRAND_DEACTIVATED)
    assert deact_row.target_role is TargetRole.ADMIN
    assert deact_row.entity_type is EntityType.BRAND
    assert deact_row.actor_id == admin.id


async def test_brand_reactivated_event(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await _seed_user(client, username="admin_ev_react", display_name="Admin", role=UserRole.ADMIN)
    await _login_as(client, monkeypatch, "admin_ev_react")

    resp = await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Reactivate Event Brand"})
    brand_id = resp.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/deactivate")
    await client.post(f"/api/v1/brands/{brand_id}/reactivate")

    rows = await _activity_rows_for_brand(client, brand_id)
    events = [r.event for r in rows]
    assert ActivityEvent.BRAND_REACTIVATED in events

    react_row = next(r for r in rows if r.event is ActivityEvent.BRAND_REACTIVATED)
    assert react_row.target_role is TargetRole.ADMIN
    assert react_row.entity_type is EntityType.BRAND
    assert react_row.actor_id == admin.id


async def test_brand_vendor_assigned_event(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await _seed_user(client, username="admin_ev_assign", display_name="Admin", role=UserRole.ADMIN)
    await _login_as(client, monkeypatch, "admin_ev_assign")

    resp = await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Assign Event Brand"})
    brand_id = resp.json()["id"]

    vendor = await _make_vendor_direct(client, "Event Assign Vendor")
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor["id"]})

    rows = await _activity_rows_for_brand(client, brand_id)
    events = [r.event for r in rows]
    assert ActivityEvent.BRAND_VENDOR_ASSIGNED in events

    assign_row = next(r for r in rows if r.event is ActivityEvent.BRAND_VENDOR_ASSIGNED)
    assert assign_row.target_role is TargetRole.ADMIN
    assert assign_row.entity_type is EntityType.BRAND
    assert assign_row.entity_id == brand_id
    assert assign_row.actor_id == admin.id


async def test_brand_vendor_unassigned_event(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await _seed_user(client, username="admin_ev_unassign", display_name="Admin", role=UserRole.ADMIN)
    await _login_as(client, monkeypatch, "admin_ev_unassign")

    resp = await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Unassign Event Brand"})
    brand_id = resp.json()["id"]

    vendor = await _make_vendor_direct(client, "Event Unassign Vendor")
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor["id"]})
    await client.delete(f"/api/v1/brands/{brand_id}/vendors/{vendor['id']}")

    rows = await _activity_rows_for_brand(client, brand_id)
    events = [r.event for r in rows]
    assert ActivityEvent.BRAND_VENDOR_UNASSIGNED in events

    unassign_row = next(r for r in rows if r.event is ActivityEvent.BRAND_VENDOR_UNASSIGNED)
    assert unassign_row.target_role is TargetRole.ADMIN
    assert unassign_row.entity_type is EntityType.BRAND
    assert unassign_row.entity_id == brand_id
    assert unassign_row.actor_id == admin.id
