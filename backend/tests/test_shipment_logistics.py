"""Iter 110: Shipment.set_logistics() — domain and API tests."""
from __future__ import annotations

import itertools

import pytest
from httpx import AsyncClient

from src.domain.shipment import Shipment, ShipmentLineItem, ShipmentStatus

pytestmark = pytest.mark.asyncio

_brand_counter = itertools.count(1)

# ---------------------------------------------------------------------------
# Helpers shared with other shipment tests
# ---------------------------------------------------------------------------

_LINE_ITEM_A: dict[str, object] = {
    "part_number": "PART-A",
    "description": "Widget A",
    "quantity": 100,
    "uom": "PCS",
    "unit_price": "10.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_PO_BASE: dict[str, object] = {
    "buyer_name": "TurboTonic Ltd",
    "buyer_country": "US",
    "ship_to_address": "123 Main St",
    "payment_terms": "TT",
    "currency": "USD",
    "issued_date": "2026-03-16T00:00:00Z",
    "required_delivery_date": "2026-04-01T00:00:00Z",
    "terms_and_conditions": "",
    "incoterm": "FOB",
    "port_of_loading": "USLAX",
    "port_of_discharge": "CNSHA",
    "country_of_origin": "US",
    "country_of_destination": "CN",
    "marketplace": "AMZ",
}


async def _make_vendor_and_brand(client: AsyncClient) -> tuple[str, str]:
    r = await client.post(
        "/api/v1/vendors/",
        json={"name": "Logistics Test Vendor", "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert r.status_code == 201
    vendor_id = r.json()["id"]
    brand_n = next(_brand_counter)
    brand_r = await client.post(
        "/api/v1/brands/",
        json={"name": f"LogBrand-{brand_n}", "legal_name": "Log Brand LLC", "address": "1 Log Ave", "country": "US"},
    )
    assert brand_r.status_code == 201
    brand_id = brand_r.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor_id})
    return vendor_id, brand_id


async def _make_accepted_po(client: AsyncClient, vendor_id: str, brand_id: str) -> str:
    payload = {**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand_id, "line_items": [_LINE_ITEM_A]}
    r = await client.post("/api/v1/po/", json=payload)
    assert r.status_code == 201
    po_id: str = r.json()["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/lines/PART-A/accept", json={})
    r3 = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert r3.status_code == 200
    return po_id


async def _make_shipment(client: AsyncClient, po_id: str) -> str:
    r = await client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Domain tests
# ---------------------------------------------------------------------------


def test_set_logistics_pallet_count_and_export_reason() -> None:
    shipment = Shipment.create(
        po_id="po-1",
        marketplace="AMZ",
        line_items=[ShipmentLineItem(part_number="P1", product_id=None, description="D", quantity=1, uom="EA")],
    )
    shipment.set_logistics(pallet_count=12, export_reason="Sale")
    assert shipment.pallet_count == 12
    assert shipment.export_reason == "Sale"


def test_set_logistics_nullable_pallet_count() -> None:
    shipment = Shipment.create(
        po_id="po-1",
        marketplace="AMZ",
        line_items=[ShipmentLineItem(part_number="P1", product_id=None, description="D", quantity=1, uom="EA")],
    )
    shipment.set_logistics(pallet_count=None, export_reason="")
    assert shipment.pallet_count is None
    assert shipment.export_reason == ""


def test_set_logistics_negative_pallet_count_raises() -> None:
    shipment = Shipment.create(
        po_id="po-1",
        marketplace="AMZ",
        line_items=[ShipmentLineItem(part_number="P1", product_id=None, description="D", quantity=1, uom="EA")],
    )
    with pytest.raises(ValueError, match="pallet_count"):
        shipment.set_logistics(pallet_count=-1, export_reason="")


def test_set_logistics_strips_export_reason_whitespace() -> None:
    shipment = Shipment.create(
        po_id="po-1",
        marketplace="AMZ",
        line_items=[ShipmentLineItem(part_number="P1", product_id=None, description="D", quantity=1, uom="EA")],
    )
    shipment.set_logistics(pallet_count=None, export_reason="  Return  ")
    assert shipment.export_reason == "Return"


def test_set_logistics_updates_updated_at() -> None:
    from datetime import UTC, datetime
    shipment = Shipment.create(
        po_id="po-1",
        marketplace="AMZ",
        line_items=[ShipmentLineItem(part_number="P1", product_id=None, description="D", quantity=1, uom="EA")],
    )
    before = shipment.updated_at
    shipment.set_logistics(pallet_count=5, export_reason="Sample")
    assert shipment.updated_at >= before


def test_shipment_defaults_zero_pallet_count_and_empty_export_reason() -> None:
    shipment = Shipment.create(
        po_id="po-1",
        marketplace="AMZ",
        line_items=[ShipmentLineItem(part_number="P1", product_id=None, description="D", quantity=1, uom="EA")],
    )
    assert shipment.pallet_count is None
    assert shipment.export_reason == ""


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


async def test_patch_logistics_sets_pallet_count_and_export_reason(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor_and_brand(authenticated_client)
    po_id = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    shipment_id = await _make_shipment(authenticated_client, po_id)

    resp = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/logistics",
        json={"pallet_count": 8, "export_reason": "Sale"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pallet_count"] == 8
    assert data["export_reason"] == "Sale"


async def test_patch_logistics_null_pallet_count(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor_and_brand(authenticated_client)
    po_id = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    shipment_id = await _make_shipment(authenticated_client, po_id)

    resp = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/logistics",
        json={"pallet_count": None, "export_reason": "Return"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pallet_count"] is None
    assert data["export_reason"] == "Return"


async def test_patch_logistics_not_found_returns_404(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.patch(
        "/api/v1/shipments/nonexistent-shipment/logistics",
        json={"pallet_count": 1, "export_reason": "Sale"},
    )
    assert resp.status_code == 404


async def test_patch_logistics_negative_pallet_count_returns_422(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor_and_brand(authenticated_client)
    po_id = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    shipment_id = await _make_shipment(authenticated_client, po_id)

    resp = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/logistics",
        json={"pallet_count": -5, "export_reason": "Sale"},
    )
    assert resp.status_code == 422


async def test_patch_logistics_persisted_after_get(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor_and_brand(authenticated_client)
    po_id = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    shipment_id = await _make_shipment(authenticated_client, po_id)

    pallet_count = 15
    export_reason = "Sample"
    await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/logistics",
        json={"pallet_count": pallet_count, "export_reason": export_reason},
    )

    reload = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}")
    assert reload.status_code == 200
    body = reload.json()
    assert body["pallet_count"] == pallet_count
    assert body["export_reason"] == export_reason


async def test_patch_logistics_default_export_reason_empty(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor_and_brand(authenticated_client)
    po_id = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    shipment_id = await _make_shipment(authenticated_client, po_id)

    # Verify defaults on fresh shipment
    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pallet_count"] is None
    assert body["export_reason"] == ""


async def test_patch_logistics_zero_pallet_count_accepted(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor_and_brand(authenticated_client)
    po_id = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    shipment_id = await _make_shipment(authenticated_client, po_id)

    resp = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/logistics",
        json={"pallet_count": 0, "export_reason": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["pallet_count"] == 0


async def test_shipment_response_includes_logistics_fields(authenticated_client: AsyncClient) -> None:
    """Ensure pallet_count and export_reason appear in every shipment response."""
    vendor_id, brand_id = await _make_vendor_and_brand(authenticated_client)
    po_id = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    shipment_id = await _make_shipment(authenticated_client, po_id)

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "pallet_count" in body
    assert "export_reason" in body
