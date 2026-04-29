from __future__ import annotations

import os
from typing import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio

from src.schema import init_db
from src.seed import seed

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)


@pytest_asyncio.fixture
async def seeded_conn() -> AsyncIterator[asyncpg.Connection]:
    # Seed into a transaction that is rolled back at teardown so the test leaves
    # no rows behind. init_db is idempotent; seed() early-exits when users exist
    # so the transaction must be clean before calling it.
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    # seed() opens its own transaction; asyncpg nests this as a savepoint.
    tx = conn.transaction()
    await tx.start()
    try:
        await seed(conn)
        yield conn
    finally:
        await tx.rollback()
        await conn.close()


@pytest.mark.asyncio
async def test_seed_vendors_variety(seeded_conn: asyncpg.Connection) -> None:
    vendor_count = await seeded_conn.fetchval("SELECT COUNT(*) FROM vendors")
    vendor_type_count = await seeded_conn.fetchval(
        "SELECT COUNT(DISTINCT vendor_type) FROM vendors"
    )
    country_count = await seeded_conn.fetchval(
        "SELECT COUNT(DISTINCT country) FROM vendors"
    )
    assert vendor_count >= 5, f"expected >=5 vendors, got {vendor_count}"
    assert vendor_type_count >= 3, f"expected >=3 vendor types, got {vendor_type_count}"
    assert country_count >= 5, f"expected >=5 countries, got {country_count}"


@pytest.mark.asyncio
async def test_seed_purchase_orders_variety(seeded_conn: asyncpg.Connection) -> None:
    po_count = await seeded_conn.fetchval("SELECT COUNT(*) FROM purchase_orders")
    po_status_count = await seeded_conn.fetchval(
        "SELECT COUNT(DISTINCT status) FROM purchase_orders"
    )
    assert po_count >= 10, f"expected >=10 POs, got {po_count}"
    assert po_status_count >= 4, f"expected >=4 distinct PO statuses, got {po_status_count}"


@pytest.mark.asyncio
async def test_seed_invoices_variety(seeded_conn: asyncpg.Connection) -> None:
    invoice_count = await seeded_conn.fetchval("SELECT COUNT(*) FROM invoices")
    invoice_status_count = await seeded_conn.fetchval(
        "SELECT COUNT(DISTINCT status) FROM invoices"
    )
    assert invoice_count >= 6, f"expected >=6 invoices, got {invoice_count}"
    assert (
        invoice_status_count >= 3
    ), f"expected >=3 distinct invoice statuses, got {invoice_status_count}"


@pytest.mark.asyncio
async def test_seed_milestones_variety(seeded_conn: asyncpg.Connection) -> None:
    milestone_count = await seeded_conn.fetchval(
        "SELECT COUNT(*) FROM milestone_updates"
    )
    milestone_stage_count = await seeded_conn.fetchval(
        "SELECT COUNT(DISTINCT milestone) FROM milestone_updates"
    )
    distinct_pos = await seeded_conn.fetchval(
        "SELECT COUNT(DISTINCT po_id) FROM milestone_updates"
    )
    assert milestone_count >= 6, f"expected >=6 milestone rows, got {milestone_count}"
    assert (
        milestone_stage_count >= 3
    ), f"expected >=3 distinct stages, got {milestone_stage_count}"
    assert distinct_pos >= 3, f"expected milestones on >=3 POs, got {distinct_pos}"


@pytest.mark.asyncio
async def test_seed_activity_variety(seeded_conn: asyncpg.Connection) -> None:
    activity_count = await seeded_conn.fetchval("SELECT COUNT(*) FROM activity_log")
    event_type_count = await seeded_conn.fetchval(
        "SELECT COUNT(DISTINCT event) FROM activity_log"
    )
    assert activity_count >= 15, f"expected >=15 activity rows, got {activity_count}"
    assert (
        event_type_count >= 6
    ), f"expected >=6 distinct event types, got {event_type_count}"


@pytest.mark.asyncio
async def test_seed_users_variety(seeded_conn: asyncpg.Connection) -> None:
    user_role_count = await seeded_conn.fetchval(
        "SELECT COUNT(DISTINCT role) FROM users"
    )
    assert user_role_count >= 3, f"expected >=3 distinct roles, got {user_role_count}"

    # Deterministic usernames from earlier seed revisions must remain so that
    # existing tests and docs that reference them keep working.
    known_usernames = {"alice", "bob", "carol", "dave", "erin", "frank"}
    rows = await seeded_conn.fetch("SELECT username FROM users")
    present = {r["username"] for r in rows}
    missing = known_usernames - present
    assert not missing, f"lost fixture usernames: {missing}"


@pytest.mark.asyncio
async def test_seed_po_attachments(seeded_conn: asyncpg.Connection) -> None:
    # At least one SIGNED_PO file must be attached to a PROCUREMENT PO.
    procurement_pos_with_signed_pdf = await seeded_conn.fetchval(
        """
        SELECT COUNT(*)
        FROM files f
        JOIN purchase_orders p ON p.id = f.entity_id
        WHERE f.entity_type = 'PO'
          AND f.file_type = 'SIGNED_PO'
          AND p.po_type = 'PROCUREMENT'
        """
    )
    assert procurement_pos_with_signed_pdf >= 1, (
        f"expected >=1 SIGNED_PO file on a PROCUREMENT PO, got {procurement_pos_with_signed_pdf}"
    )

    # At least one SIGNED_AGREEMENT file must be attached to an OPEX PO.
    opex_pos_with_signed_agreement_pdf = await seeded_conn.fetchval(
        """
        SELECT COUNT(*)
        FROM files f
        JOIN purchase_orders p ON p.id = f.entity_id
        WHERE f.entity_type = 'PO'
          AND f.file_type = 'SIGNED_AGREEMENT'
          AND p.po_type = 'OPEX'
        """
    )
    assert opex_pos_with_signed_agreement_pdf >= 1, (
        f"expected >=1 SIGNED_AGREEMENT file on an OPEX PO, got {opex_pos_with_signed_agreement_pdf}"
    )
