from __future__ import annotations

from contextlib import asynccontextmanager
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
from src.repository import PurchaseOrderRepository
from src.routers.dashboard import get_activity_repo as dash_get_activity_repo
from src.routers.dashboard import get_invoice_repo as dash_get_invoice_repo
from src.routers.dashboard import get_milestone_repo as dash_get_milestone_repo
from src.routers.dashboard import get_repo as dash_get_repo
from src.routers.dashboard import get_vendor_repo as dash_get_vendor_repo
from src.routers.invoice import get_activity_repo as invoice_get_activity_repo
from src.routers.invoice import get_invoice_repo as invoice_get_invoice_repo
from src.routers.invoice import get_po_repo as invoice_get_po_repo
from src.routers.invoice import get_vendor_repo as invoice_get_vendor_repo
from src.routers.milestone import get_milestone_repo
from src.routers.milestone import get_activity_repo as milestone_get_activity_repo
from src.routers.purchase_order import get_activity_repo as po_get_activity_repo
from src.routers.purchase_order import get_invoice_repo as po_get_invoice_repo
from src.routers.purchase_order import get_repo
from src.routers.purchase_order import get_vendor_repo as po_get_vendor_repo
from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo
from src.milestone_repository import MilestoneRepository
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

_LINE_ITEM_2 = {
    "part_number": "PN-002",
    "description": "Widget B",
    "quantity": 50,
    "uom": "EA",
    "unit_price": "10.00",
    "hs_code": "8471.40",
    "country_of_origin": "US",
}

_PO_PAYLOAD = {
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
    "line_items": [_LINE_ITEM, _LINE_ITEM_2],
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
        app.dependency_overrides[invoice_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[invoice_get_activity_repo] = override_get_activity_repo
        app.dependency_overrides[po_get_invoice_repo] = override_get_invoice_repo
        app.dependency_overrides[get_milestone_repo] = override_get_milestone_repo
        app.dependency_overrides[milestone_get_activity_repo] = override_get_activity_repo

        transport = ASGITransport(app=app)
        with patch("src.routers.purchase_order.get_db", _test_get_db):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

    app.dependency_overrides.clear()


async def _create_accepted_po(client: AsyncClient, po_type: str = "PROCUREMENT") -> dict:
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Test Vendor", "country": "US", "vendor_type": po_type},
    )
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
    payload["po_type"] = po_type
    po = await client.post("/api/v1/po/", json=payload)
    po_id = po.json()["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")
    await client.post(f"/api/v1/po/{po_id}/accept")
    return (await client.get(f"/api/v1/po/{po_id}")).json()


async def test_invoiced_quantities_excludes_disputed(client: AsyncClient) -> None:
    # Disputed invoices must not count toward invoiced totals.
    pn1 = "PN-001"
    pn2 = "PN-002"
    pn1_ordered = 100
    pn2_ordered = 50

    po = await _create_accepted_po(client)
    po_id = po["id"]

    # Invoice A: counts toward totals (DRAFT, not disputed).
    inv_a = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [
                {"part_number": pn1, "quantity": 30},
                {"part_number": pn2, "quantity": 20},
            ],
        },
    )
    assert inv_a.status_code == 201

    # Invoice B: submitted then disputed — must be excluded from invoiced totals.
    inv_b = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [
                {"part_number": pn1, "quantity": 20},
                {"part_number": pn2, "quantity": 10},
            ],
        },
    )
    assert inv_b.status_code == 201
    inv_b_id = inv_b.json()["id"]
    await client.post(f"/api/v1/invoices/{inv_b_id}/submit")
    dispute_resp = await client.post(
        f"/api/v1/invoices/{inv_b_id}/dispute",
        json={"reason": "test"},
    )
    assert dispute_resp.json()["status"] == "DISPUTED"

    resp = await client.get(f"/api/v1/invoices/po/{po_id}/remaining")
    assert resp.status_code == 200
    lines_by_part = {line["part_number"]: line for line in resp.json()["lines"]}

    # PN-001: only invoice A's 30 counted; invoice B's 20 excluded.
    assert lines_by_part[pn1]["invoiced"] == 30, "disputed invoice B must not count toward invoiced"
    assert lines_by_part[pn1]["remaining"] == pn1_ordered - 30

    # PN-002: only invoice A's 20 counted; invoice B's 10 excluded.
    assert lines_by_part[pn2]["invoiced"] == 20, "disputed invoice B must not count toward invoiced"
    assert lines_by_part[pn2]["remaining"] == pn2_ordered - 20


