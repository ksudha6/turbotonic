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
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "Test Vendor", "country": "US", "vendor_type": "PROCUREMENT"})
    assert vendor_resp.status_code == 201
    p["vendor_id"] = vendor_resp.json()["id"]
    resp = await client.post("/api/v1/po/", json=p)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# PDF endpoint — basic contract
# ---------------------------------------------------------------------------


async def test_pdf_endpoint_returns_pdf(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    po_id = po["id"]
    po_number = po["po_number"]

    resp = await client.get(f"/api/v1/po/{po_id}/pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0
    assert po_number in resp.headers["content-disposition"]


async def test_pdf_endpoint_404_for_nonexistent_po(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    nonexistent_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/po/{nonexistent_id}/pdf")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PDF export across all statuses
# ---------------------------------------------------------------------------


async def test_pdf_exports_for_every_status(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # DRAFT: create only
    po_draft = await _create_po(client)
    assert po_draft["status"] == POStatus.DRAFT.value

    # PENDING: create + submit
    po_pending = await _create_po(client)
    submit_resp = await client.post(f"/api/v1/po/{po_pending['id']}/submit")
    assert submit_resp.json()["po"]["status"] == POStatus.PENDING.value

    # ACCEPTED: create + submit + accept
    po_accepted = await _create_po(client)
    await client.post(f"/api/v1/po/{po_accepted['id']}/submit")
    accept_resp = await client.post(f"/api/v1/po/{po_accepted['id']}/accept")
    assert accept_resp.json()["status"] == POStatus.ACCEPTED.value

    # REJECTED: create + submit + remove all lines + submit-response
    # (iter 056: PO REJECTED is reachable only via convergence when all lines REMOVED)
    po_rejected = await _create_po(client)
    await client.post(f"/api/v1/po/{po_rejected['id']}/submit")
    for li in po_rejected["line_items"]:
        await client.post(f"/api/v1/po/{po_rejected['id']}/lines/{li['part_number']}/remove", json={})
    rejected_resp = await client.post(f"/api/v1/po/{po_rejected['id']}/submit-response", json={})
    assert rejected_resp.json()["status"] == POStatus.REJECTED.value

    # REVISED: create + submit + converge to REJECTED + update (revise)
    po_revised = await _create_po(client)
    vendor_id = po_revised["vendor_id"]
    await client.post(f"/api/v1/po/{po_revised['id']}/submit")
    for li in po_revised["line_items"]:
        await client.post(f"/api/v1/po/{po_revised['id']}/lines/{li['part_number']}/remove", json={})
    await client.post(f"/api/v1/po/{po_revised['id']}/submit-response", json={})
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


async def test_pdf_contains_resolved_labels(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
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


async def test_pdf_excludes_rejection_history(authenticated_client: AsyncClient) -> None:
    # Iter 056: rejection_history is no longer written by the negotiation flow, but the
    # PDF must still not surface legacy comments if any were seeded. Drive a PO through
    # convergence to REJECTED and assert no stray comment text appears.
    client = authenticated_client
    rejection_marker = "UNIQUE_REJECTION_MARKER_12345"

    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    for li in po["line_items"]:
        await client.post(f"/api/v1/po/{po['id']}/lines/{li['part_number']}/remove", json={})
    rejected_resp = await client.post(f"/api/v1/po/{po['id']}/submit-response", json={})
    assert rejected_resp.status_code == 200

    pdf_resp = await client.get(f"/api/v1/po/{po['id']}/pdf")
    assert pdf_resp.status_code == 200

    pdf_text = _extract_pdf_text(pdf_resp.content)
    assert rejection_marker not in pdf_text


# ---------------------------------------------------------------------------
# PDF content: currency appears in header only, not on line item cells
# ---------------------------------------------------------------------------


async def test_pdf_currency_in_header_not_line_items(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # The PO uses USD. The PDF should state currency once in the header/trade
    # details section. Line item cells must not repeat the currency code.
    currency_code = "USD"
    unit_price = "5.00"
    line_total = "50.00"  # quantity 10 * unit_price 5.00

    po = await _create_po(client)
    pdf_resp = await client.get(f"/api/v1/po/{po['id']}/pdf")
    assert pdf_resp.status_code == 200

    pdf_text = _extract_pdf_text(pdf_resp.content)

    # Currency label must appear in the document (header / trade details).
    assert currency_code in pdf_text

    # The numeric values must appear without the currency code appended.
    # If the code were still appended, "5.00 USD" or "50.00 USD" would appear.
    assert f"{unit_price} {currency_code}" not in pdf_text
    assert f"{line_total} {currency_code}" not in pdf_text


# ---------------------------------------------------------------------------
# Iter 058 -- PDF filters to ACCEPTED-only scope and stamps MODIFIED after negotiation
# ---------------------------------------------------------------------------


_LINE_ITEM_KEEP: dict = {
    "part_number": "PN-KEEP",
    "description": "Keep widget",
    "quantity": 10,
    "uom": "EA",
    "unit_price": "5.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_LINE_ITEM_DROP: dict = {
    "part_number": "PN-DROP",
    "description": "Drop widget",
    "quantity": 20,
    "uom": "EA",
    "unit_price": "3.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}


async def _create_two_line_po(client: AsyncClient) -> dict:
    vendor_resp = await client.post(
        "/api/v1/vendors/", json={"name": "Two Line Vendor", "country": "US", "vendor_type": "PROCUREMENT"}
    )
    assert vendor_resp.status_code == 201
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_resp.json()["id"]}
    payload["line_items"] = [_LINE_ITEM_KEEP, _LINE_ITEM_DROP]
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def test_pdf_excludes_removed_line_from_rendered_output(authenticated_client: AsyncClient) -> None:
    # After a PO converges to ACCEPTED with one line REMOVED, the PDF must not
    # render the REMOVED part_number.
    client = authenticated_client
    po = await _create_two_line_po(client)
    po_id = po["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    # Accept one, remove the other, then submit-response to converge.
    await client.post(f"/api/v1/po/{po_id}/lines/PN-KEEP/accept", json={})
    await client.post(f"/api/v1/po/{po_id}/lines/PN-DROP/remove", json={})
    converge_resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert converge_resp.status_code == 200
    assert converge_resp.json()["status"] == POStatus.ACCEPTED.value

    pdf_resp = await client.get(f"/api/v1/po/{po_id}/pdf")
    assert pdf_resp.status_code == 200

    pdf_text = _extract_pdf_text(pdf_resp.content)
    assert "PN-KEEP" in pdf_text, (
        "accepted line PN-KEEP must appear in PDF"
    )
    assert "PN-DROP" not in pdf_text, (
        "removed line PN-DROP must not appear in the PDF after convergence"
    )


async def test_pdf_modified_stamp_absent_before_first_round(authenticated_client: AsyncClient) -> None:
    # round_count == 0 means the PO has not been through any negotiation round; the
    # MODIFIED stamp must not appear.
    client = authenticated_client
    po = await _create_po(client)
    pdf_resp = await client.get(f"/api/v1/po/{po['id']}/pdf")
    assert pdf_resp.status_code == 200
    pdf_text = _extract_pdf_text(pdf_resp.content)
    assert "MODIFIED" not in pdf_text, (
        f"MODIFIED stamp must only appear with round_count >= 1; DRAFT PDF: {pdf_text[:200]!r}"
    )


async def test_pdf_modified_stamp_present_after_first_round(authenticated_client: AsyncClient) -> None:
    # After one completed round (round_count >= 1) the stamp must appear in the PDF.
    client = authenticated_client
    po = await _create_two_line_po(client)
    po_id = po["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/lines/PN-KEEP/modify", json={"fields": {"quantity": 8}})
    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert submit_resp.status_code == 200
    # Mid-loop: round_count should be 1.
    assert submit_resp.json()["round_count"] == 1

    pdf_resp = await client.get(f"/api/v1/po/{po_id}/pdf")
    assert pdf_resp.status_code == 200
    pdf_text = _extract_pdf_text(pdf_resp.content)
    assert "MODIFIED" in pdf_text, (
        f"MODIFIED stamp must appear once round_count >= 1; got PDF: {pdf_text[:300]!r}"
    )


async def test_pdf_line_count_matches_accepted_lines_only(authenticated_client: AsyncClient) -> None:
    # A converged PO with one ACCEPTED and one REMOVED line must render exactly one
    # numbered line row in the PDF. Each rendered row starts with an index cell,
    # so counting part_numbers is a robust check.
    client = authenticated_client
    po = await _create_two_line_po(client)
    po_id = po["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/lines/PN-KEEP/accept", json={})
    await client.post(f"/api/v1/po/{po_id}/lines/PN-DROP/remove", json={})
    converge_resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert converge_resp.json()["status"] == POStatus.ACCEPTED.value

    pdf_resp = await client.get(f"/api/v1/po/{po_id}/pdf")
    pdf_text = _extract_pdf_text(pdf_resp.content)
    # Only the ACCEPTED part_number must appear.
    assert pdf_text.count("PN-KEEP") >= 1
    assert pdf_text.count("PN-DROP") == 0, (
        f"PN-DROP must not appear in the rendered PDF; got: {pdf_text!r}"
    )
