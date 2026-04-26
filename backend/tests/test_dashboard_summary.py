from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import AsyncIterator
from unittest.mock import patch

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from src.activity_repository import ActivityLogRepository
from src.auth.session import COOKIE_NAME, create_session_cookie
from src.certificate_repository import CertificateRepository
from src.domain.user import User, UserRole
from src.domain.vendor import Vendor, VendorType
from src.invoice_repository import InvoiceRepository
from src.main import app
from src.milestone_repository import MilestoneRepository
from src.qualification_type_repository import QualificationTypeRepository
from src.product_repository import ProductRepository
from src.repository import PurchaseOrderRepository
from src.routers.activity import get_activity_repo as activity_get_activity_repo
from src.routers.auth import get_user_repo as auth_get_user_repo
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
from src.routers.milestone import get_milestone_repo as milestone_get_milestone_repo
from src.routers.milestone import get_po_repo as milestone_get_po_repo
from src.routers.purchase_order import get_activity_repo as po_get_activity_repo
from src.routers.purchase_order import get_cert_repo as po_get_cert_repo
from src.routers.purchase_order import get_email_service as po_get_email_service
from src.routers.purchase_order import get_invoice_repo as po_get_invoice_repo
from src.routers.purchase_order import get_notification_dispatcher as po_get_notification_dispatcher
from src.routers.purchase_order import get_product_repo as po_get_product_repo
from src.routers.purchase_order import get_qualification_repo as po_get_qualification_repo
from src.routers.purchase_order import get_repo
from src.routers.purchase_order import get_vendor_repo as po_get_vendor_repo
from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo
from src.schema import init_db
from src.services.email import RenderedEmail, render_email
from src.services.notifications import NotificationDispatcher
from src.user_repository import UserRepository
from src.vendor_repository import VendorRepository

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)

pytestmark = pytest.mark.asyncio

SUMMARY_URL = "/api/v1/dashboard/summary"