async def test_over_invoicing_rejected(client: AsyncClient) -> None:
    # A second invoice must be rejected when it would exceed the ordered quantity.
    pn1 = "PN-001"
    pn1_ordered = 100

    po = await _create_accepted_po(client)
    po_id = po["id"]

    first = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": pn1, "quantity": 60}],
        },
    )
    # First invoice for 60 of 100 must succeed.
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": pn1, "quantity": 50}],
        },
    )
    # 60 already invoiced + 50 requested = 110 > 100 ordered; must be rejected.
    assert second.status_code == 409, "over-invoicing must return 409"

    detail = second.json()["detail"]
    # Detail is a list of violation objects; confirm the violating part is present.
    violation_parts = [v["part_number"] for v in detail]
    assert pn1 in violation_parts, "violation detail must name the offending part number"

    violation = next(v for v in detail if v["part_number"] == pn1)
    assert violation["ordered"] == pn1_ordered
    assert violation["already_invoiced"] == 60
    assert violation["requested"] == 50


async def test_partial_invoice_accepted(client: AsyncClient) -> None:
    # An invoice covering only part of one line must succeed and leave the rest available.
    pn1 = "PN-001"
    pn2 = "PN-002"
    pn1_ordered = 100
    pn2_ordered = 50
    pn1_invoiced = 40

    po = await _create_accepted_po(client)
    po_id = po["id"]

    inv = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": pn1, "quantity": pn1_invoiced}],
        },
    )
    assert inv.status_code == 201

    resp = await client.get(f"/api/v1/invoices/po/{po_id}/remaining")
    assert resp.status_code == 200
    lines_by_part = {line["part_number"]: line for line in resp.json()["lines"]}

    # PN-001: partially invoiced.
    assert lines_by_part[pn1]["invoiced"] == pn1_invoiced
    assert lines_by_part[pn1]["remaining"] == pn1_ordered - pn1_invoiced

    # PN-002: untouched by this invoice.
    assert lines_by_part[pn2]["invoiced"] == 0, "uninvoiced line must report zero invoiced"
    assert lines_by_part[pn2]["remaining"] == pn2_ordered


async def test_zero_quantity_lines_excluded(client: AsyncClient) -> None:
    # Line items with quantity=0 must not appear in the saved invoice.
    pn1 = "PN-001"
    pn2 = "PN-002"

    po = await _create_accepted_po(client)
    po_id = po["id"]

    inv = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [
                {"part_number": pn1, "quantity": 30},
                {"part_number": pn2, "quantity": 0},
            ],
        },
    )
    assert inv.status_code == 201
    inv_id = inv.json()["id"]

    get_resp = await client.get(f"/api/v1/invoices/{inv_id}")
    assert get_resp.status_code == 200
    line_items = get_resp.json()["line_items"]

    present_parts = [li["part_number"] for li in line_items]
    # Zero-quantity line must be stripped; only the active line must be stored.
    assert pn1 in present_parts, "non-zero line must be present"
    assert pn2 not in present_parts, "zero-quantity line must be excluded"
    assert len(line_items) == 1, "invoice must contain exactly one line item"


async def test_remaining_endpoint(client: AsyncClient) -> None:
    # /remaining must reflect only active (non-disputed) invoices and update after each invoice.
    pn1 = "PN-001"
    pn2 = "PN-002"
    pn1_ordered = 100
    pn2_ordered = 50
    pn1_partial = 25

    po = await _create_accepted_po(client)
    po_id = po["id"]

    # Before any invoices: both lines fully available.
    resp = await client.get(f"/api/v1/invoices/po/{po_id}/remaining")
    assert resp.status_code == 200
    lines_by_part = {line["part_number"]: line for line in resp.json()["lines"]}

    assert lines_by_part[pn1]["invoiced"] == 0
    assert lines_by_part[pn1]["remaining"] == pn1_ordered
    assert lines_by_part[pn2]["invoiced"] == 0
    assert lines_by_part[pn2]["remaining"] == pn2_ordered

    # Create a partial invoice for PN-001 only.
    inv = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": pn1, "quantity": pn1_partial}],
        },
    )
    assert inv.status_code == 201

    # After partial invoice: PN-001 reduced, PN-002 unchanged.
    resp2 = await client.get(f"/api/v1/invoices/po/{po_id}/remaining")
    assert resp2.status_code == 200
    lines_by_part2 = {line["part_number"]: line for line in resp2.json()["lines"]}

    assert lines_by_part2[pn1]["invoiced"] == pn1_partial
    assert lines_by_part2[pn1]["remaining"] == pn1_ordered - pn1_partial
    assert lines_by_part2[pn2]["invoiced"] == 0, "uninvoiced line must remain at zero"
    assert lines_by_part2[pn2]["remaining"] == pn2_ordered


