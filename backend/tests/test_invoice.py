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
from src.repository import PurchaseOrderRepository
from src.routers.dashboard import get_repo as dash_get_repo
from src.routers.dashboard import get_vendor_repo as dash_get_vendor_repo
from src.routers.invoice import get_invoice_repo as invoice_get_invoice_repo
from src.routers.invoice import get_po_repo as invoice_get_po_repo
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

        @asynccontextmanager
        async def _test_get_db(*_args, **_kwargs) -> AsyncIterator[aiosqlite.Connection]:
            yield conn

        app.dependency_overrides[get_repo] = override_get_repo
        app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[vendor_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[dash_get_repo] = override_get_repo
        app.dependency_overrides[dash_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[invoice_get_invoice_repo] = override_get_invoice_repo
        app.dependency_overrides[invoice_get_po_repo] = override_get_repo
        app.dependency_overrides[po_get_invoice_repo] = override_get_invoice_repo

        transport = ASGITransport(app=app)
        with patch("src.routers.purchase_order.get_db", _test_get_db):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

    app.dependency_overrides.clear()


async def _create_accepted_po(client: AsyncClient) -> dict:
    vendor = await client.post(
        "/api/v1/vendors/",
        json={"name": "Test Vendor", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    payload = dict(_PO_PAYLOAD)
    payload["vendor_id"] = vendor.json()["id"]
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
