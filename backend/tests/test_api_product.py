from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_vendor(client: AsyncClient, name: str = "Test Vendor") -> dict:
    resp = await client.post(
        "/api/v1/vendors/",
        json={"name": name, "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_product(
    client: AsyncClient,
    vendor_id: str,
    part_number: str = "PN-001",
    description: str = "",
    requires_certification: bool = False,
) -> dict:
    resp = await client.post(
        "/api/v1/products/",
        json={
            "vendor_id": vendor_id,
            "part_number": part_number,
            "description": description,
            "requires_certification": requires_certification,
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_product_returns_201(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    resp = await client.post(
        "/api/v1/products/",
        json={
            "vendor_id": vendor["id"],
            "part_number": "PN-001",
            "description": "Widget A",
            "requires_certification": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["vendor_id"] == vendor["id"]
    assert data["part_number"] == "PN-001"
    assert data["description"] == "Widget A"
    assert data["requires_certification"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_product_defaults(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])
    assert product["description"] == ""
    assert product["requires_certification"] is False


async def test_create_product_rejects_empty_part_number(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    resp = await client.post(
        "/api/v1/products/",
        json={"vendor_id": vendor["id"], "part_number": ""},
    )
    assert resp.status_code == 422


async def test_create_product_rejects_empty_vendor_id(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post(
        "/api/v1/products/",
        json={"vendor_id": "", "part_number": "PN-001"},
    )
    assert resp.status_code == 422


async def test_duplicate_vendor_part_number_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    await _create_product(client, vendor["id"], part_number="PN-DUP")
    resp = await client.post(
        "/api/v1/products/",
        json={"vendor_id": vendor["id"], "part_number": "PN-DUP"},
    )
    assert resp.status_code == 409


async def test_same_part_number_different_vendors_ok(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    v1 = await _create_vendor(client, name="Vendor A")
    v2 = await _create_vendor(client, name="Vendor B")
    p1 = await _create_product(client, v1["id"], part_number="PN-SHARED")
    p2 = await _create_product(client, v2["id"], part_number="PN-SHARED")
    assert p1["id"] != p2["id"]


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


async def test_get_product_by_id(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    created = await _create_product(client, vendor["id"], description="Detail test")
    resp = await client.get(f"/api/v1/products/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["description"] == "Detail test"


async def test_get_nonexistent_product_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.get("/api/v1/products/fake-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


async def test_list_products_returns_array(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    await _create_product(client, vendor["id"], part_number="PN-A")
    await _create_product(client, vendor["id"], part_number="PN-B")
    resp = await client.get("/api/v1/products/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


async def test_list_products_filters_by_vendor_id(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    v1 = await _create_vendor(client, name="Vendor 1")
    v2 = await _create_vendor(client, name="Vendor 2")
    await _create_product(client, v1["id"], part_number="PN-V1")
    await _create_product(client, v2["id"], part_number="PN-V2")

    resp = await client.get("/api/v1/products/", params={"vendor_id": v1["id"]})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["vendor_id"] == v1["id"]
    assert data[0]["part_number"] == "PN-V1"


# ---------------------------------------------------------------------------
# Update (PATCH)
# ---------------------------------------------------------------------------


async def test_update_requires_certification(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])
    assert product["requires_certification"] is False

    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"requires_certification": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["requires_certification"] is True


async def test_update_description(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])
    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"description": "Updated desc"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated desc"


async def test_update_nonexistent_product_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.patch(
        "/api/v1/products/fake-id",
        json={"description": "x"},
    )
    assert resp.status_code == 404


async def test_partial_update_preserves_other_fields(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    product = await _create_product(
        client, vendor["id"], description="Original", requires_certification=True,
    )
    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"description": "Changed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Changed"
    assert data["requires_certification"] is True