async def test_list_invoices_returns_all(client: AsyncClient) -> None:
    # GET /api/v1/invoices/ must return all invoices across all POs.
    po1 = await _create_accepted_po(client)
    po2 = await _create_accepted_po(client)

    inv1 = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po1["id"],
            "line_items": [{"part_number": "PN-001", "quantity": 10}],
        },
    )
    assert inv1.status_code == 201

    inv2 = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po2["id"],
            "line_items": [{"part_number": "PN-001", "quantity": 20}],
        },
    )
    assert inv2.status_code == 201

    resp = await client.get("/api/v1/invoices/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2

    expected_po_ids = {po1["id"], po2["id"]}
    required_keys = {"po_number", "vendor_name", "invoice_number", "status", "subtotal", "po_id"}
    for item in items:
        assert required_keys <= item.keys(), f"invoice list item missing keys: {required_keys - item.keys()}"
    returned_po_ids = {item["po_id"] for item in items}
    assert returned_po_ids == expected_po_ids


async def test_list_invoices_filter_by_status(client: AsyncClient) -> None:
    # GET /api/v1/invoices/?status=X must return only invoices in that status.
    po = await _create_accepted_po(client)
    po_id = po["id"]

    # PN-001 has 100 units; split 50/50 so each invoice stays within the guard.
    inv_draft = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PN-001", "quantity": 50}],
        },
    )
    assert inv_draft.status_code == 201
    inv_draft_id = inv_draft.json()["id"]

    inv_submitted = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PN-001", "quantity": 50}],
        },
    )
    assert inv_submitted.status_code == 201
    inv_submitted_id = inv_submitted.json()["id"]

    submit_resp = await client.post(f"/api/v1/invoices/{inv_submitted_id}/submit")
    assert submit_resp.status_code == 200

    draft_resp = await client.get("/api/v1/invoices/?status=DRAFT")
    assert draft_resp.status_code == 200
    draft_items = draft_resp.json()["items"]
    assert len(draft_items) == 1, "only one invoice must be in DRAFT"
    assert draft_items[0]["id"] == inv_draft_id
    assert draft_items[0]["status"] == "DRAFT"

    submitted_resp = await client.get("/api/v1/invoices/?status=SUBMITTED")
    assert submitted_resp.status_code == 200
    submitted_items = submitted_resp.json()["items"]
    assert len(submitted_items) == 1, "only one invoice must be in SUBMITTED"
    assert submitted_items[0]["id"] == inv_submitted_id
    assert submitted_items[0]["status"] == "SUBMITTED"


async def test_list_invoices_empty(client: AsyncClient) -> None:
    # GET /api/v1/invoices/ with no invoices in the database must return an empty list.
    resp = await client.get("/api/v1/invoices/")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


