"""Endpoint + permission + validation tests for /api/v1/po/{po_id}/documents.

Iteration 084, task 13 (endpoint tests).

Architecture notes:
- Tests use the real Postgres DB via the rolled-back-transaction pattern; no
  mocks for the database layer.
- The po_documents router declares its own DI functions (get_po_repo,
  get_document_repo, get_activity_repo, get_file_storage). These are overridden
  here alongside the main conftest overrides so all requests share the test
  transaction.
- list_po_documents also calls `get_db` directly for the batch username fetch.
  That context manager is patched in the same `patch()` block as the purchase
  order router.
- File storage writes to a per-test tempdir that is torn down after each fixture.
"""
from __future__ import annotations

import asyncio
import io
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
from src.document_repository import DocumentRepository
from src.domain.activity import ActivityEvent, EntityType, TargetRole
from src.domain.purchase_order import POType
from src.domain.user import User, UserRole
from src.domain.vendor import Vendor, VendorType
from src.main import app
from src.repository import PurchaseOrderRepository
from src.routers.po_documents import (
    get_activity_repo as po_doc_get_activity_repo,
    get_document_repo as po_doc_get_document_repo,
    get_file_storage as po_doc_get_file_storage,
    get_po_repo as po_doc_get_po_repo,
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

# Minimal valid PDF bytes (enough for content_type check; router checks
# content_type header, not magic bytes).
_PDF_BYTES = b"%PDF-1.4 test content for po document storage"

# Over the 10 MB limit by one byte.
_OVERSIZED_PDF_BYTES = b"x" * (10 * 1024 * 1024 + 1)

_PDF_CONTENT_TYPE = "application/pdf"
_PNG_CONTENT_TYPE = "image/png"

_SIGNED_PO = "SIGNED_PO"
_COUNTERSIGNED_PO = "COUNTERSIGNED_PO"
_SIGNED_AGREEMENT = "SIGNED_AGREEMENT"
_AMENDMENT = "AMENDMENT"
_ADDENDUM = "ADDENDUM"

# PO creation payload template; vendor_id is replaced per test.
_PO_PAYLOAD_TEMPLATE: dict = {
    "vendor_id": "__REPLACE__",
    "buyer_name": "TurboTonic Ltd",
    "buyer_country": "US",
    "ship_to_address": "123 Main St",
    "payment_terms": "NET30",
    "currency": "USD",
    "issued_date": "2026-04-01T00:00:00Z",
    "required_delivery_date": "2026-05-01T00:00:00Z",
    "terms_and_conditions": "Standard T&C",
    "incoterm": "FOB",
    "port_of_loading": "USLAX",
    "port_of_discharge": "CNSHA",
    "country_of_origin": "US",
    "country_of_destination": "CN",
    "line_items": [
        {
            "part_number": "P1",
            "description": "Widget",
            "quantity": 10,
            "uom": "EA",
            "unit_price": "5.00",
            "hs_code": "7318.15",
            "country_of_origin": "US",
        }
    ],
}


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _po_payload(vendor_id: str, po_type: str = "PROCUREMENT") -> dict:
    return {**_PO_PAYLOAD_TEMPLATE, "vendor_id": vendor_id, "po_type": po_type}


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
    _add_po_doc_overrides(conn, upload_dir)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    cookies = _client_cookies(user)
    with (
        patch("src.routers.purchase_order.get_db", _test_get_db),
        patch("src.routers.product.get_db", _test_get_db),
        patch("src.routers.po_documents.get_db", _test_get_db),
        patch("src.auth.middleware.get_db", _test_get_db),
    ):
        async with AsyncClient(
            transport=transport, base_url="http://test", cookies=cookies
        ) as ac:
            yield ac


def _add_po_doc_overrides(conn: asyncpg.Connection, upload_dir: Path) -> None:
    """Add dependency overrides specific to the po_documents router."""

    async def override_get_po_repo() -> AsyncIterator[PurchaseOrderRepository]:
        yield PurchaseOrderRepository(conn)

    async def override_get_document_repo() -> AsyncIterator[DocumentRepository]:
        yield DocumentRepository(conn)

    async def override_get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
        yield ActivityLogRepository(conn)

    def override_get_file_storage() -> FileStorageService:
        return FileStorageService(upload_dir)

    app.dependency_overrides[po_doc_get_po_repo] = override_get_po_repo
    app.dependency_overrides[po_doc_get_document_repo] = override_get_document_repo
    app.dependency_overrides[po_doc_get_activity_repo] = override_get_activity_repo
    app.dependency_overrides[po_doc_get_file_storage] = override_get_file_storage


# ---------------------------------------------------------------------------
# Shared fixture: two vendors, per-role users, one PROCUREMENT PO, one OPEX PO
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def env():
    """
    Seed state:
      - vendor_a: PROCUREMENT vendor; vendor_b: OPEX vendor
      - procurement_po: DRAFT PROCUREMENT PO for vendor_a
      - opex_po: DRAFT OPEX PO for vendor_b
      - users: admin, sm, pm (PROCUREMENT_MANAGER), fm (FREIGHT_MANAGER),
               ql (QUALITY_LAB), vendor_a_user, vendor_b_user
      - upload_dir: temp dir cleaned up after the test
    """
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()

    upload_dir = Path(tempfile.mkdtemp())
    fake_email = FakeEmailService()

    # Vendors
    vendor_a = await _create_vendor(conn, "VendorA PROCUREMENT", "PROCUREMENT")
    vendor_b = await _create_vendor(conn, "VendorB OPEX", "OPEX")

    # Users
    admin = await _create_user(conn, "admin-doc", UserRole.ADMIN)
    sm = await _create_user(conn, "sm-doc", UserRole.SM)
    pm = await _create_user(conn, "pm-doc", UserRole.PROCUREMENT_MANAGER)
    fm = await _create_user(conn, "fm-doc", UserRole.FREIGHT_MANAGER)
    ql = await _create_user(conn, "ql-doc", UserRole.QUALITY_LAB)
    vendor_a_user = await _create_user(
        conn, "vendor-a-doc", UserRole.VENDOR, vendor_id=vendor_a.id
    )
    vendor_b_user = await _create_user(
        conn, "vendor-b-doc", UserRole.VENDOR, vendor_id=vendor_b.id
    )

    # POs — created via API using admin client so they get IDs back cleanly
    await _setup_overrides(conn, upload_dir, fake_email)
    _add_po_doc_overrides(conn, upload_dir)

    @asynccontextmanager
    async def _test_get_db() -> AsyncIterator[asyncpg.Connection]:
        yield conn

    transport = ASGITransport(app=app)
    admin_cookies = _client_cookies(admin)

    with (
        patch("src.routers.purchase_order.get_db", _test_get_db),
        patch("src.routers.product.get_db", _test_get_db),
        patch("src.routers.po_documents.get_db", _test_get_db),
        patch("src.auth.middleware.get_db", _test_get_db),
    ):
        async with AsyncClient(
            transport=transport, base_url="http://test", cookies=admin_cookies
        ) as setup_client:
            proc_resp = await setup_client.post(
                "/api/v1/po/", json=_po_payload(vendor_a.id, "PROCUREMENT")
            )
            assert proc_resp.status_code == 201, proc_resp.text
            procurement_po = proc_resp.json()

            opex_resp = await setup_client.post(
                "/api/v1/po/", json=_po_payload(vendor_b.id, "OPEX")
            )
            assert opex_resp.status_code == 201, opex_resp.text
            opex_po = opex_resp.json()

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
        "procurement_po": procurement_po,
        "opex_po": opex_po,
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
    po_id: str,
    file_type: str = _SIGNED_PO,
    content: bytes = _PDF_BYTES,
    content_type: str = _PDF_CONTENT_TYPE,
    filename: str = "signed.pdf",
) -> tuple[int, dict]:
    resp = await client.post(
        f"/api/v1/po/{po_id}/documents",
        files={"file": (filename, io.BytesIO(content), content_type)},
        data={"file_type": file_type},
    )
    body: dict = resp.json() if resp.status_code not in (204,) else {}
    return resp.status_code, body


