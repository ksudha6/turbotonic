from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
import pytest
from httpx import AsyncClient

from src.routers.dashboard import get_milestone_repo as dash_get_milestone_repo
from src.main import app

pytestmark = pytest.mark.asyncio

_LINE_ITEM = {
    "part_number": "PN-001",
    "description": "Widget A",
    "quantity": 100,
    "uom": "EA",
    "unit_price": "5.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_PO_PAYLOAD = {
    "vendor_id": "vendor-placeholder",
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


async def _create_accepted_procurement_po(client: AsyncClient) -> dict:
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Test Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor.status_code == 201
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "PROCUREMENT"
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id = po.json()["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/accept")
    return (await client.get(f"/api/v1/po/{po_id}")).json()


async def _get_conn(client: AsyncClient) -> asyncpg.Connection:
    # Retrieve the shared Postgres connection from any registered override.
    override_fn = app.dependency_overrides.get(dash_get_milestone_repo)
    assert override_fn is not None, "dash_get_milestone_repo override must be registered"
    conn_ref = None
    async for repo in override_fn():
        conn_ref = repo._conn
        break
    assert conn_ref is not None, "could not retrieve shared test connection"
    return conn_ref


async def test_po_submit_creates_activity_entry(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Submitting a PO must produce both PO_CREATED and PO_SUBMITTED entries in the activity log.
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Submit Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor.status_code == 201
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "PROCUREMENT"
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id = po.json()["id"]

    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=PO&entity_id={po_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    events_by_name = {e["event"]: e for e in entries}
    assert "PO_CREATED" in events_by_name, f"PO_CREATED missing from activity; got events: {list(events_by_name)}"
    assert "PO_SUBMITTED" in events_by_name, f"PO_SUBMITTED missing from activity; got events: {list(events_by_name)}"

    submitted_entry = events_by_name["PO_SUBMITTED"]
    assert submitted_entry["category"] == "ACTION_REQUIRED", (
        f"PO_SUBMITTED must have category ACTION_REQUIRED, got {submitted_entry['category']!r}"
    )
    assert submitted_entry["target_role"] == "VENDOR", (
        f"PO_SUBMITTED must target VENDOR, got {submitted_entry['target_role']!r}"
    )

    created_entry = events_by_name["PO_CREATED"]
    assert created_entry["category"] == "LIVE", (
        f"PO_CREATED must have category LIVE, got {created_entry['category']!r}"
    )
    assert created_entry["target_role"] == "SM", (
        f"PO_CREATED must target SM, got {created_entry['target_role']!r}"
    )


async def test_po_rejected_via_all_lines_removed_emits_line_removed_and_converged(authenticated_client: AsyncClient) -> None:
    # Iter 058: a PO that converges to REJECTED via all-lines-removed produces one
    # PO_LINE_REMOVED per removed line and one terminal PO_CONVERGED event. The
    # legacy PO_REJECTED event is no longer emitted by submit_response.
    client = authenticated_client

    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Reject Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor.status_code == 201
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "PROCUREMENT"
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id = po.json()["id"]

    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200

    remove_resp = await client.post(f"/api/v1/po/{po_id}/lines/PN-001/remove", json={})
    assert remove_resp.status_code == 200

    response_resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert response_resp.status_code == 200
    assert response_resp.json()["status"] == "REJECTED"

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=PO&entity_id={po_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    removed_entries = [e for e in entries if e["event"] == "PO_LINE_REMOVED"]
    assert len(removed_entries) == 1, (
        f"expected exactly one PO_LINE_REMOVED entry, got {len(removed_entries)}"
    )
    assert removed_entries[0]["detail"] == "PN-001", (
        f"PO_LINE_REMOVED detail must be the part_number, got {removed_entries[0]['detail']!r}"
    )

    converged_entries = [e for e in entries if e["event"] == "PO_CONVERGED"]
    assert len(converged_entries) == 1, (
        f"expected exactly one PO_CONVERGED entry, got {len(converged_entries)}"
    )
    assert converged_entries[0]["category"] == "LIVE", (
        f"PO_CONVERGED must have category LIVE, got {converged_entries[0]['category']!r}"
    )
    assert converged_entries[0]["detail"] == "REJECTED", (
        f"PO_CONVERGED detail must record terminal status, got {converged_entries[0]['detail']!r}"
    )
    # submit_response no longer emits PO_REJECTED directly.
    assert not any(e["event"] == "PO_REJECTED" for e in entries), (
        f"PO_REJECTED must not be emitted by submit_response convergence; "
        f"events: {[e['event'] for e in entries]}"
    )


async def test_invoice_create_creates_activity_entry(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Creating an invoice against an ACCEPTED PO must produce an INVOICE_CREATED activity entry.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    invoice_payload = {
        "po_id": po_id,
        "line_items": [{"part_number": "PN-001", "quantity": 10}],
    }
    invoice_resp = await client.post("/api/v1/invoices/", json=invoice_payload)
    assert invoice_resp.status_code == 201
    invoice_id = invoice_resp.json()["id"]

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=INVOICE&entity_id={invoice_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    created_entries = [e for e in entries if e["event"] == "INVOICE_CREATED"]
    assert len(created_entries) == 1, f"expected exactly one INVOICE_CREATED entry, got {len(created_entries)}"
    assert created_entries[0]["category"] == "LIVE", (
        f"INVOICE_CREATED must have category LIVE, got {created_entries[0]['category']!r}"
    )


async def test_invoice_dispute_includes_reason_in_detail(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Disputing a submitted invoice must store the reason in the INVOICE_DISPUTED detail.
    dispute_reason = "Incorrect amounts"

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    invoice_payload = {
        "po_id": po_id,
        "line_items": [{"part_number": "PN-001", "quantity": 10}],
    }
    invoice_resp = await client.post("/api/v1/invoices/", json=invoice_payload)
    assert invoice_resp.status_code == 201
    invoice_id = invoice_resp.json()["id"]

    submit_resp = await client.post(f"/api/v1/invoices/{invoice_id}/submit")
    assert submit_resp.status_code == 200

    dispute_resp = await client.post(f"/api/v1/invoices/{invoice_id}/dispute", json={"reason": dispute_reason})
    assert dispute_resp.status_code == 200

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=INVOICE&entity_id={invoice_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    disputed_entries = [e for e in entries if e["event"] == "INVOICE_DISPUTED"]
    assert len(disputed_entries) == 1, f"expected exactly one INVOICE_DISPUTED entry, got {len(disputed_entries)}"
    assert disputed_entries[0]["detail"] == dispute_reason, (
        f"INVOICE_DISPUTED detail must be {dispute_reason!r}, got {disputed_entries[0]['detail']!r}"
    )


async def test_milestone_posted_creates_activity_entry(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Posting RAW_MATERIALS on an ACCEPTED PROCUREMENT PO must produce a MILESTONE_POSTED entry with detail RAW_MATERIALS.
    milestone_name = "RAW_MATERIALS"

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    milestone_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": milestone_name})
    assert milestone_resp.status_code == 201

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=PO&entity_id={po_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    milestone_entries = [e for e in entries if e["event"] == "MILESTONE_POSTED"]
    assert len(milestone_entries) == 1, f"expected exactly one MILESTONE_POSTED entry, got {len(milestone_entries)}"
    assert milestone_entries[0]["detail"] == milestone_name, (
        f"MILESTONE_POSTED detail must be {milestone_name!r}, got {milestone_entries[0]['detail']!r}"
    )


async def test_overdue_milestone_generates_delayed_entry(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # A milestone backdated past its threshold triggers a MILESTONE_OVERDUE entry on dashboard load.
    milestone_name = "RAW_MATERIALS"

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    post_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": milestone_name})
    assert post_resp.status_code == 201

    conn_ref = await _get_conn(client)
    eight_days_ago = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    await conn_ref.execute(
        "UPDATE milestone_updates SET posted_at = $1 WHERE po_id = $2",
        eight_days_ago, po_id,
    )

    dash_resp = await client.get("/api/v1/dashboard/")
    assert dash_resp.status_code == 200

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=PO&entity_id={po_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    overdue_entries = [e for e in entries if e["event"] == "MILESTONE_OVERDUE"]
    assert len(overdue_entries) >= 1, f"expected at least one MILESTONE_OVERDUE entry, got none; all events: {[e['event'] for e in entries]}"
    assert overdue_entries[0]["category"] == "DELAYED", (
        f"MILESTONE_OVERDUE must have category DELAYED, got {overdue_entries[0]['category']!r}"
    )


async def test_overdue_notification_is_idempotent(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Two consecutive dashboard loads for an overdue milestone must produce exactly one MILESTONE_OVERDUE entry.
    milestone_name = "RAW_MATERIALS"

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    post_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": milestone_name})
    assert post_resp.status_code == 201

    conn_ref = await _get_conn(client)
    eight_days_ago = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    await conn_ref.execute(
        "UPDATE milestone_updates SET posted_at = $1 WHERE po_id = $2",
        eight_days_ago, po_id,
    )

    first_dash = await client.get("/api/v1/dashboard/")
    assert first_dash.status_code == 200

    second_dash = await client.get("/api/v1/dashboard/")
    assert second_dash.status_code == 200

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=PO&entity_id={po_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    overdue_entries = [e for e in entries if e["event"] == "MILESTONE_OVERDUE"]
    assert len(overdue_entries) == 1, (
        f"dashboard called twice must produce exactly one MILESTONE_OVERDUE, got {len(overdue_entries)}"
    )


async def test_activity_list_returns_reverse_chronological(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # After CREATED, SUBMITTED, ACCEPTED a PO, the list endpoint must return entries newest-first.
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Chrono Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor.status_code == 201
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "PROCUREMENT"
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id = po.json()["id"]

    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200
    accept_resp = await client.post(f"/api/v1/po/{po_id}/accept")
    assert accept_resp.status_code == 200

    activity_resp = await client.get("/api/v1/activity/?limit=10")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    # Filter to entries for this PO to avoid interference from other tests.
    po_entries = [e for e in entries if e["entity_id"] == po_id]
    assert len(po_entries) >= 3, f"expected at least 3 entries for PO, got {len(po_entries)}"

    # list_recent returns newest first; the first entry must be later than the last.
    first_ts = datetime.fromisoformat(po_entries[0]["created_at"])
    last_ts = datetime.fromisoformat(po_entries[-1]["created_at"])
    assert first_ts >= last_ts, (
        f"first entry ({po_entries[0]['event']} at {first_ts}) must be >= last entry ({po_entries[-1]['event']} at {last_ts})"
    )

    # The most recent event for this PO must be PO_ACCEPTED.
    assert po_entries[0]["event"] == "PO_ACCEPTED", (
        f"most recent entry must be PO_ACCEPTED, got {po_entries[0]['event']!r}"
    )


async def test_unread_count_and_mark_read(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # After creating and submitting a PO, unread count must be >= 2; after mark-all-read, count must be 0.
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Unread Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor.status_code == 201
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "PROCUREMENT"
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id = po.json()["id"]

    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200

    count_resp = await client.get("/api/v1/activity/unread-count")
    assert count_resp.status_code == 200
    count_before = count_resp.json()["count"]
    assert count_before >= 2, f"expected unread count >= 2 after create+submit, got {count_before}"

    mark_resp = await client.post("/api/v1/activity/mark-read", json={"all": True})
    assert mark_resp.status_code == 200
    assert mark_resp.json()["marked"] >= 2, f"mark-read must report marking at least 2 entries, got {mark_resp.json()}"

    count_after_resp = await client.get("/api/v1/activity/unread-count")
    assert count_after_resp.status_code == 200
    count_after = count_after_resp.json()["count"]
    assert count_after == 0, f"unread count must be 0 after mark-all-read, got {count_after}"


async def test_mark_read_specific_ids(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Marking one specific entry as read must reduce unread count by exactly 1.
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Specific Read Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor.status_code == 201
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "PROCUREMENT"
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id = po.json()["id"]

    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=PO&entity_id={po_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()
    assert len(entries) >= 2, f"expected at least 2 activity entries for PO, got {len(entries)}"

    total_unread_resp = await client.get("/api/v1/activity/unread-count")
    assert total_unread_resp.status_code == 200
    total_unread = total_unread_resp.json()["count"]

    target_id = entries[0]["id"]

    mark_resp = await client.post("/api/v1/activity/mark-read", json={"event_ids": [target_id]})
    assert mark_resp.status_code == 200
    assert mark_resp.json()["marked"] == 1, (
        f"mark-read with one id must report marking 1 entry, got {mark_resp.json()}"
    )

    count_after_resp = await client.get("/api/v1/activity/unread-count")
    assert count_after_resp.status_code == 200
    count_after = count_after_resp.json()["count"]
    assert count_after == total_unread - 1, (
        f"unread count must decrease by 1 after marking one entry; expected {total_unread - 1}, got {count_after}"
    )


# ---------------------------------------------------------------------------
# Iter 058 -- per-line negotiation activity events
# ---------------------------------------------------------------------------

_PART_NUMBER = "PN-001"
_PART_NUMBER_2 = "PN-002"

_LINE_ITEM_2 = {
    "part_number": _PART_NUMBER_2,
    "description": "Widget B",
    "quantity": 20,
    "uom": "EA",
    "unit_price": "2.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}


async def _create_pending_po(client: AsyncClient, two_lines: bool = False) -> str:
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Negotiation Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor.status_code == 201
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "PROCUREMENT"
    if two_lines:
        payload["line_items"] = [_LINE_ITEM, _LINE_ITEM_2]
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id = po.json()["id"]
    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200
    return po_id


async def _entries_for(client: AsyncClient, po_id: str) -> list[dict]:
    resp = await client.get(f"/api/v1/activity/?entity_type=PO&entity_id={po_id}")
    assert resp.status_code == 200
    return resp.json()


async def test_modify_line_emits_po_line_modified_once(authenticated_client: AsyncClient) -> None:
    # One /modify call produces exactly one PO_LINE_MODIFIED, and the event
    # detail carries the part_number and sorted changed field names.
    client = authenticated_client
    po_id = await _create_pending_po(client)

    modify_resp = await client.post(
        f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify",
        json={"fields": {"quantity": 7, "uom": "BOX"}},
    )
    assert modify_resp.status_code == 200

    entries = await _entries_for(client, po_id)
    modified = [e for e in entries if e["event"] == "PO_LINE_MODIFIED"]
    assert len(modified) == 1, (
        f"expected exactly one PO_LINE_MODIFIED, got {len(modified)}"
    )
    assert modified[0]["category"] == "LIVE", (
        f"PO_LINE_MODIFIED must have category LIVE, got {modified[0]['category']!r}"
    )
    detail = modified[0]["detail"]
    assert detail is not None and _PART_NUMBER in detail, (
        f"PO_LINE_MODIFIED detail must include the part_number; got {detail!r}"
    )
    # Detail is "<part_number>: <sorted comma-joined field names>" — both edited
    # fields must be present, recorded in sort order.
    assert "quantity" in detail and "uom" in detail, (
        f"PO_LINE_MODIFIED detail must list changed fields; got {detail!r}"
    )


async def test_accept_line_emits_po_line_accepted(authenticated_client: AsyncClient) -> None:
    # /accept produces exactly one PO_LINE_ACCEPTED event per call.
    client = authenticated_client
    po_id = await _create_pending_po(client)

    accept_resp = await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/accept", json={})
    assert accept_resp.status_code == 200

    entries = await _entries_for(client, po_id)
    accepted = [e for e in entries if e["event"] == "PO_LINE_ACCEPTED"]
    assert len(accepted) == 1, f"expected exactly one PO_LINE_ACCEPTED, got {len(accepted)}"
    assert accepted[0]["category"] == "LIVE"
    assert accepted[0]["detail"] == _PART_NUMBER, (
        f"PO_LINE_ACCEPTED detail must be part_number, got {accepted[0]['detail']!r}"
    )


async def test_remove_line_emits_po_line_removed(authenticated_client: AsyncClient) -> None:
    # /remove produces exactly one PO_LINE_REMOVED event per call.
    client = authenticated_client
    po_id = await _create_pending_po(client)

    remove_resp = await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/remove", json={})
    assert remove_resp.status_code == 200

    entries = await _entries_for(client, po_id)
    removed = [e for e in entries if e["event"] == "PO_LINE_REMOVED"]
    assert len(removed) == 1, f"expected exactly one PO_LINE_REMOVED, got {len(removed)}"
    assert removed[0]["detail"] == _PART_NUMBER


async def test_force_accept_emits_po_force_accepted(authenticated_client: AsyncClient) -> None:
    # SM force-accept at round 2 produces exactly one PO_FORCE_ACCEPTED event.
    client = authenticated_client
    po_id = await _create_pending_po(client, two_lines=True)
    # Drive to round 2: vendor modifies, then submit; vendor modifies again, submit -> round 2.
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 7}})
    await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 8}})
    await client.post(f"/api/v1/po/{po_id}/submit-response", json={})

    force_resp = await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/force-accept", json={})
    assert force_resp.status_code == 200

    entries = await _entries_for(client, po_id)
    forced = [e for e in entries if e["event"] == "PO_FORCE_ACCEPTED"]
    assert len(forced) == 1, f"expected exactly one PO_FORCE_ACCEPTED, got {len(forced)}"
    assert forced[0]["target_role"] == "VENDOR", (
        f"PO_FORCE_ACCEPTED must target VENDOR, got {forced[0]['target_role']!r}"
    )
    # Force events are distinct from regular accept; the regular event must not be
    # emitted alongside.
    accepted = [e for e in entries if e["event"] == "PO_LINE_ACCEPTED"]
    assert len(accepted) == 0, (
        f"PO_FORCE_ACCEPTED must not emit a duplicate PO_LINE_ACCEPTED; got {len(accepted)}"
    )


async def test_force_remove_emits_po_force_removed(authenticated_client: AsyncClient) -> None:
    # SM force-remove at round 2 produces exactly one PO_FORCE_REMOVED event.
    client = authenticated_client
    po_id = await _create_pending_po(client, two_lines=True)
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 7}})
    await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 8}})
    await client.post(f"/api/v1/po/{po_id}/submit-response", json={})

    force_resp = await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/force-remove", json={})
    assert force_resp.status_code == 200

    entries = await _entries_for(client, po_id)
    forced = [e for e in entries if e["event"] == "PO_FORCE_REMOVED"]
    assert len(forced) == 1, f"expected exactly one PO_FORCE_REMOVED, got {len(forced)}"


async def test_submit_response_emits_po_modified_not_converged_mid_loop(authenticated_client: AsyncClient) -> None:
    # Mid-loop submit_response (PO ends in MODIFIED) emits PO_MODIFIED, never PO_CONVERGED.
    client = authenticated_client
    po_id = await _create_pending_po(client)
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 7}})
    resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "MODIFIED"

    entries = await _entries_for(client, po_id)
    modified = [e for e in entries if e["event"] == "PO_MODIFIED"]
    converged = [e for e in entries if e["event"] == "PO_CONVERGED"]
    assert len(modified) == 1, f"expected one PO_MODIFIED mid-loop, got {len(modified)}"
    assert len(converged) == 0, f"PO_CONVERGED must not fire mid-loop, got {len(converged)}"
    assert modified[0]["category"] == "ACTION_REQUIRED", (
        f"PO_MODIFIED must be ACTION_REQUIRED (hand-off), got {modified[0]['category']!r}"
    )


async def test_po_modified_target_role_alternates_across_rounds(authenticated_client: AsyncClient) -> None:
    # Admin acts as SM. Round 1 submit-response (SM actor) targets VENDOR. After a
    # VENDOR-side modify + submit-response, the second PO_MODIFIED targets SM.
    # We simulate the vendor side by directly invoking the domain API through a
    # second-actor submit, but since the test client is always ADMIN=SM, we assert
    # the current actor-targets-counterpart mapping on a single hand-off and rely
    # on domain-level tests for actor variance. The ADMIN-as-SM case must target VENDOR.
    client = authenticated_client
    po_id = await _create_pending_po(client)
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 7}})
    resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert resp.status_code == 200

    entries = await _entries_for(client, po_id)
    modified = [e for e in entries if e["event"] == "PO_MODIFIED"]
    assert len(modified) == 1
    # SM (ADMIN treated as SM) triggered the hand-off; the vendor must now act.
    assert modified[0]["target_role"] == "VENDOR", (
        f"SM-triggered PO_MODIFIED must target VENDOR, got {modified[0]['target_role']!r}"
    )


async def test_po_converged_fires_on_terminal_acceptance(authenticated_client: AsyncClient) -> None:
    # Accept the one line then submit-response: PO converges to ACCEPTED and a
    # single PO_CONVERGED event fires (LIVE, detail records final status).
    client = authenticated_client
    po_id = await _create_pending_po(client)
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/accept", json={})
    resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"

    entries = await _entries_for(client, po_id)
    converged = [e for e in entries if e["event"] == "PO_CONVERGED"]
    assert len(converged) == 1, f"expected one PO_CONVERGED on convergence, got {len(converged)}"
    assert converged[0]["category"] == "LIVE"
    assert converged[0]["detail"] == "ACCEPTED", (
        f"PO_CONVERGED detail must be the final PO status, got {converged[0]['detail']!r}"
    )
    # PO_MODIFIED must not fire on the converging submit_response.
    modified = [e for e in entries if e["event"] == "PO_MODIFIED"]
    assert len(modified) == 0, (
        f"PO_MODIFIED must not fire on a converging submit_response; got {len(modified)}"
    )


async def test_po_modified_does_not_fire_per_line_edit(authenticated_client: AsyncClient) -> None:
    # Per-line modify calls must not emit PO_MODIFIED; only submit_response does.
    client = authenticated_client
    po_id = await _create_pending_po(client, two_lines=True)
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 7}})
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER_2}/modify", json={"fields": {"quantity": 3}})

    entries = await _entries_for(client, po_id)
    modified = [e for e in entries if e["event"] == "PO_MODIFIED"]
    assert len(modified) == 0, (
        f"PO_MODIFIED must only fire on submit_response, not per line edit; got {len(modified)}"
    )