async def test_list_invoices_filter_by_po_number(client: AsyncClient) -> None:
    # GET /api/v1/invoices/?po_number=X must return only invoices whose PO number contains X.
    po1 = await _create_accepted_po(client)
    po2 = await _create_accepted_po(client)

    inv1 = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po1["id"],
            "line_items": [{"part_number": "PN-001", "quantity": 10}],
        },
    )
    assert inv1.status_code == 201

    inv2 = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po2["id"],
            "line_items": [{"part_number": "PN-001", "quantity": 10}],
        },
    )
    assert inv2.status_code == 201

    # Retrieve both to get their po_numbers.
    all_resp = await client.get("/api/v1/invoices/")
    assert all_resp.status_code == 200
    all_items = all_resp.json()["items"]
    assert len(all_items) == 2

    po_numbers = {item["po_id"]: item["po_number"] for item in all_items}
    target_po_number = po_numbers[po1["id"]]

    # Filter by the full po_number of the first PO.
    resp = await client.get(f"/api/v1/invoices/?po_number={target_po_number}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1, "filter by po_number must return exactly one invoice"
    assert items[0]["po_id"] == po1["id"]
    assert items[0]["po_number"] == target_po_number


async def test_list_invoices_filter_by_vendor_name(client: AsyncClient) -> None:
    # GET /api/v1/invoices/?vendor_name=X must return only invoices from vendors whose name contains X.
    alpha_vendor_name = "Alpha Corp"
    beta_vendor_name = "Beta Ltd"

    alpha_vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": alpha_vendor_name, "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert alpha_vendor.status_code == 201
    alpha_vendor_id = alpha_vendor.json()["id"]

    beta_vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": beta_vendor_name, "country": "GB", "vendor_type": "PROCUREMENT"},
    )
    assert beta_vendor.status_code == 201
    beta_vendor_id = beta_vendor.json()["id"]

    async def _make_po_for_vendor(vendor_id: str) -> dict:
        payload = dict(_PO_PAYLOAD)
        payload["vendor_id"] = vendor_id
        po = await client.post("/api/v1/po/", json=payload)
        po_id = po.json()["id"]
        await client.post(f"/api/v1/po/{po_id}/submit")
        await client.post(f"/api/v1/po/{po_id}/accept")
        return (await client.get(f"/api/v1/po/{po_id}")).json()

    alpha_po = await _make_po_for_vendor(alpha_vendor_id)
    beta_po = await _make_po_for_vendor(beta_vendor_id)

    alpha_inv = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": alpha_po["id"],
            "line_items": [{"part_number": "PN-001", "quantity": 10}],
        },
    )
    assert alpha_inv.status_code == 201

    beta_inv = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": beta_po["id"],
            "line_items": [{"part_number": "PN-001", "quantity": 10}],
        },
    )
    assert beta_inv.status_code == 201

    alpha_resp = await client.get("/api/v1/invoices/?vendor_name=Alpha")
    assert alpha_resp.status_code == 200
    alpha_items = alpha_resp.json()["items"]
    assert len(alpha_items) == 1, "vendor_name=Alpha must return only Alpha Corp invoice"
    assert alpha_items[0]["vendor_name"] == alpha_vendor_name

    beta_resp = await client.get("/api/v1/invoices/?vendor_name=Beta")
    assert beta_resp.status_code == 200
    beta_items = beta_resp.json()["items"]
    assert len(beta_items) == 1, "vendor_name=Beta must return only Beta Ltd invoice"
    assert beta_items[0]["vendor_name"] == beta_vendor_name


async def test_list_invoices_filter_by_invoice_number(client: AsyncClient) -> None:
    # GET /api/v1/invoices/?invoice_number=X must return only invoices whose invoice_number contains X.
    po = await _create_accepted_po(client)
    po_id = po["id"]

    # PN-001 has 100 units; create two invoices of 50 each.
    inv_a = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PN-001", "quantity": 50}],
        },
    )
    assert inv_a.status_code == 201

    inv_b = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PN-001", "quantity": 50}],
        },
    )
    assert inv_b.status_code == 201

    # Get all to retrieve their invoice_numbers.
    all_resp = await client.get("/api/v1/invoices/")
    assert all_resp.status_code == 200
    all_items = all_resp.json()["items"]
    assert len(all_items) == 2

    inv_a_id = inv_a.json()["id"]
    target_invoice_number = next(item["invoice_number"] for item in all_items if item["id"] == inv_a_id)

    resp = await client.get(f"/api/v1/invoices/?invoice_number={target_invoice_number}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1, "filter by invoice_number must return exactly one invoice"
    assert items[0]["invoice_number"] == target_invoice_number
    assert items[0]["id"] == inv_a_id


async def test_list_invoices_filter_by_date_range(client: AsyncClient) -> None:
    # GET /api/v1/invoices/?date_from=X&date_to=Y must return invoices within the date range.
    today = "2026-04-03"
    future_date = "2099-01-01"
    past_date = "2000-01-01"

    po = await _create_accepted_po(client)
    po_id = po["id"]

    inv = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PN-001", "quantity": 10}],
        },
    )
    assert inv.status_code == 201

    # Invoice created today must appear when date range spans today.
    today_resp = await client.get(f"/api/v1/invoices/?date_from={today}&date_to={today}")
    assert today_resp.status_code == 200
    today_items = today_resp.json()["items"]
    assert len(today_items) == 1, "invoice created today must be returned for today's date range"

    # date_from in far future must exclude all invoices.
    future_resp = await client.get(f"/api/v1/invoices/?date_from={future_date}")
    assert future_resp.status_code == 200
    assert future_resp.json()["items"] == [], "date_from in far future must return empty list"

    # date_to in far past must exclude all invoices.
    past_resp = await client.get(f"/api/v1/invoices/?date_to={past_date}")
    assert past_resp.status_code == 200
    assert past_resp.json()["items"] == [], "date_to in far past must return empty list"