async def _list(client: AsyncClient, po_id: str) -> tuple[int, list]:
    resp = await client.get(f"/api/v1/po/{po_id}/documents")
    return resp.status_code, resp.json() if resp.status_code == 200 else []


async def _download(
    client: AsyncClient, po_id: str, file_id: str
) -> int:
    resp = await client.get(f"/api/v1/po/{po_id}/documents/{file_id}")
    return resp.status_code


async def _delete(client: AsyncClient, po_id: str, file_id: str) -> int:
    resp = await client.delete(f"/api/v1/po/{po_id}/documents/{file_id}")
    return resp.status_code


# ---------------------------------------------------------------------------
# A. Permission matrix — table-driven
# ---------------------------------------------------------------------------
#
# Each row: (label, po_type_key, role_key, action, expected_status)
# po_type_key: "procurement_po" or "opex_po"
# role_key: key in the env dict for the acting user
# action: "upload" | "list" | "download" | "delete"
# expected_status: 201, 200, 204, 403, 404
#
# VENDOR(own) for PROCUREMENT = vendor_a_user acting on procurement_po
# VENDOR(own) for OPEX         = vendor_b_user acting on opex_po
# VENDOR(other) for PROCUREMENT = vendor_b_user acting on procurement_po
# VENDOR(other) for OPEX        = vendor_a_user acting on opex_po
#
# Note: cross-vendor VENDOR access returns 404 (iter 032 security invariant:
# a VENDOR must not learn whether a PO exists for another vendor). In-scope
# role-deny (e.g. OPEX VENDOR own attempting manage) returns 403.