class _FakeEmailService:
    """Stub email service — records calls without sending."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    @property
    def enabled(self) -> bool:
        return True

    def render(self, template_name: str, context: dict) -> RenderedEmail:
        return render_email(template_name, context)

    async def send(self, to: list[str], subject: str, body_html: str, body_text: str) -> None:
        self.calls.append((to, subject))


def _setup_overrides(conn: asyncpg.Connection) -> None:
    fake_email = _FakeEmailService()

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

    async def override_get_cert_repo() -> AsyncIterator[CertificateRepository]:
        yield CertificateRepository(conn)

    async def override_get_qt_repo() -> AsyncIterator[QualificationTypeRepository]:
        yield QualificationTypeRepository(conn)

    async def override_get_user_repo() -> AsyncIterator[UserRepository]:
        yield UserRepository(conn)

    def override_get_email_service() -> _FakeEmailService:
        return fake_email

    async def override_get_notification_dispatcher() -> AsyncIterator[NotificationDispatcher]:
        yield NotificationDispatcher(
            email_service=fake_email,  # type: ignore[arg-type]
            user_repo=UserRepository(conn),
            activity_repo=ActivityLogRepository(conn),
        )

    app.dependency_overrides[get_repo] = override_get_repo
    app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[po_get_invoice_repo] = override_get_invoice_repo
    app.dependency_overrides[po_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[po_get_product_repo] = override_get_product_repo
    app.dependency_overrides[po_get_qualification_repo] = override_get_qt_repo
    app.dependency_overrides[po_get_cert_repo] = override_get_cert_repo
    app.dependency_overrides[po_get_email_service] = override_get_email_service
    app.dependency_overrides[po_get_notification_dispatcher] = override_get_notification_dispatcher
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
    app.dependency_overrides[milestone_get_milestone_repo] = override_get_milestone_repo
    app.dependency_overrides[milestone_get_po_repo] = override_get_repo
    app.dependency_overrides[milestone_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[activity_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[auth_get_user_repo] = override_get_user_repo


@asynccontextmanager
async def _client_ctx(
    role: UserRole, vendor_id: str | None = None
) -> AsyncIterator[tuple[AsyncClient, asyncpg.Connection]]:
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    _setup_overrides(conn)

    # Create user for the given role
    if role is UserRole.VENDOR:
        if vendor_id is None:
            v = Vendor.create(name="Vendor For Role", country="CN", vendor_type=VendorType.PROCUREMENT)
            await VendorRepository(conn).save(v)
            vendor_id = v.id
        user = User.create(
            username=f"test-{role.value.lower()}-summary",
            display_name=f"Test {role.value}",
            role=role,
            vendor_id=vendor_id,
        )
    else:
        user = User.create(
            username=f"test-{role.value.lower()}-summary",
            display_name=f"Test {role.value}",
            role=role,
        )

    await UserRepository(conn).save(user)
    cookie_value = create_session_cookie(user.id)
    cookies = {COOKIE_NAME: cookie_value}

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    with patch("src.routers.purchase_order.get_db", _test_get_db), \
         patch("src.routers.product.get_db", _test_get_db), \
         patch("src.auth.middleware.get_db", _test_get_db):
        async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as ac:
            yield ac, conn

    await tx.rollback()
    await conn.close()
    app.dependency_overrides.clear()


async def _seed_vendor(client: AsyncClient, name: str = "Test Vendor") -> dict:
    resp = await client.post(
        "/api/v1/vendors/",
        json={"name": name, "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _seed_procurement_po(client: AsyncClient, vendor_id: str) -> dict:
    body = {
        "vendor_id": vendor_id,
        "po_type": "PROCUREMENT",
        "buyer_name": "TurboTonic Ltd",
        "buyer_country": "US",
        "ship_to_address": "123 Main St",
        "payment_terms": "TT",
        "currency": "USD",
        "issued_date": "2026-03-24T00:00:00+00:00",
        "required_delivery_date": "2026-04-24T00:00:00+00:00",
        "terms_and_conditions": "Standard terms",
        "incoterm": "FOB",
        "port_of_loading": "CNSHA",
        "port_of_discharge": "USLAX",
        "country_of_origin": "CN",
        "country_of_destination": "US",
        "line_items": [
            {
                "part_number": "P1",
                "description": "Part",
                "quantity": 10,
                "uom": "PCS",
                "unit_price": "100.00",
                "hs_code": "8471",
                "country_of_origin": "CN",
            }
        ],
    }
    resp = await client.post("/api/v1/po/", json=body)
    assert resp.status_code == 201
    return resp.json()


async def _seed_opex_vendor(client: AsyncClient, name: str = "Opex Vendor") -> dict:
    """Create an OPEX vendor."""
    resp = await client.post(
        "/api/v1/vendors/",
        json={"name": name, "country": "CN", "vendor_type": "OPEX"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _seed_opex_po(client: AsyncClient, vendor_id: str) -> dict:
    """Create an OPEX PO. vendor_id must belong to an OPEX vendor."""
    body = {
        "vendor_id": vendor_id,
        "po_type": "OPEX",
        "buyer_name": "TurboTonic Ltd",
        "buyer_country": "US",
        "ship_to_address": "123 Main St",
        "payment_terms": "TT",
        "currency": "USD",
        "issued_date": "2026-03-24T00:00:00+00:00",
        "required_delivery_date": "2026-04-24T00:00:00+00:00",
        "terms_and_conditions": "Standard terms",
        "incoterm": "FOB",
        "port_of_loading": "CNSHA",
        "port_of_discharge": "USLAX",
        "country_of_origin": "CN",
        "country_of_destination": "US",
        "line_items": [
            {
                "part_number": "P2",
                "description": "Opex Part",
                "quantity": 5,
                "uom": "PCS",
                "unit_price": "200.00",
                "hs_code": "8471",
                "country_of_origin": "CN",
            }
        ],
    }
    resp = await client.post("/api/v1/po/", json=body)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


async def _seed_freight_vendor(client: AsyncClient, name: str = "Freight Vendor") -> dict:
    """Create a FREIGHT vendor."""
    resp = await client.post(
        "/api/v1/vendors/",
        json={"name": name, "country": "DE", "vendor_type": "FREIGHT"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _submit_and_accept_po(client: AsyncClient, po_id: str) -> None:
    """Submit then accept a PO via the API."""
    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200
    accept_resp = await client.post(f"/api/v1/po/{po_id}/accept")
    assert accept_resp.status_code == 200


async def _post_milestones_up_to(
    client: AsyncClient, po_id: str, target: str
) -> None:
    """Post milestones in sequence up to and including target."""
    order = ["RAW_MATERIALS", "PRODUCTION_STARTED", "QC_PASSED", "READY_FOR_SHIPMENT", "SHIPPED"]
    for ms in order:
        resp = await client.post(
            f"/api/v1/po/{po_id}/milestones", json={"milestone": ms}
        )
        assert resp.status_code == 201
        if ms == target:
            break


async def _create_and_submit_invoice(
    client: AsyncClient, po_id: str, part_number: str, quantity: int
) -> dict:
    """Create an invoice and submit it; return the invoice JSON."""
    create_resp = await client.post(
        "/api/v1/invoices/",
        json={"po_id": po_id, "line_items": [{"part_number": part_number, "quantity": quantity}]},
    )
    assert create_resp.status_code == 201
    inv = create_resp.json()
    submit_resp = await client.post(f"/api/v1/invoices/{inv['id']}/submit")
    assert submit_resp.status_code == 200
    return submit_resp.json()


async def test_admin_sees_global_kpis_and_activity() -> None:
    async with _client_ctx(UserRole.ADMIN) as (ac, _conn):
        vendor = await _seed_vendor(ac, "AdminVendor")
        vendor_id = vendor["id"]

        # Create procurement POs so pending_pos >= 1
        await _seed_procurement_po(ac, vendor_id)
        await _seed_procurement_po(ac, vendor_id)

        resp = await ac.get(SUMMARY_URL)
        assert resp.status_code == 200

        data = resp.json()

        # ADMIN/SM roles must not receive FM fields
        assert data["fm_kpis"] is None
        assert data["fm_ready_batches"] == []
        assert data["fm_pending_invoices"] == []

        kpis = data["kpis"]
        # All seven KPI keys present (counts + per-KPI USD values + outstanding A/P)
        assert set(kpis.keys()) == {
            "pending_pos",
            "pending_pos_value_usd",
            "awaiting_acceptance",
            "awaiting_acceptance_value_usd",
            "in_production",
            "in_production_value_usd",
            "outstanding_ap_usd",
        }
        assert isinstance(kpis["pending_pos"], int)
        assert isinstance(kpis["awaiting_acceptance"], int)
        assert isinstance(kpis["in_production"], int)
        assert isinstance(kpis["outstanding_ap_usd"], str)
        assert isinstance(kpis["pending_pos_value_usd"], str)
        assert isinstance(kpis["awaiting_acceptance_value_usd"], str)
        assert isinstance(kpis["in_production_value_usd"], str)

        # DRAFT POs count as pending — two were created
        assert kpis["pending_pos"] >= 1
        # USD value follows the count
        assert Decimal(kpis["pending_pos_value_usd"]) > Decimal("0")

        # Lists present
        assert isinstance(data["awaiting_acceptance"], list)
        assert isinstance(data["activity"], list)

        # Capped at their limits
        assert len(data["activity"]) <= 20
        assert len(data["awaiting_acceptance"]) <= 10

        # Activity exclusion: no excluded events in the dashboard feed
        excluded = {
            "PO_LINE_MODIFIED",
            "PO_LINE_ACCEPTED",
            "PO_LINE_REMOVED",
            "PO_FORCE_ACCEPTED",
            "PO_FORCE_REMOVED",
            "PO_CONVERGED",
            "EMAIL_SEND_FAILED",
        }
        for entry in data["activity"]:
            assert entry["event"] not in excluded


async def test_sm_scopes_to_procurement() -> None:
    async with _client_ctx(UserRole.SM) as (sm_ac, conn):
        # Also create an ADMIN user in the same transaction so the admin request
        # sees the same seeded data.
        admin_user = User.create(
            username="test-admin-summary-scoping",
            display_name="Test Admin",
            role=UserRole.ADMIN,
        )
        await UserRepository(conn).save(admin_user)
        admin_cookie = create_session_cookie(admin_user.id)

        proc_vendor = await _seed_vendor(sm_ac, "ScopingProcurementVendor")
        proc_vendor_id = proc_vendor["id"]
        opex_vendor = await _seed_opex_vendor(sm_ac, "ScopingOpexVendor")
        opex_vendor_id = opex_vendor["id"]

        # One PROCUREMENT PO and one OPEX PO (vendor types must match PO types)
        await _seed_procurement_po(sm_ac, proc_vendor_id)
        await _seed_opex_po(sm_ac, opex_vendor_id)

        sm_resp = await sm_ac.get(SUMMARY_URL)
        assert sm_resp.status_code == 200
        sm_data = sm_resp.json()

        # Make an admin request reusing the same transport/conn/overrides
        @asynccontextmanager
        async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
            yield conn

        transport = ASGITransport(app=app)
        with patch("src.routers.purchase_order.get_db", _test_get_db), \
             patch("src.routers.product.get_db", _test_get_db), \
             patch("src.auth.middleware.get_db", _test_get_db):
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                cookies={COOKIE_NAME: admin_cookie},
            ) as admin_ac:
                admin_resp = await admin_ac.get(SUMMARY_URL)

        assert admin_resp.status_code == 200
        admin_data = admin_resp.json()

        sm_kpis = sm_data["kpis"]
        admin_kpis = admin_data["kpis"]

        # SM must not receive FM fields
        assert sm_data["fm_kpis"] is None
        assert sm_data["fm_ready_batches"] == []
        assert sm_data["fm_pending_invoices"] == []

        # SM counts must be a subset of ADMIN counts (SM = PROCUREMENT only)
        assert sm_kpis["pending_pos"] <= admin_kpis["pending_pos"]
        assert sm_kpis["awaiting_acceptance"] <= admin_kpis["awaiting_acceptance"]
        assert sm_kpis["in_production"] <= admin_kpis["in_production"]
        assert Decimal(sm_kpis["outstanding_ap_usd"]) <= Decimal(admin_kpis["outstanding_ap_usd"])

        # With PROCUREMENT (1) + OPEX (1), ADMIN sees 2, SM sees 1
        assert admin_kpis["pending_pos"] > sm_kpis["pending_pos"]


async def test_vendor_returns_empty_payload() -> None:
    async with _client_ctx(UserRole.VENDOR) as (ac, _conn):
        resp = await ac.get(SUMMARY_URL)
        assert resp.status_code == 200

        data = resp.json()
        kpis = data["kpis"]

        assert kpis["pending_pos"] == 0
        assert kpis["pending_pos_value_usd"] == "0.00"
        assert kpis["awaiting_acceptance"] == 0
        assert kpis["awaiting_acceptance_value_usd"] == "0.00"
        assert kpis["in_production"] == 0
        assert kpis["in_production_value_usd"] == "0.00"
        assert kpis["outstanding_ap_usd"] == "0.00"
        assert data["awaiting_acceptance"] == []
        assert data["activity"] == []
        # VENDOR role must not receive FM fields
        assert data["fm_kpis"] is None
        assert data["fm_ready_batches"] == []
        assert data["fm_pending_invoices"] == []


async def test_unauthenticated_returns_401(client: AsyncClient) -> None:
    resp = await client.get(SUMMARY_URL)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# FREIGHT_MANAGER tests
# ---------------------------------------------------------------------------


async def test_fm_sees_shipment_and_invoice_kpis() -> None:
    async with _client_ctx(UserRole.FREIGHT_MANAGER) as (ac, _conn):
        resp = await ac.get(SUMMARY_URL)
        assert resp.status_code == 200

        data = resp.json()

        # FM-specific fields populated
        assert data["fm_kpis"] is not None
        fm_kpis = data["fm_kpis"]
        assert set(fm_kpis.keys()) == {
            "ready_batches",
            "shipments_in_flight",
            "pending_invoices",
            "pending_invoices_value_usd",
            "docs_missing",
        }
        assert isinstance(fm_kpis["ready_batches"], int)
        assert isinstance(fm_kpis["shipments_in_flight"], int)
        assert fm_kpis["shipments_in_flight"] >= 0
        assert isinstance(fm_kpis["pending_invoices"], int)
        assert isinstance(fm_kpis["pending_invoices_value_usd"], str)
        # pending_invoices_value_usd is a decimal string
        Decimal(fm_kpis["pending_invoices_value_usd"])

        assert isinstance(data["fm_ready_batches"], list)
        assert isinstance(data["fm_pending_invoices"], list)

        # ADMIN-style KPI block is all zeros for FM
        kpis = data["kpis"]
        assert kpis["pending_pos"] == 0
        assert kpis["pending_pos_value_usd"] == "0.00"
        assert kpis["awaiting_acceptance"] == 0
        assert kpis["awaiting_acceptance_value_usd"] == "0.00"
        assert kpis["in_production"] == 0
        assert kpis["in_production_value_usd"] == "0.00"
        assert kpis["outstanding_ap_usd"] == "0.00"
        assert data["awaiting_acceptance"] == []


