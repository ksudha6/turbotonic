from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from src.domain.certificate import Certificate, CertificateStatus
from src.domain.purchase_order import LineItemStatus, POStatus
from src.domain.product import Product
from src.domain.qualification_type import QualificationType
from src.services.quality_gate import CertWarningReason

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

_LINE_ITEM_2: dict = {
    "part_number": "PN-002",
    "description": "Widget B",
    "quantity": 5,
    "uom": "EA",
    "unit_price": "3.00",
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
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "Test Vendor", "country": "US", "vendor_type": "PROCUREMENT"})
    assert vendor_resp.status_code == 201
    p["vendor_id"] = vendor_resp.json()["id"]
    resp = await client.post("/api/v1/po/", json=p)
    assert resp.status_code == 201
    return resp.json()


async def _create_two_line_po(client: AsyncClient) -> dict:
    vendor_resp = await client.post(
        "/api/v1/vendors/", json={"name": "TwoLine Vendor", "country": "US", "vendor_type": "PROCUREMENT"}
    )
    assert vendor_resp.status_code == 201
    vendor_id = vendor_resp.json()["id"]
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "line_items": [_LINE_ITEM, _LINE_ITEM_2]}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _create_pending_po(client: AsyncClient, two_lines: bool = False) -> dict:
    po = await (_create_two_line_po(client) if two_lines else _create_po(client))
    r = await client.post(f"/api/v1/po/{po['id']}/submit")
    assert r.status_code == 200
    # Submit returns POSubmitResponse({po: ..., cert_warnings: []}); unwrap the po.
    return r.json()["po"]


# ---------------------------------------------------------------------------
# Create, list, get, submit, accept (unchanged endpoints)
# ---------------------------------------------------------------------------