_PERMISSION_MATRIX: tuple[tuple[str, str, str, str, int], ...] = (
    # --- PROCUREMENT list/download: view roles ---
    ("proc_admin_list",     "procurement_po", "admin",         "list",     200),
    ("proc_sm_list",        "procurement_po", "sm",            "list",     200),
    ("proc_pm_list",        "procurement_po", "pm",            "list",     200),
    ("proc_fm_list",        "procurement_po", "fm",            "list",     200),
    ("proc_ql_list",        "procurement_po", "ql",            "list",     200),
    ("proc_vendor_own_list","procurement_po", "vendor_a_user", "list",     200),
    ("proc_vendor_other_list","procurement_po","vendor_b_user","list",     404),
    # --- PROCUREMENT upload/delete: manage roles ---
    ("proc_admin_upload",   "procurement_po", "admin",         "upload",   201),
    ("proc_sm_upload",      "procurement_po", "sm",            "upload",   201),
    ("proc_pm_upload",      "procurement_po", "pm",            "upload",   403),
    ("proc_fm_upload",      "procurement_po", "fm",            "upload",   403),
    ("proc_ql_upload",      "procurement_po", "ql",            "upload",   403),
    ("proc_vendor_own_upload","procurement_po","vendor_a_user","upload",   201),
    ("proc_vendor_other_upload","procurement_po","vendor_b_user","upload", 404),
    # --- OPEX list/download: view roles ---
    ("opex_admin_list",     "opex_po",        "admin",         "list",     200),
    ("opex_fm_list",        "opex_po",        "fm",            "list",     200),
    ("opex_vendor_own_list","opex_po",        "vendor_b_user", "list",     200),
    ("opex_sm_list",        "opex_po",        "sm",            "list",     403),
    ("opex_pm_list",        "opex_po",        "pm",            "list",     403),
    ("opex_ql_list",        "opex_po",        "ql",            "list",     403),
    ("opex_vendor_other_list","opex_po",      "vendor_a_user", "list",     404),
    # --- OPEX upload/delete: manage roles ---
    ("opex_admin_upload",   "opex_po",        "admin",         "upload",   201),
    ("opex_fm_upload",      "opex_po",        "fm",            "upload",   201),
    ("opex_sm_upload",      "opex_po",        "sm",            "upload",   403),
    ("opex_pm_upload",      "opex_po",        "pm",            "upload",   403),
    ("opex_ql_upload",      "opex_po",        "ql",            "upload",   403),
    ("opex_vendor_own_upload","opex_po",      "vendor_b_user", "upload",   403),
    ("opex_vendor_other_upload","opex_po",    "vendor_a_user", "upload",   404),
)


