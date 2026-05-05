"""Endpoint + permission + validation tests for /api/v1/invoices/{invoice_id}/documents.

Iteration 112, task: invoice document CRUD + permission matrix + activity event + 422 validation.

Architecture notes:
- Tests use the real Postgres DB via the rolled-back-transaction pattern; no
  mocks for the database layer.
- The invoice_documents router declares its own DI functions (get_invoice_repo,
  get_po_repo, get_document_repo, get_activity_repo, get_file_storage). These are
  overridden here alongside the main conftest overrides so all requests share the
  test transaction.
- list_invoice_documents also calls `get_db` directly for the batch username fetch.
  That context manager is patched in the same `patch()` block.
- File storage writes to a per-test tempdir that is torn down after each fixture.
"""
from __future__ import annotations

import asyncio
import io
import shutil
import tempfile
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import patch

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.activity_repository import ActivityLogRepository
from src.auth.session import COOKIE_NAME, create_session_cookie
from src.brand_repository import BrandRepository
from src.document_repository import DocumentRepository
from src.domain.activity import ActivityEvent, EntityType, TargetRole
from src.domain.brand import Brand
from src.domain.invoice import Invoice, InvoiceLineItem, InvoiceStatus
from src.domain.purchase_order import POType
from src.domain.user import User, UserRole
from src.domain.vendor import Vendor, VendorType
from src.invoice_repository import InvoiceRepository
from src.main import app
from src.repository import PurchaseOrderRepository
from src.routers.invoice_documents import (
    get_activity_repo as inv_doc_get_activity_repo,
    get_document_repo as inv_doc_get_document_repo,
    get_file_storage as inv_doc_get_file_storage,
    get_invoice_repo as inv_doc_get_invoice_repo,
    get_po_repo as inv_doc_get_po_repo,
)
from src.schema import init_db
from src.services.file_storage import FileStorageService
from src.user_repository import UserRepository
from src.vendor_repository import VendorRepository
from tests.conftest import TEST_DATABASE_URL, _setup_overrides, FakeEmailService

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PDF_BYTES = b"%PDF-1.4 test content for invoice document storage"
_OVERSIZED_PDF_BYTES = b"x" * (10 * 1024 * 1024 + 1)
_PDF_CONTENT_TYPE = "application/pdf"
_PNG_CONTENT_TYPE = "image/png"

_VENDOR_INVOICE_PDF = "VENDOR_INVOICE_PDF"
_CREDIT_NOTE = "CREDIT_NOTE"
_DEBIT_NOTE = "DEBIT_NOTE"
_OTHER = "OTHER"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


async def _create_vendor(
    conn: asyncpg.Connection, name: str, vendor_type: str = "PROCUREMENT"
) -> Vendor:
    v = Vendor.create(name=name, country="US", vendor_type=VendorType(vendor_type))
    await VendorRepository(conn).save(v)
    return v


async def _create_user(
    conn: asyncpg.Connection,
    username: str,
    role: UserRole,
    vendor_id: str | None = None,
) -> User:
    u = User.create(username=username, display_name=username, role=role, vendor_id=vendor_id)
    await UserRepository(conn).save(u)
    return u


def _client_cookies(user: User) -> dict[str, str]:
    return {COOKIE_NAME: create_session_cookie(user.id)}


@asynccontextmanager
async def _make_authed_client(
    conn: asyncpg.Connection,
    upload_dir: Path,
    fake_email: FakeEmailService,
    user: User,
) -> AsyncIterator[AsyncClient]:
    """Yield an AsyncClient authenticated as user, with all DI overrides applied."""
    await _setup_overrides(conn, upload_dir, fake_email)
    _add_inv_doc_overrides(conn, upload_dir)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    cookies = _client_cookies(user)
    with (
        patch("src.routers.purchase_order.get_db", _test_get_db),
        patch("src.routers.product.get_db", _test_get_db),
        patch("src.routers.invoice_documents.get_db", _test_get_db),
        patch("src.auth.middleware.get_db", _test_get_db),
    ):
        async with AsyncClient(
            transport=transport, base_url="http://test", cookies=cookies
        ) as ac:
            yield ac


