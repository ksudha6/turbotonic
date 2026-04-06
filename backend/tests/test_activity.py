from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import AsyncIterator
from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.activity_repository import ActivityLogRepository
from src.db import get_db
from src.invoice_repository import InvoiceRepository
from src.main import app
from src.milestone_repository import MilestoneRepository
from src.repository import PurchaseOrderRepository
from src.routers.activity import get_activity_repo as activity_get_activity_repo
from src.routers.dashboard import get_activity_repo as dash_get_activity_repo
from src.routers.dashboard import get_invoice_repo as dash_get_invoice_repo
from src.routers.dashboard import get_milestone_repo as dash_get_milestone_repo
from src.routers.dashboard import get_repo as dash_get_repo
from src.routers.dashboard import get_vendor_repo as dash_get_vendor_repo
from src.routers.invoice import get_activity_repo as invoice_get_activity_repo
from src.routers.invoice import get_invoice_repo as invoice_get_invoice_repo
from src.routers.invoice import get_po_repo as invoice_get_po_repo
from src.routers.milestone import get_activity_repo as milestone_get_activity_repo
from src.routers.milestone import get_milestone_repo
from src.routers.milestone import get_po_repo as milestone_get_po_repo
from src.routers.purchase_order import get_activity_repo as po_get_activity_repo
from src.routers.purchase_order import get_invoice_repo as po_get_invoice_repo
from src.routers.purchase_order import get_repo
from src.routers.purchase_order import get_vendor_repo as po_get_vendor_repo
from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo
from src.schema import init_db
from src.vendor_repository import VendorRepository

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


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await init_db(conn)

        async def override_get_repo() -> AsyncIterator[PurchaseOrderRepository]:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield PurchaseOrderRepository(conn)

        async def override_get_vendor_repo() -> AsyncIterator[VendorRepository]:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield VendorRepository(conn)

        async def override_get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield InvoiceRepository(conn)

        async def override_get_milestone_repo() -> AsyncIterator[MilestoneRepository]:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield MilestoneRepository(conn)

        async def override_get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield ActivityLogRepository(conn)

        @asynccontextmanager
        async def _test_get_db(*_args, **_kwargs) -> AsyncIterator[aiosqlite.Connection]:
            yield conn

        app.dependency_overrides[get_repo] = override_get_repo
        app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[po_get_activity_repo] = override_get_activity_repo
        app.dependency_overrides[vendor_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[dash_get_repo] = override_get_repo
        app.dependency_overrides[dash_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[dash_get_invoice_repo] = override_get_invoice_repo
        app.dependency_overrides[dash_get_milestone_repo] = override_get_milestone_repo
        app.dependency_overrides[dash_get_activity_repo] = override_get_activity_repo
        app.dependency_overrides[invoice_get_invoice_repo] = override_get_invoice_repo
        app.dependency_overrides[invoice_get_po_repo] = override_get_repo
        app.dependency_overrides[invoice_get_activity_repo] = override_get_activity_repo
        app.dependency_overrides[po_get_invoice_repo] = override_get_invoice_repo
        app.dependency_overrides[get_milestone_repo] = override_get_milestone_repo
        app.dependency_overrides[milestone_get_po_repo] = override_get_repo
        app.dependency_overrides[milestone_get_activity_repo] = override_get_activity_repo
        app.dependency_overrides[activity_get_activity_repo] = override_get_activity_repo

        transport = ASGITransport(app=app)
        with patch("src.routers.purchase_order.get_db", _test_get_db):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

    app.dependency_overrides.clear()


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


async def _get_conn(client: AsyncClient) -> aiosqlite.Connection:
    # Retrieve the shared in-memory connection from any registered override.
    override_fn = app.dependency_overrides.get(dash_get_milestone_repo)
    assert override_fn is not None, "dash_get_milestone_repo override must be registered"
    conn_ref = None
    async for repo in override_fn():
        conn_ref = repo._conn
        break
    assert conn_ref is not None, "could not retrieve shared test connection"
    return conn_ref


async def test_po_submit_creates_activity_entry(client: AsyncClient) -> None:
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


async def test_po_reject_includes_comment_in_detail(client: AsyncClient) -> None:
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


async def test_invoice_create_creates_activity_entry(client: AsyncClient) -> None:
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


async def test_invoice_dispute_includes_reason_in_detail(client: AsyncClient) -> None:
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


async def test_milestone_posted_creates_activity_entry(client: AsyncClient) -> None:
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


async def test_overdue_milestone_generates_delayed_entry(client: AsyncClient) -> None:
    # A milestone backdated past its threshold triggers a MILESTONE_OVERDUE entry on dashboard load.
    milestone_name = "RAW_MATERIALS"

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    post_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": milestone_name})
    assert post_resp.status_code == 201

    conn_ref = await _get_conn(client)
    eight_days_ago = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    await conn_ref.execute(
        "UPDATE milestone_updates SET posted_at = ? WHERE po_id = ?",
        (eight_days_ago, po_id),
    )
    await conn_ref.commit()

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


async def test_overdue_notification_is_idempotent(client: AsyncClient) -> None:
    # Two consecutive dashboard loads for an overdue milestone must produce exactly one MILESTONE_OVERDUE entry.
    milestone_name = "RAW_MATERIALS"

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    post_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": milestone_name})
    assert post_resp.status_code == 201

    conn_ref = await _get_conn(client)
    eight_days_ago = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    await conn_ref.execute(
        "UPDATE milestone_updates SET posted_at = ? WHERE po_id = ?",
        (eight_days_ago, po_id),
    )
    await conn_ref.commit()

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


async def test_activity_list_returns_reverse_chronological(client: AsyncClient) -> None:
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


async def test_unread_count_and_mark_read(client: AsyncClient) -> None:
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


async def test_mark_read_specific_ids(client: AsyncClient) -> None:
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