async def test_create_po_returns_201_with_draft_status(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    data = await _create_po(client)
    assert data["status"] == POStatus.DRAFT.value
    assert data["po_number"].startswith("PO-")
    assert data["vendor_id"]
    assert len(data["line_items"]) == 1
    assert data["total_value"] == "50.00"
    assert data["round_count"] == 0
    assert data["last_actor_role"] is None


async def test_list_pos_returns_array(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    await _create_po(client)
    await _create_po(client)
    resp = await client.get("/api/v1/po/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_list_pos_with_status_filter(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")

    resp = await client.get("/api/v1/po/", params={"status": "PENDING"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == POStatus.PENDING.value


async def test_list_pos_invalid_status_returns_422(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.get("/api/v1/po/", params={"status": "INVALID"})
    assert resp.status_code == 422


async def _create_vendor(client: AsyncClient, name: str, country: str = "US", vendor_type: str = "PROCUREMENT") -> str:
    resp = await client.post("/api/v1/vendors/", json={"name": name, "country": country, "vendor_type": vendor_type})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_po_for_vendor(client: AsyncClient, vendor_id: str, overrides: dict | None = None) -> dict:
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, **(overrides or {})}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def test_list_pos_search_by_po_number(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    resp = await client.get("/api/v1/po/", params={"search": po["po_number"]})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_pos_search_by_vendor_name(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_a = await _create_vendor(client, "AlphaSupplier")
    vendor_b = await _create_vendor(client, "BetaSupplier")
    await _create_po_for_vendor(client, vendor_a)
    await _create_po_for_vendor(client, vendor_b)
    resp = await client.get("/api/v1/po/", params={"search": "AlphaSupplier"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["vendor_name"] == "AlphaSupplier"


async def test_list_pos_search_by_buyer_name(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client, "GenericVendor")
    await _create_po_for_vendor(client, vendor_id, {"buyer_name": "UniqueCorpXYZ"})
    await _create_po_for_vendor(client, vendor_id, {"buyer_name": "OtherBuyerABC"})
    resp = await client.get("/api/v1/po/", params={"search": "UniqueCorpXYZ"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_pos_search_case_insensitive(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client, "CaseSensitiveVendor")
    await _create_po_for_vendor(client, vendor_id)
    resp = await client.get("/api/v1/po/", params={"search": "casesensitivevendor"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_pos_filter_by_vendor_id(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_a = await _create_vendor(client, "FilterVendorA")
    vendor_b = await _create_vendor(client, "FilterVendorB")
    await _create_po_for_vendor(client, vendor_a)
    await _create_po_for_vendor(client, vendor_b)
    resp = await client.get("/api/v1/po/", params={"vendor_id": vendor_a})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_pos_filter_by_currency(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client, "CurrencyVendor")
    await _create_po_for_vendor(client, vendor_id, {"currency": "USD"})
    await _create_po_for_vendor(client, vendor_id, {"currency": "EUR"})
    resp = await client.get("/api/v1/po/", params={"currency": "EUR"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_pos_combined_filters(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_a = await _create_vendor(client, "ComboVendorA")
    vendor_b = await _create_vendor(client, "ComboVendorB")
    po_a1 = await _create_po_for_vendor(client, vendor_a, {"currency": "USD"})
    await _create_po_for_vendor(client, vendor_a, {"currency": "EUR"})
    await _create_po_for_vendor(client, vendor_b, {"currency": "USD"})
    await client.post(f"/api/v1/po/{po_a1['id']}/submit")
    resp = await client.get("/api/v1/po/", params={"vendor_id": vendor_a, "currency": "USD", "status": "PENDING"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == POStatus.PENDING.value


async def test_list_pos_sort_by_issued_date_asc(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client, "SortVendor")
    await _create_po_for_vendor(client, vendor_id, {"issued_date": "2026-01-01T00:00:00Z"})
    await _create_po_for_vendor(client, vendor_id, {"issued_date": "2026-06-01T00:00:00Z"})
    await _create_po_for_vendor(client, vendor_id, {"issued_date": "2026-03-01T00:00:00Z"})
    resp = await client.get("/api/v1/po/", params={"sort_by": "issued_date", "sort_dir": "asc"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items[0]["issued_date"] < items[1]["issued_date"] < items[2]["issued_date"]


async def test_list_pos_default_sort_created_at_desc(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client, "DefaultSortVendor")
    await _create_po_for_vendor(client, vendor_id)
    await _create_po_for_vendor(client, vendor_id)
    resp = await client.get("/api/v1/po/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items[0]["po_number"] > items[1]["po_number"]


async def test_list_pos_page_size_200_accepted(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.get("/api/v1/po/", params={"page_size": 200})
    assert resp.status_code == 200


async def test_list_pos_page_size_201_rejected(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.get("/api/v1/po/", params={"page_size": 201})
    assert resp.status_code == 422


async def test_list_pos_invalid_sort_by_returns_422(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.get("/api/v1/po/", params={"sort_by": "injected_column"})
    assert resp.status_code == 422


async def test_list_pos_pagination(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client, "PaginationVendor")
    for _ in range(5):
        await _create_po_for_vendor(client, vendor_id)
    resp = await client.get("/api/v1/po/", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


async def test_list_pos_page_beyond_last_returns_empty(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client, "EmptyPageVendor")
    await _create_po_for_vendor(client, vendor_id)
    resp = await client.get("/api/v1/po/", params={"page": 99, "page_size": 20})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0


async def test_list_pos_empty_search_returns_all(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_id = await _create_vendor(client, "EmptySearchVendor")
    await _create_po_for_vendor(client, vendor_id)
    await _create_po_for_vendor(client, vendor_id)
    resp = await client.get("/api/v1/po/", params={"search": ""})
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


async def test_get_po_detail_returns_full_po(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    resp = await client.get(f"/api/v1/po/{po['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == po["id"]
    assert "rejection_history" in data
    assert data["round_count"] == 0


async def test_get_nonexistent_po_returns_404(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.get("/api/v1/po/does-not-exist")
    assert resp.status_code == 404


async def test_submit_transitions_draft_to_pending(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    resp = await client.post(f"/api/v1/po/{po['id']}/submit")
    assert resp.status_code == 200
    data = resp.json()
    # Submit returns POSubmitResponse wrapping {po, cert_warnings}.
    assert data["po"]["status"] == POStatus.PENDING.value
    assert "cert_warnings" in data


async def test_accept_transitions_pending_to_accepted(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    resp = await client.post(f"/api/v1/po/{po['id']}/accept")
    assert resp.status_code == 200
    assert resp.json()["status"] == POStatus.ACCEPTED.value


async def test_accept_on_draft_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    resp = await client.post(f"/api/v1/po/{po['id']}/accept")
    assert resp.status_code == 409


async def test_submit_on_pending_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    resp = await client.post(f"/api/v1/po/{po['id']}/submit")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Reference data validation (unchanged)
# ---------------------------------------------------------------------------


async def test_create_po_invalid_currency_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "V", "country": "US", "vendor_type": "PROCUREMENT"})
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_resp.json()["id"], "currency": "FAKE"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_create_po_invalid_port_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "V", "country": "US", "vendor_type": "PROCUREMENT"})
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_resp.json()["id"], "port_of_loading": "ZZZZZ"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_create_po_invalid_incoterm_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "V", "country": "US", "vendor_type": "PROCUREMENT"})
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_resp.json()["id"], "incoterm": "NOPE"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_create_po_invalid_payment_terms_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_resp = await client.post("/api/v1/vendors/", json={"name": "V", "country": "US", "vendor_type": "PROCUREMENT"})
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_resp.json()["id"], "payment_terms": "NOPE"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Bulk transition (iter 056 drops reject branch)
# ---------------------------------------------------------------------------


async def test_bulk_submit_transitions_drafts_to_pending(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    pos = [await _create_po(client) for _ in range(3)]
    resp = await client.post("/api/v1/po/bulk/transition", json={"po_ids": [p["id"] for p in pos], "action": "submit"})
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert r["success"] is True
        assert r["new_status"] == POStatus.PENDING.value


async def test_bulk_accept_transitions_pending_to_accepted(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    pos = [await _create_po(client) for _ in range(2)]
    for p in pos:
        await client.post(f"/api/v1/po/{p['id']}/submit")
    resp = await client.post("/api/v1/po/bulk/transition", json={"po_ids": [p["id"] for p in pos], "action": "accept"})
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert r["new_status"] == POStatus.ACCEPTED.value


async def test_bulk_reject_returns_422(authenticated_client: AsyncClient) -> None:
    # Iter 056: the 'reject' branch is gone; bulk reject must return 422.
    resp = await authenticated_client.post(
        "/api/v1/po/bulk/transition",
        json={"po_ids": ["some-id"], "action": "reject", "comment": "whatever"},
    )
    assert resp.status_code == 422


async def test_bulk_transition_partial_failure(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po_pending = await _create_po(client)
    po_draft = await _create_po(client)
    await client.post(f"/api/v1/po/{po_pending['id']}/submit")
    resp = await client.post(
        "/api/v1/po/bulk/transition",
        json={"po_ids": [po_pending["id"], po_draft["id"]], "action": "accept"},
    )
    assert resp.status_code == 200
    results = {r["po_id"]: r for r in resp.json()["results"]}
    assert results[po_pending["id"]]["success"] is True
    assert results[po_draft["id"]]["success"] is False


async def test_bulk_transition_invalid_action(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.post("/api/v1/po/bulk/transition", json={"po_ids": ["some-id"], "action": "delete"})
    assert resp.status_code == 422


async def test_bulk_transition_empty_po_ids(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.post("/api/v1/po/bulk/transition", json={"po_ids": [], "action": "submit"})
    assert resp.status_code == 422


async def test_bulk_transition_nonexistent_po(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    resp = await client.post(
        "/api/v1/po/bulk/transition",
        json={"po_ids": [po["id"], "nonexistent-id"], "action": "submit"},
    )
    assert resp.status_code == 200
    results = {r["po_id"]: r for r in resp.json()["results"]}
    assert results[po["id"]]["success"] is True
    assert results["nonexistent-id"]["success"] is False


# ---------------------------------------------------------------------------
# HS code validation (unchanged)
# ---------------------------------------------------------------------------


async def _make_payload_with_hs_code(client: AsyncClient, hs_code: str) -> tuple[dict, int]:
    vendor_resp = await client.post(
        "/api/v1/vendors/", json={"name": "HS Vendor", "country": "US", "vendor_type": "PROCUREMENT"}
    )
    vendor_id = vendor_resp.json()["id"]
    line_item = {**_LINE_ITEM, "hs_code": hs_code}
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "line_items": [line_item]}
    resp = await client.post("/api/v1/po/", json=payload)
    return resp.json(), resp.status_code


async def test_create_po_hs_code_too_short_returns_422(authenticated_client: AsyncClient) -> None:
    _, status = await _make_payload_with_hs_code(authenticated_client, "AB")
    assert status == 422


async def test_create_po_hs_code_valid_with_dots_returns_201(authenticated_client: AsyncClient) -> None:
    _, status = await _make_payload_with_hs_code(authenticated_client, "7318.15")
    assert status == 201


async def test_create_po_hs_code_minimum_length_returns_201(authenticated_client: AsyncClient) -> None:
    _, status = await _make_payload_with_hs_code(authenticated_client, "1234")
    assert status == 201


# ---------------------------------------------------------------------------
# Iter 056: line-level negotiation endpoints
# ---------------------------------------------------------------------------


async def test_modify_line_returns_200_and_persists_change(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    resp = await client.post(
        f"/api/v1/po/{po['id']}/lines/PN-001/modify",
        json={"fields": {"quantity": 7}},
    )
    assert resp.status_code == 200
    data = resp.json()
    line = next(li for li in data["line_items"] if li["part_number"] == "PN-001")
    assert line["quantity"] == 7
    assert line["status"] == LineItemStatus.MODIFIED_BY_SM.value
    assert any(e["field"] == "quantity" for e in line["history"])


async def test_modify_line_non_editable_field_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    resp = await client.post(
        f"/api/v1/po/{po['id']}/lines/PN-001/modify",
        json={"fields": {"po_number": "PO-999"}},
    )
    assert resp.status_code == 422


async def test_modify_line_unknown_part_number_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    resp = await client.post(
        f"/api/v1/po/{po['id']}/lines/NOPE/modify",
        json={"fields": {"quantity": 5}},
    )
    assert resp.status_code == 404


async def test_modify_line_on_draft_po_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_po(client)
    resp = await client.post(
        f"/api/v1/po/{po['id']}/lines/PN-001/modify",
        json={"fields": {"quantity": 5}},
    )
    assert resp.status_code == 409


async def test_accept_line_returns_200(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    resp = await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/accept", json={})
    assert resp.status_code == 200
    data = resp.json()
    line = next(li for li in data["line_items"] if li["part_number"] == "PN-001")
    assert line["status"] == LineItemStatus.ACCEPTED.value


async def test_accept_line_terminal_state_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/accept", json={})
    resp = await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/accept", json={})
    assert resp.status_code == 409


async def test_remove_line_returns_200(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    resp = await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/remove", json={})
    assert resp.status_code == 200
    data = resp.json()
    line = next(li for li in data["line_items"] if li["part_number"] == "PN-001")
    assert line["status"] == LineItemStatus.REMOVED.value


async def test_force_accept_at_round_one_returns_403(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client, two_lines=True)
    # Move to round 1 only
    await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/modify", json={"fields": {"quantity": 7}})
    await client.post(f"/api/v1/po/{po['id']}/submit-response", json={})

    resp = await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/force-accept", json={})
    assert resp.status_code == 403


async def _drive_to_round_two(client: AsyncClient, po_id: str) -> None:
    await client.post(f"/api/v1/po/{po_id}/lines/PN-001/modify", json={"fields": {"quantity": 7}})
    await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    await client.post(f"/api/v1/po/{po_id}/lines/PN-001/modify", json={"fields": {"quantity": 8}})
    await client.post(f"/api/v1/po/{po_id}/submit-response", json={})


async def test_force_accept_at_round_two_for_sm_returns_200(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client, two_lines=True)
    await _drive_to_round_two(client, po["id"])
    # Line PN-001 still MODIFIED; SM force-accepts
    resp = await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/force-accept", json={})
    assert resp.status_code == 200
    data = resp.json()
    line = next(li for li in data["line_items"] if li["part_number"] == "PN-001")
    assert line["status"] == LineItemStatus.ACCEPTED.value


async def test_force_remove_at_round_two_for_sm_returns_200(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client, two_lines=True)
    await _drive_to_round_two(client, po["id"])
    resp = await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/force-remove", json={})
    assert resp.status_code == 200
    data = resp.json()
    line = next(li for li in data["line_items"] if li["part_number"] == "PN-001")
    assert line["status"] == LineItemStatus.REMOVED.value


async def test_submit_response_increments_round_and_returns_updated_po(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/modify", json={"fields": {"quantity": 7}})
    resp = await client.post(f"/api/v1/po/{po['id']}/submit-response", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["round_count"] == 1
    assert data["status"] == POStatus.MODIFIED.value


async def test_submit_response_convergence_sets_po_accepted(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    # Accept the single line, then submit_response -> convergence -> ACCEPTED
    await client.post(f"/api/v1/po/{po['id']}/lines/PN-001/accept", json={})
    resp = await client.post(f"/api/v1/po/{po['id']}/submit-response", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == POStatus.ACCEPTED.value


async def test_unknown_part_number_on_accept_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    resp = await client.post(f"/api/v1/po/{po['id']}/lines/NOPE/accept", json={})
    assert resp.status_code == 404


async def test_accept_lines_endpoint_removed(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    resp = await client.post(
        f"/api/v1/po/{po['id']}/accept-lines",
        json={"decisions": [{"part_number": "PN-001", "status": "ACCEPTED"}]},
    )
    assert resp.status_code == 404


async def test_reject_endpoint_removed(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    po = await _create_pending_po(client)
    resp = await client.post(f"/api/v1/po/{po['id']}/reject", json={"comment": "no"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Iter 059: advance payment gate and post-acceptance line mutations
# ---------------------------------------------------------------------------


_ADVANCE_PO_PAYLOAD: dict = {**_PO_PAYLOAD, "payment_terms": "100_PCT_ADVANCE"}


async def _create_accepted_po(client: AsyncClient, payload: dict | None = None) -> dict:
    po = await _create_po(client, payload)
    await client.post(f"/api/v1/po/{po['id']}/submit")
    r = await client.post(f"/api/v1/po/{po['id']}/accept")
    assert r.status_code == 200
    return r.json()


async def test_mark_advance_paid_returns_200_for_advance_required_po(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client, _ADVANCE_PO_PAYLOAD)
    resp = await client.post(f"/api/v1/po/{po['id']}/mark-advance-paid", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["advance_paid_at"] is not None


async def test_mark_advance_paid_is_idempotent_over_http(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client, _ADVANCE_PO_PAYLOAD)
    r1 = await client.post(f"/api/v1/po/{po['id']}/mark-advance-paid", json={})
    r2 = await client.post(f"/api/v1/po/{po['id']}/mark-advance-paid", json={})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["advance_paid_at"] == r2.json()["advance_paid_at"]


async def test_mark_advance_paid_returns_409_on_non_advance_terms(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client)  # uses TT, no advance
    resp = await client.post(f"/api/v1/po/{po['id']}/mark-advance-paid", json={})
    assert resp.status_code == 409


async def test_mark_advance_paid_returns_409_on_draft_po(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_po(client, _ADVANCE_PO_PAYLOAD)
    resp = await client.post(f"/api/v1/po/{po['id']}/mark-advance-paid", json={})
    assert resp.status_code == 409


async def test_add_line_post_accept_returns_201_and_adds_line(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client)
    new_line = {
        "part_number": "PN-NEW",
        "description": "Added after acceptance",
        "quantity": 2,
        "uom": "EA",
        "unit_price": "4.00",
        "hs_code": "8471.30",
        "country_of_origin": "US",
    }
    resp = await client.post(f"/api/v1/po/{po['id']}/lines", json={"line": new_line})
    assert resp.status_code == 201
    data = resp.json()
    parts = [li["part_number"] for li in data["line_items"]]
    assert "PN-NEW" in parts
    added = next(li for li in data["line_items"] if li["part_number"] == "PN-NEW")
    assert added["status"] == LineItemStatus.ACCEPTED.value


async def test_add_line_post_accept_returns_409_when_advance_paid(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client, _ADVANCE_PO_PAYLOAD)
    await client.post(f"/api/v1/po/{po['id']}/mark-advance-paid", json={})
    new_line = {
        "part_number": "PN-NEW",
        "description": "x",
        "quantity": 1,
        "uom": "EA",
        "unit_price": "1.00",
        "hs_code": "8471.30",
        "country_of_origin": "US",
    }
    resp = await client.post(f"/api/v1/po/{po['id']}/lines", json={"line": new_line})
    assert resp.status_code == 409


async def test_add_line_post_accept_returns_422_on_invalid_payload(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client)
    bad_line = {
        "part_number": "PN-NEW",
        "description": "x",
        "quantity": 0,  # invalid
        "uom": "EA",
        "unit_price": "1.00",
        "hs_code": "8471.30",
        "country_of_origin": "US",
    }
    resp = await client.post(f"/api/v1/po/{po['id']}/lines", json={"line": bad_line})
    assert resp.status_code == 422


async def test_remove_line_post_accept_returns_200(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client, {**_PO_PAYLOAD, "line_items": [_LINE_ITEM, _LINE_ITEM_2]})
    resp = await client.delete(f"/api/v1/po/{po['id']}/lines/PN-002")
    assert resp.status_code == 200
    data = resp.json()
    removed = next(li for li in data["line_items"] if li["part_number"] == "PN-002")
    assert removed["status"] == LineItemStatus.REMOVED.value


async def test_remove_line_post_accept_returns_409_on_downstream_artifact(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client, {**_PO_PAYLOAD, "line_items": [_LINE_ITEM, _LINE_ITEM_2]})
    # Create an invoice that references PN-001 so it cannot be removed.
    inv_resp = await client.post(
        "/api/v1/invoices/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PN-001", "quantity": 1}]},
    )
    assert inv_resp.status_code == 201
    resp = await client.delete(f"/api/v1/po/{po['id']}/lines/PN-001")
    assert resp.status_code == 409
    assert "invoice or shipment" in resp.json()["detail"]


async def test_remove_line_post_accept_returns_409_when_gate_closed(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client, _ADVANCE_PO_PAYLOAD)
    await client.post(f"/api/v1/po/{po['id']}/mark-advance-paid", json={})
    resp = await client.delete(f"/api/v1/po/{po['id']}/lines/PN-001")
    assert resp.status_code == 409


async def test_remove_line_post_accept_returns_404_on_unknown_part(
    authenticated_client: AsyncClient,
) -> None:
    client = authenticated_client
    po = await _create_accepted_po(client)
    resp = await client.delete(f"/api/v1/po/{po['id']}/lines/NOPE")
    assert resp.status_code == 404


async def test_po_response_carries_advance_paid_at_field(
    authenticated_client: AsyncClient,
) -> None:
    # Migration contract: newly-accepted POs post-iter-059 start with advance_paid_at=None.
    client = authenticated_client
    po = await _create_accepted_po(client)
    resp = await client.get(f"/api/v1/po/{po['id']}")
    assert resp.status_code == 200
    assert resp.json()["advance_paid_at"] is None


async def test_advance_required_derivation_is_consistent_with_metadata(
    authenticated_client: AsyncClient,
) -> None:
    # Acts as the migration test: a PO with an advance-required term must carry
    # that derivation in its reference data, not in a stored boolean.
    client = authenticated_client
    ref = await client.get("/api/v1/reference-data/")
    terms = {t["code"]: t for t in ref.json()["payment_terms"]}
    assert terms["100_PCT_ADVANCE"]["has_advance"] is True
    assert terms["NET30"]["has_advance"] is False


async def test_reference_data_payment_terms_includes_has_advance(
    authenticated_client: AsyncClient,
) -> None:
    resp = await authenticated_client.get("/api/v1/reference-data/")
    assert resp.status_code == 200
    terms = resp.json()["payment_terms"]
    # Every entry carries a has_advance flag.
    for entry in terms:
        assert "has_advance" in entry
        assert isinstance(entry["has_advance"], bool)


# ---------------------------------------------------------------------------
# Iter 039: quality gate on PO submit
# ---------------------------------------------------------------------------

_MARKETPLACE = "AMZ"

_LINE_WITH_PRODUCT: dict = {
    "part_number": "PN-CERT",
    "description": "Cert-required widget",
    "quantity": 1,
    "uom": "EA",
    "unit_price": "10.00",
    "hs_code": "8471.30",
    "country_of_origin": "CN",
    "product_id": None,  # populated per test
}


async def _setup_product_with_qual(
    client: AsyncClient,
    vendor_id: str,
) -> tuple[str, str]:
    """Create a product and assign a qualification type. Returns (product_id, qt_id)."""
    product_resp = await client.post(
        "/api/v1/products/",
        json={"vendor_id": vendor_id, "part_number": "PN-CERT", "description": "Cert widget", "manufacturing_address": ""},
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


async def _create_valid_cert(
    client: AsyncClient,
    product_id: str,
    qt_id: str,
    *,
    expired: bool = False,
    status: str = "VALID",
) -> str:
    expiry = "2020-01-01T00:00:00Z" if expired else "2099-01-01T00:00:00Z"
    cert_resp = await client.post(
        "/api/v1/certificates/",
        json={
            "product_id": product_id,
            "qualification_type_id": qt_id,
            "cert_number": "CERT-001",
            "issuer": "TestLab",
            "issue_date": "2024-01-01T00:00:00Z",
            "expiry_date": expiry,
            "target_market": _MARKETPLACE,
        },
    )
    assert cert_resp.status_code == 201
    cert_id: str = cert_resp.json()["id"]
    if status == "VALID":
        mark_resp = await client.patch(f"/api/v1/certificates/{cert_id}", json={"status": "VALID"})
        assert mark_resp.status_code == 200
    return cert_id


async def _create_marketplace_po_with_product(
    client: AsyncClient,
    product_id: str,
) -> dict:
    vendor_resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "CertVendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor_resp.status_code == 201
    vendor_id: str = vendor_resp.json()["id"]
    line = {**_LINE_WITH_PRODUCT, "product_id": product_id}
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "line_items": [line], "marketplace": _MARKETPLACE}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def test_submit_po_returns_po_submit_response_shape(authenticated_client: AsyncClient) -> None:
    po = await _create_po(authenticated_client)
    resp = await authenticated_client.post(f"/api/v1/po/{po['id']}/submit")
    assert resp.status_code == 200
    data = resp.json()
    # Assert the wrapper shape has exactly these top-level keys.
    assert set(data.keys()) == {"po", "cert_warnings"}
    assert data["po"]["status"] == POStatus.PENDING.value
    assert isinstance(data["cert_warnings"], list)


async def test_submit_po_with_valid_cert_returns_empty_warnings(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_resp = await client.post(
        "/api/v1/vendors/", json={"name": "VendorV", "country": "US", "vendor_type": "PROCUREMENT"}
    )
    vendor_id: str = vendor_resp.json()["id"]
    product_id, qt_id = await _setup_product_with_qual(client, vendor_id)
    await _create_valid_cert(client, product_id, qt_id)
    line = {**_LINE_WITH_PRODUCT, "product_id": product_id}
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "line_items": [line], "marketplace": _MARKETPLACE}
    po_resp = await client.post("/api/v1/po/", json=payload)
    po_id: str = po_resp.json()["id"]

    resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cert_warnings"] == []


async def test_submit_po_with_missing_cert_returns_warning(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor_resp = await client.post(
        "/api/v1/vendors/", json={"name": "VendorM", "country": "US", "vendor_type": "PROCUREMENT"}
    )
    vendor_id: str = vendor_resp.json()["id"]
    product_id, qt_id = await _setup_product_with_qual(client, vendor_id)
    # No cert created.
    line = {**_LINE_WITH_PRODUCT, "product_id": product_id}
    payload = {**_PO_PAYLOAD, "vendor_id": vendor_id, "line_items": [line], "marketplace": _MARKETPLACE}
    po_resp = await client.post("/api/v1/po/", json=payload)
    po_id: str = po_resp.json()["id"]

    resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert resp.status_code == 200
    warnings = resp.json()["cert_warnings"]
    assert len(warnings) == 1
    expected_reason = CertWarningReason.MISSING.value
    assert warnings[0]["reason"] == expected_reason
    assert warnings[0]["part_number"] == "PN-CERT"
    assert warnings[0]["qualification_name"] == "CE Mark"
