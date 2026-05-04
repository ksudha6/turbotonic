"""Permanent tests for PO ↔ Brand wiring (iter 108).

Covers:
- brand_id required on PO create
- vendor-not-in-brand validation
- brand_id immutable on PATCH
- PO detail response carries full brand block
"""
from __future__ import annotations

import itertools

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_brand_counter = itertools.count(1)

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


async def _make_vendor(client: AsyncClient, name: str = "Wiring Vendor") -> str:
    resp = await client.post(
        "/api/v1/vendors/",
        json={"name": name, "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _make_brand(
    client: AsyncClient,
    legal_name: str = "Wiring Brand LLC",
    address: str = "1 Wiring Ave",
    country: str = "US",
    tax_id: str = "",
) -> dict:
    n = next(_brand_counter)
    resp = await client.post(
        "/api/v1/brands/",
        json={
            "name": f"WiringBrand-{n}",
            "legal_name": legal_name,
            "address": address,
            "country": country,
            "tax_id": tax_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_po_create_requires_brand_id(authenticated_client: AsyncClient) -> None:
    # PO create without brand_id must return 422 (required field).
    client = authenticated_client
    vendor_id = await _make_vendor(client, "RequiresBrandVendor")
    payload = {**_PO_BASE, "vendor_id": vendor_id}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_po_create_rejects_vendor_not_in_brand(authenticated_client: AsyncClient) -> None:
    # Vendor exists but is not linked to the brand: must return 422 naming the brand.
    client = authenticated_client
    vendor_id = await _make_vendor(client, "UnlinkedVendor")
    brand = await _make_brand(client)
    # Brand exists but vendor is NOT assigned to it.
    payload = {**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand["id"]}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422
    detail = resp.json().get("detail", "")
    assert brand["name"] in detail, f"brand name should appear in error; got: {detail!r}"


async def test_po_brand_id_immutable_on_edit(authenticated_client: AsyncClient) -> None:
    # PUT with a different brand_id must return 422 (brand_id is immutable after create).
    client = authenticated_client
    vendor_id = await _make_vendor(client, "ImmutableBrandVendor")
    brand_a = await _make_brand(client)
    brand_b = await _make_brand(client)
    await client.post(f"/api/v1/brands/{brand_a['id']}/vendors", json={"vendor_id": vendor_id})
    await client.post(f"/api/v1/brands/{brand_b['id']}/vendors", json={"vendor_id": vendor_id})
    payload = {**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand_a["id"]}
    po_resp = await client.post("/api/v1/po/", json=payload)
    assert po_resp.status_code == 201
    po_id = po_resp.json()["id"]
    # PUT with a different brand_id; the full update body is required.
    update_body = {**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand_b["id"]}
    put_resp = await client.put(f"/api/v1/po/{po_id}", json=update_body)
    assert put_resp.status_code == 422


async def test_po_response_carries_brand_block(authenticated_client: AsyncClient) -> None:
    # PO detail response must include the full brand block populated from the JOIN.
    client = authenticated_client
    vendor_id = await _make_vendor(client, "BrandBlockVendor")
    brand_legal_name = "Block Brand LLC"
    brand_address = "99 Block St"
    brand_country = "GB"
    brand_tax_id = "GB123456789"
    brand = await _make_brand(
        client,
        legal_name=brand_legal_name,
        address=brand_address,
        country=brand_country,
        tax_id=brand_tax_id,
    )
    await client.post(f"/api/v1/brands/{brand['id']}/vendors", json={"vendor_id": vendor_id})
    payload = {**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand["id"]}
    po_resp = await client.post("/api/v1/po/", json=payload)
    assert po_resp.status_code == 201
    po_id = po_resp.json()["id"]

    detail = await client.get(f"/api/v1/po/{po_id}")
    assert detail.status_code == 200
    data = detail.json()

    assert data["brand_id"] == brand["id"]
    assert data["brand_name"] == brand["name"]
    assert data["brand_legal_name"] == brand_legal_name
    assert data["brand_address"] == brand_address
    assert data["brand_country"] == brand_country
    assert data["brand_tax_id"] == brand_tax_id
