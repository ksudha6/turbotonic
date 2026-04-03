from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.db import get_db
from src.invoice_repository import InvoiceRepository
from src.main import app
from src.milestone_repository import MilestoneRepository
from src.repository import PurchaseOrderRepository
from src.routers.dashboard import get_invoice_repo as dash_get_invoice_repo
from src.routers.dashboard import get_milestone_repo as dash_get_milestone_repo
from src.routers.dashboard import get_repo as dash_get_repo
from src.routers.dashboard import get_vendor_repo as dash_get_vendor_repo
from src.routers.invoice import get_invoice_repo as invoice_get_invoice_repo
from src.routers.invoice import get_po_repo as invoice_get_po_repo
from src.routers.milestone import get_milestone_repo
from src.routers.milestone import get_po_repo as milestone_get_po_repo
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

        @asynccontextmanager
        async def _test_get_db(*_args, **_kwargs) -> AsyncIterator[aiosqlite.Connection]:
            yield conn

        app.dependency_overrides[get_repo] = override_get_repo
        app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[vendor_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[dash_get_repo] = override_get_repo
        app.dependency_overrides[dash_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[dash_get_invoice_repo] = override_get_invoice_repo
        app.dependency_overrides[dash_get_milestone_repo] = override_get_milestone_repo
        app.dependency_overrides[invoice_get_invoice_repo] = override_get_invoice_repo
        app.dependency_overrides[invoice_get_po_repo] = override_get_repo
        app.dependency_overrides[po_get_invoice_repo] = override_get_invoice_repo
        app.dependency_overrides[get_milestone_repo] = override_get_milestone_repo
        app.dependency_overrides[milestone_get_po_repo] = override_get_repo

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


async def test_post_milestone_on_accepted_procurement_po_returns_201(client: AsyncClient) -> None:
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


async def test_reject_milestone_on_non_accepted_po(client: AsyncClient) -> None:
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


async def test_reject_milestone_on_non_procurement_po(client: AsyncClient) -> None:
    # Posting a milestone on an ACCEPTED OPEX PO must return 409.
    po = await _create_accepted_opex_po(client)
    po_id = po["id"]

    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert resp.status_code == 409, f"expected 409 for OPEX PO, got {resp.status_code}: {resp.text}"


async def test_reject_out_of_order_milestone(client: AsyncClient) -> None:
    # After RAW_MATERIALS, posting QC_PASSED (skipping PRODUCTION_STARTED) must return 409.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    first = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert first.status_code == 201

    skip = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "QC_PASSED"})
    assert skip.status_code == 409, f"expected 409 for out-of-order milestone, got {skip.status_code}: {skip.text}"


async def test_reject_duplicate_milestone(client: AsyncClient) -> None:
    # Posting RAW_MATERIALS twice must return 409 on the second attempt.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    first = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert first.status_code == 201

    duplicate = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert duplicate.status_code == 409, f"expected 409 for duplicate milestone, got {duplicate.status_code}: {duplicate.text}"


async def test_get_milestones_returns_posted_order(client: AsyncClient) -> None:
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


async def test_get_milestones_empty(client: AsyncClient) -> None:
    # GET milestones on a PO with none posted must return 200 with an empty list.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    resp = await client.get(f"/api/v1/po/{po_id}/milestones")
    assert resp.status_code == 200
    assert resp.json() == [], "no milestones posted must return empty list"


async def test_post_invalid_milestone_value_returns_422(client: AsyncClient) -> None:
    # Posting an unrecognised milestone value must return 422.
    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "INVALID"})
    assert resp.status_code == 422, f"expected 422 for invalid milestone, got {resp.status_code}: {resp.text}"


async def test_po_list_includes_current_milestone(client: AsyncClient) -> None:
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


async def test_po_list_current_milestone_null_when_no_milestones(client: AsyncClient) -> None:
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


async def test_po_list_filter_by_milestone(client: AsyncClient) -> None:
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


async def test_dashboard_production_summary(client: AsyncClient) -> None:
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


async def test_dashboard_overdue_pos(client: AsyncClient) -> None:
    # A PO at RAW_MATERIALS with posted_at backdated to 8 days ago must appear in overdue_pos.
    # RAW_MATERIALS threshold is 7 days, so 8 days ago exceeds it.
    from datetime import UTC, datetime, timedelta  # noqa: PLC0415

    po = await _create_accepted_procurement_po(client)
    po_id = po["id"]

    post_resp = await client.post(f"/api/v1/po/{po_id}/milestones", json={"milestone": "RAW_MATERIALS"})
    assert post_resp.status_code == 201

    # The fixture shares a single aiosqlite connection across all dependency overrides.
    # Retrieve the conn by calling the registered override for dash_get_milestone_repo.
    from src.main import app as _app  # noqa: PLC0415
    override_fn = _app.dependency_overrides.get(dash_get_milestone_repo)
    assert override_fn is not None, "dash_get_milestone_repo override must be registered"
    conn_ref = None
    async for repo in override_fn():
        conn_ref = repo._conn
        break
    assert conn_ref is not None, "could not retrieve shared test connection"

    eight_days_ago = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    await conn_ref.execute(
        "UPDATE milestone_updates SET posted_at = ? WHERE po_id = ?",
        (eight_days_ago, po_id),
    )
    await conn_ref.commit()

    dash_resp = await client.get("/api/v1/dashboard/")
    assert dash_resp.status_code == 200
    overdue = dash_resp.json()["overdue_pos"]
    overdue_ids = [o["id"] for o in overdue]
    assert po_id in overdue_ids, f"PO {po_id} must appear in overdue_pos; got {overdue}"
    matching = next(o for o in overdue if o["id"] == po_id)
    assert matching["milestone"] == "RAW_MATERIALS"
    assert matching["days_since_update"] >= 8
