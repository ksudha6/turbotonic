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
from src.db import get_db
from src.document_repository import DocumentRepository
from src.domain.user import User, UserRole
from src.invoice_repository import InvoiceRepository
from src.main import app
from src.milestone_repository import MilestoneRepository
from src.repository import PurchaseOrderRepository
from src.routers.activity import get_activity_repo as activity_get_activity_repo
from src.routers.auth import get_user_repo as auth_get_user_repo
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
from src.routers.milestone import get_milestone_repo as milestone_get_milestone_repo
from src.routers.milestone import get_po_repo as milestone_get_po_repo
from src.routers.purchase_order import get_activity_repo as po_get_activity_repo
from src.routers.purchase_order import get_invoice_repo as po_get_invoice_repo
from src.routers.purchase_order import get_repo
from src.routers.purchase_order import get_vendor_repo as po_get_vendor_repo
from src.routers.product import get_product_repo as product_get_product_repo
from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo
from src.schema import init_db
from src.product_repository import ProductRepository
from src.services.file_storage import FileStorageService
from src.user_repository import UserRepository
from src.vendor_repository import VendorRepository

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)

_current_upload_dir: Path | None = None


async def _setup_overrides(conn: asyncpg.Connection, upload_dir: Path) -> None:
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

    async def override_get_user_repo() -> AsyncIterator[UserRepository]:
        yield UserRepository(conn)

    async def override_get_document_repo() -> AsyncIterator[DocumentRepository]:
        yield DocumentRepository(conn)

    def override_get_file_storage() -> FileStorageService:
        return FileStorageService(upload_dir)

    app.dependency_overrides[get_repo] = override_get_repo
    app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
    app.dependency_overrides[po_get_invoice_repo] = override_get_invoice_repo
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
    app.dependency_overrides[milestone_get_milestone_repo] = override_get_milestone_repo
    app.dependency_overrides[milestone_get_po_repo] = override_get_repo
    app.dependency_overrides[milestone_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[activity_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[product_get_product_repo] = override_get_product_repo
    app.dependency_overrides[auth_get_user_repo] = override_get_user_repo
    app.dependency_overrides[document_get_document_repo] = override_get_document_repo
    app.dependency_overrides[document_get_file_storage] = override_get_file_storage


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Unauthenticated client -- for testing 401/403 behaviour on pre-auth flows."""
    global _current_upload_dir
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    upload_dir = Path(tempfile.mkdtemp())
    _current_upload_dir = upload_dir
    await _setup_overrides(conn, upload_dir)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    with patch("src.routers.purchase_order.get_db", _test_get_db), \
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
    global _current_upload_dir
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
    await _setup_overrides(conn, upload_dir)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    with patch("src.routers.purchase_order.get_db", _test_get_db), \
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
