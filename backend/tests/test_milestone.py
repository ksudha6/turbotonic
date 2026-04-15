from __future__ import annotations

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


async def _create_accepted_opex_po(client: AsyncClient) -> dict:
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "OPEX Vendor", "country": "US", "vendor_type": "OPEX"},
    )
    assert vendor.status_code == 201
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "OPEX"
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id = po.json()["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/accept")
    return (await client.get(f"/api/v1/po/{po_id}")).json()


async def test_post_milestone_on_accepted_procurement_po_returns_201(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Posting RAW_MATERIALS on an ACCEPTED PROCUREMENT PO must return 201 with milestone and posted_at.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert resp.status_code == 201, f"expected 201, got {resp.status_code}: {resp.text}"

    data = resp.json()
    required_keys = {"milestone", "posted_at"}
    assert required_keys <= data.keys(), f"response missing keys: {required_keys - data.keys()}"
    assert data["milestone"] == "RAW_MATERIALS"
    assert data["posted_at"] is not None


async def test_reject_milestone_on_non_accepted_po(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Posting a milestone on a DRAFT PO must return 409.
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Draft Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = "PROCUREMENT"
    po = await client.post("/api/v1/po/", json=payload)
    po_id = po.json()["id"]

    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert resp.status_code == 409, f"expected 409 for DRAFT PO, got {resp.status_code}: {resp.text}"


async def test_reject_milestone_on_non_procurement_po(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Posting a milestone on an ACCEPTED OPEX PO must return 409.
    po = await _create_accepted_opex_po(client)
    po_id = po["id"]

    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert resp.status_code == 409, f"expected 409 for OPEX PO, got {resp.status_code}: {resp.text}"


async def test_reject_out_of_order_milestone(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # After RAW_MATERIALS, posting QC_PASSED (skipping PRODUCTION_STARTED) must return 409.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    first = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert first.status_code == 201

    skip = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "QC_PASSED"})
    assert skip.status_code == 409, f"expected 409 for out-of-order milestone, got {skip.status_code}: {skip.text}"


async def test_reject_duplicate_milestone(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Posting RAW_MATERIALS twice must return 409 on the second attempt.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    first = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert first.status_code == 201

    duplicate = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert duplicate.status_code == 409, f"expected 409 for duplicate milestone, got {duplicate.status_code}: {duplicate.text}"


async def test_get_milestones_returns_posted_order(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # GET milestones after posting RAW_MATERIALS then PRODUCTION_STARTED must return both in order.
    raw_materials = "RAW_MATERIALS"
    production_started = "PRODUCTION_STARTED"

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": raw_materials})
    await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": production_started})

    resp = await client.get(f"/api/v1/po/{po_id}/milestones")
    assert resp.status_code == 200

    items = resp.json()
    assert len(items) == 2, "must return exactly two milestones"
    assert items[0]["milestone"] == raw_materials, "first item must be RAW_MATERIALS"
    assert items[1]["milestone"] == production_started, "second item must be PRODUCTION_STARTED"


async def test_get_milestones_empty(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # GET milestones on a PO with none posted must return 200 with an empty list.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    resp = await client.get(f"/api/v1/po/{po_id}/milestones")
    assert resp.status_code == 200
    assert resp.json() == [], "no milestones posted must return empty list"


async def test_post_invalid_milestone_value_returns_422(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # Posting an unrecognised milestone value must return 422.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "INVALID"})
    assert resp.status_code == 422, f"expected 422 for invalid milestone, got {resp.status_code}: {resp.text}"


async def test_po_list_includes_current_milestone(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # An ACCEPTED PROCUREMENT PO with RAW_MATERIALS posted must appear with current_milestone set.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    post_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert post_resp.status_code == 201

    list_resp = await client.get("/api/v1/po/")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    matching = [item for item in items if item["id"] == po_id]
    assert len(matching) == 1, "PO must appear in list"
    assert matching[0]["current_milestone"] == "RAW_MATERIALS", (
        f"expected RAW_MATERIALS, got {matching[0]['current_milestone']!r}"
    )


async def test_po_list_current_milestone_null_when_no_milestones(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # An ACCEPTED PROCUREMENT PO with no milestones posted must have current_milestone null.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    list_resp = await client.get("/api/v1/po/")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    matching = [item for item in items if item["id"] == po_id]
    assert len(matching) == 1, "PO must appear in list"
    assert matching[0]["current_milestone"] is None, (
        f"expected None, got {matching[0]['current_milestone']!r}"
    )


async def test_po_list_filter_by_milestone(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # With two POs at different milestones, filtering by one milestone returns only that PO.
    po_a = await _create_accepted_procurement_po(client)
    po_b = await _create_accepted_procurement_po(client)

    await client.post(f"/api/v1/po/{po_a['id']}/milestones", json={"milestone": "RAW_MATERIALS"})
    await client.post(f"/api/v1/po/{po_b['id']}/milestones", json={"milestone": "RAW_MATERIALS"})
    await client.post(f"/api/v1/po/{po_b['id']}/milestones", json={"milestone": "PRODUCTION_STARTED"})

    list_resp = await client.get("/api/v1/po/?milestone=RAW_MATERIALS")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    ids = [item["id"] for item in items]
    assert po_a["id"] in ids, "PO at RAW_MATERIALS must be in results"
    assert po_b["id"] not in ids, "PO at PRODUCTION_STARTED must not appear when filtering RAW_MATERIALS"


async def test_dashboard_production_summary(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # After posting RAW_MATERIALS on one PO and PRODUCTION_STARTED on another,
    # production_summary must count one PO at each stage.
    po_a = await _create_accepted_procurement_po(client)
    po_b = await _create_accepted_procurement_po(client)

    await client.post(f"/api/v1/po/{po_a['id']}/milestones", json={"milestone": "RAW_MATERIALS"})
    await client.post(f"/api/v1/po/{po_b['id']}/milestones", json={"milestone": "RAW_MATERIALS"})
    await client.post(f"/api/v1/po/{po_b['id']}/milestones", json={"milestone": "PRODUCTION_STARTED"})

    dash_resp = await client.get("/api/v1/dashboard/")
    assert dash_resp.status_code == 200
    summary = {s["milestone"]: s["count"] for s in dash_resp.json()["production_summary"]}
    assert summary.get("RAW_MATERIALS") == 1, f"expected 1 at RAW_MATERIALS, got {summary}"
    assert summary.get("PRODUCTION_STARTED") == 1, f"expected 1 at PRODUCTION_STARTED, got {summary}"


async def test_dashboard_overdue_pos(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    # A PO at RAW_MATERIALS with posted_at backdated to 8 days ago must appear in overdue_pos.
    # RAW_MATERIALS threshold is 7 days, so 8 days ago exceeds it.
    from datetime import UTC, datetime, timedelta  # noqa: PLC0415

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    post_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert post_resp.status_code == 201

    # Retrieve the shared Postgres connection from any registered override.
    override_fn = app.dependency_overrides.get(dash_get_milestone_repo)
    assert override_fn is not None, "dash_get_milestone_repo override must be registered"
    conn_ref = None
    async for repo in override_fn():
        conn_ref = repo._conn
        break
    assert conn_ref is not None, "could not retrieve shared test connection"

    eight_days_ago = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    await conn_ref.execute(
        "UPDATE milestone_updates SET posted_at = $1 WHERE po_id = $2",
        eight_days_ago, po_id,
    )

    dash_resp = await client.get("/api/v1/dashboard/")
    assert dash_resp.status_code == 200
    overdue = dash_resp.json()["overdue_pos"]
    overdue_ids = [o["id"] for o in overdue]
    assert po_id in overdue_ids, f"PO {po_id} must appear in overdue_pos; got {overdue}"
    matching = next(o for o in overdue if o["id"] == po_id)
    assert matching["milestone"] == "RAW_MATERIALS"
    assert matching["days_since_update"] >= 8
