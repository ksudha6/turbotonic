from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import patch

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.activity_repository import ActivityLogRepository
from src.auth.session import COOKIE_NAME, create_session_cookie
from src.certificate_repository import CertificateRepository
from src.db import get_db
from src.document_repository import DocumentRepository
from src.domain.user import User, UserRole
from src.invoice_repository import InvoiceRepository
from src.main import app
from src.milestone_repository import MilestoneRepository
from src.repository import PurchaseOrderRepository
from src.shipment_repository import ShipmentRepository
from src.routers.activity import get_activity_repo as activity_get_activity_repo
from src.routers.auth import get_user_repo as auth_get_user_repo
from src.routers.certificate import get_activity_repo_for_cert as cert_get_activity_repo
from src.routers.certificate import get_cert_repo
from src.routers.certificate import get_document_repo_for_cert as cert_get_document_repo
from src.routers.certificate import get_file_storage_for_cert as cert_get_file_storage
from src.routers.certificate import get_product_repo_for_cert as cert_get_product_repo
from src.routers.certificate import get_qt_repo_for_cert as cert_get_qt_repo
from src.routers.dashboard import get_activity_repo as dash_get_activity_repo
from src.routers.dashboard import get_invoice_repo as dash_get_invoice_repo
from src.routers.dashboard import get_milestone_repo as dash_get_milestone_repo
from src.routers.dashboard import get_repo as dash_get_repo
from src.routers.dashboard import get_vendor_repo as dash_get_vendor_repo
from src.routers.document import get_document_repo as document_get_document_repo
from src.routers.document import get_file_storage as document_get_file_storage
from src.routers.invoice import get_activity_repo as invoice_get_activity_repo
from src.routers.invoice import get_invoice_repo as invoice_get_invoice_repo
from src.routers.invoice import get_po_repo as invoice_get_po_repo
from src.routers.invoice import get_vendor_repo as invoice_get_vendor_repo
from src.routers.milestone import get_activity_repo as milestone_get_activity_repo
from src.routers.milestone import get_cert_repo as milestone_get_cert_repo
from src.routers.milestone import get_milestone_repo as milestone_get_milestone_repo
from src.routers.milestone import get_po_repo as milestone_get_po_repo
from src.routers.milestone import get_product_repo as milestone_get_product_repo
from src.routers.milestone import get_qualification_repo as milestone_get_qualification_repo
from src.routers.purchase_order import get_activity_repo as po_get_activity_repo
from src.routers.purchase_order import get_cert_repo as po_get_cert_repo
from src.routers.purchase_order import get_email_service as po_get_email_service
from src.routers.purchase_order import get_invoice_repo as po_get_invoice_repo
from src.routers.purchase_order import get_notification_dispatcher as po_get_notification_dispatcher
from src.routers.purchase_order import get_product_repo as po_get_product_repo
from src.routers.purchase_order import get_qualification_repo as po_get_qualification_repo
from src.routers.purchase_order import get_repo
from src.routers.purchase_order import get_vendor_repo as po_get_vendor_repo
from src.routers.product import get_product_repo as product_get_product_repo
from src.routers.packaging import get_packaging_repo as packaging_get_packaging_repo
from src.routers.packaging import get_product_repo_for_packaging as packaging_get_product_repo
from src.routers.packaging import get_document_repo_for_packaging as packaging_get_document_repo
from src.routers.packaging import get_file_storage_for_packaging as packaging_get_file_storage
from src.routers.packaging import get_activity_repo_for_packaging as packaging_get_activity_repo
from src.routers.product import get_packaging_repo_for_product as product_get_packaging_repo
from src.routers.qualification_type import get_qt_repo as qt_get_qt_repo
from src.routers.shipment import (
    get_shipment_repo,
    get_po_repo_for_shipment as shipment_get_po_repo,
    get_vendor_repo_for_shipment as shipment_get_vendor_repo,
    get_activity_repo_for_shipment as shipment_get_activity_repo,
    get_cert_repo_for_shipment as shipment_get_cert_repo,
    get_packaging_repo_for_shipment as shipment_get_packaging_repo,
    get_qt_repo_for_shipment as shipment_get_qt_repo,
    get_document_repo_for_shipment as shipment_get_document_repo,
    get_file_storage_for_shipment as shipment_get_file_storage,
)
from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo
from src.schema import init_db
from src.packaging_repository import PackagingSpecRepository
from src.product_repository import ProductRepository
from src.qualification_type_repository import QualificationTypeRepository
from src.services.email import EmailService, RenderedEmail, render_email
from src.services.file_storage import FileStorageService
from src.services.notifications import NotificationDispatcher
from src.user_repository import UserRepository
from src.vendor_repository import VendorRepository

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)

