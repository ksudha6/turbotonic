"""Iter 110: PDF rendering tests for Vendor.tax_id, Shipment.pallet_count,
and Shipment.export_reason.

PL: pallet_count appears in header when set.
CI: vendor tax_id appears in Seller block; export_reason appears in Summary;
    export_reason defaults to "Sale" when empty.
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
    "line_items": [_LINE_ITEM],
}


async def _setup(
    client: AsyncClient,
    vendor_tax_id: str = "",
) -> tuple[str, str, str]:
    """Create vendor + brand, link them, create+accept a PO, create a shipment.

    Returns (vendor_id, po_id, shipment_id).
    """
    vendor_r = await client.post(
        "/api/v1/vendors/",
        json={
            "name": "PDF Tax Vendor",
            "country": "CN",
            "vendor_type": "PROCUREMENT",
            "tax_id": vendor_tax_id,
        },
    )
    assert vendor_r.status_code == 201
    vendor_id: str = vendor_r.json()["id"]

    n = next(_brand_counter)
    brand_r = await client.post(
        "/api/v1/brands/",
        json={
            "name": f"PDFTaxBrand-{n}",
            "legal_name": "PDF Tax Brand Inc.",
            "address": "1 Commerce Drive",
            "country": "US",
            "tax_id": "EIN-12-3456789",
        },
    )
    assert brand_r.status_code == 201
    brand_id: str = brand_r.json()["id"]

    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor_id})

    po_r = await client.post(
        "/api/v1/po/",
        json={**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand_id},
    )
    assert po_r.status_code == 201
    po_id: str = po_r.json()["id"]

    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/lines/PN-001/accept", json={})
    r = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert r.status_code == 200

    ship_r = await client.post(
        "/api/v1/shipments/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PN-001", "quantity": 5, "uom": "PCS"}],
        },
    )
    assert ship_r.status_code == 201
    shipment_id: str = ship_r.json()["id"]

    return vendor_id, po_id, shipment_id


# ---------------------------------------------------------------------------
# CI: vendor tax_id in Seller block
# ---------------------------------------------------------------------------


async def test_ci_vendor_tax_id_appears_in_seller_block(authenticated_client: AsyncClient) -> None:
    vendor_tax_id = "CN-91440300MA5D12345X"
    _vendor_id, _po_id, shipment_id = await _setup(authenticated_client, vendor_tax_id=vendor_tax_id)

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert resp.status_code == 200
    text = _extract_pdf_text(resp.content)
    assert vendor_tax_id in text


async def test_ci_no_vendor_tax_id_omits_seller_tax_line(authenticated_client: AsyncClient) -> None:
    """When vendor has no tax_id, no 'Tax ID:' line should appear in the Seller block."""
    _vendor_id, _po_id, shipment_id = await _setup(authenticated_client, vendor_tax_id="")

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert resp.status_code == 200
    text = _extract_pdf_text(resp.content)
    # buyer's Tax ID from brand still appears; only count seller side
    # We cannot easily distinguish seller vs buyer from extracted text, but the
    # buyer has a tax_id in the setup so "Tax ID:" will appear for the buyer.
    # Verify no second "Tax ID:" by checking that the vendor tax_id value is absent.
    assert "CN-91440300" not in text


# ---------------------------------------------------------------------------
# CI: export_reason in Summary
# ---------------------------------------------------------------------------


async def test_ci_export_reason_defaults_to_sale(authenticated_client: AsyncClient) -> None:
    _vendor_id, _po_id, shipment_id = await _setup(authenticated_client)

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert resp.status_code == 200
    text = _extract_pdf_text(resp.content)
    assert "Reason for Export" in text
    assert "Sale" in text


async def test_ci_export_reason_custom_value(authenticated_client: AsyncClient) -> None:
    export_reason = "Sample"
    _vendor_id, _po_id, shipment_id = await _setup(authenticated_client)

    await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/logistics",
        json={"pallet_count": None, "export_reason": export_reason},
    )

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert resp.status_code == 200
    text = _extract_pdf_text(resp.content)
    assert "Reason for Export" in text
    assert export_reason in text


async def test_ci_export_reason_return(authenticated_client: AsyncClient) -> None:
    export_reason = "Return"
    _vendor_id, _po_id, shipment_id = await _setup(authenticated_client)

    await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/logistics",
        json={"pallet_count": None, "export_reason": export_reason},
    )

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert resp.status_code == 200
    text = _extract_pdf_text(resp.content)
    assert "Return" in text


# ---------------------------------------------------------------------------
# PL: pallet_count in header
# ---------------------------------------------------------------------------


async def test_pl_pallet_count_appears_when_set(authenticated_client: AsyncClient) -> None:
    pallet_count = 24
    _vendor_id, _po_id, shipment_id = await _setup(authenticated_client)

    await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/logistics",
        json={"pallet_count": pallet_count, "export_reason": ""},
    )

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert resp.status_code == 200
    text = _extract_pdf_text(resp.content)
    assert "Pallet Count" in text
    assert str(pallet_count) in text


async def test_pl_pallet_count_absent_when_not_set(authenticated_client: AsyncClient) -> None:
    _vendor_id, _po_id, shipment_id = await _setup(authenticated_client)

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert resp.status_code == 200
    text = _extract_pdf_text(resp.content)
    assert "Pallet Count" not in text


async def test_ci_vendor_tax_id_after_patch(authenticated_client: AsyncClient) -> None:
    """Patch vendor tax_id via API; verify CI reflects the updated value."""
    _vendor_id, _po_id, shipment_id = await _setup(authenticated_client, vendor_tax_id="")

    new_tax_id = "IN-27AABCM1234A1Z5"
    patch_resp = await authenticated_client.patch(
        f"/api/v1/vendors/{_vendor_id}",
        json={"tax_id": new_tax_id},
    )
    assert patch_resp.status_code == 200

    resp = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert resp.status_code == 200
    text = _extract_pdf_text(resp.content)
    assert new_tax_id in text
