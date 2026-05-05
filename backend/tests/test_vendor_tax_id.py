"""Iter 110: Vendor.tax_id — domain, repository, and API tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.vendor import Vendor, VendorType

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Domain tests
# ---------------------------------------------------------------------------


def test_vendor_create_default_tax_id() -> None:
    vendor = Vendor.create(name="Test Co", country="US", vendor_type=VendorType.PROCUREMENT)
    assert vendor.tax_id == ""


def test_vendor_create_with_tax_id() -> None:
    tax_id = "EIN-12-3456789"
    vendor = Vendor.create(name="Test Co", country="US", vendor_type=VendorType.PROCUREMENT, tax_id=tax_id)
    assert vendor.tax_id == tax_id


def test_vendor_tax_id_is_mutable() -> None:
    vendor = Vendor.create(name="Test Co", country="US", vendor_type=VendorType.PROCUREMENT)
    vendor.tax_id = "GB123456789"
    assert vendor.tax_id == "GB123456789"


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


async def test_create_vendor_without_tax_id_defaults_empty(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.post(
        "/api/v1/vendors/",
        json={"name": "Tax Test Corp", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tax_id"] == ""


async def test_create_vendor_with_tax_id(authenticated_client: AsyncClient) -> None:
    tax_id = "EIN-36-1234567"
    resp = await authenticated_client.post(
        "/api/v1/vendors/",
        json={"name": "Tax Inc", "country": "US", "vendor_type": "PROCUREMENT", "tax_id": tax_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tax_id"] == tax_id


async def test_get_vendor_includes_tax_id(authenticated_client: AsyncClient) -> None:
    tax_id = "DE123456789"
    create_resp = await authenticated_client.post(
        "/api/v1/vendors/",
        json={"name": "German Tax Co", "country": "DE", "vendor_type": "PROCUREMENT", "tax_id": tax_id},
    )
    vendor_id = create_resp.json()["id"]

    get_resp = await authenticated_client.get(f"/api/v1/vendors/{vendor_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["tax_id"] == tax_id


async def test_patch_vendor_tax_id(authenticated_client: AsyncClient) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/vendors/",
        json={"name": "Patchable Vendor", "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert create_resp.status_code == 201
    vendor_id = create_resp.json()["id"]
    assert create_resp.json()["tax_id"] == ""

    new_tax_id = "CN-91440300MA5D12345X"
    patch_resp = await authenticated_client.patch(
        f"/api/v1/vendors/{vendor_id}",
        json={"tax_id": new_tax_id},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["tax_id"] == new_tax_id
    assert data["id"] == vendor_id


async def test_patch_vendor_not_found_returns_404(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.patch(
        "/api/v1/vendors/nonexistent-vendor-id",
        json={"tax_id": "EIN-12-9999999"},
    )
    assert resp.status_code == 404


async def test_patch_vendor_no_fields_is_noop(authenticated_client: AsyncClient) -> None:
    """PATCH with no recognized fields performs a read-back with no change."""
    create_resp = await authenticated_client.post(
        "/api/v1/vendors/",
        json={"name": "Noop Vendor", "country": "US", "vendor_type": "OPEX", "tax_id": "EIN-55-1234567"},
    )
    vendor_id = create_resp.json()["id"]

    patch_resp = await authenticated_client.patch(
        f"/api/v1/vendors/{vendor_id}",
        json={},
    )
    assert patch_resp.status_code == 200
    # tax_id is unchanged
    assert patch_resp.json()["tax_id"] == "EIN-55-1234567"


async def test_list_vendors_includes_tax_id(authenticated_client: AsyncClient) -> None:
    tax_id = "VN-0123456789"
    await authenticated_client.post(
        "/api/v1/vendors/",
        json={"name": "Vietnam Co", "country": "VN", "vendor_type": "PROCUREMENT", "tax_id": tax_id},
    )
    resp = await authenticated_client.get("/api/v1/vendors/")
    assert resp.status_code == 200
    vendors = resp.json()
    # Find our vendor
    match = next((v for v in vendors if v.get("tax_id") == tax_id), None)
    assert match is not None


async def test_patch_vendor_tax_id_persisted_after_reload(authenticated_client: AsyncClient) -> None:
    """Verify tax_id survives a round-trip through the repository."""
    create_resp = await authenticated_client.post(
        "/api/v1/vendors/",
        json={"name": "Persist Test Vendor", "country": "IN", "vendor_type": "PROCUREMENT"},
    )
    vendor_id = create_resp.json()["id"]

    new_tax_id = "IN-27AABCM1234A1Z5"
    await authenticated_client.patch(
        f"/api/v1/vendors/{vendor_id}",
        json={"tax_id": new_tax_id},
    )

    reload_resp = await authenticated_client.get(f"/api/v1/vendors/{vendor_id}")
    assert reload_resp.status_code == 200
    assert reload_resp.json()["tax_id"] == new_tax_id