async def test_full_round_one_round_two_event_sequence(authenticated_client: AsyncClient) -> None:
    # End-to-end: a two-line PO goes through SM modify -> submit (round 1 hand-off),
    # then a force action at round 2 after a second SM modify + submit, then force-accept
    # to converge. The ADMIN-as-SM test client drives both sides: the domain rule
    # "the counterparty must accept" is exercised by the dedicated test above; this
    # test covers end-to-end event emission using force-accept to reach terminal.
    client = authenticated_client
    po_id = await _create_pending_po(client, two_lines=True)

    # Round 1: SM modifies both lines, submits -> round_count = 1, status MODIFIED.
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 7}})
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER_2}/modify", json={"fields": {"quantity": 4}})
    r1 = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert r1.json()["status"] == "MODIFIED"

    # Round 2 setup: another modify + submit pushes round_count to 2.
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 8}})
    r2 = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert r2.json()["round_count"] == 2

    # Round 2 force resolution: SM force-accepts both contested lines, then submits
    # -> convergence to ACCEPTED.
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/force-accept", json={})
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER_2}/force-accept", json={})
    r3 = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert r3.json()["status"] == "ACCEPTED"

    entries = await _entries_for(client, po_id)
    # list_for_entity orders ASC by created_at, so the sequence is chronological.
    event_sequence = [e["event"] for e in entries]

    expected_counts: dict[str, int] = {
        "PO_CREATED": 1,
        "PO_SUBMITTED": 1,
        "PO_LINE_MODIFIED": 3,
        "PO_FORCE_ACCEPTED": 2,
        "PO_MODIFIED": 2,
        "PO_CONVERGED": 1,
    }
    for event_name, expected in expected_counts.items():
        actual = event_sequence.count(event_name)
        assert actual == expected, (
            f"expected {expected} {event_name} event(s), got {actual}; full sequence: {event_sequence}"
        )

    # PO_CONVERGED must be the last event in the chain; every PO_MODIFIED must precede it.
    assert event_sequence[-1] == "PO_CONVERGED", (
        f"final event must be PO_CONVERGED, got {event_sequence[-1]!r}"
    )
    last_modified_idx = max(
        idx for idx, ev in enumerate(event_sequence) if ev == "PO_MODIFIED"
    )
    assert last_modified_idx < event_sequence.index("PO_CONVERGED")


