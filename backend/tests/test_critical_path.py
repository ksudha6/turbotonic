from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_full_po_lifecycle(authenticated_client: AsyncClient):
    client = authenticated_client
    """Regression safety net: vendor -> PO -> submit -> accept -> invoice -> milestone."""

    # 1. Create vendor
    vendor_resp = await client.post("/api/v1/vendors/", json={
        "name": "Lifecycle Test Vendor",
        "country": "CN",
        "vendor_type": "PROCUREMENT",
    })
    assert vendor_resp.status_code == 201
    vendor_id = vendor_resp.json()["id"]

    # 2. Create PO with line items
    po_resp = await client.post("/api/v1/po/", json={
        "vendor_id": vendor_id,
        "po_type": "PROCUREMENT",
        "buyer_name": "Test Buyer",
        "buyer_country": "US",
        "ship_to_address": "123 Test St",
        "payment_terms": "NET30",
        "currency": "USD",
        "issued_date": "2026-04-15T00:00:00Z",
        "required_delivery_date": "2026-05-15T00:00:00Z",
        "terms_and_conditions": "Standard",
        "incoterm": "FOB",
        "port_of_loading": "CNSHA",
        "port_of_discharge": "USLAX",
        "country_of_origin": "CN",
        "country_of_destination": "US",
        "line_items": [
            {
                "part_number": "TEST-001",
                "description": "Test Widget",
                "quantity": 100,
                "uom": "PCS",
                "unit_price": "10.00",
                "hs_code": "7318.15",
                "country_of_origin": "CN",
            }
        ],
    })
    assert po_resp.status_code == 201
    po_id = po_resp.json()["id"]
    assert po_resp.json()["status"] == "DRAFT"

    # 3. Submit PO
    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200
    assert submit_resp.json()["po"]["status"] == "PENDING"

    # 4. Accept PO
    accept_resp = await client.post(f"/api/v1/po/{po_id}/accept")
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "ACCEPTED"

    # 5. Create invoice from PO
    invoice_resp = await client.post("/api/v1/invoices/", json={
        "po_id": po_id,
        "line_items": [
            {
                "part_number": "TEST-001",
                "description": "Test Widget",
                "quantity": 50,
                "uom": "PCS",
                "unit_price": "10.00",
            }
        ],
    })
    assert invoice_resp.status_code == 201
    invoice_id = invoice_resp.json()["id"]
    assert invoice_resp.json()["status"] == "DRAFT"

    # 6. Submit invoice
    submit_inv = await client.post(f"/api/v1/invoices/{invoice_id}/submit")
    assert submit_inv.status_code == 200
    assert submit_inv.json()["status"] == "SUBMITTED"

    # 7. Post milestones in sequence
    milestones = ["RAW_MATERIALS", "PRODUCTION_STARTED", "QC_PASSED", "READY_TO_SHIP"]
    for ms in milestones:
        ms_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": ms})
        assert ms_resp.status_code == 201, f"Failed to post milestone {ms}: {ms_resp.text}"
