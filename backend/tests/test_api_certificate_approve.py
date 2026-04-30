"""Iter 105: POST /{cert_id}/approve endpoint tests.

Uses authenticated_client (ADMIN) for the happy path — ADMIN bypasses role guards.
Role-guard tests (403) use a dedicated _make_cert_client helper that creates a
minimal role-specific session with only the cert + product + qualification DI wired.
"""
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
from src.certificate_repository import CertificateRepository
from src.domain.activity import ActivityEvent, EntityType
from src.domain.certificate import CertificateStatus
from src.domain.user import User, UserRole
from src.document_repository import DocumentRepository
from src.main import app
from src.product_repository import ProductRepository
from src.qualification_type_repository import QualificationTypeRepository
from src.routers.activity import get_activity_repo as activity_get_activity_repo
from src.routers.auth import get_activity_repo as auth_get_activity_repo
from src.routers.auth import get_user_repo as auth_get_user_repo
from src.routers.certificate import (
    get_activity_repo_for_cert as cert_get_activity_repo,
    get_cert_repo,
    get_document_repo_for_cert as cert_get_document_repo,
    get_file_storage_for_cert as cert_get_file_storage,
    get_product_repo_for_cert as cert_get_product_repo,
    get_qt_repo_for_cert as cert_get_qt_repo,
)
from src.schema import init_db
from src.services.file_storage import FileStorageService
from src.user_repository import UserRepository

pytestmark = pytest.mark.asyncio

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)

