from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.purchase_order import POStatus

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

_PO_PAYLOAD: dict = {
    "vendor_id": "vendor-1",
    "ship_to_address": "123 Main St",
    "payment_terms": "NET30",
    "currency": "USD",
    "issued_date": "2026-03-16T00:00:00Z",
    "required_delivery_date": "2026-04-01T00:00:00Z",
    "terms_and_conditions": "Standard T&C",
    "incoterm": "FOB",
    "port_of_loading": "Los Angeles",
    "port_of_discharge": "Shanghai",
    "country_of_origin": "US",
    "country_of_destination": "CN",
    "line_items": [_LINE_ITEM],
}


async def _create_po(client: AsyncClient, payload: dict | None = None) -> dict:
    resp = await client.post("/api/v1/po/", json=payload or _PO_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_po_returns_201_with_draft_status(client: AsyncClient) -> None:
    data = await _create_po(client)
    assert data["status"] == POStatus.DRAFT.value
    assert data["po_number"].startswith("PO-")
    assert data["vendor_id"] == "vendor-1"
    assert len(data["line_items"]) == 1
    assert data["total_value"] == "50.00"


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


async def test_list_pos_returns_array(client: AsyncClient) -> None:
    await _create_po(client)
    await _create_po(client)
    resp = await client.get("/api/v1/po/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


async def test_list_pos_with_status_filter(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")

    resp = await client.get("/api/v1/po/", params={"status": "PENDING"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == POStatus.PENDING.value

    resp_draft = await client.get("/api/v1/po/", params={"status": "DRAFT"})
    assert resp_draft.status_code == 200
    assert len(resp_draft.json()) == 0


async def test_list_pos_invalid_status_returns_422(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/po/", params={"status": "INVALID"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


async def test_get_po_detail_returns_full_po(client: AsyncClient) -> None:
    po = await _create_po(client)
    resp = await client.get(f"/api/v1/po/{po['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == po["id"]
    assert len(data["line_items"]) == 1
    assert data["line_items"][0]["part_number"] == "PN-001"
    assert "rejection_history" in data


async def test_get_nonexistent_po_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/po/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


async def test_submit_transitions_draft_to_pending(client: AsyncClient) -> None:
    po = await _create_po(client)
    assert po["status"] == POStatus.DRAFT.value

    resp = await client.post(f"/api/v1/po/{po['id']}/submit")
    assert resp.status_code == 200
    assert resp.json()["status"] == POStatus.PENDING.value


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------


async def test_accept_transitions_pending_to_accepted(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")

    resp = await client.post(f"/api/v1/po/{po['id']}/accept")
    assert resp.status_code == 200
    assert resp.json()["status"] == POStatus.ACCEPTED.value


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------


async def test_reject_transitions_pending_to_rejected_with_comment(client: AsyncClient) -> None:
    rejection_comment = "Price too high"
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")

    resp = await client.post(
        f"/api/v1/po/{po['id']}/reject", json={"comment": rejection_comment}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == POStatus.REJECTED.value
    assert len(data["rejection_history"]) == 1
    assert data["rejection_history"][0]["comment"] == rejection_comment


async def test_reject_with_empty_comment_returns_422(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")

    resp = await client.post(f"/api/v1/po/{po['id']}/reject", json={"comment": "   "})
    assert resp.status_code == 422


async def test_reject_with_missing_comment_returns_422(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")

    resp = await client.post(f"/api/v1/po/{po['id']}/reject", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Invalid transitions → 409
# ---------------------------------------------------------------------------


async def test_accept_on_draft_returns_409(client: AsyncClient) -> None:
    po = await _create_po(client)
    resp = await client.post(f"/api/v1/po/{po['id']}/accept")
    assert resp.status_code == 409


async def test_submit_on_pending_returns_409(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    resp = await client.post(f"/api/v1/po/{po['id']}/submit")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Update (revise)
# ---------------------------------------------------------------------------


async def test_update_rejected_po_returns_revised_status(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    await client.post(f"/api/v1/po/{po['id']}/reject", json={"comment": "Needs revision"})

    updated_payload = {**_PO_PAYLOAD, "currency": "EUR"}
    resp = await client.put(f"/api/v1/po/{po['id']}", json=updated_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == POStatus.REVISED.value
    assert data["currency"] == "EUR"


async def test_update_non_rejected_po_returns_409(client: AsyncClient) -> None:
    po = await _create_po(client)
    resp = await client.put(f"/api/v1/po/{po['id']}", json=_PO_PAYLOAD)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Resubmit
# ---------------------------------------------------------------------------


async def test_resubmit_revised_returns_pending(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    await client.post(f"/api/v1/po/{po['id']}/reject", json={"comment": "Fix it"})
    await client.put(f"/api/v1/po/{po['id']}", json=_PO_PAYLOAD)

    resp = await client.post(f"/api/v1/po/{po['id']}/resubmit")
    assert resp.status_code == 200
    assert resp.json()["status"] == POStatus.PENDING.value


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


async def test_full_lifecycle(client: AsyncClient) -> None:
    rejection_comment = "Quantity too high"
    revised_currency = "GBP"

    # Create → DRAFT
    po = await _create_po(client)
    assert po["status"] == POStatus.DRAFT.value

    # Submit → PENDING
    resp = await client.post(f"/api/v1/po/{po['id']}/submit")
    assert resp.json()["status"] == POStatus.PENDING.value

    # Reject → REJECTED
    resp = await client.post(
        f"/api/v1/po/{po['id']}/reject", json={"comment": rejection_comment}
    )
    assert resp.json()["status"] == POStatus.REJECTED.value

    # Update → REVISED
    revised_payload = {**_PO_PAYLOAD, "currency": revised_currency}
    resp = await client.put(f"/api/v1/po/{po['id']}", json=revised_payload)
    assert resp.json()["status"] == POStatus.REVISED.value

    # Resubmit → PENDING
    resp = await client.post(f"/api/v1/po/{po['id']}/resubmit")
    assert resp.json()["status"] == POStatus.PENDING.value

    # Accept → ACCEPTED
    resp = await client.post(f"/api/v1/po/{po['id']}/accept")
    data = resp.json()
    assert data["status"] == POStatus.ACCEPTED.value
    assert data["currency"] == revised_currency
    assert len(data["rejection_history"]) == 1
    assert data["rejection_history"][0]["comment"] == rejection_comment