_current_upload_dir: Path | None = None
_current_fake_email: "FakeEmailService | None" = None


class FakeEmailService:
    """Drop-in replacement for EmailService that records calls.

    Every call to `send` appends a `(to, template_name, context)` tuple to
    `calls` so tests can assert recipient set and template choice without
    any SMTP. The `render` method reuses the real Jinja2 renderer so tests can
    still assert on subject/body content where relevant.
    """

    def __init__(self) -> None:
        # Each entry: (to_list, template_name, context_dict). Public attr so tests
        # can inspect the full log in order.
        self.calls: list[tuple[list[str], str, dict]] = []
        # The last rendered email is stashed so tests that care about subject
        # lines can assert on the rendered form without re-rendering.
        self.last_rendered: RenderedEmail | None = None
        # Send is success-by-default; set to False or raise from `fail_next` to
        # exercise the EMAIL_SEND_FAILED activity-log branch.
        self._raise_on_send: Exception | None = None

    @property
    def enabled(self) -> bool:
        return True

    def render(self, template_name: str, context: dict) -> RenderedEmail:
        rendered = render_email(template_name, context)
        self.last_rendered = rendered
        return rendered

    def fail_next(self, exc: Exception) -> None:
        # Arm the next `send` to raise. Tests use this to drive the
        # EMAIL_SEND_FAILED activity-log path without a real SMTP error.
        self._raise_on_send = exc

    async def send(
        self,
        to: list[str],
        subject: str,
        body_html: str,
        body_text: str,
    ) -> None:
        # Template name is recovered from the subject pattern when callers used
        # `render` earlier; for completeness we accept arbitrary subject/body
        # and tag the record with the current last_rendered template.
        template_name = _subject_to_template(subject)
        ctx: dict = {"subject": subject, "body_text": body_text, "body_html": body_html}
        self.calls.append((list(to), template_name, ctx))
        if self._raise_on_send is not None:
            exc = self._raise_on_send
            self._raise_on_send = None
            raise exc


def _subject_to_template(subject: str) -> str:
    # Reverse of _subject_for in src.services.email. We use the event-summary
    # fragment because the subject template is stable. Tests can also just
    # read the `calls` tuple and assert on the resolved name.
    mapping = {
        "accepted": "po_accepted",
        "modified by counterparty": "po_modified",
        "line modified": "po_line_modified",
        "advance payment recorded": "po_advance_paid",
    }
    for fragment, name in mapping.items():
        if subject.endswith(fragment):
            return name
    return "unknown"


