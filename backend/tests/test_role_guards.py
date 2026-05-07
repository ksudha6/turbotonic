from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import patch

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from src.activity_repository import ActivityLogRepository
from src.auth.session import COOKIE_NAME, create_session_cookie
from src.db import get_db
from src.domain.user import User, UserRole
from src.invoice_repository import InvoiceRepository
from src.main import app
from src.milestone_repository import MilestoneRepository
from src.product_repository import ProductRepository
from src.repository import PurchaseOrderRepository
from src.routers.activity import get_activity_repo as activity_get_activity_repo
from src.routers.auth import get_activity_repo as auth_get_activity_repo
from src.routers.auth import get_user_repo as auth_get_user_repo
from src.routers.dashboard import get_activity_repo as dash_get_activity_repo
from src.routers.dashboard import get_invoice_repo as dash_get_invoice_repo
from src.routers.dashboard import get_milestone_repo as dash_get_milestone_repo
from src.routers.dashboard import get_repo as dash_get_repo
from src.routers.dashboard import get_user_repo as dash_get_user_repo
from src.routers.dashboard import get_vendor_repo as dash_get_vendor_repo
from src.routers.invoice import get_activity_repo as invoice_get_activity_repo
from src.routers.invoice import get_invoice_repo as invoice_get_invoice_repo
from src.routers.invoice import get_po_repo as invoice_get_po_repo
from src.routers.invoice import get_user_repo as invoice_get_user_repo
from src.routers.invoice import get_vendor_repo as invoice_get_vendor_repo
from src.routers.milestone import get_activity_repo as milestone_get_activity_repo
from src.routers.milestone import get_milestone_repo as milestone_get_milestone_repo
from src.routers.milestone import get_po_repo as milestone_get_po_repo
from src.routers.product import get_product_repo as product_get_product_repo
from src.brand_repository import BrandRepository
from src.domain.brand import Brand
from src.routers.brands import (
    get_brand_repo as brands_get_brand_repo,
    get_vendor_repo_for_brands as brands_get_vendor_repo,
    get_activity_repo_for_brands as brands_get_activity_repo,
)
from src.routers.purchase_order import get_activity_repo as po_get_activity_repo
from src.routers.purchase_order import get_brand_repo as po_get_brand_repo
from src.routers.purchase_order import get_invoice_repo as po_get_invoice_repo
from src.routers.purchase_order import get_repo
from src.routers.purchase_order import get_user_repo as po_get_user_repo
from src.routers.purchase_order import get_vendor_repo as po_get_vendor_repo
from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo
from src.schema import init_db
from src.user_repository import UserRepository
from src.vendor_repository import VendorRepository

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)

pytestmark = pytest.mark.asyncio

_PO_PAYLOAD = {
    "vendor_id": "x",
    "po_type": "PROCUREMENT",
    "buyer_name": "B",
    "buyer_country": "US",
    "ship_to_address": "A",
    "payment_terms": "NET30",
    "currency": "USD",
    "issued_date": "2026-04-15T00:00:00Z",
    "required_delivery_date": "2026-05-15T00:00:00Z",
    "terms_and_conditions": "T",
    "incoterm": "FOB",
    "port_of_loading": "CNSHA",
    "port_of_discharge": "USLAX",
    "country_of_origin": "CN",
    "country_of_destination": "US",
    "line_items": [
        {
            "part_number": "P1",
            "description": "D",
            "quantity": 10,
            "uom": "PCS",
            "unit_price": "1.00",
            "hs_code": "7318.15",
            "country_of_origin": "CN",
        }
    ],
}


