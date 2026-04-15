"""Permanent tests: vendor-scoped data access isolation (iteration 032).

VENDOR users see only data belonging to their vendor.
SM/ADMIN users see everything.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal
from datetime import UTC, datetime
from typing import AsyncIterator
from unittest.mock import patch

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.session import COOKIE_NAME, create_session_cookie
from src.domain.purchase_order import LineItem, POType, PurchaseOrder
from src.domain.user import User, UserRole
from src.domain.vendor import Vendor, VendorType
from src.invoice_repository import InvoiceRepository
from src.main import app
from src.repository import PurchaseOrderRepository
from src.schema import init_db
from src.user_repository import UserRepository
from src.vendor_repository import VendorRepository

# Import shared test helpers from conftest
from tests.conftest import TEST_DATABASE_URL, _setup_overrides

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_VENDOR_ALPHA_NAME = "Vendor Alpha"
_VENDOR_BETA_NAME = "Vendor Beta"

_ISSUED_DATE = "2026-04-15T00:00:00Z"
_DELIVERY_DATE = "2026-05-15T00:00:00Z"

_PO_LINE_ITEM = {
    "part_number": "P1",
    "description": "D",
    "quantity": 10,
    "uom": "PCS",
    "unit_price": "1.00",
    "hs_code": "7318.15",
    "country_of_origin": "CN",
}

_INVOICE_LINE_ITEMS = [
    {
        "part_number": "P1",
        "description": "D",
        "quantity": 5,
        "uom": "PCS",
        "unit_price": "1.00",
    }
]


def _po_payload(vendor_id: str) -> dict:
    return {
        "vendor_id": vendor_id,
        "po_type": "PROCUREMENT",
        "buyer_name": "B",
        "buyer_country": "US",
        "ship_to_address": "A",
        "payment_terms": "NET30",
        "currency": "USD",
        "issued_date": _ISSUED_DATE,
        "required_delivery_date": _DELIVERY_DATE,
        "terms_and_conditions": "T",
        "incoterm": "FOB",
        "port_of_loading": "CNSHA",
        "port_of_discharge": "USLAX",
        "country_of_origin": "CN",
        "country_of_destination": "US",
        "line_items": [_PO_LINE_ITEM],
    }


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def vendor_scoping_env():
    """Create two vendors, three users, and two POs in a single transaction."""
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    # Vendors
    v1 = Vendor.create(name=_VENDOR_ALPHA_NAME, country="CN", vendor_type=VendorType.PROCUREMENT)
    v2 = Vendor.create(name=_VENDOR_BETA_NAME, country="IN", vendor_type=VendorType.PROCUREMENT)
    vendor_repo = VendorRepository(conn)
    await vendor_repo.save(v1)
    await vendor_repo.save(v2)

    # Users
    u1 = User.create(username="vendor-u1", display_name="Vendor U1", role=UserRole.VENDOR, vendor_id=v1.id)
    u2 = User.create(username="vendor-u2", display_name="Vendor U2", role=UserRole.VENDOR, vendor_id=v2.id)
    sm = User.create(username="sm-user", display_name="SM User", role=UserRole.SM)
    user_repo = UserRepository(conn)
    await user_repo.save(u1)
    await user_repo.save(u2)
    await user_repo.save(sm)

    # POs created directly via domain + repository (status DRAFT)
    now = datetime.now(UTC)
    po1 = PurchaseOrder.create(
        po_number="PO-TEST-V1-001",
        vendor_id=v1.id,
        po_type=POType.PROCUREMENT,
        buyer_name="B",
        buyer_country="US",
        ship_to_address="A",
        payment_terms="NET30",
        currency="USD",
        issued_date=now,
        required_delivery_date=now,
        terms_and_conditions="T",
        incoterm="FOB",
        port_of_loading="CNSHA",
        port_of_discharge="USLAX",
        country_of_origin="CN",
        country_of_destination="US",
        line_items=[
            LineItem(
                part_number="P1",
                description="D",
                quantity=10,
                uom="PCS",
                unit_price=Decimal("1.00"),
                hs_code="7318.15",
                country_of_origin="CN",
            )
        ],
    )
    po2 = PurchaseOrder.create(
        po_number="PO-TEST-V2-001",
        vendor_id=v2.id,
        po_type=POType.PROCUREMENT,
        buyer_name="B",
        buyer_country="US",
        ship_to_address="A",
        payment_terms="NET30",
        currency="USD",
        issued_date=now,
        required_delivery_date=now,
        terms_and_conditions="T",
        incoterm="FOB",
        port_of_loading="CNSHA",
        port_of_discharge="USLAX",
        country_of_origin="CN",
        country_of_destination="US",
        line_items=[
            LineItem(
                part_number="P1",
                description="D",
                quantity=10,
                uom="PCS",
                unit_price=Decimal("1.00"),
                hs_code="7318.15",
                country_of_origin="CN",
            )
        ],
    )
    po_repo = PurchaseOrderRepository(conn)
    await po_repo.save(po1)
    await po_repo.save(po2)

    # Session cookies
    cookie_v1 = {COOKIE_NAME: create_session_cookie(u1.id)}
    cookie_v2 = {COOKIE_NAME: create_session_cookie(u2.id)}
    cookie_sm = {COOKIE_NAME: create_session_cookie(sm.id)}

    # Dependency overrides for this connection
    await _setup_overrides(conn)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    with (
        patch("src.routers.purchase_order.get_db", _test_get_db),
        patch("src.auth.middleware.get_db", _test_get_db),
    ):
        async with (
            AsyncClient(transport=transport, base_url="http://test", cookies=cookie_v1) as client_v1,
            AsyncClient(transport=transport, base_url="http://test", cookies=cookie_v2) as client_v2,
            AsyncClient(transport=transport, base_url="http://test", cookies=cookie_sm) as client_sm,
        ):
            yield {
                "client_v1": client_v1,
                "client_v2": client_v2,
                "client_sm": client_sm,
                "po1_id": po1.id,
                "po2_id": po2.id,
                "v1_id": v1.id,
                "v2_id": v2.id,
                "conn": conn,
            }

    await tx.rollback()
    await conn.close()
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# PO scoping
# ---------------------------------------------------------------------------


async def test_vendor_u1_lists_only_own_pos(vendor_scoping_env) -> None:
    """U1 list returns only V1 POs; V2's PO is absent."""
    env = vendor_scoping_env
    resp = await env["client_v1"].get("/api/v1/po/")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert env["po1_id"] in ids, "V1's PO must appear in U1's list"
    assert env["po2_id"] not in ids, "V2's PO must not appear in U1's list"


