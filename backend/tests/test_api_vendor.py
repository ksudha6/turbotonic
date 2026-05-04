from __future__ import annotations

import itertools

import pytest
from httpx import AsyncClient

from src.domain.vendor import VendorStatus

_brand_counter = itertools.count(1)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

_LINE_ITEM: dict = {
    "part_number": "PN-001",
    "description": "Widget A",
    "quantity": 10,
    "uom": "EA",
    "unit_price": "5.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_PO_BASE: dict = {
    "buyer_name": "TurboTonic Ltd",
    "buyer_country": "US",
    "ship_to_address": "123 Main St",
    "payment_terms": "TT",
    "currency": "USD",
    "issued_date": "2026-03-16T00:00:00Z",
    "required_delivery_date": "2026-04-01T00:00:00Z",
    "terms_and_conditions": "Standard T&C",
    "incoterm": "FOB",
    "port_of_loading": "USLAX",
    "port_of_discharge": "CNSHA",
    "country_of_origin": "US",
    "country_of_destination": "CN",
    "line_items": [_LINE_ITEM],
}


async def _create_vendor(client: AsyncClient, name: str = "Test Vendor", country: str = "US", vendor_type: str = "PROCUREMENT") -> dict:
    resp = await client.post("/api/v1/vendors/", json={"name": name, "country": country, "vendor_type": vendor_type})
    assert resp.status_code == 201
    return resp.json()


async def _create_po(client: AsyncClient, vendor_id: str) -> dict:
    brand_n = next(_brand_counter)
    brand_resp = await client.post(
        "/api/v1/brands/",
        json={"name": f"VendorBrand-{brand_n}", "legal_name": "Vendor Brand LLC", "address": "1 VendorBrand Ave", "country": "US"},
    )
    assert brand_resp.status_code == 201
    brand_id = brand_resp.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor_id})
    payload = {**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand_id}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Vendor create
# ---------------------------------------------------------------------------


async def test_create_vendor_returns_201(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post("/api/v1/vendors/", json={"name": "Acme Corp", "country": "US", "vendor_type": "PROCUREMENT"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["country"] == "US"
    assert data["status"] == VendorStatus.ACTIVE.value
    assert "id" in data


async def test_create_vendor_rejects_empty_name(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post("/api/v1/vendors/", json={"name": "", "country": "US", "vendor_type": "PROCUREMENT"})
    assert resp.status_code == 422


async def test_create_vendor_with_valid_country_code_returns_201(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post("/api/v1/vendors/", json={"name": "Valid Country Vendor", "country": "DE", "vendor_type": "PROCUREMENT"})
    assert resp.status_code == 201
    assert resp.json()["country"] == "DE"


async def test_create_vendor_with_invalid_country_code_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post("/api/v1/vendors/", json={"name": "Bad Country Vendor", "country": "XX", "vendor_type": "PROCUREMENT"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Vendor list
# ---------------------------------------------------------------------------


async def test_list_vendors_returns_array(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    await _create_vendor(client, name="Vendor A")
    await _create_vendor(client, name="Vendor B")
    resp = await client.get("/api/v1/vendors/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


async def test_list_vendors_filters_by_status(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client, name="Active Vendor")
    inactive_vendor = await _create_vendor(client, name="Inactive Vendor")
    await client.post(f"/api/v1/vendors/{inactive_vendor['id']}/deactivate")

    resp = await client.get("/api/v1/vendors/", params={"status": "ACTIVE"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == vendor["id"]
    assert data[0]["status"] == VendorStatus.ACTIVE.value


# ---------------------------------------------------------------------------
# Vendor detail
# ---------------------------------------------------------------------------


async def test_get_vendor_by_id(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    created = await _create_vendor(client, name="Detail Vendor", country="DE")
    resp = await client.get(f"/api/v1/vendors/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["name"] == "Detail Vendor"
    assert data["country"] == "DE"


async def test_get_nonexistent_vendor_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.get("/api/v1/vendors/fake-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Vendor deactivate
# ---------------------------------------------------------------------------


async def test_deactivate_vendor(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    resp = await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == VendorStatus.INACTIVE.value


async def test_deactivate_already_inactive_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    resp = await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Vendor reactivate
# ---------------------------------------------------------------------------


async def test_reactivate_vendor(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    resp = await client.post(f"/api/v1/vendors/{vendor['id']}/reactivate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == VendorStatus.ACTIVE.value


async def test_reactivate_already_active_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    resp = await client.post(f"/api/v1/vendors/{vendor['id']}/reactivate")
    assert resp.status_code == 409


async def test_reactivate_nonexistent_vendor_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post("/api/v1/vendors/fake-id/reactivate")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PO creation with vendor validation
# ---------------------------------------------------------------------------


async def test_create_po_with_inactive_vendor_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    payload = {**_PO_BASE, "vendor_id": vendor["id"]}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_create_po_with_nonexistent_vendor_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    payload = {**_PO_BASE, "vendor_id": "nonexistent-vendor-id"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PO response includes vendor and buyer fields
# ---------------------------------------------------------------------------


async def test_po_response_includes_buyer_fields(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    po = await _create_po(client, vendor_id=vendor["id"])
    assert po["buyer_name"] == "TurboTonic Ltd"
    assert po["buyer_country"] == "US"


async def test_po_response_includes_vendor_name(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client, name="Global Parts Co", country="DE")
    po = await _create_po(client, vendor_id=vendor["id"])
    assert po["vendor_name"] == "Global Parts Co"
    assert po["vendor_country"] == "DE"


async def test_po_list_includes_vendor_name(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client, name="List Vendor", country="JP")
    await _create_po(client, vendor_id=vendor["id"])
    resp = await client.get("/api/v1/po/")
    assert resp.status_code == 200
    data = resp.json()
    items = data["items"]
    assert data["total"] == 1
    assert len(items) == 1
    assert items[0]["vendor_name"] == "List Vendor"
    assert items[0]["vendor_country"] == "JP"


# ---------------------------------------------------------------------------
# Reference data endpoint
# ---------------------------------------------------------------------------


async def test_reference_data_returns_all_sets(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.get("/api/v1/reference-data/")
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {"currencies", "incoterms", "payment_terms", "countries", "ports", "vendor_types", "po_types"}
    assert set(data.keys()) == expected_keys
    for key in expected_keys:
        assert len(data[key]) > 0
        first = data[key][0]
        assert "code" in first
        assert "label" in first
