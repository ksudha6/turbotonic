from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.product import Product
from src.domain.user import UserRole
from src.domain.vendor import Vendor, VendorType
from src.product_repository import ProductRepository
from src.vendor_repository import VendorRepository
from tests.test_role_guards import _make_client_with_role

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
    manufacturing_address: str = "",
) -> dict:
    resp = await client.post(
        "/api/v1/products/",
        json={
            "vendor_id": vendor_id,
            "part_number": part_number,
            "description": description,
            "manufacturing_address": manufacturing_address,
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
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["vendor_id"] == vendor["id"]
    assert data["part_number"] == "PN-001"
    assert data["description"] == "Widget A"
    assert data["qualifications"] == []
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_product_defaults(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])
    assert product["description"] == ""
    assert product["manufacturing_address"] == ""
    assert product["qualifications"] == []


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
    assert data["qualifications"] == []


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
    # each list item includes qualifications
    for item in data:
        assert "qualifications" in item
        assert isinstance(item["qualifications"], list)


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


async def test_update_description(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])
    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"description": "Updated desc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Updated desc"
    assert data["qualifications"] == []


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
        client, vendor["id"], description="Original", manufacturing_address="123 Factory Rd",
    )
    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"description": "Changed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Changed"
    assert data["manufacturing_address"] == "123 Factory Rd"


async def test_update_manufacturing_address(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])
    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"manufacturing_address": "456 Plant Ave"},
    )
    assert resp.status_code == 200
    assert resp.json()["manufacturing_address"] == "456 Plant Ave"


# ---------------------------------------------------------------------------
# Role-scoped read access (iter: products read for VENDOR + PROCUREMENT_MANAGER)
# ---------------------------------------------------------------------------


async def _seed_other_vendor_with_product(conn, part_number: str = "PN-OTHER") -> tuple[str, str]:
    """Seed a second vendor and one product on it. Returns (vendor_id, product_id)."""
    other = Vendor.create(name="Other Vendor", country="DE", vendor_type=VendorType.PROCUREMENT)
    await VendorRepository(conn).save(other)
    product = Product.create(
        vendor_id=other.id, part_number=part_number, description="Other vendor product"
    )
    await ProductRepository(conn).save(product)
    return other.id, product.id


async def test_vendor_can_list_their_own_products() -> None:
    async for ac, conn in _make_client_with_role(UserRole.VENDOR):
        # Helper auto-created the VENDOR's own vendor row. Seed one own product.
        own_vendor_id = (await VendorRepository(conn).list_vendors())[0].id
        own_product = Product.create(vendor_id=own_vendor_id, part_number="PN-MINE")
        await ProductRepository(conn).save(own_product)
        # Plus a product on a different vendor that VENDOR must not see.
        await _seed_other_vendor_with_product(conn)

        resp = await ac.get("/api/v1/products/")
        assert resp.status_code == 200
        data = resp.json()
        ids = {item["id"] for item in data}
        assert own_product.id in ids
        assert all(item["vendor_id"] == own_vendor_id for item in data)


async def test_vendor_cannot_see_other_vendor_products_via_query() -> None:
    async for ac, conn in _make_client_with_role(UserRole.VENDOR):
        own_vendor_id = (await VendorRepository(conn).list_vendors())[0].id
        own_product = Product.create(vendor_id=own_vendor_id, part_number="PN-MINE")
        await ProductRepository(conn).save(own_product)
        other_vendor_id, _ = await _seed_other_vendor_with_product(conn)

        # Even with ?vendor_id=other, VENDOR's own vendor_id is forced server-side.
        resp = await ac.get(f"/api/v1/products/?vendor_id={other_vendor_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["vendor_id"] == own_vendor_id for item in data)


async def test_vendor_gets_404_on_other_vendor_product_by_id() -> None:
    async for ac, conn in _make_client_with_role(UserRole.VENDOR):
        _, other_product_id = await _seed_other_vendor_with_product(conn)
        resp = await ac.get(f"/api/v1/products/{other_product_id}")
        assert resp.status_code == 404


async def test_vendor_can_get_own_product_by_id() -> None:
    async for ac, conn in _make_client_with_role(UserRole.VENDOR):
        own_vendor_id = (await VendorRepository(conn).list_vendors())[0].id
        own_product = Product.create(vendor_id=own_vendor_id, part_number="PN-MINE")
        await ProductRepository(conn).save(own_product)
        resp = await ac.get(f"/api/v1/products/{own_product.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == own_product.id


async def test_procurement_manager_can_list_all_products() -> None:
    async for ac, conn in _make_client_with_role(UserRole.PROCUREMENT_MANAGER):
        v1 = Vendor.create(name="V1", country="CN", vendor_type=VendorType.PROCUREMENT)
        v2 = Vendor.create(name="V2", country="DE", vendor_type=VendorType.PROCUREMENT)
        await VendorRepository(conn).save(v1)
        await VendorRepository(conn).save(v2)
        p1 = Product.create(vendor_id=v1.id, part_number="PN-A")
        p2 = Product.create(vendor_id=v2.id, part_number="PN-B")
        await ProductRepository(conn).save(p1)
        await ProductRepository(conn).save(p2)

        resp = await ac.get("/api/v1/products/")
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()}
        assert {p1.id, p2.id}.issubset(ids)


async def test_procurement_manager_can_get_any_product_by_id() -> None:
    async for ac, conn in _make_client_with_role(UserRole.PROCUREMENT_MANAGER):
        v = Vendor.create(name="V", country="CN", vendor_type=VendorType.PROCUREMENT)
        await VendorRepository(conn).save(v)
        product = Product.create(vendor_id=v.id, part_number="PN-X")
        await ProductRepository(conn).save(product)

        resp = await ac.get(f"/api/v1/products/{product.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == product.id