async def _make_client_with_role(
    role: UserRole, vendor_id: str | None = None
) -> AsyncIterator[tuple[AsyncClient, asyncpg.Connection]]:
    """Async generator that yields (client, conn) authenticated as the given role."""
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    if role is UserRole.VENDOR:
        if vendor_id is None:
            # Create a real vendor to satisfy the FK constraint
            from src.domain.vendor import Vendor, VendorType
            v = Vendor.create(name="Test Vendor Co", country="CN", vendor_type=VendorType.PROCUREMENT)
            from src.vendor_repository import VendorRepository as VR
            await VR(conn).save(v)
            vendor_id = v.id
        user = User.create(
            username=f"test-{role.value.lower()}",
            display_name=f"Test {role.value}",
            role=role,
            vendor_id=vendor_id,
        )
    else:
        user = User.create(
            username=f"test-{role.value.lower()}",
            display_name=f"Test {role.value}",
            role=role,
        )

    repo = UserRepository(conn)
    await repo.save(user)

    cookie_value = create_session_cookie(user.id)
    cookies = {COOKIE_NAME: cookie_value}

    async def override_get_repo() -> AsyncIterator[PurchaseOrderRepository]:
        yield PurchaseOrderRepository(conn)

    async def override_get_vendor_repo() -> AsyncIterator[VendorRepository]:
        yield VendorRepository(conn)

    async def override_get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
        yield InvoiceRepository(conn)

    async def override_get_milestone_repo() -> AsyncIterator[MilestoneRepository]:
        yield MilestoneRepository(conn)

    async def override_get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
        yield ActivityLogRepository(conn)

    async def override_get_product_repo() -> AsyncIterator[ProductRepository]:
        yield ProductRepository(conn)

    async def override_get_user_repo() -> AsyncIterator[UserRepository]:
        yield UserRepository(conn)

    async def override_get_brand_repo() -> AsyncIterator[BrandRepository]:
        yield BrandRepository(conn)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    app.dependency_overrides[get_repo] = override_get_repo
    app.dependency_overrides[po_get_brand_repo] = override_get_brand_repo
    app.dependency_overrides[po_get_user_repo] = override_get_user_repo
    app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[brands_get_brand_repo] = override_get_brand_repo
    app.dependency_overrides[brands_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[brands_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[po_get_invoice_repo] = override_get_invoice_repo
    app.dependency_overrides[po_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[vendor_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[dash_get_repo] = override_get_repo
    app.dependency_overrides[dash_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[dash_get_invoice_repo] = override_get_invoice_repo
    app.dependency_overrides[dash_get_milestone_repo] = override_get_milestone_repo
    app.dependency_overrides[dash_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[dash_get_user_repo] = override_get_user_repo
    app.dependency_overrides[invoice_get_invoice_repo] = override_get_invoice_repo
    app.dependency_overrides[invoice_get_user_repo] = override_get_user_repo
    app.dependency_overrides[invoice_get_po_repo] = override_get_repo
    app.dependency_overrides[invoice_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[invoice_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[milestone_get_milestone_repo] = override_get_milestone_repo
    app.dependency_overrides[milestone_get_po_repo] = override_get_repo
    app.dependency_overrides[milestone_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[activity_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[product_get_product_repo] = override_get_product_repo
    app.dependency_overrides[auth_get_user_repo] = override_get_user_repo
    app.dependency_overrides[auth_get_activity_repo] = override_get_activity_repo

    transport = ASGITransport(app=app)
    with patch("src.routers.purchase_order.get_db", _test_get_db), \
         patch("src.routers.product.get_db", _test_get_db), \
         patch("src.auth.middleware.get_db", _test_get_db):
        async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as ac:
            yield ac, conn

    await tx.rollback()
    await conn.close()
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 401 tests -- unauthenticated requests
# ---------------------------------------------------------------------------


async def test_unauthenticated_returns_401(client: AsyncClient) -> None:
    for url in [
        "/api/v1/po/",
        "/api/v1/vendors/",
        "/api/v1/products/",
        "/api/v1/dashboard/",
        "/api/v1/reference-data/",
    ]:
        resp = await client.get(url)
        assert resp.status_code == 401, (
            f"expected 401 for GET {url}, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# SM role tests
# ---------------------------------------------------------------------------


async def test_sm_can_create_vendor() -> None:
    async for ac, conn in _make_client_with_role(UserRole.SM):
        resp = await ac.post(
            "/api/v1/vendors/",
            json={"name": "Test Vendor", "country": "CN", "vendor_type": "PROCUREMENT"},
        )
        assert resp.status_code == 201


async def test_sm_can_create_po() -> None:
    async for ac, conn in _make_client_with_role(UserRole.SM):
        v = await ac.post(
            "/api/v1/vendors/",
            json={"name": "V", "country": "CN", "vendor_type": "PROCUREMENT"},
        )
        assert v.status_code == 201
        vid = v.json()["id"]
        # Brand creation requires ADMIN role; use domain+repository directly.
        brand = Brand.create(name="RoleGuardBrand", legal_name="RoleGuard Brand LLC", address="1 Guard Ave", country="US")
        await BrandRepository(conn).save(brand)
        await BrandRepository(conn).assign_vendor(brand.id, vid)
        payload = {**_PO_PAYLOAD, "vendor_id": vid, "brand_id": brand.id}
        resp = await ac.post("/api/v1/po/", json=payload)
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# VENDOR role tests
# ---------------------------------------------------------------------------


async def test_vendor_cannot_create_po() -> None:
    async for ac, conn in _make_client_with_role(UserRole.VENDOR):
        resp = await ac.post("/api/v1/po/", json=_PO_PAYLOAD)
        assert resp.status_code == 403


async def test_vendor_cannot_create_vendor() -> None:
    async for ac, conn in _make_client_with_role(UserRole.VENDOR):
        resp = await ac.post(
            "/api/v1/vendors/",
            json={"name": "V", "country": "CN", "vendor_type": "PROCUREMENT"},
        )
        assert resp.status_code == 403


async def test_vendor_cannot_create_product() -> None:
    async for ac, conn in _make_client_with_role(UserRole.VENDOR):
        resp = await ac.post(
            "/api/v1/products/",
            json={"vendor_id": "x", "part_number": "P", "description": "D"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# FREIGHT_MANAGER role tests
# ---------------------------------------------------------------------------


async def test_freight_manager_can_list_invoices() -> None:
    async for ac, conn in _make_client_with_role(UserRole.FREIGHT_MANAGER):
        resp = await ac.get("/api/v1/invoices/")
        assert resp.status_code == 200


async def test_freight_manager_cannot_create_po() -> None:
    async for ac, conn in _make_client_with_role(UserRole.FREIGHT_MANAGER):
        resp = await ac.post("/api/v1/po/", json=_PO_PAYLOAD)
        assert resp.status_code == 403


async def test_freight_manager_cannot_create_vendor() -> None:
    async for ac, conn in _make_client_with_role(UserRole.FREIGHT_MANAGER):
        resp = await ac.post(
            "/api/v1/vendors/",
            json={"name": "V", "country": "CN", "vendor_type": "PROCUREMENT"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# QUALITY_LAB role tests
# ---------------------------------------------------------------------------


async def test_quality_lab_can_list_products() -> None:
    async for ac, conn in _make_client_with_role(UserRole.QUALITY_LAB):
        resp = await ac.get("/api/v1/products/")
        assert resp.status_code == 200


async def test_quality_lab_cannot_create_vendor() -> None:
    async for ac, conn in _make_client_with_role(UserRole.QUALITY_LAB):
        resp = await ac.post(
            "/api/v1/vendors/",
            json={"name": "V", "country": "CN", "vendor_type": "PROCUREMENT"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# ADMIN role tests
# ---------------------------------------------------------------------------


async def test_admin_can_call_any_endpoint() -> None:
    async for ac, conn in _make_client_with_role(UserRole.ADMIN):
        resp = await ac.get("/api/v1/dashboard/")
        assert resp.status_code == 200
        resp = await ac.get("/api/v1/vendors/")
        assert resp.status_code == 200
        resp = await ac.get("/api/v1/products/")
        assert resp.status_code == 200
        resp = await ac.get("/api/v1/reference-data/")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# require_auth: any authenticated role can access read-only aggregates
# ---------------------------------------------------------------------------


async def test_any_role_can_access_dashboard() -> None:
    for role in [UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER, UserRole.QUALITY_LAB]:
        async for ac, conn in _make_client_with_role(role):
            resp = await ac.get("/api/v1/dashboard/")
            assert resp.status_code == 200, f"{role.value} must access dashboard"


async def test_any_role_can_access_reference_data() -> None:
    for role in [UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER, UserRole.QUALITY_LAB]:
        async for ac, conn in _make_client_with_role(role):
            resp = await ac.get("/api/v1/reference-data/")
            assert resp.status_code == 200, f"{role.value} must access reference-data"


# ---------------------------------------------------------------------------
# Invite guard: only ADMIN can invite
# ---------------------------------------------------------------------------


async def test_sm_cannot_invite_users() -> None:
    async for ac, conn in _make_client_with_role(UserRole.SM):
        resp = await ac.post(
            "/api/v1/users/invite",
            json={"username": "x", "display_name": "X", "role": "SM"},
        )
        assert resp.status_code == 403