@pytest.mark.parametrize(
    "label,po_type_key,role_key,action,expected_status",
    _PERMISSION_MATRIX,
    ids=[row[0] for row in _PERMISSION_MATRIX],
)
async def test_permission_matrix(
    env: dict,
    label: str,
    po_type_key: str,
    role_key: str,
    action: str,
    expected_status: int,
) -> None:
    conn = env["conn"]
    upload_dir = env["upload_dir"]
    fake_email = env["fake_email"]
    user: User = env[role_key]
    po: dict = env[po_type_key]
    po_id: str = po["id"]

    # For download/delete tests we need a pre-existing file. Upload as admin first.
    pre_uploaded_file_id: str | None = None
    if action in ("download", "delete"):
        # Pick an acceptable file_type for the PO type.
        ft = _SIGNED_PO if po_type_key == "procurement_po" else _SIGNED_AGREEMENT
        async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as admin_client:
            status, body = await _upload(admin_client, po_id, file_type=ft)
            assert status == 201, f"pre-upload for {label} failed: {body}"
            pre_uploaded_file_id = body["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, user) as ac:
        if action == "upload":
            ft = _SIGNED_PO if po_type_key == "procurement_po" else _SIGNED_AGREEMENT
            status, _ = await _upload(ac, po_id, file_type=ft)
        elif action == "list":
            status, _ = await _list(ac, po_id)
        elif action == "download":
            assert pre_uploaded_file_id is not None
            status = await _download(ac, po_id, pre_uploaded_file_id)
        elif action == "delete":
            assert pre_uploaded_file_id is not None
            status = await _delete(ac, po_id, pre_uploaded_file_id)
        else:
            raise ValueError(f"unknown action: {action}")

    assert status == expected_status, (
        f"[{label}] role={user.role.value}, action={action}, po_type={po_type_key}: "
        f"expected {expected_status}, got {status}"
    )


# ---------------------------------------------------------------------------
# B. file_type vocabulary mismatch → 422
# ---------------------------------------------------------------------------


async def test_sm_upload_signed_agreement_to_procurement_po_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["sm"]) as client:
        status, _ = await _upload(client, po_id, file_type=_SIGNED_AGREEMENT)
    assert status == 422


async def test_admin_upload_signed_po_to_opex_po_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["opex_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, po_id, file_type=_SIGNED_PO)
    assert status == 422


async def test_admin_upload_countersigned_po_to_opex_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["opex_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, po_id, file_type=_COUNTERSIGNED_PO)
    assert status == 422


async def test_upload_empty_file_type_string_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, po_id, file_type="")
    assert status == 422


async def test_upload_whitespace_file_type_string_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, po_id, file_type="   ")
    assert status == 422


async def test_upload_unknown_file_type_string_returns_422(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, po_id, file_type="FOO")
    assert status == 422


# ---------------------------------------------------------------------------
# C. MIME type rejection → 415
# ---------------------------------------------------------------------------


