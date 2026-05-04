"""Permanent tests confirming packing list and commercial invoice PDFs
emit the Brand's legal name, address, and country in the buyer/consignee
block rather than the PO's buyer_name or hardcoded constants (iter 108).
"""
from __future__ import annotations

import io
import itertools

import pytest
from httpx import AsyncClient
from pypdf import PdfReader

pytestmark = pytest.mark.asyncio

_brand_counter = itertools.count(1)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


_LINE_ITEM: dict = {
    "part_number": "PN-001",
    "description": "Widget A",
    "quantity": 10,
    "uom": "PCS",
    "unit_price": "5.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_PO_BASE: dict = {
    "buyer_name": "OldBuyerName ShouldNotAppear",
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


async def _setup(
    client: AsyncClient,
    brand_legal_name: str,
    brand_address: str,
    brand_country: str = "US",
    brand_tax_id: str = "",
) -> tuple[str, str]:
    """Create vendor + brand, link them, create+accept a PO, create a shipment.

    Returns (po_id, shipment_id).
    """
    vendor_r = await client.post(
        "/api/v1/vendors/",
        json={"name": "PDFBrandVendor", "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert vendor_r.status_code == 201
    vendor_id: str = vendor_r.json()["id"]

    n = next(_brand_counter)
    brand_r = await client.post(
        "/api/v1/brands/",
        json={
            "name": f"PDFBrand-{n}",
            "legal_name": brand_legal_name,
            "address": brand_address,
            "country": brand_country,
            "tax_id": brand_tax_id,
        },
    )
    assert brand_r.status_code == 201
    brand_id: str = brand_r.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor_id})

    po_r = await client.post("/api/v1/po/", json={**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand_id})
    assert po_r.status_code == 201
    po_id: str = po_r.json()["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/accept")

    shp_r = await client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PN-001", "quantity": 5, "uom": "PCS"}]},
    )
    assert shp_r.status_code == 201
    shipment_id: str = shp_r.json()["id"]
    return po_id, shipment_id


async def test_packing_list_pdf_renders_brand_buyer_block(authenticated_client: AsyncClient) -> None:
    # Packing list Consignee block must show brand legal_name and address;
    # po.buyer_name must not appear (it predates brand wiring).
    client = authenticated_client
    brand_legal_name = "Acme Legal Entity Ltd"
    brand_address = "42 Brand Street"
    _po_id, shipment_id = await _setup(
        client,
        brand_legal_name=brand_legal_name,
        brand_address=brand_address,
    )

    resp = await client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert resp.status_code == 200
    pdf_text = _extract_pdf_text(resp.content)

    assert brand_legal_name in pdf_text, (
        f"brand legal_name {brand_legal_name!r} not found in packing list PDF"
    )
    assert brand_address in pdf_text, (
        f"brand address {brand_address!r} not found in packing list PDF"
    )
    assert "OldBuyerName ShouldNotAppear" not in pdf_text, (
        "po.buyer_name must not appear in packing list consignee block after brand wiring"
    )


async def test_commercial_invoice_pdf_renders_brand_buyer_block_with_tax_id(
    authenticated_client: AsyncClient,
) -> None:
    # Commercial invoice Buyer block must show brand legal_name, address, and
    # "Tax ID: <tax_id>" line when tax_id is non-empty.
    client = authenticated_client
    brand_legal_name = "Beacon Goods (UK) Ltd"
    brand_address = "10 Beacon Road, London"
    brand_tax_id = "GB987654321"
    _po_id, shipment_id = await _setup(
        client,
        brand_legal_name=brand_legal_name,
        brand_address=brand_address,
        brand_country="GB",
        brand_tax_id=brand_tax_id,
    )

    resp = await client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert resp.status_code == 200
    pdf_text = _extract_pdf_text(resp.content)

    assert brand_legal_name in pdf_text, (
        f"brand legal_name {brand_legal_name!r} not found in commercial invoice PDF"
    )
    assert brand_address in pdf_text, (
        f"brand address {brand_address!r} not found in commercial invoice PDF"
    )
    assert f"Tax ID: {brand_tax_id}" in pdf_text, (
        f"tax ID line 'Tax ID: {brand_tax_id}' not found in commercial invoice PDF"
    )


async def test_commercial_invoice_pdf_omits_tax_id_line_when_empty(
    authenticated_client: AsyncClient,
) -> None:
    # When brand.tax_id is empty, the "Tax ID:" line must not appear.
    client = authenticated_client
    _po_id, shipment_id = await _setup(
        client,
        brand_legal_name="No Tax ID Brand LLC",
        brand_address="1 Empty Tax Ave",
        brand_tax_id="",
    )

    resp = await client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert resp.status_code == 200
    pdf_text = _extract_pdf_text(resp.content)

    assert "Tax ID:" not in pdf_text, (
        "Tax ID line must not appear when brand.tax_id is empty"
    )
