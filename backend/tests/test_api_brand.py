from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.user import User, UserRole, UserStatus
from src.domain.vendor import Vendor, VendorType

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

_BRAND_BASE: dict = {
    "name": "Acme Brands",
    "legal_name": "Acme Brands Inc.",
    "address": "123 Commerce Blvd",
    "country": "US",
    "tax_id": "12-3456789",
}


async def _create_brand(client: AsyncClient, name: str = "Test Brand") -> dict:
    payload = {
        "name": name,
        "legal_name": f"{name} Legal",
        "address": "100 Main St",
        "country": "US",
        "tax_id": "",
    }
    resp = await client.post("/api/v1/brands/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


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


async def _create_vendor_direct(client: AsyncClient, name: str = "Test Vendor") -> dict:
    from src.main import app
    from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo

    override = app.dependency_overrides[vendor_get_vendor_repo]
    async for repo in override():
        vendor = Vendor.create(name=name, country="US", vendor_type=VendorType.PROCUREMENT)
        await repo.save(vendor)
        return {"id": vendor.id, "name": vendor.name}
    raise RuntimeError("override did not yield a repo")


# ---------------------------------------------------------------------------
# Create brand
# ---------------------------------------------------------------------------


async def test_create_brand_admin_succeeds(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post("/api/v1/brands/", json=_BRAND_BASE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == _BRAND_BASE["name"]
    assert data["legal_name"] == _BRAND_BASE["legal_name"]
    assert data["address"] == _BRAND_BASE["address"]
    assert data["country"] == _BRAND_BASE["country"]
    assert data["tax_id"] == _BRAND_BASE["tax_id"]
    assert data["status"] == "ACTIVE"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.parametrize("role", [
    UserRole.SM,
    UserRole.FREIGHT_MANAGER,
    UserRole.QUALITY_LAB,
    UserRole.PROCUREMENT_MANAGER,
])
async def test_create_brand_non_admin_403(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    role: UserRole,
) -> None:
    username = f"user_{role.value.lower()}"
    await _seed_user(client, username=username, display_name=f"User {role.value}", role=role)
    await _login_as(client, monkeypatch, username)
    resp = await client.post("/api/v1/brands/", json=_BRAND_BASE)
    assert resp.status_code == 403


async def test_create_brand_vendor_role_403(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # VENDOR role requires a vendor_id — create a vendor first then seed the user
    vendor = await _create_vendor_direct(client, "Vendor For Role Check")
    from src.main import app
    from src.routers.auth import get_user_repo as auth_get_user_repo

    override = app.dependency_overrides[auth_get_user_repo]
    async for repo in override():
        user = User.create(
            username="user_vendor_role",
            display_name="User VENDOR",
            role=UserRole.VENDOR,
            vendor_id=vendor["id"],
        )
        await repo.save(user)
        break

    await _login_as(client, monkeypatch, "user_vendor_role")
    resp = await client.post("/api/v1/brands/", json=_BRAND_BASE)
    assert resp.status_code == 403


async def test_create_brand_rejects_empty_legal_name(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    payload = {**_BRAND_BASE, "legal_name": ""}
    resp = await client.post("/api/v1/brands/", json=payload)
    assert resp.status_code == 422


async def test_create_brand_rejects_unknown_country(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    payload = {**_BRAND_BASE, "name": "Country Brand", "country": "XX"}
    resp = await client.post("/api/v1/brands/", json=payload)
    assert resp.status_code == 422


async def test_create_brand_rejects_duplicate_name(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    await client.post("/api/v1/brands/", json=_BRAND_BASE)
    resp = await client.post("/api/v1/brands/", json=_BRAND_BASE)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# List brands
# ---------------------------------------------------------------------------


async def test_list_brands_admin_and_sm_succeed(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create an admin user and log in to create some brands
    admin = await _seed_user(client, username="admin_list", display_name="Admin List", role=UserRole.ADMIN)
    await _login_as(client, monkeypatch, "admin_list")

    await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Brand Alpha"})
    await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Brand Beta"})

    # Admin can list
    resp = await client.get("/api/v1/brands/")
    assert resp.status_code == 200
    names = [b["name"] for b in resp.json()]
    assert "Brand Alpha" in names
    assert "Brand Beta" in names

    # SM can list
    sm = await _seed_user(client, username="sm_list", display_name="SM List", role=UserRole.SM)
    await _login_as(client, monkeypatch, "sm_list")
    resp = await client.get("/api/v1/brands/")
    assert resp.status_code == 200


async def test_list_brands_status_filter(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed_user(client, username="admin_filter", display_name="Admin Filter", role=UserRole.ADMIN)
    await _login_as(client, monkeypatch, "admin_filter")

    await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Active Brand X"})
    deact_resp = await client.post("/api/v1/brands/", json={**_BRAND_BASE, "name": "Inactive Brand X"})
    brand_id = deact_resp.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/deactivate")

    resp = await client.get("/api/v1/brands/", params={"status": "ACTIVE"})
    assert resp.status_code == 200
    names = [b["name"] for b in resp.json()]
    assert "Active Brand X" in names
    assert "Inactive Brand X" not in names


# ---------------------------------------------------------------------------
# Get brand
# ---------------------------------------------------------------------------


async def test_get_brand_returns_full_row(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    created = await _create_brand(client, "Full Row Brand")
    resp = await client.get(f"/api/v1/brands/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["name"] == "Full Row Brand"
    assert "legal_name" in data
    assert "address" in data
    assert "country" in data
    assert "tax_id" in data
    assert "status" in data


async def test_get_brand_unknown_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.get("/api/v1/brands/nonexistent-brand-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update brand
# ---------------------------------------------------------------------------


async def test_update_brand_partial(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    brand = await _create_brand(client, "Patch Brand")
    brand_id = brand["id"]
    original_updated_at = brand["updated_at"]

    import asyncio
    await asyncio.sleep(0.01)

    resp = await client.patch(f"/api/v1/brands/{brand_id}", json={"legal_name": "Updated Legal"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["legal_name"] == "Updated Legal"
    assert data["name"] == "Patch Brand"  # unchanged
    assert data["updated_at"] != original_updated_at


# ---------------------------------------------------------------------------
# Deactivate / reactivate
# ---------------------------------------------------------------------------


async def test_deactivate_brand_with_no_active_pos(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    brand = await _create_brand(client, "Deactivate Brand")
    resp = await client.post(f"/api/v1/brands/{brand['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "INACTIVE"


async def test_deactivate_brand_with_active_pos_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    brand = await _create_brand(client, "Busy Brand")
    brand_id = brand["id"]

    # Create a vendor, assign to brand, then create a PO
    from src.main import app
    from src.routers.brands import get_brand_repo as brands_get_brand_repo

    vendor = await _create_vendor_direct(client, "PO Vendor For Deactivate")
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor["id"]})

    # Insert a PO directly via the repo to avoid PO creation validation complexity
    override = app.dependency_overrides[brands_get_brand_repo]
    async for repo in override():
        conn = repo._conn
        from datetime import UTC, datetime
        from uuid import uuid4
        now_iso = datetime.now(UTC).isoformat()
        po_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO purchase_orders
                (id, po_number, status, vendor_id, po_type, currency, issued_date,
                 required_delivery_date, created_at, updated_at, brand_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            po_id, f"PO-TEST-{po_id[:8]}", "DRAFT", vendor["id"], "PROCUREMENT",
            "USD", now_iso, now_iso, now_iso, now_iso, brand_id,
        )
        break

    resp = await client.post(f"/api/v1/brands/{brand_id}/deactivate")
    assert resp.status_code == 409
    assert "active PO" in resp.json()["detail"]


async def test_reactivate_brand(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    brand = await _create_brand(client, "Reactivate Brand")
    await client.post(f"/api/v1/brands/{brand['id']}/deactivate")
    resp = await client.post(f"/api/v1/brands/{brand['id']}/reactivate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# Vendor assignment
# ---------------------------------------------------------------------------


async def test_assign_vendor_to_brand_idempotent(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    brand = await _create_brand(client, "Brand For Vendor Assign")
    vendor = await _create_vendor_direct(client, "Assign Vendor")

    # Assign twice — both should succeed
    resp1 = await client.post(
        f"/api/v1/brands/{brand['id']}/vendors",
        json={"vendor_id": vendor["id"]},
    )
    assert resp1.status_code == 200

    resp2 = await client.post(
        f"/api/v1/brands/{brand['id']}/vendors",
        json={"vendor_id": vendor["id"]},
    )
    assert resp2.status_code == 200

    # Only one entry in the vendor list
    resp = await client.get(f"/api/v1/brands/{brand['id']}/vendors")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_assign_unknown_vendor_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    brand = await _create_brand(client, "Brand Unknown Vendor")
    resp = await client.post(
        f"/api/v1/brands/{brand['id']}/vendors",
        json={"vendor_id": "nonexistent-vendor-id"},
    )
    assert resp.status_code == 404


async def test_unassign_vendor_blocked_when_active_po_uses_pair(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    brand = await _create_brand(client, "Brand PO Block Unassign")
    brand_id = brand["id"]
    vendor = await _create_vendor_direct(client, "Vendor PO Block")

    await client.post(
        f"/api/v1/brands/{brand_id}/vendors",
        json={"vendor_id": vendor["id"]},
    )

    # Insert an active PO for this brand+vendor pair
    from src.main import app
    from src.routers.brands import get_brand_repo as brands_get_brand_repo

    override = app.dependency_overrides[brands_get_brand_repo]
    async for repo in override():
        conn = repo._conn
        from datetime import UTC, datetime
        from uuid import uuid4
        now_iso = datetime.now(UTC).isoformat()
        po_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO purchase_orders
                (id, po_number, status, vendor_id, po_type, currency, issued_date,
                 required_delivery_date, created_at, updated_at, brand_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            po_id, f"PO-UNASSIGN-{po_id[:8]}", "DRAFT", vendor["id"], "PROCUREMENT",
            "USD", now_iso, now_iso, now_iso, now_iso, brand_id,
        )
        break

    resp = await client.delete(f"/api/v1/brands/{brand_id}/vendors/{vendor['id']}")
    assert resp.status_code == 409


async def test_unassign_vendor_succeeds_with_no_active_po(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    brand = await _create_brand(client, "Brand Clean Unassign")
    vendor = await _create_vendor_direct(client, "Vendor Clean")

    await client.post(
        f"/api/v1/brands/{brand['id']}/vendors",
        json={"vendor_id": vendor["id"]},
    )

    resp = await client.delete(f"/api/v1/brands/{brand['id']}/vendors/{vendor['id']}")
    assert resp.status_code == 200

    vendor_list = await client.get(f"/api/v1/brands/{brand['id']}/vendors")
    assert vendor_list.json() == []
