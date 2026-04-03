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
    # Ensure a valid active vendor exists
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "Test Vendor", "country": "US", "vendor_type": "PROCUREMENT"})
    assert vendor_resp.status_code == 201
    p["vendor_id"] = vendor_resp.json()["id"]
    resp = await client.post("/api/v1/po/", json=p)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_po_returns_201_with_draft_status(client: AsyncClient) -> None:
    data = await _create_po(client)
    assert data["status"] == POStatus.DRAFT.value
    assert data["po_number"].startswith("PO-")
    assert data["vendor_id"]  # vendor id is assigned dynamically
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
    assert "items" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_list_pos_with_status_filter(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")

    resp = await client.get("/api/v1/po/", params={"status": "PENDING"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == POStatus.PENDING.value

    resp_draft = await client.get("/api/v1/po/", params={"status": "DRAFT"})
    assert resp_draft.status_code == 200
    assert resp_draft.json()["total"] == 0
    assert len(resp_draft.json()["items"]) == 0


async def test_list_pos_invalid_status_returns_422(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/po/", params={"status": "INVALID"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


async def _create_vendor(client: AsyncClient, name: str, country: str = "US", vendor_type: str = "PROCUREMENT") -> str:
    resp = await client.post("/api/v1/vendors/", json={"name": name, "country": country, "vendor_type": vendor_type})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_po_for_vendor(client: AsyncClient, vendor_id: str, overrides: dict | None = None) -> dict:
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, **(overrides or {})}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def test_list_pos_search_by_po_number(client: AsyncClient) -> None:
    po = await _create_po(client)
    po_number = po["po_number"]
    # Search by exact po_number prefix
    resp = await client.get("/api/v1/po/", params={"search": po_number})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["po_number"] == po_number


async def test_list_pos_search_by_vendor_name(client: AsyncClient) -> None:
    vendor_a = await _create_vendor(client, "AlphaSupplier")
    vendor_b = await _create_vendor(client, "BetaSupplier")
    await _create_po_for_vendor(client, vendor_a)
    await _create_po_for_vendor(client, vendor_b)

    resp = await client.get("/api/v1/po/", params={"search": "AlphaSupplier"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["vendor_name"] == "AlphaSupplier"


async def test_list_pos_search_by_buyer_name(client: AsyncClient) -> None:
    vendor_id = await _create_vendor(client, "GenericVendor")
    await _create_po_for_vendor(client, vendor_id, {"buyer_name": "UniqueCorpXYZ"})
    await _create_po_for_vendor(client, vendor_id, {"buyer_name": "OtherBuyerABC"})

    resp = await client.get("/api/v1/po/", params={"search": "UniqueCorpXYZ"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["buyer_name"] == "UniqueCorpXYZ"


async def test_list_pos_search_case_insensitive(client: AsyncClient) -> None:
    vendor_id = await _create_vendor(client, "CaseSensitiveVendor")
    await _create_po_for_vendor(client, vendor_id)

    resp = await client.get("/api/v1/po/", params={"search": "casesensitivevendor"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


async def test_list_pos_filter_by_vendor_id(client: AsyncClient) -> None:
    vendor_a = await _create_vendor(client, "FilterVendorA")
    vendor_b = await _create_vendor(client, "FilterVendorB")
    await _create_po_for_vendor(client, vendor_a)
    await _create_po_for_vendor(client, vendor_b)

    resp = await client.get("/api/v1/po/", params={"vendor_id": vendor_a})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["vendor_id"] == vendor_a


async def test_list_pos_filter_by_currency(client: AsyncClient) -> None:
    vendor_id = await _create_vendor(client, "CurrencyVendor")
    await _create_po_for_vendor(client, vendor_id, {"currency": "USD"})
    await _create_po_for_vendor(client, vendor_id, {"currency": "EUR"})

    resp = await client.get("/api/v1/po/", params={"currency": "EUR"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["currency"] == "EUR"


async def test_list_pos_combined_filters(client: AsyncClient) -> None:
    vendor_a = await _create_vendor(client, "ComboVendorA")
    vendor_b = await _create_vendor(client, "ComboVendorB")
    # vendor_a: USD draft, USD pending
    po_a1 = await _create_po_for_vendor(client, vendor_a, {"currency": "USD"})
    await _create_po_for_vendor(client, vendor_a, {"currency": "EUR"})
    # vendor_b: USD draft
    await _create_po_for_vendor(client, vendor_b, {"currency": "USD"})

    await client.post(f"/api/v1/po/{po_a1['id']}/submit")

    resp = await client.get("/api/v1/po/", params={"vendor_id": vendor_a, "currency": "USD", "status": "PENDING"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["vendor_id"] == vendor_a
    assert data["items"][0]["currency"] == "USD"
    assert data["items"][0]["status"] == POStatus.PENDING.value


# ---------------------------------------------------------------------------
# Sort
# ---------------------------------------------------------------------------


async def test_list_pos_sort_by_issued_date_asc(client: AsyncClient) -> None:
    vendor_id = await _create_vendor(client, "SortVendor")
    await _create_po_for_vendor(client, vendor_id, {"issued_date": "2026-01-01T00:00:00Z"})
    await _create_po_for_vendor(client, vendor_id, {"issued_date": "2026-06-01T00:00:00Z"})
    await _create_po_for_vendor(client, vendor_id, {"issued_date": "2026-03-01T00:00:00Z"})

    resp = await client.get("/api/v1/po/", params={"sort_by": "issued_date", "sort_dir": "asc"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 3
    assert items[0]["issued_date"] < items[1]["issued_date"] < items[2]["issued_date"]


async def test_list_pos_default_sort_created_at_desc(client: AsyncClient) -> None:
    vendor_id = await _create_vendor(client, "DefaultSortVendor")
    await _create_po_for_vendor(client, vendor_id)
    await _create_po_for_vendor(client, vendor_id)

    resp = await client.get("/api/v1/po/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    # Default is created_at desc — most recently created first
    assert items[0]["po_number"] > items[1]["po_number"]


# ---------------------------------------------------------------------------
# page_size validation boundary
# ---------------------------------------------------------------------------


async def test_list_pos_page_size_200_accepted(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/po/", params={"page_size": 200})
    assert resp.status_code == 200


async def test_list_pos_page_size_201_rejected(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/po/", params={"page_size": 201})
    assert resp.status_code == 422


async def test_list_pos_invalid_sort_by_returns_422(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/po/", params={"sort_by": "injected_column"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


async def test_list_pos_pagination(client: AsyncClient) -> None:
    vendor_id = await _create_vendor(client, "PaginationVendor")
    for _ in range(5):
        await _create_po_for_vendor(client, vendor_id)

    resp = await client.get("/api/v1/po/", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2


async def test_list_pos_page_beyond_last_returns_empty(client: AsyncClient) -> None:
    vendor_id = await _create_vendor(client, "EmptyPageVendor")
    await _create_po_for_vendor(client, vendor_id)

    resp = await client.get("/api/v1/po/", params={"page": 99, "page_size": 20})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 0


async def test_list_pos_empty_search_returns_all(client: AsyncClient) -> None:
    vendor_id = await _create_vendor(client, "EmptySearchVendor")
    await _create_po_for_vendor(client, vendor_id)
    await _create_po_for_vendor(client, vendor_id)

    resp = await client.get("/api/v1/po/", params={"search": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


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

    updated_payload = {**_PO_PAYLOAD, "vendor_id": po["vendor_id"], "currency": "EUR"}
    resp = await client.put(f"/api/v1/po/{po['id']}", json=updated_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == POStatus.REVISED.value
    assert data["currency"] == "EUR"


async def test_update_non_rejected_po_returns_409(client: AsyncClient) -> None:
    po = await _create_po(client)
    updated_payload = {**_PO_PAYLOAD, "vendor_id": po["vendor_id"]}
    resp = await client.put(f"/api/v1/po/{po['id']}", json=updated_payload)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Resubmit
# ---------------------------------------------------------------------------


async def test_resubmit_revised_returns_pending(client: AsyncClient) -> None:
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    await client.post(f"/api/v1/po/{po['id']}/reject", json={"comment": "Fix it"})
    await client.put(f"/api/v1/po/{po['id']}", json={**_PO_PAYLOAD, "vendor_id": po["vendor_id"]})

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
    revised_payload = {**_PO_PAYLOAD, "vendor_id": po["vendor_id"], "currency": revised_currency}
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


# ---------------------------------------------------------------------------
# Reference data validation
# ---------------------------------------------------------------------------


async def test_create_po_invalid_currency_returns_422(client: AsyncClient) -> None:
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "V", "country": "US", "vendor_type": "PROCUREMENT"})
    vendor_id = vendor_resp.json()["id"]
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "currency": "FAKE"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_create_po_invalid_port_returns_422(client: AsyncClient) -> None:
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "V", "country": "US", "vendor_type": "PROCUREMENT"})
    vendor_id = vendor_resp.json()["id"]
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "port_of_loading": "ZZZZZ"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_create_po_invalid_incoterm_returns_422(client: AsyncClient) -> None:
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "V", "country": "US", "vendor_type": "PROCUREMENT"})
    vendor_id = vendor_resp.json()["id"]
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "incoterm": "NOPE"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_create_po_invalid_payment_terms_returns_422(client: AsyncClient) -> None:
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "V", "country": "US", "vendor_type": "PROCUREMENT"})
    vendor_id = vendor_resp.json()["id"]
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "payment_terms": "NOPE"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Bulk transition
# ---------------------------------------------------------------------------


async def test_bulk_submit_transitions_drafts_to_pending(client: AsyncClient) -> None:
    expected_status = POStatus.PENDING.value
    po1 = await _create_po(client)
    po2 = await _create_po(client)
    po3 = await _create_po(client)
    po_ids = [po1["id"], po2["id"], po3["id"]]

    resp = await client.post("/api/v1/po/bulk/transition", json={"po_ids": po_ids, "action": "submit"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 3
    for result in data["results"]:
        assert result == {"po_id": result["po_id"], "success": True, "error": None, "new_status": expected_status}


async def test_bulk_accept_transitions_pending_to_accepted(client: AsyncClient) -> None:
    expected_status = POStatus.ACCEPTED.value
    po1 = await _create_po(client)
    po2 = await _create_po(client)
    await client.post(f"/api/v1/po/{po1['id']}/submit")
    await client.post(f"/api/v1/po/{po2['id']}/submit")
    po_ids = [po1["id"], po2["id"]]

    resp = await client.post("/api/v1/po/bulk/transition", json={"po_ids": po_ids, "action": "accept"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    for result in data["results"]:
        assert result == {"po_id": result["po_id"], "success": True, "error": None, "new_status": expected_status}


async def test_bulk_reject_requires_comment(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/po/bulk/transition", json={"po_ids": ["some-id"], "action": "reject"})
    assert resp.status_code == 422


async def test_bulk_reject_with_comment_succeeds(client: AsyncClient) -> None:
    rejection_comment = "Not acceptable"
    expected_status = POStatus.REJECTED.value
    po1 = await _create_po(client)
    po2 = await _create_po(client)
    await client.post(f"/api/v1/po/{po1['id']}/submit")
    await client.post(f"/api/v1/po/{po2['id']}/submit")
    po_ids = [po1["id"], po2["id"]]

    resp = await client.post(
        "/api/v1/po/bulk/transition",
        json={"po_ids": po_ids, "action": "reject", "comment": rejection_comment},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    for result in data["results"]:
        assert result == {"po_id": result["po_id"], "success": True, "error": None, "new_status": expected_status}


async def test_bulk_transition_partial_failure(client: AsyncClient) -> None:
    po_pending = await _create_po(client)
    po_draft = await _create_po(client)
    await client.post(f"/api/v1/po/{po_pending['id']}/submit")

    resp = await client.post(
        "/api/v1/po/bulk/transition",
        json={"po_ids": [po_pending["id"], po_draft["id"]], "action": "accept"},
    )
    assert resp.status_code == 200
    results = {r["po_id"]: r for r in resp.json()["results"]}

    assert results[po_pending["id"]] == {
        "po_id": po_pending["id"],
        "success": True,
        "error": None,
        "new_status": POStatus.ACCEPTED.value,
    }
    assert results[po_draft["id"]]["success"] is False
    assert results[po_draft["id"]]["error"] is not None


async def test_bulk_transition_invalid_action(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/po/bulk/transition", json={"po_ids": ["some-id"], "action": "delete"})
    assert resp.status_code == 422


async def test_bulk_transition_empty_po_ids(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/po/bulk/transition", json={"po_ids": [], "action": "submit"})
    assert resp.status_code == 422


async def test_bulk_transition_nonexistent_po(client: AsyncClient) -> None:
    nonexistent_id = "nonexistent-id"
    po = await _create_po(client)

    resp = await client.post(
        "/api/v1/po/bulk/transition",
        json={"po_ids": [po["id"], nonexistent_id], "action": "submit"},
    )
    assert resp.status_code == 200
    results = {r["po_id"]: r for r in resp.json()["results"]}

    assert results[po["id"]] == {
        "po_id": po["id"],
        "success": True,
        "error": None,
        "new_status": POStatus.PENDING.value,
    }
    assert results[nonexistent_id] == {
        "po_id": nonexistent_id,
        "success": False,
        "error": "Purchase order not found",
        "new_status": None,
    }


# ---------------------------------------------------------------------------
# HS code validation
# ---------------------------------------------------------------------------


async def _make_payload_with_hs_code(client: AsyncClient, hs_code: str) -> tuple[dict, int]:
    """Create a PO payload with the given hs_code and return (response_json, status_code)."""
    vendor_resp = await client.post(
        "/api/v1/vendors/", json={"name": "HS Vendor", "country": "US", "vendor_type": "PROCUREMENT"}
    )
    assert vendor_resp.status_code == 201
    vendor_id = vendor_resp.json()["id"]
    line_item = {**_LINE_ITEM, "hs_code": hs_code}
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "line_items": [line_item]}
    resp = await client.post("/api/v1/po/", json=payload)
    return resp.json(), resp.status_code


async def test_create_po_hs_code_too_short_returns_422(client: AsyncClient) -> None:
    # "AB" is too short (2 chars) and contains non-digit characters
    _, status = await _make_payload_with_hs_code(client, "AB")
    assert status == 422


async def test_create_po_hs_code_valid_with_dots_returns_201(client: AsyncClient) -> None:
    # "7318.15" is valid: digits and dots, 7 characters
    _, status = await _make_payload_with_hs_code(client, "7318.15")
    assert status == 201


async def test_create_po_hs_code_minimum_length_returns_201(client: AsyncClient) -> None:
    # "1234" is the minimum valid HS code: 4 digits
    _, status = await _make_payload_with_hs_code(client, "1234")
    assert status == 201
