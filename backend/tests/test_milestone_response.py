"""Permanent tests for the GET /api/v1/po/{id}/milestones response shape.

Iter 082 extends MilestoneResponse with is_overdue and days_overdue.
The latest posted milestone is the "stuck" stage; earlier rows have moved
on so are always is_overdue=False / days_overdue=None.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.main import app
from src.routers.dashboard import get_milestone_repo as dash_get_milestone_repo

pytestmark = pytest.mark.asyncio

_brand_counter = itertools.count(1)


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
    "po_type": "PROCUREMENT",
    "line_items": [_LINE_ITEM],
}


async def _create_accepted_procurement_po(client: AsyncClient) -> str:
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Test Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor.status_code == 201
    vendor_id = vendor.json()["id"]
    brand_n = next(_brand_counter)
    brand = await client.post("/api/v1/brands/", json={"name": f"MsrBrand-{brand_n}", "legal_name": "Msr Brand LLC", "address": "1 Msr Ave", "country": "US"})
    assert brand.status_code == 201
    brand_id = brand.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor_id})
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor_id
    payload["brand_id"] = brand_id
    po = await client.post("/api/v1/po/", json=payload)
    assert po.status_code == 201
    po_id: str = po.json()["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/accept")
    return po_id


async def _shared_conn():
    """Retrieve the shared Postgres connection from a registered DI override.

    The test conftest registers the same connection under every repo
    dependency; we reach in through dash_get_milestone_repo because it is
    always present and exposes the underlying connection on _conn.
    """
    override_fn = app.dependency_overrides.get(dash_get_milestone_repo)
    assert override_fn is not None, "dash_get_milestone_repo override must be registered"
    async for repo in override_fn():
        return repo._conn
    raise AssertionError("could not retrieve shared test connection")


async def _backdate_milestone(po_id: str, milestone: str, days_ago: int) -> None:
    """Rewrite a posted_at timestamp directly so we can place a milestone in
    the past without faking the system clock.
    """
    conn = await _shared_conn()
    backdated = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    await conn.execute(
        "UPDATE milestone_updates SET posted_at = $1 WHERE po_id = $2 AND milestone = $3",
        backdated, po_id, milestone,
    )


async def test_list_milestones_marks_latest_as_overdue_when_stuck_past_threshold(
    authenticated_client: AsyncClient,
) -> None:
    # RAW_MATERIALS threshold is 7 days. Posting 10 days ago must produce
    # is_overdue=True with days_overdue=3 on the latest (and only) row.
    client = authenticated_client
    po_id = await _create_accepted_procurement_po(client)

    post_resp = await client.post(
        f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"}
    )
    assert post_resp.status_code == 201
    await _backdate_milestone(po_id, "RAW_MATERIALS", days_ago=10)

    list_resp = await client.get(f"/api/v1/po/{po_id}/milestones")
    assert list_resp.status_code == 200
    rows: list[dict] = list_resp.json()
    assert len(rows) == 1, f"expected single row; got {rows}"

    expected_keys = {"milestone", "posted_at", "is_overdue", "days_overdue"}
    assert set(rows[0].keys()) >= expected_keys, (
        f"row missing keys {expected_keys - rows[0].keys()}: {rows[0]}"
    )
    assert rows[0]["milestone"] == "RAW_MATERIALS"
    assert rows[0]["is_overdue"] is True
    assert rows[0]["days_overdue"] == 3, (
        f"expected days_overdue=3 (10 days - 7 threshold); got {rows[0]['days_overdue']}"
    )


async def test_list_milestones_marks_earlier_rows_not_overdue(
    authenticated_client: AsyncClient,
) -> None:
    # RAW_MATERIALS posted 30 days ago + PRODUCTION_STARTED posted 2 days ago.
    # The latest row is PRODUCTION_STARTED, well within its 7-day threshold,
    # so neither row is overdue.
    client = authenticated_client
    po_id = await _create_accepted_procurement_po(client)

    raw_resp = await client.post(
        f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"}
    )
    assert raw_resp.status_code == 201
    prod_resp = await client.post(
        f"/api/v1/po/{po_id}/milestones", json={"milestone": "PRODUCTION_STARTED"}
    )
    assert prod_resp.status_code == 201

    await _backdate_milestone(po_id, "RAW_MATERIALS", days_ago=30)
    await _backdate_milestone(po_id, "PRODUCTION_STARTED", days_ago=2)

    list_resp = await client.get(f"/api/v1/po/{po_id}/milestones")
    assert list_resp.status_code == 200
    rows: list[dict] = list_resp.json()
    assert len(rows) == 2, f"expected two rows; got {rows}"

    raw_row = next(r for r in rows if r["milestone"] == "RAW_MATERIALS")
    prod_row = next(r for r in rows if r["milestone"] == "PRODUCTION_STARTED")

    # Earlier (no longer current) row is never overdue regardless of age.
    assert raw_row["is_overdue"] is False, (
        f"RAW_MATERIALS is not the latest row, must be is_overdue=False; got {raw_row}"
    )
    assert raw_row["days_overdue"] is None

    # Latest row sits within its 7-day threshold (2 days old), not overdue.
    assert prod_row["is_overdue"] is False, (
        f"PRODUCTION_STARTED 2d old vs 7d threshold must be is_overdue=False; got {prod_row}"
    )
    assert prod_row["days_overdue"] is None


async def test_list_milestones_returns_empty_list_when_none_posted(
    authenticated_client: AsyncClient,
) -> None:
    # An ACCEPTED PROCUREMENT PO with no milestones posted must return
    # 200 with an empty list — no error, no synthesised rows.
    client = authenticated_client
    po_id = await _create_accepted_procurement_po(client)

    resp = await client.get(f"/api/v1/po/{po_id}/milestones")
    assert resp.status_code == 200
    assert resp.json() == [], f"expected empty list; got {resp.json()}"
