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
from src.milestone_repository import MilestoneRepository
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
from src.routers.milestone import get_activity_repo as milestone_get_activity_repo
from src.routers.milestone import get_milestone_repo
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


async def _create_invoice(client: AsyncClient, po_id: str, part_number: str, quantity: int) -> dict:
    resp = await client.post(
        "/api/v1/invoices/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": part_number, "quantity": quantity}],
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_invoice_pdf_returns_bytes(client: AsyncClient) -> None:
    # GET /{id}/pdf must return 200, application/pdf content-type, and non-empty body.
    po = await _create_accepted_po(client)
    invoice = await _create_invoice(client, po["id"], "PN-001", 10)
    invoice_id = invoice["id"]

    resp = await client.get(f"/api/v1/invoices/{invoice_id}/pdf")

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0, "PDF response body must not be empty"


async def test_invoice_pdf_not_found(client: AsyncClient) -> None:
    # GET /nonexistent-id/pdf must return 404.
    nonexistent_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/invoices/{nonexistent_id}/pdf")

    assert resp.status_code == 404, f"expected 404, got {resp.status_code}"


async def test_bulk_invoice_pdf(client: AsyncClient) -> None:
    # POST /bulk/pdf with two invoice IDs must return 200, application/pdf, non-empty body.
    po = await _create_accepted_po(client)
    po_id = po["id"]

    # PN-001 has 100 units; split into two invoices of 50 each.
    invoice_a = await _create_invoice(client, po_id, "PN-001", 50)
    invoice_b = await _create_invoice(client, po_id, "PN-001", 50)
    invoice_a_id = invoice_a["id"]
    invoice_b_id = invoice_b["id"]

    resp = await client.post(
        "/api/v1/invoices/bulk/pdf",
        json={"invoice_ids": [invoice_a_id, invoice_b_id]},
    )

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0, "bulk PDF response body must not be empty"


async def test_bulk_invoice_pdf_empty_ids(client: AsyncClient) -> None:
    # POST /bulk/pdf with an empty invoice_ids list must return 400.
    resp = await client.post(
        "/api/v1/invoices/bulk/pdf",
        json={"invoice_ids": []},
    )

    assert resp.status_code == 400, f"expected 400, got {resp.status_code}"


async def test_bulk_invoice_pdf_skips_missing(client: AsyncClient) -> None:
    # POST /bulk/pdf with a mix of valid and nonexistent IDs must return 200 (missing IDs are skipped).
    po = await _create_accepted_po(client)
    invoice = await _create_invoice(client, po["id"], "PN-001", 10)
    invoice_id = invoice["id"]
    missing_id = "00000000-0000-0000-0000-000000000000"

    resp = await client.post(
        "/api/v1/invoices/bulk/pdf",
        json={"invoice_ids": [invoice_id, missing_id]},
    )

    assert resp.status_code == 200, f"expected 200 when mixing valid and missing IDs, got {resp.status_code}: {resp.text}"
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0, "bulk PDF body must not be empty when at least one valid ID exists"
