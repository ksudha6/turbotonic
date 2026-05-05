"""Iter 111: brand assignment via invite and PATCH /users endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import make_test_brand


pytestmark = pytest.mark.asyncio


async def _invite_user(
    client: AsyncClient,
    *,
    username: str = "testuser",
    role: str = "SM",
    brand_ids: list[str] | None = None,
) -> dict:
    payload: dict = {
        "username": username,
        "display_name": username,
        "role": role,
    }
    if brand_ids is not None:
        payload["brand_ids"] = brand_ids
    resp = await client.post("/api/v1/users/invite", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_invite_sm_with_brand_ids_assigns_brands(authenticated_client: AsyncClient):
    brand = await make_test_brand(authenticated_client, name="Brand-Alpha")
    brand_id = brand["id"]

    result = await _invite_user(
        authenticated_client,
        username="scoped-sm",
        role="SM",
        brand_ids=[brand_id],
    )
    user_id = result["user"]["id"]
    assert result["user"]["brand_ids"] == [brand_id]

    # Verify via GET
    get_resp = await authenticated_client.get(f"/api/v1/users/{user_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["user"]["brand_ids"] == [brand_id]


async def test_invite_vendor_brand_ids_ignored(authenticated_client: AsyncClient):
    """VENDOR role ignores brand_ids; brand_ids must be empty in response."""
    brand = await make_test_brand(authenticated_client, name="Brand-Vendor-Ignored")
    brand_id = brand["id"]

    # Need a vendor to attach the VENDOR user to
    vendor_resp = await authenticated_client.post(
        "/api/v1/vendors/",
        json={"name": "Test Vendor Bi", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor_resp.status_code == 201, vendor_resp.text
    vendor_id = vendor_resp.json()["id"]

    payload = {
        "username": "vendor-brand-ignored",
        "display_name": "Vendor Brand Ignored",
        "role": "VENDOR",
        "vendor_id": vendor_id,
        "brand_ids": [brand_id],
    }
    resp = await authenticated_client.post("/api/v1/users/invite", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["brand_ids"] == []


async def test_invite_admin_brand_ids_ignored(authenticated_client: AsyncClient):
    """ADMIN role ignores brand_ids."""
    brand = await make_test_brand(authenticated_client, name="Brand-Admin-Ignored")
    brand_id = brand["id"]

    payload = {
        "username": "admin-brand-ignored",
        "display_name": "Admin Brand Ignored",
        "role": "ADMIN",
        "brand_ids": [brand_id],
    }
    resp = await authenticated_client.post("/api/v1/users/invite", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["brand_ids"] == []


async def test_patch_user_sets_brands(authenticated_client: AsyncClient):
    brand_a = await make_test_brand(authenticated_client, name="Brand-PA")
    brand_b = await make_test_brand(authenticated_client, name="Brand-PB")

    invite = await _invite_user(authenticated_client, username="patch-sm", role="SM")
    user_id = invite["user"]["id"]

    patch_resp = await authenticated_client.patch(
        f"/api/v1/users/{user_id}",
        json={"brand_ids": [brand_a["id"], brand_b["id"]]},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assigned = sorted(patch_resp.json()["user"]["brand_ids"])
    assert assigned == sorted([brand_a["id"], brand_b["id"]])


async def test_patch_user_clears_brands(authenticated_client: AsyncClient):
    brand = await make_test_brand(authenticated_client, name="Brand-Clear")

    invite = await _invite_user(
        authenticated_client,
        username="clear-sm",
        role="SM",
        brand_ids=[brand["id"]],
    )
    user_id = invite["user"]["id"]

    # Clear all brands
    patch_resp = await authenticated_client.patch(
        f"/api/v1/users/{user_id}",
        json={"brand_ids": []},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["user"]["brand_ids"] == []


async def test_patch_user_no_brand_ids_key_unchanged(authenticated_client: AsyncClient):
    brand = await make_test_brand(authenticated_client, name="Brand-Unchanged")

    invite = await _invite_user(
        authenticated_client,
        username="unchanged-sm",
        role="SM",
        brand_ids=[brand["id"]],
    )
    user_id = invite["user"]["id"]

    # PATCH without brand_ids key — assignments must stay intact
    patch_resp = await authenticated_client.patch(
        f"/api/v1/users/{user_id}",
        json={"display_name": "Updated Name"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["user"]["brand_ids"] == [brand["id"]]


async def test_invite_unknown_brand_id_returns_404(authenticated_client: AsyncClient):
    payload = {
        "username": "sm-bad-brand",
        "display_name": "SM Bad Brand",
        "role": "SM",
        "brand_ids": ["nonexistent-brand-id"],
    }
    resp = await authenticated_client.post("/api/v1/users/invite", json=payload)
    assert resp.status_code == 404


async def test_brand_users_updated_event_emitted(authenticated_client: AsyncClient):
    brand = await make_test_brand(authenticated_client, name="Brand-Event")

    invite = await _invite_user(authenticated_client, username="event-sm", role="SM")
    user_id = invite["user"]["id"]

    await authenticated_client.patch(
        f"/api/v1/users/{user_id}",
        json={"brand_ids": [brand["id"]]},
    )

    activity_resp = await authenticated_client.get("/api/v1/activity/?limit=20")
    assert activity_resp.status_code == 200
    events = [e["event"] for e in activity_resp.json()]
    assert "BRAND_USERS_UPDATED" in events


async def test_list_users_includes_brand_ids(authenticated_client: AsyncClient):
    brand = await make_test_brand(authenticated_client, name="Brand-List")
    invite = await _invite_user(
        authenticated_client,
        username="list-sm",
        role="SM",
        brand_ids=[brand["id"]],
    )
    user_id = invite["user"]["id"]

    list_resp = await authenticated_client.get("/api/v1/users/")
    assert list_resp.status_code == 200
    users = list_resp.json()["users"]
    target = next((u for u in users if u["id"] == user_id), None)
    assert target is not None
    assert target["brand_ids"] == [brand["id"]]
