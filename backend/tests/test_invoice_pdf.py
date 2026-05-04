from __future__ import annotations

import itertools

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_brand_counter = itertools.count(1)

_LINE_ITEM = {
    "part_number": "PN-001",
    "description": "Widget A",
    "quantity": 100,
    "uom": "EA",
    "unit_price": "5.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_LINE_ITEM_2 = {
    "part_number": "PN-002",
    "description": "Widget B",
    "quantity": 50,
    "uom": "EA",
    "unit_price": "10.00",
    "hs_code": "8471.40",
    "country_of_origin": "US",
}

_PO_PAYLOAD = {
    "vendor_id": "vendor-1",
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
    "line_items": [_LINE_ITEM, _LINE_ITEM_2],
}


async def _create_accepted_po(client: AsyncClient) -> dict:
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Test Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    vendor_id = vendor.json()["id"]
    brand_n = next(_brand_counter)
    brand = await client.post("/api/v1/brands/", json={"name": f"InvPDFBrand-{brand_n}", "legal_name": "InvPDF Brand LLC", "address": "1 Inv Ave", "country": "US"})
    brand_id = brand.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor_id})
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor_id
    payload["brand_id"] = brand_id
    po = await client.post("/api/v1/po/", json=payload)
    po_id = po.json()["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/accept")
    return (await client.get(f"/api/v1/po/{po_id}")).json()


async def _create_invoice(client: AsyncClient, po_id: str, part_number: str, quantity: int) -> dict:
    resp = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": part_number, "quantity": quantity}],
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_invoice_pdf_returns_bytes(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # GET /{id}/pdf must return 200, application/pdf content-type, and non-empty body.
    po = await _create_accepted_po(client)
    invoice = await _create_invoice(client, po["id"], "PN-001", 10)
    invoice_id = invoice["id"]

    resp = await client.get(f"/api/v1/invoices/{invoice_id}/pdf")

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0, "PDF response body must not be empty"


async def test_invoice_pdf_not_found(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # GET /nonexistent-id/pdf must return 404.
    nonexistent_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/invoices/{nonexistent_id}/pdf")

    assert resp.status_code == 404, f"expected 404, got {resp.status_code}"


async def test_bulk_invoice_pdf(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # POST /bulk/pdf with two invoice IDs must return 200, application/pdf, non-empty body.
    po = await _create_accepted_po(client)
    po_id = po["id"]

    # PN-001 has 100 units; split into two invoices of 50 each.
    invoice_a = await _create_invoice(client, po_id, "PN-001", 50)
    invoice_b = await _create_invoice(client, po_id, "PN-001", 50)
    invoice_a_id = invoice_a["id"]
    invoice_b_id = invoice_b["id"]

    resp = await client.post(
        "/api/v1/invoices/bulk/pdf",
        json={"invoice_ids": [invoice_a_id, invoice_b_id]},
    )

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0, "bulk PDF response body must not be empty"


async def test_bulk_invoice_pdf_empty_ids(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # POST /bulk/pdf with an empty invoice_ids list must return 400.
    resp = await client.post(
        "/api/v1/invoices/bulk/pdf",
        json={"invoice_ids": []},
    )

    assert resp.status_code == 400, f"expected 400, got {resp.status_code}"


async def test_bulk_invoice_pdf_skips_missing(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # POST /bulk/pdf with a mix of valid and nonexistent IDs must return 200 (missing IDs are skipped).
    po = await _create_accepted_po(client)
    invoice = await _create_invoice(client, po["id"], "PN-001", 10)
    invoice_id = invoice["id"]
    missing_id = "00000000-0000-0000-0000-000000000000"

    resp = await client.post(
        "/api/v1/invoices/bulk/pdf",
        json={"invoice_ids": [invoice_id, missing_id]},
    )

    assert resp.status_code == 200, f"expected 200 when mixing valid and missing IDs, got {resp.status_code}: {resp.text}"
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0, "bulk PDF body must not be empty when at least one valid ID exists"