def _add_inv_doc_overrides(conn: asyncpg.Connection, upload_dir: Path) -> None:
    """Add dependency overrides specific to the invoice_documents router."""

    async def override_get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
        yield InvoiceRepository(conn)

    async def override_get_po_repo() -> AsyncIterator[PurchaseOrderRepository]:
        yield PurchaseOrderRepository(conn)

    async def override_get_document_repo() -> AsyncIterator[DocumentRepository]:
        yield DocumentRepository(conn)

    async def override_get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
        yield ActivityLogRepository(conn)

    def override_get_file_storage() -> FileStorageService:
        return FileStorageService(upload_dir)

    app.dependency_overrides[inv_doc_get_invoice_repo] = override_get_invoice_repo
    app.dependency_overrides[inv_doc_get_po_repo] = override_get_po_repo
    app.dependency_overrides[inv_doc_get_document_repo] = override_get_document_repo
    app.dependency_overrides[inv_doc_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[inv_doc_get_file_storage] = override_get_file_storage


# ---------------------------------------------------------------------------
# Shared fixture: two vendors, per-role users, one invoice
# ---------------------------------------------------------------------------


async def _create_accepted_po_and_invoice(
    conn: asyncpg.Connection,
    vendor: Vendor,
    brand: Brand,
) -> tuple[dict, str]:
    """Create an ACCEPTED PO + DRAFT invoice for vendor. Returns (po_dict, invoice_id).

    Inserts directly via SQL to bypass domain validation, matching the same pattern
    used by test_po_documents_router.py (API-based approach there, direct SQL here
    since we need an ACCEPTED PO without running the full PO API transition pipeline).
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    po_id = str(uuid4())
    po_number = f"PO-INV-DOC-{po_id[:8]}"
    now = datetime.now(UTC).isoformat()

    # Insert PO at ACCEPTED status directly.
    await conn.execute(
        """
        INSERT INTO purchase_orders (
            id, po_number, po_type, status, vendor_id, brand_id,
            buyer_name, buyer_country, ship_to_address,
            payment_terms, currency,
            issued_date, required_delivery_date,
            terms_and_conditions, incoterm,
            port_of_loading, port_of_discharge,
            country_of_origin, country_of_destination,
            round_count, last_actor_role, advance_paid_at,
            created_at, updated_at
        ) VALUES (
            $1, $2, 'PROCUREMENT', 'ACCEPTED', $3, $4,
            'TurboTonic Ltd', 'US', '123 Main St',
            'NET30', 'USD',
            $5, $5,
            'Standard T&C', 'FOB',
            'USLAX', 'CNSHA',
            'US', 'CN',
            0, NULL, NULL,
            $5, $5
        )
        """,
        po_id, po_number, vendor.id, brand.id, now,
    )

    # Insert a line item with ACCEPTED status.
    await conn.execute(
        """
        INSERT INTO line_items (
            id, po_id, part_number, description,
            quantity, uom, unit_price, hs_code, country_of_origin,
            product_id, status, sort_order, required_delivery_date
        ) VALUES ($1, $2, 'P1', 'Widget', 10, 'EA', '5.00', '7318.15', 'US', NULL, 'ACCEPTED', 0, NULL)
        """,
        str(uuid4()), po_id,
    )

    # Create invoice.
    inv_repo = InvoiceRepository(conn)
    invoice = Invoice.create(
        invoice_number=f"INV-DOC-{po_id[:8]}",
        po_id=po_id,
        po_status="ACCEPTED",
        po_type="PROCUREMENT",
        payment_terms="NET30",
        currency="USD",
        line_items=[
            InvoiceLineItem(
                part_number="P1",
                description="Widget",
                quantity=10,
                uom="EA",
                unit_price=Decimal("5.00"),
            )
        ],
    )
    await inv_repo.save(invoice)
    return {"id": po_id, "vendor_id": vendor.id}, invoice.id


@pytest_asyncio.fixture
async def env():
    """
    Seed state:
      - vendor_a: PROCUREMENT vendor; vendor_b: different PROCUREMENT vendor
      - invoice_a: DRAFT invoice for vendor_a
      - users: admin, sm, pm, fm, ql, vendor_a_user, vendor_b_user
      - upload_dir: temp dir cleaned up after the test
    """
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    upload_dir = Path(tempfile.mkdtemp())
    fake_email = FakeEmailService()

    # Vendors
    vendor_a = await _create_vendor(conn, "VendorA INV DOC", "PROCUREMENT")
    vendor_b = await _create_vendor(conn, "VendorB INV DOC", "PROCUREMENT")

    # Brands
    brand_a = Brand.create(name="InvDocBrand A", legal_name="InvDocBrand A LLC", address="1 Ave", country="US")
    brand_b = Brand.create(name="InvDocBrand B", legal_name="InvDocBrand B LLC", address="2 Ave", country="US")
    brand_repo = BrandRepository(conn)
    await brand_repo.save(brand_a)
    await brand_repo.save(brand_b)
    await brand_repo.assign_vendor(brand_a.id, vendor_a.id)
    await brand_repo.assign_vendor(brand_b.id, vendor_b.id)

    # Users
    admin = await _create_user(conn, "admin-inv-doc", UserRole.ADMIN)
    sm = await _create_user(conn, "sm-inv-doc", UserRole.SM)
    pm = await _create_user(conn, "pm-inv-doc", UserRole.PROCUREMENT_MANAGER)
    fm = await _create_user(conn, "fm-inv-doc", UserRole.FREIGHT_MANAGER)
    ql = await _create_user(conn, "ql-inv-doc", UserRole.QUALITY_LAB)
    vendor_a_user = await _create_user(
        conn, "vendor-a-inv-doc", UserRole.VENDOR, vendor_id=vendor_a.id
    )
    vendor_b_user = await _create_user(
        conn, "vendor-b-inv-doc", UserRole.VENDOR, vendor_id=vendor_b.id
    )

    # Invoice for vendor_a
    po_a, invoice_a_id = await _create_accepted_po_and_invoice(conn, vendor_a, brand_a)

    yield {
        "conn": conn,
        "upload_dir": upload_dir,
        "fake_email": fake_email,
        "vendor_a": vendor_a,
        "vendor_b": vendor_b,
        "admin": admin,
        "sm": sm,
        "pm": pm,
        "fm": fm,
        "ql": ql,
        "vendor_a_user": vendor_a_user,
        "vendor_b_user": vendor_b_user,
        "invoice_a_id": invoice_a_id,
        "po_a": po_a,
    }

    await tx.rollback()
    await conn.close()
    app.dependency_overrides.clear()
    shutil.rmtree(upload_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Helpers used inside tests
# ---------------------------------------------------------------------------


async def _upload(
    client: AsyncClient,
    invoice_id: str,
    file_type: str = _VENDOR_INVOICE_PDF,
    content: bytes = _PDF_BYTES,
    content_type: str = _PDF_CONTENT_TYPE,
    filename: str = "invoice.pdf",
) -> tuple[int, dict]:
    resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/documents",
        files={"file": (filename, io.BytesIO(content), content_type)},
        data={"file_type": file_type},
    )
    body: dict = resp.json() if resp.status_code not in (204,) else {}
    return resp.status_code, body


async def _list(client: AsyncClient, invoice_id: str) -> tuple[int, list]:
    resp = await client.get(f"/api/v1/invoices/{invoice_id}/documents")
    return resp.status_code, resp.json() if resp.status_code == 200 else []


async def _download(client: AsyncClient, invoice_id: str, file_id: str) -> int:
    resp = await client.get(f"/api/v1/invoices/{invoice_id}/documents/{file_id}")
    return resp.status_code


async def _delete(client: AsyncClient, invoice_id: str, file_id: str) -> int:
    resp = await client.delete(f"/api/v1/invoices/{invoice_id}/documents/{file_id}")
    return resp.status_code


# ---------------------------------------------------------------------------
# A. Permission matrix — table-driven
# ---------------------------------------------------------------------------
#
# Permission matrix (per spec):
# - VENDOR: upload + view + delete on their own invoice (vendor_scoping)
# - SM, ADMIN: view + delete any
# - PROCUREMENT_MANAGER: read-only (view + download)
# - FREIGHT_MANAGER: read-only (view + download)
# - QUALITY_LAB: hidden (403)
#
# Cross-vendor VENDOR returns 404 (security invariant).

_PERMISSION_MATRIX: tuple[tuple[str, str, str, int], ...] = (
    # --- view / list ---
    ("admin_list",            "admin",         "list",   200),
    ("sm_list",               "sm",            "list",   200),
    ("pm_list",               "pm",            "list",   200),
    ("fm_list",               "fm",            "list",   200),
    ("ql_list",               "ql",            "list",   403),
    ("vendor_own_list",       "vendor_a_user", "list",   200),
    ("vendor_other_list",     "vendor_b_user", "list",   404),
    # --- upload ---
    ("admin_upload",          "admin",         "upload", 201),
    ("sm_upload",             "sm",            "upload", 201),
    ("pm_upload",             "pm",            "upload", 403),
    ("fm_upload",             "fm",            "upload", 403),
    ("ql_upload",             "ql",            "upload", 403),
    ("vendor_own_upload",     "vendor_a_user", "upload", 201),
    ("vendor_other_upload",   "vendor_b_user", "upload", 404),
    # --- delete ---
    ("admin_delete",          "admin",         "delete", 204),
    ("sm_delete",             "sm",            "delete", 204),
    ("pm_delete",             "pm",            "delete", 403),
    ("fm_delete",             "fm",            "delete", 403),
    ("ql_delete",             "ql",            "delete", 403),
    ("vendor_own_delete",     "vendor_a_user", "delete", 204),
    ("vendor_other_delete",   "vendor_b_user", "delete", 404),
)


@pytest.mark.parametrize(
    "label,role_key,action,expected_status",
    _PERMISSION_MATRIX,
    ids=[row[0] for row in _PERMISSION_MATRIX],
)
async def test_permission_matrix(
    env: dict,
    label: str,
    role_key: str,
    action: str,
    expected_status: int,
) -> None:
    conn = env["conn"]
    upload_dir = env["upload_dir"]
    fake_email = env["fake_email"]
    user: User = env[role_key]
    invoice_id: str = env["invoice_a_id"]

    pre_uploaded_file_id: str | None = None
    if action in ("download", "delete"):
        async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as admin_client:
            status, body = await _upload(admin_client, invoice_id)
            assert status == 201, f"pre-upload for {label} failed: {body}"
            pre_uploaded_file_id = body["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, user) as ac:
        if action == "upload":
            status, _ = await _upload(ac, invoice_id)
        elif action == "list":
            status, _ = await _list(ac, invoice_id)
        elif action == "download":
            assert pre_uploaded_file_id is not None
            status = await _download(ac, invoice_id, pre_uploaded_file_id)
        elif action == "delete":
            assert pre_uploaded_file_id is not None
            status = await _delete(ac, invoice_id, pre_uploaded_file_id)
        else:
            raise ValueError(f"unknown action: {action}")

    assert status == expected_status, (
        f"[{label}] role={user.role.value}, action={action}: "
        f"expected {expected_status}, got {status}"
    )


# ---------------------------------------------------------------------------
# B. file_type vocabulary — 422 on invalid values
# ---------------------------------------------------------------------------


async def test_upload_empty_file_type_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, invoice_id, file_type="")
    assert status == 422


async def test_upload_whitespace_file_type_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, invoice_id, file_type="   ")
    assert status == 422


async def test_upload_unknown_file_type_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, invoice_id, file_type="SIGNED_PO")
    assert status == 422


# ---------------------------------------------------------------------------
# C. MIME type rejection → 415
# ---------------------------------------------------------------------------


async def test_upload_non_pdf_mime_type_returns_415(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, invoice_id, content_type=_PNG_CONTENT_TYPE)
    assert status == 415


# ---------------------------------------------------------------------------
# D. Size rejection → 413
# ---------------------------------------------------------------------------


async def test_upload_oversized_pdf_returns_413(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, invoice_id, content=_OVERSIZED_PDF_BYTES)
    assert status == 413


# ---------------------------------------------------------------------------
# E. Empty file → 400
# ---------------------------------------------------------------------------


async def test_upload_empty_file_returns_400(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, invoice_id, content=b"")
    assert status == 400


# ---------------------------------------------------------------------------
# F. Cross-invoice file_id leakage guard
# ---------------------------------------------------------------------------


async def test_cross_invoice_download_returns_404(env: dict) -> None:
    """File uploaded to invoice_a must not be downloadable via a fake invoice_id path."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_a_id: str = env["invoice_a_id"]
    fake_invoice_id = "00000000-0000-0000-0000-000000000000"

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, invoice_a_id)
        assert status == 201
        file_id: str = body["id"]

        status = await _download(client, fake_invoice_id, file_id)
    assert status == 404


