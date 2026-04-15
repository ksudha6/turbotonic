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


async def test_po_reject_includes_comment_in_detail(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Rejecting a submitted PO with a comment must store that comment in the PO_REJECTED detail.
    reject_comment = "Quality issues"

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

    reject_resp = await client.post(f"/api/v1/po/{po_id}/reject", json={"comment": reject_comment})
    assert reject_resp.status_code == 200

    activity_resp = await client.get(f"/api/v1/activity/?entity_type=PO&entity_id={po_id}")
    assert activity_resp.status_code == 200
    entries = activity_resp.json()

    rejected_entries = [e for e in entries if e["event"] == "PO_REJECTED"]
    assert len(rejected_entries) == 1, f"expected exactly one PO_REJECTED entry, got {len(rejected_entries)}"

    rejected_entry = rejected_entries[0]
    assert rejected_entry["detail"] == reject_comment, (
        f"PO_REJECTED detail must be {reject_comment!r}, got {rejected_entry['detail']!r}"
    )
    assert rejected_entry["category"] == "LIVE", (
        f"PO_REJECTED must have category LIVE, got {rejected_entry['category']!r}"
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
