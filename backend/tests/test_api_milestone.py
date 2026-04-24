"""Permanent tests for the milestone router.

Covers existing milestone sequencing behaviour and iter-039 CERT_REQUESTED
activity emission on QC_PASSED.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.activity import ActivityEvent
from src.domain.milestone import ProductionMilestone, MILESTONE_ORDER

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

_VENDOR_PAYLOAD: dict = {"name": "MilestoneVendor", "country": "US", "vendor_type": "PROCUREMENT"}

_PO_BASE: dict = {
    "buyer_name": "Buyer",
    "buyer_country": "US",
    "ship_to_address": "123 St",
    "payment_terms": "NET30",
    "currency": "USD",
    "issued_date": "2026-01-01T00:00:00Z",
    "required_delivery_date": "2026-06-01T00:00:00Z",
    "terms_and_conditions": "T&C",
    "incoterm": "FOB",
    "port_of_loading": "USLAX",
    "port_of_discharge": "CNSHA",
    "country_of_origin": "US",
    "country_of_destination": "CN",
}

_LINE: dict = {
    "part_number": "PN-001",
    "description": "Widget",
    "quantity": 1,
    "uom": "EA",
    "unit_price": "10.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_MARKETPLACE = "AMZ"


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


async def _create_vendor(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/vendors/", json=_VENDOR_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_accepted_po(
    client: AsyncClient,
    vendor_id: str,
    marketplace: str | None = None,
    product_id: str | None = None,
) -> str:
    line = {**_LINE}
    if product_id is not None:
        line["product_id"] = product_id
    payload = {
        **_PO_BASE,
        "vendor_id": vendor_id,
        "line_items": [line],
    }
    if marketplace is not None:
        payload["marketplace"] = marketplace
    po_resp = await client.post("/api/v1/po/", json=payload)
    assert po_resp.status_code == 201
    po_id: str = po_resp.json()["id"]

    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200

    accept_resp = await client.post(f"/api/v1/po/{po_id}/accept")
    assert accept_resp.status_code == 200
    return po_id


async def _post_milestones_up_to(client: AsyncClient, po_id: str, target: ProductionMilestone) -> None:
    """Post all milestones in sequence up to and including target."""
    for ms in MILESTONE_ORDER:
        resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": ms.value})
        assert resp.status_code == 201
        if ms is target:
            break


async def _create_product_with_qual(client: AsyncClient, vendor_id: str) -> tuple[str, str]:
    product_resp = await client.post(
        "/api/v1/products/",
        json={"vendor_id": vendor_id, "part_number": "PN-001", "description": "Widget", "manufacturing_address": ""},
    )
    assert product_resp.status_code == 201
    product_id: str = product_resp.json()["id"]

    qt_resp = await client.post(
        "/api/v1/qualification-types",
        json={"name": "CE Mark", "target_market": _MARKETPLACE, "applies_to_category": "", "description": ""},
    )
    assert qt_resp.status_code == 201
    qt_id: str = qt_resp.json()["id"]

    assign_resp = await client.post(
        f"/api/v1/products/{product_id}/qualifications",
        json={"qualification_type_id": qt_id},
    )
    assert assign_resp.status_code == 201
    return product_id, qt_id


async def _create_valid_cert(client: AsyncClient, product_id: str, qt_id: str) -> str:
    cert_resp = await client.post(
        "/api/v1/certificates/",
        json={
            "product_id": product_id,
            "qualification_type_id": qt_id,
            "cert_number": "CERT-001",
            "issuer": "TestLab",
            "issue_date": "2024-01-01T00:00:00Z",
            "expiry_date": "2099-01-01T00:00:00Z",
            "target_market": _MARKETPLACE,
        },
    )
    assert cert_resp.status_code == 201
    cert_id: str = cert_resp.json()["id"]
    mark_resp = await client.patch(f"/api/v1/certificates/{cert_id}", json={"status": "VALID"})
    assert mark_resp.status_code == 200
    return cert_id


# ---------------------------------------------------------------------------
# Milestone sequencing tests (existing behaviour)
# ---------------------------------------------------------------------------


async def test_post_first_milestone_returns_201(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client)
    po_id = await _create_accepted_po(client, vendor_id)
    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert resp.status_code == 201
    assert resp.json()["milestone"] == ProductionMilestone.RAW_MATERIALS.value


async def test_post_out_of_order_milestone_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client)
    po_id = await _create_accepted_po(client, vendor_id)
    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "QC_PASSED"})
    assert resp.status_code == 409


async def test_post_milestone_on_draft_po_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client)
    payload = {**_PO_BASE, "vendor_id": vendor_id, "line_items": [_LINE]}
    po_resp = await client.post("/api/v1/po/", json=payload)
    po_id: str = po_resp.json()["id"]
    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert resp.status_code == 409


async def test_list_milestones_returns_posted_milestones(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client)
    po_id = await _create_accepted_po(client, vendor_id)
    await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    resp = await client.get(f"/api/v1/po/{po_id}/milestones")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["milestone"] == ProductionMilestone.RAW_MATERIALS.value


# ---------------------------------------------------------------------------
# Iter 039: CERT_REQUESTED activity on QC_PASSED
# ---------------------------------------------------------------------------


async def test_qc_passed_with_missing_cert_emits_cert_requested_activity(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client)
    product_id, _ = await _create_product_with_qual(client, vendor_id)
    # No cert created.
    po_id = await _create_accepted_po(client, vendor_id, marketplace=_MARKETPLACE, product_id=product_id)
    await _post_milestones_up_to(client, po_id, ProductionMilestone.QC_PASSED)

    # Verify CERT_REQUESTED activity was created via activity feed (list_recent, large limit).
    activity_resp = await client.get("/api/v1/activity/?limit=50")
    assert activity_resp.status_code == 200
    entries: list[dict] = activity_resp.json()
    cert_requested_events = [
        e for e in entries
        if e["event"] == ActivityEvent.CERT_REQUESTED.value
        and e["entity_type"] == "CERTIFICATE"
        and e["entity_id"] == product_id
    ]
    assert len(cert_requested_events) == 1


async def test_qc_passed_with_valid_cert_does_not_emit_cert_requested(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client)
    product_id, qt_id = await _create_product_with_qual(client, vendor_id)
    await _create_valid_cert(client, product_id, qt_id)
    po_id = await _create_accepted_po(client, vendor_id, marketplace=_MARKETPLACE, product_id=product_id)
    await _post_milestones_up_to(client, po_id, ProductionMilestone.QC_PASSED)

    activity_resp = await client.get("/api/v1/activity/?limit=50")
    assert activity_resp.status_code == 200
    entries: list[dict] = activity_resp.json()
    cert_requested_events = [
        e for e in entries
        if e["event"] == ActivityEvent.CERT_REQUESTED.value
    ]
    assert len(cert_requested_events) == 0


async def test_qc_passed_with_no_product_id_does_not_emit_cert_requested(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client)
    # PO with line items that have no product_id link.
    po_id = await _create_accepted_po(client, vendor_id, marketplace=_MARKETPLACE, product_id=None)
    await _post_milestones_up_to(client, po_id, ProductionMilestone.QC_PASSED)

    activity_resp = await client.get("/api/v1/activity/?limit=50")
    assert activity_resp.status_code == 200
    entries: list[dict] = activity_resp.json()
    cert_requested_events = [
        e for e in entries
        if e["event"] == ActivityEvent.CERT_REQUESTED.value
    ]
    assert len(cert_requested_events) == 0
