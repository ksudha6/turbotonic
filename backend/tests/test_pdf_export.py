from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient
from pypdf import PdfReader

from src.domain.purchase_order import POStatus
from src.domain.reference_labels import currency_label, port_label, country_label


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF given its raw bytes."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Test data
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

_PO_PAYLOAD: dict = {
    "vendor_id": "placeholder",
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


async def _create_po(client: AsyncClient, payload: dict | None = None) -> dict:
    p = dict(payload or _PO_PAYLOAD)
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "Test Vendor", "country": "US"})
    assert vendor_resp.status_code == 201
    p["vendor_id"] = vendor_resp.json()["id"]
    resp = await client.post("/api/v1/po/", json=p)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# PDF endpoint — basic contract
# ---------------------------------------------------------------------------


async def test_pdf_endpoint_returns_pdf(client: AsyncClient) -> None:
    po = await _create_po(client)
    po_id = po["id"]
    po_number = po["po_number"]

    resp = await client.get(f"/api/v1/po/{po_id}/pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0
    assert po_number in resp.headers["content-disposition"]


async def test_pdf_endpoint_404_for_nonexistent_po(client: AsyncClient) -> None:
    nonexistent_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/po/{nonexistent_id}/pdf")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PDF export across all statuses
# ---------------------------------------------------------------------------


async def test_pdf_exports_for_every_status(client: AsyncClient) -> None:
    # DRAFT: create only
    po_draft = await _create_po(client)
    assert po_draft["status"] == POStatus.DRAFT.value

    # PENDING: create + submit
    po_pending = await _create_po(client)
    submit_resp = await client.post(f"/api/v1/po/{po_pending['id']}/submit")
    assert submit_resp.json()["status"] == POStatus.PENDING.value

    # ACCEPTED: create + submit + accept
    po_accepted = await _create_po(client)
    await client.post(f"/api/v1/po/{po_accepted['id']}/submit")
    accept_resp = await client.post(f"/api/v1/po/{po_accepted['id']}/accept")
    assert accept_resp.json()["status"] == POStatus.ACCEPTED.value

    # REJECTED: create + submit + reject
    po_rejected = await _create_po(client)
    await client.post(f"/api/v1/po/{po_rejected['id']}/submit")
    reject_resp = await client.post(
        f"/api/v1/po/{po_rejected['id']}/reject", json={"comment": "Too expensive"}
    )
    assert reject_resp.json()["status"] == POStatus.REJECTED.value

    # REVISED: create + submit + reject + update (revise)
    po_revised = await _create_po(client)
    vendor_id = po_revised["vendor_id"]
    await client.post(f"/api/v1/po/{po_revised['id']}/submit")
    await client.post(
        f"/api/v1/po/{po_revised['id']}/reject", json={"comment": "Needs changes"}
    )
    revise_resp = await client.put(
        f"/api/v1/po/{po_revised['id']}",
        json={**_PO_PAYLOAD, "vendor_id": vendor_id, "currency": "EUR"},
    )
    assert revise_resp.json()["status"] == POStatus.REVISED.value

    pos_by_status = [
        (POStatus.DRAFT, po_draft),
        (POStatus.PENDING, po_pending),
        (POStatus.ACCEPTED, po_accepted),
        (POStatus.REJECTED, po_rejected),
        (POStatus.REVISED, po_revised),
    ]
    for status, po in pos_by_status:
        resp = await client.get(f"/api/v1/po/{po['id']}/pdf")
        assert resp.status_code == 200, f"Expected 200 for status {status.value}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# PDF content: resolved reference labels
# ---------------------------------------------------------------------------


async def test_pdf_contains_resolved_labels(client: AsyncClient) -> None:
    # Reference codes used in _PO_PAYLOAD and their expected resolved labels
    currency_code = "USD"
    port_of_loading_code = "USLAX"
    port_of_discharge_code = "CNSHA"
    buyer_country_code = "US"

    expected_currency_label = currency_label(currency_code)       # "US Dollar"
    expected_pol_label = port_label(port_of_loading_code)         # "Los Angeles, United States"
    expected_pod_label = port_label(port_of_discharge_code)       # "Shanghai, China"
    expected_buyer_country_label = country_label(buyer_country_code)  # "United States"

    po = await _create_po(client)
    resp = await client.get(f"/api/v1/po/{po['id']}/pdf")
    assert resp.status_code == 200

    pdf_text = _extract_pdf_text(resp.content)
    assert expected_currency_label in pdf_text
    assert expected_pol_label in pdf_text
    assert expected_pod_label in pdf_text
    assert expected_buyer_country_label in pdf_text


# ---------------------------------------------------------------------------
# PDF content: rejection history is excluded
# ---------------------------------------------------------------------------


async def test_pdf_excludes_rejection_history(client: AsyncClient) -> None:
    rejection_comment = "UNIQUE_REJECTION_MARKER_12345"

    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    reject_resp = await client.post(
        f"/api/v1/po/{po['id']}/reject", json={"comment": rejection_comment}
    )
    assert reject_resp.status_code == 200

    pdf_resp = await client.get(f"/api/v1/po/{po['id']}/pdf")
    assert pdf_resp.status_code == 200

    pdf_text = _extract_pdf_text(pdf_resp.content)
    assert rejection_comment not in pdf_text