CERT_NUMBER = "CERT-APPROVE-001"
ISSUER = "SGS"
TARGET_MARKET = "US"
ISSUE_DATE = "2024-03-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _create_vendor(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "Approve Vendor", "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_product(client: AsyncClient, vendor_id: str) -> str:
    resp = await client.post(
        "/api/v1/products/",
        json={
            "vendor_id": vendor_id,
            "part_number": "PART-APPROVE-001",
            "description": "Approve Test Product",
            "requires_certification": False,
            "manufacturing_address": "",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_qt(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/qualification-types",
        json={
            "name": "FCC",
            "description": "FCC certification",
            "target_market": TARGET_MARKET,
            "applies_to_category": "",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_valid_cert(client: AsyncClient) -> str:
    """Create a vendor, product, qualification type and a VALID cert. Return cert_id."""
    vendor_id = await _create_vendor(client)
    product_id = await _create_product(client, vendor_id)
    qt_id = await _create_qt(client)
    resp = await client.post(
        "/api/v1/certificates/",
        json={
            "product_id": product_id,
            "qualification_type_id": qt_id,
            "cert_number": CERT_NUMBER,
            "issuer": ISSUER,
            "issue_date": ISSUE_DATE,
            "target_market": TARGET_MARKET,
        },
    )
    assert resp.status_code == 201
    cert_id = resp.json()["id"]

    # Transition to VALID via PATCH
    patch_resp = await client.patch(
        f"/api/v1/certificates/{cert_id}",
        json={"status": "VALID"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == CertificateStatus.VALID.value
    return cert_id


# ---------------------------------------------------------------------------
# Role-specific client factory (cert deps only)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _cert_client(role: UserRole) -> AsyncIterator[tuple[AsyncClient, asyncpg.Connection]]:
    """Minimal client with cert DI wired; authenticated as the given role."""
    import tempfile
    from pathlib import Path

    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    user = User.create(
        username=f"cert-test-{role.value.lower()}",
        display_name=f"Cert Test {role.value}",
        role=role,
    )
    user_repo = UserRepository(conn)
    await user_repo.save(user)

    cookie_value = create_session_cookie(user.id)
    cookies = {COOKIE_NAME: cookie_value}

    upload_dir = Path(tempfile.mkdtemp())

    async def _cert_repo_dep() -> AsyncIterator[CertificateRepository]:
        yield CertificateRepository(conn)

    async def _product_repo_dep() -> AsyncIterator[ProductRepository]:
        yield ProductRepository(conn)

    async def _qt_repo_dep() -> AsyncIterator[QualificationTypeRepository]:
        yield QualificationTypeRepository(conn)

    async def _activity_repo_dep() -> AsyncIterator[ActivityLogRepository]:
        yield ActivityLogRepository(conn)

    async def _document_repo_dep() -> AsyncIterator[DocumentRepository]:
        yield DocumentRepository(conn)

    async def _user_repo_dep() -> AsyncIterator[UserRepository]:
        yield UserRepository(conn)

    def _file_storage_dep() -> FileStorageService:
        return FileStorageService(upload_dir)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    app.dependency_overrides[get_cert_repo] = _cert_repo_dep
    app.dependency_overrides[cert_get_product_repo] = _product_repo_dep
    app.dependency_overrides[cert_get_qt_repo] = _qt_repo_dep
    app.dependency_overrides[cert_get_activity_repo] = _activity_repo_dep
    app.dependency_overrides[cert_get_document_repo] = _document_repo_dep
    app.dependency_overrides[cert_get_file_storage] = _file_storage_dep
    app.dependency_overrides[activity_get_activity_repo] = _activity_repo_dep
    app.dependency_overrides[auth_get_user_repo] = _user_repo_dep
    app.dependency_overrides[auth_get_activity_repo] = _activity_repo_dep

    transport = ASGITransport(app=app)
    with patch("src.auth.middleware.get_db", _test_get_db):
        async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as ac:
            yield ac, conn

    await tx.rollback()
    await conn.close()
    app.dependency_overrides.clear()
    import shutil
    shutil.rmtree(upload_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests: happy path (ADMIN bypasses role guard)
# ---------------------------------------------------------------------------

async def test_approve_valid_cert_returns_200(authenticated_client: AsyncClient) -> None:
    cert_id = await _create_valid_cert(authenticated_client)
    resp = await authenticated_client.post(f"/api/v1/certificates/{cert_id}/approve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == cert_id
    assert body["status"] == CertificateStatus.APPROVED.value


async def test_approve_returns_full_cert_response(authenticated_client: AsyncClient) -> None:
    cert_id = await _create_valid_cert(authenticated_client)
    resp = await authenticated_client.post(f"/api/v1/certificates/{cert_id}/approve")
    assert resp.status_code == 200
    body = resp.json()
    expected_keys = {
        "id", "product_id", "qualification_type_id", "cert_number",
        "issuer", "testing_lab", "test_date", "issue_date", "expiry_date",
        "target_market", "document_id", "status", "created_at", "updated_at",
    }
    assert set(body.keys()) == expected_keys, f"Unexpected keys: {set(body.keys()) ^ expected_keys}"


# ---------------------------------------------------------------------------
# Tests: double-approve returns 409
# ---------------------------------------------------------------------------

async def test_double_approve_returns_409(authenticated_client: AsyncClient) -> None:
    cert_id = await _create_valid_cert(authenticated_client)
    first = await authenticated_client.post(f"/api/v1/certificates/{cert_id}/approve")
    assert first.status_code == 200
    second = await authenticated_client.post(f"/api/v1/certificates/{cert_id}/approve")
    assert second.status_code == 409


# ---------------------------------------------------------------------------
# Tests: approve pending cert returns 409
# ---------------------------------------------------------------------------

async def test_approve_pending_cert_returns_409(authenticated_client: AsyncClient) -> None:
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    qt_id = await _create_qt(authenticated_client)
    create_resp = await authenticated_client.post(
        "/api/v1/certificates/",
        json={
            "product_id": product_id,
            "qualification_type_id": qt_id,
            "cert_number": "CERT-PENDING-TEST",
            "issuer": ISSUER,
            "issue_date": ISSUE_DATE,
            "target_market": TARGET_MARKET,
        },
    )
    assert create_resp.status_code == 201
    cert_id = create_resp.json()["id"]
    # PENDING cert -- approve must fail
    resp = await authenticated_client.post(f"/api/v1/certificates/{cert_id}/approve")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Tests: unknown cert_id returns 404
# ---------------------------------------------------------------------------

async def test_approve_unknown_cert_returns_404(authenticated_client: AsyncClient) -> None:
    resp = await authenticated_client.post("/api/v1/certificates/nonexistent-cert-id/approve")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: role guards — non-FM roles get 403
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", [
    UserRole.SM,
    UserRole.QUALITY_LAB,
    UserRole.PROCUREMENT_MANAGER,
])
async def test_approve_non_fm_role_returns_403(role: UserRole) -> None:
    async with _cert_client(role) as (ac, conn):
        # Must create a cert to approve via a second admin connection so FK chain works.
        # Since role-scoped client shares the same conn, we create the data directly.
        from src.domain.certificate import Certificate
        from src.domain.product import Product
        from src.domain.vendor import Vendor, VendorType
        from src.domain.qualification_type import QualificationType
        from src.vendor_repository import VendorRepository
        from src.product_repository import ProductRepository as PR
        from datetime import UTC, datetime

        v = Vendor.create(name="Guard Vendor", country="CN", vendor_type=VendorType.PROCUREMENT)
        await VendorRepository(conn).save(v)

        p = Product.create(
            vendor_id=v.id,
            part_number="GUARD-PART",
            description="Guard Product",
            manufacturing_address="",
        )
        await PR(conn).save(p)

        from src.qualification_type_repository import QualificationTypeRepository as QTR
        qt = QualificationType.create(
            name="Guard QT",
            description="",
            target_market=TARGET_MARKET,
            applies_to_category="",
        )
        await QTR(conn).save(qt)

        cert = Certificate.create(
            product_id=p.id,
            qualification_type_id=qt.id,
            cert_number="CERT-GUARD",
            issuer=ISSUER,
            issue_date=datetime(2024, 1, 1, tzinfo=UTC),
            target_market=TARGET_MARKET,
        )
        cert.mark_valid()
        await CertificateRepository(conn).save(cert)

        resp = await ac.post(f"/api/v1/certificates/{cert.id}/approve")
        assert resp.status_code == 403, (
            f"Role {role.value} should get 403 but got {resp.status_code}"
        )


async def test_approve_vendor_role_returns_403() -> None:
    """VENDOR needs a vendor_id FK. Handled separately from the parametrized set."""
    from src.domain.vendor import Vendor, VendorType
    from src.vendor_repository import VendorRepository
    import tempfile
    from pathlib import Path

    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    v = Vendor.create(name="Vendor Guard Co", country="CN", vendor_type=VendorType.PROCUREMENT)
    await VendorRepository(conn).save(v)

    user = User.create(
        username="cert-test-vendor",
        display_name="Cert Test VENDOR",
        role=UserRole.VENDOR,
        vendor_id=v.id,
    )
    await UserRepository(conn).save(user)

    cookie_value = create_session_cookie(user.id)
    cookies = {COOKIE_NAME: cookie_value}

    upload_dir = Path(tempfile.mkdtemp())

    async def _cert_repo_dep() -> AsyncIterator[CertificateRepository]:
        yield CertificateRepository(conn)

    async def _product_repo_dep() -> AsyncIterator[ProductRepository]:
        yield ProductRepository(conn)

    async def _qt_repo_dep() -> AsyncIterator[QualificationTypeRepository]:
        yield QualificationTypeRepository(conn)

    async def _activity_repo_dep() -> AsyncIterator[ActivityLogRepository]:
        yield ActivityLogRepository(conn)

    async def _document_repo_dep() -> AsyncIterator[DocumentRepository]:
        yield DocumentRepository(conn)

    async def _user_repo_dep() -> AsyncIterator[UserRepository]:
        yield UserRepository(conn)

    def _file_storage_dep() -> FileStorageService:
        return FileStorageService(upload_dir)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    app.dependency_overrides[get_cert_repo] = _cert_repo_dep
    app.dependency_overrides[cert_get_product_repo] = _product_repo_dep
    app.dependency_overrides[cert_get_qt_repo] = _qt_repo_dep
    app.dependency_overrides[cert_get_activity_repo] = _activity_repo_dep
    app.dependency_overrides[cert_get_document_repo] = _document_repo_dep
    app.dependency_overrides[cert_get_file_storage] = _file_storage_dep
    app.dependency_overrides[activity_get_activity_repo] = _activity_repo_dep
    app.dependency_overrides[auth_get_user_repo] = _user_repo_dep
    app.dependency_overrides[auth_get_activity_repo] = _activity_repo_dep

    transport = ASGITransport(app=app)
    try:
        with patch("src.auth.middleware.get_db", _test_get_db):
            async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as ac:
                resp = await ac.post("/api/v1/certificates/any-id/approve")
                assert resp.status_code == 403, (
                    f"VENDOR should get 403 but got {resp.status_code}"
                )
    finally:
        await tx.rollback()
        await conn.close()
        app.dependency_overrides.clear()
        import shutil
        shutil.rmtree(upload_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests: FM role succeeds (role-specific, not ADMIN bypass)
# ---------------------------------------------------------------------------

async def test_approve_freight_manager_role_succeeds() -> None:
    """Verify FREIGHT_MANAGER (not ADMIN) specifically allowed."""
    from src.domain.certificate import Certificate
    from src.domain.product import Product
    from src.domain.vendor import Vendor, VendorType
    from src.domain.qualification_type import QualificationType
    from src.vendor_repository import VendorRepository
    from src.product_repository import ProductRepository as PR
    from src.qualification_type_repository import QualificationTypeRepository as QTR
    from datetime import UTC, datetime
    import tempfile
    from pathlib import Path

    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    v = Vendor.create(name="FM Vendor", country="CN", vendor_type=VendorType.PROCUREMENT)
    await VendorRepository(conn).save(v)

    p = Product.create(
        vendor_id=v.id,
        part_number="FM-PART",
        description="FM Test Product",
        manufacturing_address="",
    )
    await PR(conn).save(p)

    qt = QualificationType.create(
        name="FM QT",
        description="",
        target_market=TARGET_MARKET,
        applies_to_category="",
    )
    await QTR(conn).save(qt)

    cert = Certificate.create(
        product_id=p.id,
        qualification_type_id=qt.id,
        cert_number="CERT-FM-001",
        issuer=ISSUER,
        issue_date=datetime(2024, 1, 1, tzinfo=UTC),
        target_market=TARGET_MARKET,
    )
    cert.mark_valid()
    await CertificateRepository(conn).save(cert)

    fm_user = User.create(
        username="test-fm-approve",
        display_name="Test FM",
        role=UserRole.FREIGHT_MANAGER,
    )
    await UserRepository(conn).save(fm_user)

    cookie_value = create_session_cookie(fm_user.id)
    cookies = {COOKIE_NAME: cookie_value}

    upload_dir = Path(tempfile.mkdtemp())

    async def _cert_repo_dep() -> AsyncIterator[CertificateRepository]:
        yield CertificateRepository(conn)

    async def _product_repo_dep() -> AsyncIterator[ProductRepository]:
        yield ProductRepository(conn)

    async def _qt_repo_dep() -> AsyncIterator[QualificationTypeRepository]:
        yield QualificationTypeRepository(conn)

    async def _activity_repo_dep() -> AsyncIterator[ActivityLogRepository]:
        yield ActivityLogRepository(conn)

    async def _document_repo_dep() -> AsyncIterator[DocumentRepository]:
        yield DocumentRepository(conn)

    async def _user_repo_dep() -> AsyncIterator[UserRepository]:
        yield UserRepository(conn)

    def _file_storage_dep() -> FileStorageService:
        return FileStorageService(upload_dir)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    app.dependency_overrides[get_cert_repo] = _cert_repo_dep
    app.dependency_overrides[cert_get_product_repo] = _product_repo_dep
    app.dependency_overrides[cert_get_qt_repo] = _qt_repo_dep
    app.dependency_overrides[cert_get_activity_repo] = _activity_repo_dep
    app.dependency_overrides[cert_get_document_repo] = _document_repo_dep
    app.dependency_overrides[cert_get_file_storage] = _file_storage_dep
    app.dependency_overrides[activity_get_activity_repo] = _activity_repo_dep
    app.dependency_overrides[auth_get_user_repo] = _user_repo_dep
    app.dependency_overrides[auth_get_activity_repo] = _activity_repo_dep

    transport = ASGITransport(app=app)
    try:
        with patch("src.auth.middleware.get_db", _test_get_db):
            async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as ac:
                resp = await ac.post(f"/api/v1/certificates/{cert.id}/approve")
                assert resp.status_code == 200
                body = resp.json()
                assert body["status"] == CertificateStatus.APPROVED.value

                # Verify activity row written with correct event and actor_id
                rows = await conn.fetch(
                    "SELECT entity_type, entity_id, event, actor_id FROM activity_log WHERE entity_id = $1",
                    cert.id,
                )
                approve_rows = [r for r in rows if r["event"] == ActivityEvent.CERT_APPROVED.value]
                assert len(approve_rows) == 1, f"Expected 1 CERT_APPROVED row, got {len(approve_rows)}"
                approve_row = approve_rows[0]
                assert approve_row["entity_type"] == EntityType.CERTIFICATE.value
                assert approve_row["entity_id"] == cert.id
                assert approve_row["actor_id"] == fm_user.id
    finally:
        await tx.rollback()
        await conn.close()
        app.dependency_overrides.clear()
        import shutil
        shutil.rmtree(upload_dir, ignore_errors=True)