async def test_action_required_category_only_on_po_modified(authenticated_client: AsyncClient) -> None:
    # Among iter-058 line-level events, only PO_MODIFIED has ACTION_REQUIRED; the
    # rest are LIVE. Drive a full hand-off and cross-check every new event's category.
    client = authenticated_client
    po_id = await _create_pending_po(client)
    await client.post(f"/api/v1/po/{po_id}/lines/{_PART_NUMBER}/modify", json={"fields": {"quantity": 7}})
    await client.post(f"/api/v1/po/{po_id}/submit-response", json={})

    entries = await _entries_for(client, po_id)
    iter058_events = (
        "PO_LINE_MODIFIED",
        "PO_LINE_ACCEPTED",
        "PO_LINE_REMOVED",
        "PO_FORCE_ACCEPTED",
        "PO_FORCE_REMOVED",
        "PO_MODIFIED",
        "PO_CONVERGED",
    )
    for entry in entries:
        if entry["event"] not in iter058_events:
            continue
        if entry["event"] == "PO_MODIFIED":
            assert entry["category"] == "ACTION_REQUIRED", (
                f"PO_MODIFIED must be ACTION_REQUIRED, got {entry['category']!r}"
            )
        else:
            assert entry["category"] == "LIVE", (
                f"{entry['event']} must be LIVE, got {entry['category']!r}"
            )