async def test_upload_non_pdf_mime_type_returns_415(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(
            client, po_id, content_type=_PNG_CONTENT_TYPE
        )
    assert status == 415


async def test_upload_pdf_with_wrong_content_type_header_returns_415(env: dict) -> None:
    # Router checks the content_type header, not magic bytes.
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(
            client, po_id, content=_PDF_BYTES, content_type="text/plain"
        )
    assert status == 415


# ---------------------------------------------------------------------------
# D. Size rejection → 413
# ---------------------------------------------------------------------------


async def test_upload_oversized_pdf_returns_413(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, po_id, content=_OVERSIZED_PDF_BYTES)
    assert status == 413


# ---------------------------------------------------------------------------
# E. Empty file rejection → 400
# ---------------------------------------------------------------------------


async def test_upload_empty_file_returns_400(env: dict) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, _ = await _upload(client, po_id, content=b"")
    assert status == 400


# ---------------------------------------------------------------------------
# F. Cross-PO file id leakage guard
# ---------------------------------------------------------------------------


async def test_cross_po_download_returns_404(env: dict) -> None:
    """File uploaded to PO_A must not be downloadable via PO_B's path."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_a_id: str = env["procurement_po"]["id"]
    po_b_id: str = env["opex_po"]["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, po_a_id, file_type=_SIGNED_PO)
        assert status == 201
        file_id: str = body["id"]

        # PO_B path with PO_A's file_id must 404.
        status = await _download(client, po_b_id, file_id)
    assert status == 404


async def test_cross_po_delete_returns_404(env: dict) -> None:
    """File uploaded to PO_A must not be deletable via PO_B's path."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_a_id: str = env["procurement_po"]["id"]
    po_b_id: str = env["opex_po"]["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, po_a_id, file_type=_SIGNED_PO)
        assert status == 201
        file_id = body["id"]

        status = await _delete(client, po_b_id, file_id)
    assert status == 404


# ---------------------------------------------------------------------------
# G. List ordering — uploaded_at DESC
# ---------------------------------------------------------------------------


async def test_list_returns_files_in_uploaded_at_desc_order(env: dict) -> None:
    """Three files uploaded with distinct timestamps must arrive newest-first."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]

    file_ids: list[str] = []
    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        for i in range(3):
            status, body = await _upload(
                client, po_id, file_type=_AMENDMENT, filename=f"doc_{i}.pdf"
            )
            assert status == 201
            file_ids.append(body["id"])
            # Small sleep so inserted_at timestamps differ.
            await asyncio.sleep(0.05)

        status, items = await _list(client, po_id)

    assert status == 200
    assert len(items) == 3
    returned_ids = [item["id"] for item in items]
    # Newest upload is first; file_ids was built in insertion order.
    assert returned_ids == list(reversed(file_ids)), (
        f"expected DESC order {list(reversed(file_ids))}, got {returned_ids}"
    )


# ---------------------------------------------------------------------------
# H. Username denormalization — batch fetch for multiple uploaders
# ---------------------------------------------------------------------------


async def test_list_resolves_uploaded_by_username_for_each_uploader(env: dict) -> None:
    """Two files uploaded by different users must each carry their own username."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    sm_user: User = env["sm"]
    admin_user: User = env["admin"]

    # SM uploads first.
    async with _make_authed_client(conn, upload_dir, fake_email, sm_user) as sm_client:
        status, body = await _upload(sm_client, po_id, file_type=_SIGNED_PO)
        assert status == 201
        sm_file_id: str = body["id"]

    # Admin uploads second.
    async with _make_authed_client(conn, upload_dir, fake_email, admin_user) as admin_client:
        status, body = await _upload(admin_client, po_id, file_type=_COUNTERSIGNED_PO)
        assert status == 201
        admin_file_id: str = body["id"]

        # List as admin; both files should be present.
        status, items = await _list(admin_client, po_id)

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


async def test_upload_to_procurement_po_writes_activity_row_targeting_sm(
    env: dict,
) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, po_id, file_type=_SIGNED_PO)
        assert status == 201

    row = await conn.fetchrow(
        """
        SELECT event, entity_type, entity_id, target_role
        FROM activity_log
        WHERE entity_type = $1 AND entity_id = $2 AND event = $3
        ORDER BY created_at DESC LIMIT 1
        """,
        EntityType.PO.value,
        po_id,
        ActivityEvent.PO_DOCUMENT_UPLOADED.value,
    )
    assert row is not None, "expected one PO_DOCUMENT_UPLOADED activity row"
    assert row["target_role"] == TargetRole.SM.value, (
        f"PROCUREMENT upload must target SM, got {row['target_role']!r}"
    )


async def test_upload_to_opex_po_writes_activity_row_targeting_freight_manager(
    env: dict,
) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["opex_po"]["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, po_id, file_type=_SIGNED_AGREEMENT)
        assert status == 201

    row = await conn.fetchrow(
        """
        SELECT event, entity_type, entity_id, target_role
        FROM activity_log
        WHERE entity_type = $1 AND entity_id = $2 AND event = $3
        ORDER BY created_at DESC LIMIT 1
        """,
        EntityType.PO.value,
        po_id,
        ActivityEvent.PO_DOCUMENT_UPLOADED.value,
    )
    assert row is not None, "expected one PO_DOCUMENT_UPLOADED activity row"
    assert row["target_role"] == TargetRole.FREIGHT_MANAGER.value, (
        f"OPEX upload must target FREIGHT_MANAGER, got {row['target_role']!r}"
    )


async def test_delete_does_not_write_activity_row(env: dict) -> None:
    """DELETE has no activity event (upload-only precedent from iter 046)."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, po_id, file_type=_SIGNED_PO)
        assert status == 201
        file_id: str = body["id"]

        # Count activity rows before delete.
        count_before = await conn.fetchval(
            "SELECT COUNT(*) FROM activity_log WHERE entity_id = $1 AND event = $2",
            po_id,
            ActivityEvent.PO_DOCUMENT_UPLOADED.value,
        )
        status = await _delete(client, po_id, file_id)
        assert status == 204

        count_after = await conn.fetchval(
            "SELECT COUNT(*) FROM activity_log WHERE entity_id = $1 AND event = $2",
            po_id,
            ActivityEvent.PO_DOCUMENT_UPLOADED.value,
        )
    # Delete must not add any new PO_DOCUMENT_UPLOADED rows.
    assert count_after == count_before, (
        "DELETE must not write a PO_DOCUMENT_UPLOADED activity row"
    )


# ---------------------------------------------------------------------------
# J. Delete removes the row; subsequent GET returns 404
# ---------------------------------------------------------------------------


async def test_delete_removes_file_and_subsequent_download_returns_404(
    env: dict,
) -> None:
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]

    async with _make_authed_client(conn, upload_dir, fake_email, env["admin"]) as client:
        status, body = await _upload(client, po_id, file_type=_SIGNED_PO)
        assert status == 201
        file_id: str = body["id"]

        status = await _delete(client, po_id, file_id)
        assert status == 204

        # List must now be empty.
        list_status, items = await _list(client, po_id)
        assert list_status == 200
        assert items == [], f"expected empty list after delete, got {items}"

        # Direct download must 404.
        download_status = await _download(client, po_id, file_id)
    assert download_status == 404


# ---------------------------------------------------------------------------
# Upload response shape
# ---------------------------------------------------------------------------


async def test_upload_response_has_expected_shape(env: dict) -> None:
    """Upload response must carry the full file metadata including resolved username."""
    conn, upload_dir, fake_email = env["conn"], env["upload_dir"], env["fake_email"]
    po_id: str = env["procurement_po"]["id"]
    admin_user: User = env["admin"]

    async with _make_authed_client(conn, upload_dir, fake_email, admin_user) as client:
        status, body = await _upload(
            client, po_id, file_type=_SIGNED_PO, filename="contract.pdf"
        )
    assert status == 201
    # Assert every key is present and has the correct shape.
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
    assert body["entity_type"] == "PO"
    assert body["entity_id"] == po_id
    assert body["file_type"] == _SIGNED_PO
    assert body["original_name"] == "contract.pdf"
    assert body["content_type"] == _PDF_CONTENT_TYPE
    assert body["size_bytes"] == len(_PDF_BYTES)
    assert body["uploaded_by_username"] == admin_user.username