async def test_dashboard_includes_invoice_summary(client: AsyncClient) -> None:
    # GET /api/v1/dashboard/ must include invoice_summary with at least one entry
    # after an invoice exists.
    po = await _create_accepted_po(client)
    po_id = po["id"]

    inv = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PN-001", "quantity": 10}],
        },
    )
    assert inv.status_code == 201

    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()

    assert "invoice_summary" in data, "dashboard response must contain invoice_summary key"
    invoice_summary = data["invoice_summary"]
    assert isinstance(invoice_summary, list)
    assert len(invoice_summary) >= 1, "invoice_summary must have at least one entry"

    required_keys = {"status", "count", "total_usd"}
    for entry in invoice_summary:
        assert required_keys <= entry.keys(), f"invoice_summary entry missing keys: {required_keys - entry.keys()}"


async def test_create_opex_invoice(client: AsyncClient) -> None:
    # Creating an invoice against an ACCEPTED OPEX PO must succeed and include all line items at full quantity.
    pn1 = "PN-001"
    pn2 = "PN-002"
    pn1_ordered = 100
    pn2_ordered = 50

    po = await _create_accepted_po(client, po_type="OPEX")
    po_id = po["id"]

    resp = await client.post("/api/v1/invoices/", json={"po_id": po_id})
    assert resp.status_code == 201, f"expected 201, got {resp.status_code}: {resp.text}"

    invoice = resp.json()
    assert invoice["po_id"] == po_id, "invoice must reference the OPEX PO"

    line_items_by_part = {li["part_number"]: li for li in invoice["line_items"]}
    assert set(line_items_by_part.keys()) == {pn1, pn2}, "invoice must contain exactly the two PO line items"
    assert line_items_by_part[pn1]["quantity"] == pn1_ordered, "PN-001 must be invoiced at full ordered quantity"
    assert line_items_by_part[pn2]["quantity"] == pn2_ordered, "PN-002 must be invoiced at full ordered quantity"


async def test_create_second_opex_invoice_returns_409(client: AsyncClient) -> None:
    # A second invoice attempt on the same OPEX PO must return 409.
    po = await _create_accepted_po(client, po_type="OPEX")
    po_id = po["id"]

    first = await client.post("/api/v1/invoices/", json={"po_id": po_id})
    assert first.status_code == 201, f"first OPEX invoice must succeed: {first.text}"

    second = await client.post("/api/v1/invoices/", json={"po_id": po_id})
    assert second.status_code == 409, "second OPEX invoice must be rejected with 409"
    assert "already exists" in second.json()["detail"], "409 detail must state an invoice already exists"


async def test_create_opex_invoice_with_line_items_returns_422(client: AsyncClient) -> None:
    # Sending line_items when creating an OPEX invoice must return 422.
    po = await _create_accepted_po(client, po_type="OPEX")
    po_id = po["id"]

    resp = await client.post(
        "/api/v1/invoices/",
        json={"po_id": po_id, "line_items": [{"part_number": "PN-001", "quantity": 10}]},
    )
    assert resp.status_code == 422, "OPEX invoice with line_items must return 422"
    assert "line_items" in resp.json()["detail"], "422 detail must mention line_items"


async def test_opex_invoice_lifecycle(client: AsyncClient) -> None:
    # An OPEX invoice must progress through the full lifecycle: Draft → Submitted → Approved → Paid.
    # Dispute from Submitted must also work.
    po = await _create_accepted_po(client, po_type="OPEX")
    po_id = po["id"]

    create_resp = await client.post("/api/v1/invoices/", json={"po_id": po_id})
    assert create_resp.status_code == 201
    invoice_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "DRAFT", "new OPEX invoice must be in DRAFT"

    submit_resp = await client.post(f"/api/v1/invoices/{invoice_id}/submit")
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "SUBMITTED", "invoice must advance to SUBMITTED"

    approve_resp = await client.post(f"/api/v1/invoices/{invoice_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED", "invoice must advance to APPROVED"

    pay_resp = await client.post(f"/api/v1/invoices/{invoice_id}/pay")
    assert pay_resp.status_code == 200
    assert pay_resp.json()["status"] == "PAID", "invoice must advance to PAID"

    # Dispute path: create a second OPEX PO to test dispute → resolve.
    po2 = await _create_accepted_po(client, po_type="OPEX")
    inv2_resp = await client.post("/api/v1/invoices/", json={"po_id": po2["id"]})
    assert inv2_resp.status_code == 201
    inv2_id = inv2_resp.json()["id"]

    await client.post(f"/api/v1/invoices/{inv2_id}/submit")
    dispute_resp = await client.post(
        f"/api/v1/invoices/{inv2_id}/dispute", json={"reason": "wrong amount"}
    )
    assert dispute_resp.status_code == 200
    assert dispute_resp.json()["status"] == "DISPUTED", "invoice must advance to DISPUTED"