# ---------------------------------------------------------------------------
# G. List ordering — uploaded_at DESC
# ---------------------------------------------------------------------------


async def test_list_returns_files_in_uploaded_at_desc_order(env: dict) -> None:
    """Three files uploaded with distinct timestamps must arrive newest-first."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]

    file_ids: list[str] = []
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        for i in range(3):
            status, body = await _upload(
                client, invoice_id, file_type=_OTHER, filename=f"doc_{i}.pdf"
            )
            assert status == 201
            file_ids.append(body["id"])
            await asyncio.sleep(0.05)

        status, items = await _list(client, invoice_id)

    assert status == 200
    assert len(items) == 3
    returned_ids = [item["id"] for item in items]
    assert returned_ids == list(reversed(file_ids)), (
        f"expected DESC order {list(reversed(file_ids))}, got {returned_ids}"
    )


# ---------------------------------------------------------------------------
# H. Username denormalization
# ---------------------------------------------------------------------------


async def test_list_resolves_uploaded_by_username_for_each_uploader(env: dict) -> None:
    """Two files uploaded by different users must each carry their own username."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    sm_user: User = env["sm"]
    admin_user: User = env["admin"]

    async with _make_authed_client(conn, upload_dir, fake_email, sm_user) as sm_client:
        status, body = await _upload(sm_client, invoice_id, file_type=_VENDOR_INVOICE_PDF)
        assert status == 201
        sm_file_id: str = body["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, admin_user) as admin_client:
        status, body = await _upload(admin_client, invoice_id, file_type=_CREDIT_NOTE)
        assert status == 201
        admin_file_id: str = body["id"]

        status, items = await _list(admin_client, invoice_id)

    assert status == 200
    assert len(items) == 2

    by_id = {item["id"]: item for item in items}
    assert by_id[sm_file_id]["uploaded_by_username"] == sm_user.username, (
        "SM file must carry SM's username"
    )
    assert by_id[admin_file_id]["uploaded_by_username"] == admin_user.username, (
        "Admin file must carry admin's username"
    )


# ---------------------------------------------------------------------------
# I. Activity row written on upload
# ---------------------------------------------------------------------------


async def test_upload_writes_activity_row_targeting_sm(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, invoice_id)
        assert status == 201

    row = await conn.fetchrow(
        """
        SELECT event, entity_type, entity_id, target_role
        FROM activity_log
        WHERE entity_type = $1 AND entity_id = $2 AND event = $3
        ORDER BY created_at DESC LIMIT 1
        """,
        EntityType.INVOICE.value,
        invoice_id,
        ActivityEvent.INVOICE_DOCUMENT_UPLOADED.value,
    )
    assert row is not None, "expected one INVOICE_DOCUMENT_UPLOADED activity row"
    assert row["target_role"] == TargetRole.SM.value, (
        f"invoice document upload must target SM, got {row['target_role']!r}"
    )


async def test_delete_does_not_write_activity_row(env: dict) -> None:
    """DELETE has no activity event (upload-only precedent from iter 084)."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, invoice_id)
        assert status == 201
        file_id: str = body["id"]

        count_before = await conn.fetchval(
            "SELECT COUNT(*) FROM activity_log WHERE entity_id = $1 AND event = $2",
            invoice_id,
            ActivityEvent.INVOICE_DOCUMENT_UPLOADED.value,
        )
        status = await _delete(client, invoice_id, file_id)
        assert status == 204

        count_after = await conn.fetchval(
            "SELECT COUNT(*) FROM activity_log WHERE entity_id = $1 AND event = $2",
            invoice_id,
            ActivityEvent.INVOICE_DOCUMENT_UPLOADED.value,
        )
    assert count_after == count_before, (
        "DELETE must not write an INVOICE_DOCUMENT_UPLOADED activity row"
    )


# ---------------------------------------------------------------------------
# J. Delete removes the row; subsequent GET returns 404
# ---------------------------------------------------------------------------


async def test_delete_removes_file_and_subsequent_download_returns_404(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, invoice_id)
        assert status == 201
        file_id: str = body["id"]

        status = await _delete(client, invoice_id, file_id)
        assert status == 204

        list_status, items = await _list(client, invoice_id)
        assert list_status == 200
        assert items == [], f"expected empty list after delete, got {items}"

        download_status = await _download(client, invoice_id, file_id)
    assert download_status == 404


# ---------------------------------------------------------------------------
# K. Upload response shape
# ---------------------------------------------------------------------------


async def test_upload_response_has_expected_shape(env: dict) -> None:
    """Upload response must carry the full file metadata including resolved username."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    admin_user: User = env["admin"]

    async with _make_authed_client(conn, upload_dir, fake_email, admin_user) as client:
        status, body = await _upload(
            client, invoice_id, file_type=_VENDOR_INVOICE_PDF, filename="invoice.pdf"
        )
    assert status == 201
    assert set(body.keys()) == {
        "id",
        "entity_type",
        "entity_id",
        "file_type",
        "original_name",
        "content_type",
        "size_bytes",
        "uploaded_at",
        "uploaded_by",
        "uploaded_by_username",
    }, f"unexpected response keys: {set(body.keys())}"
    assert body["entity_type"] == "INVOICE"
    assert body["entity_id"] == invoice_id
    assert body["file_type"] == _VENDOR_INVOICE_PDF
    assert body["original_name"] == "invoice.pdf"
    assert body["content_type"] == _PDF_CONTENT_TYPE
    assert body["size_bytes"] == len(_PDF_BYTES)
    assert body["uploaded_by_username"] == admin_user.username


# ---------------------------------------------------------------------------
# L. All valid file types accepted
# ---------------------------------------------------------------------------


async def test_all_valid_file_types_are_accepted(env: dict) -> None:
    """Each InvoiceAttachmentType value must return 201."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    invoice_id: str = env["invoice_a_id"]
    valid_types = [_VENDOR_INVOICE_PDF, _CREDIT_NOTE, _DEBIT_NOTE, _OTHER]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        for ft in valid_types:
            status, body = await _upload(client, invoice_id, file_type=ft, filename=f"{ft}.pdf")
            assert status == 201, f"expected 201 for {ft}, got {status}: {body}"