async def _setup_overrides(
    conn: asyncpg.Connection,
    upload_dir: Path,
    fake_email: "FakeEmailService",
) -> None:
    """Register all FastAPI dependency overrides for the given connection."""
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

    async def override_get_packaging_repo() -> AsyncIterator[PackagingSpecRepository]:
        yield PackagingSpecRepository(conn)

    async def override_get_cert_repo() -> AsyncIterator[CertificateRepository]:
        yield CertificateRepository(conn)

    async def override_get_qt_repo() -> AsyncIterator[QualificationTypeRepository]:
        yield QualificationTypeRepository(conn)

    async def override_get_user_repo() -> AsyncIterator[UserRepository]:
        yield UserRepository(conn)

    async def override_get_document_repo() -> AsyncIterator[DocumentRepository]:
        yield DocumentRepository(conn)

    async def override_get_shipment_repo() -> AsyncIterator[ShipmentRepository]:
        yield ShipmentRepository(conn)

    def override_get_file_storage() -> FileStorageService:
        return FileStorageService(upload_dir)

    app.dependency_overrides[get_repo] = override_get_repo
    app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[po_get_invoice_repo] = override_get_invoice_repo
    app.dependency_overrides[po_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[po_get_product_repo] = override_get_product_repo
    app.dependency_overrides[po_get_qualification_repo] = override_get_qt_repo
    app.dependency_overrides[po_get_cert_repo] = override_get_cert_repo
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
    app.dependency_overrides[milestone_get_product_repo] = override_get_product_repo
    app.dependency_overrides[milestone_get_qualification_repo] = override_get_qt_repo
    app.dependency_overrides[milestone_get_cert_repo] = override_get_cert_repo
    app.dependency_overrides[activity_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[product_get_product_repo] = override_get_product_repo
    app.dependency_overrides[packaging_get_packaging_repo] = override_get_packaging_repo
    app.dependency_overrides[packaging_get_product_repo] = override_get_product_repo
    app.dependency_overrides[packaging_get_document_repo] = override_get_document_repo
    app.dependency_overrides[packaging_get_file_storage] = override_get_file_storage
    app.dependency_overrides[packaging_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[product_get_packaging_repo] = override_get_packaging_repo
    app.dependency_overrides[get_cert_repo] = override_get_cert_repo
    app.dependency_overrides[cert_get_product_repo] = override_get_product_repo
    app.dependency_overrides[cert_get_qt_repo] = override_get_qt_repo
    app.dependency_overrides[cert_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[cert_get_document_repo] = override_get_document_repo
    app.dependency_overrides[cert_get_file_storage] = override_get_file_storage
    app.dependency_overrides[qt_get_qt_repo] = override_get_qt_repo
    app.dependency_overrides[auth_get_user_repo] = override_get_user_repo
    app.dependency_overrides[document_get_document_repo] = override_get_document_repo
    app.dependency_overrides[document_get_file_storage] = override_get_file_storage
    app.dependency_overrides[get_shipment_repo] = override_get_shipment_repo
    app.dependency_overrides[shipment_get_po_repo] = override_get_repo
    app.dependency_overrides[shipment_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[shipment_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[shipment_get_cert_repo] = override_get_cert_repo
    app.dependency_overrides[shipment_get_packaging_repo] = override_get_packaging_repo
    app.dependency_overrides[shipment_get_qt_repo] = override_get_qt_repo
    app.dependency_overrides[shipment_get_document_repo] = override_get_document_repo
    app.dependency_overrides[shipment_get_file_storage] = override_get_file_storage

    # Iter 060: route EmailService and NotificationDispatcher DI to the fake so
    # no test hits the network. Dispatcher is built here because it binds the
    # same shared conn as the rest of the overrides.
    def override_get_email_service() -> FakeEmailService:
        return fake_email

    async def override_get_notification_dispatcher() -> AsyncIterator[NotificationDispatcher]:
        yield NotificationDispatcher(
            email_service=fake_email,  # type: ignore[arg-type]
            user_repo=UserRepository(conn),
            activity_repo=ActivityLogRepository(conn),
        )

    app.dependency_overrides[po_get_email_service] = override_get_email_service
    app.dependency_overrides[po_get_notification_dispatcher] = override_get_notification_dispatcher


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Unauthenticated client -- for testing 401/403 behaviour on pre-auth flows."""
    global _current_upload_dir, _current_fake_email
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    upload_dir = Path(tempfile.mkdtemp())
    _current_upload_dir = upload_dir
    fake_email = FakeEmailService()
    _current_fake_email = fake_email
    await _setup_overrides(conn, upload_dir, fake_email)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    with patch("src.routers.purchase_order.get_db", _test_get_db), \
         patch("src.routers.product.get_db", _test_get_db), \
         patch("src.auth.middleware.get_db", _test_get_db):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    await tx.rollback()
    await conn.close()
    app.dependency_overrides.clear()
    shutil.rmtree(upload_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def authenticated_client() -> AsyncIterator[AsyncClient]:
    """Client with ADMIN session cookie -- for tests that require authentication."""
    global _current_upload_dir, _current_fake_email
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    # Create an ADMIN user directly in the database so the session middleware
    # can resolve the user from the cookie.
    admin = User.create(username="test-admin", display_name="Test Admin", role=UserRole.ADMIN)
    repo = UserRepository(conn)
    await repo.save(admin)

    cookie_value = create_session_cookie(admin.id)
    cookies = {COOKIE_NAME: cookie_value}

    upload_dir = Path(tempfile.mkdtemp())
    _current_upload_dir = upload_dir
    fake_email = FakeEmailService()
    _current_fake_email = fake_email
    await _setup_overrides(conn, upload_dir, fake_email)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    with patch("src.routers.purchase_order.get_db", _test_get_db), \
         patch("src.routers.product.get_db", _test_get_db), \
         patch("src.auth.middleware.get_db", _test_get_db):
        async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as ac:
            yield ac

    await tx.rollback()
    await conn.close()
    app.dependency_overrides.clear()
    shutil.rmtree(upload_dir, ignore_errors=True)


@pytest.fixture
def upload_dir() -> Path:
    assert _current_upload_dir is not None
    return _current_upload_dir


@pytest.fixture
def fake_email_service() -> FakeEmailService:
    """The FakeEmailService bound to the current test's dependency overrides.

    Tests that need to assert on sent emails request this fixture and read
    `calls` after making the API call. No explicit dependency-override step is
    needed: the conftest always substitutes the fake for the real service.
    """
    assert _current_fake_email is not None, (
        "fake_email_service fixture requires `client` or `authenticated_client` "
        "to have initialised the shared FakeEmailService first"
    )
    return _current_fake_email