async def test_vendor_u1_cannot_get_v2_po(vendor_scoping_env) -> None:
    """U1 direct fetch of V2's PO returns 404."""
    env = vendor_scoping_env
    resp = await env["client_v1"].get(f"/api/v1/po/{env['po2_id']}")
    assert resp.status_code == 404


async def test_vendor_u1_can_get_own_po(vendor_scoping_env) -> None:
    """U1 direct fetch of their own PO returns 200."""
    env = vendor_scoping_env
    resp = await env["client_v1"].get(f"/api/v1/po/{env['po1_id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == env["po1_id"]


async def test_sm_lists_all_pos(vendor_scoping_env) -> None:
    """SM list response contains both V1 and V2 POs."""
    env = vendor_scoping_env
    resp = await env["client_sm"].get("/api/v1/po/")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert env["po1_id"] in ids, "V1's PO must appear in SM list"
    assert env["po2_id"] in ids, "V2's PO must appear in SM list"


async def test_sm_can_view_any_po(vendor_scoping_env) -> None:
    """SM can fetch both V1 and V2 POs directly."""
    env = vendor_scoping_env
    for po_id in (env["po1_id"], env["po2_id"]):
        resp = await env["client_sm"].get(f"/api/v1/po/{po_id}")
        assert resp.status_code == 200, f"SM should be able to view PO {po_id}"


# ---------------------------------------------------------------------------
# Invoice scoping
# ---------------------------------------------------------------------------


async def test_vendor_u1_lists_only_own_invoices(vendor_scoping_env) -> None:
    """U1 invoice list contains only invoices on V1's POs."""
    env = vendor_scoping_env
    # SM submits and accepts PO1, then creates an invoice on it
    await env["client_sm"].post(f"/api/v1/po/{env['po1_id']}/submit")
    await env["client_sm"].post(f"/api/v1/po/{env['po1_id']}/accept")
    create_resp = await env["client_sm"].post(
        "/api/v1/invoices/",
        json={"po_id": env["po1_id"], "line_items": _INVOICE_LINE_ITEMS},
    )
    assert create_resp.status_code == 201
    inv1_id = create_resp.json()["id"]

    # SM submits and accepts PO2, creates invoice on it
    await env["client_sm"].post(f"/api/v1/po/{env['po2_id']}/submit")
    await env["client_sm"].post(f"/api/v1/po/{env['po2_id']}/accept")
    create_resp2 = await env["client_sm"].post(
        "/api/v1/invoices/",
        json={"po_id": env["po2_id"], "line_items": _INVOICE_LINE_ITEMS},
    )
    assert create_resp2.status_code == 201
    inv2_id = create_resp2.json()["id"]

    # U1 sees only V1 invoice
    list_resp = await env["client_v1"].get("/api/v1/invoices/")
    assert list_resp.status_code == 200
    inv_ids = [item["id"] for item in list_resp.json()["items"]]
    assert inv1_id in inv_ids, "V1's invoice must appear in U1's invoice list"
    assert inv2_id not in inv_ids, "V2's invoice must not appear in U1's invoice list"


async def test_vendor_u1_cannot_get_v2_invoice(vendor_scoping_env) -> None:
    """U1 direct fetch of an invoice on V2's PO returns 404."""
    env = vendor_scoping_env
    # Prepare PO2 invoice via SM
    await env["client_sm"].post(f"/api/v1/po/{env['po2_id']}/submit")
    await env["client_sm"].post(f"/api/v1/po/{env['po2_id']}/accept")
    create_resp = await env["client_sm"].post(
        "/api/v1/invoices/",
        json={"po_id": env["po2_id"], "line_items": _INVOICE_LINE_ITEMS},
    )
    assert create_resp.status_code == 201
    inv2_id = create_resp.json()["id"]

    resp = await env["client_v1"].get(f"/api/v1/invoices/{inv2_id}")
    assert resp.status_code == 404


async def test_vendor_u1_cannot_create_invoice_on_v2_po(vendor_scoping_env) -> None:
    """U1 attempt to create invoice on V2's PO returns 404."""
    env = vendor_scoping_env
    # Accept PO2 as SM so it passes the status guard before vendor check
    await env["client_sm"].post(f"/api/v1/po/{env['po2_id']}/submit")
    await env["client_sm"].post(f"/api/v1/po/{env['po2_id']}/accept")

    resp = await env["client_v1"].post(
        "/api/v1/invoices/",
        json={"po_id": env["po2_id"], "line_items": _INVOICE_LINE_ITEMS},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Milestone scoping
# ---------------------------------------------------------------------------


async def test_vendor_u1_cannot_list_milestones_for_v2_po(vendor_scoping_env) -> None:
    """U1 milestone list on V2's PO returns 404."""
    env = vendor_scoping_env
    resp = await env["client_v1"].get(f"/api/v1/po/{env['po2_id']}/milestones")
    assert resp.status_code == 404


async def test_vendor_u1_cannot_post_milestone_on_v2_po(vendor_scoping_env) -> None:
    """U1 attempt to post a milestone on V2's PO returns 404."""
    env = vendor_scoping_env
    resp = await env["client_v1"].post(
        f"/api/v1/po/{env['po2_id']}/milestones",
        json={"milestone": "PRODUCTION_STARTED"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Activity scoping
# ---------------------------------------------------------------------------


async def test_vendor_u1_activity_scoped(vendor_scoping_env) -> None:
    """U1's activity feed contains only events associated with V1."""
    env = vendor_scoping_env
    # Generate activity on both POs by submitting them as SM
    await env["client_sm"].post(f"/api/v1/po/{env['po1_id']}/submit")
    await env["client_sm"].post(f"/api/v1/po/{env['po2_id']}/submit")

    resp = await env["client_v1"].get("/api/v1/activity/")
    assert resp.status_code == 200
    events = resp.json()
    # All events in the list must be associated with V1's PO
    for event in events:
        assert event["entity_id"] != env["po2_id"], (
            f"V2's PO event must not appear in U1's activity feed: {event}"
        )


async def test_vendor_u1_unread_count_scoped(vendor_scoping_env) -> None:
    """U1's unread count reflects only V1 events."""
    env = vendor_scoping_env
    # Generate activity on V1 PO only
    await env["client_sm"].post(f"/api/v1/po/{env['po1_id']}/submit")

    resp_v1 = await env["client_v1"].get("/api/v1/activity/unread-count")
    assert resp_v1.status_code == 200
    v1_count = resp_v1.json()["count"]

    # Generate activity on V2 PO; V1's count must not increase
    await env["client_sm"].post(f"/api/v1/po/{env['po2_id']}/submit")

    resp_v1_after = await env["client_v1"].get("/api/v1/activity/unread-count")
    assert resp_v1_after.status_code == 200
    assert resp_v1_after.json()["count"] == v1_count, (
        "U1's unread count must not increase when V2 PO receives activity"
    )


# ---------------------------------------------------------------------------
# Dashboard scoping
# ---------------------------------------------------------------------------


async def test_vendor_dashboard_scoped(vendor_scoping_env) -> None:
    """U1's dashboard PO count reflects only V1 data."""
    env = vendor_scoping_env
    resp_v1 = await env["client_v1"].get("/api/v1/dashboard/")
    assert resp_v1.status_code == 200

    resp_sm = await env["client_sm"].get("/api/v1/dashboard/")
    assert resp_sm.status_code == 200

    v1_total = sum(
        entry["count"] for entry in resp_v1.json()["po_summary"]
    )
    sm_total = sum(
        entry["count"] for entry in resp_sm.json()["po_summary"]
    )
    # SM sees both POs; U1 sees only their own
    assert v1_total < sm_total, (
        "V1's dashboard PO total must be less than SM's (which includes both vendors)"
    )
    assert v1_total == 1, "V1's dashboard must reflect exactly 1 PO"


