from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import os

import asyncpg
import pytest
import pytest_asyncio

from src.domain.purchase_order import (
    LineItem,
    LineItemStatus,
    POStatus,
    PurchaseOrder,
)
from src.domain.user import UserRole
from src.repository import PurchaseOrderRepository
from src.schema import init_db

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

ISSUED = datetime(2026, 1, 1, tzinfo=UTC)
DELIVERY = datetime(2026, 3, 1, tzinfo=UTC)

BASE_CREATE_KWARGS = dict(
    vendor_id="vendor-abc",
    buyer_name="TurboTonic Ltd",
    buyer_country="US",
    ship_to_address="123 Main St",
    payment_terms="TT",
    currency="USD",
    issued_date=ISSUED,
    required_delivery_date=DELIVERY,
    terms_and_conditions="Standard terms",
    incoterm="FOB",
    port_of_loading="CNSHA",
    port_of_discharge="USLAX",
    country_of_origin="CN",
    country_of_destination="US",
)

REVISE_KWARGS = dict(
    vendor_id="vendor-xyz",
    buyer_name="TurboTonic Ltd",
    buyer_country="US",
    ship_to_address="456 New Ave",
    payment_terms="LC",
    currency="USD",
    issued_date=ISSUED,
    required_delivery_date=DELIVERY,
    terms_and_conditions="Revised terms",
    incoterm="CIF",
    port_of_loading="CNNGB",
    port_of_discharge="USLGB",
    country_of_origin="CN",
    country_of_destination="US",
)


def make_line_item(
    part_number: str = "PN-001",
    quantity: int = 10,
    unit_price: Decimal = Decimal("5.00"),
) -> LineItem:
    return LineItem(
        part_number=part_number,
        description="Widget",
        quantity=quantity,
        uom="EA",
        unit_price=unit_price,
        hs_code="8471.30",
        country_of_origin="CN",
    )


def make_po(po_number: str = "PO-TEST-0001", **overrides: object) -> PurchaseOrder:
    kwargs = dict(**BASE_CREATE_KWARGS, po_number=po_number)
    kwargs.update(overrides)
    if "line_items" not in kwargs:
        kwargs["line_items"] = [make_line_item()]
    return PurchaseOrder.create(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def repo() -> asyncpg.Connection:
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()
    try:
        yield PurchaseOrderRepository(conn)
    finally:
        await tx.rollback()
        await conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id(repo: PurchaseOrderRepository) -> None:
    po = make_po("PO-20260101-0001")
    await repo.save(po)

    retrieved = await repo.get(po.id)

    assert retrieved is not None
    assert retrieved.id == po.id
    assert retrieved.po_number == po.po_number
    assert retrieved.status is POStatus.DRAFT
    assert retrieved.vendor_id == po.vendor_id
    assert retrieved.currency == po.currency
    assert retrieved.issued_date == ISSUED
    assert retrieved.required_delivery_date == DELIVERY
    assert len(retrieved.line_items) == 1
    assert retrieved.line_items[0].part_number == "PN-001"
    assert retrieved.line_items[0].unit_price == Decimal("5.00")
    assert retrieved.rejection_history == []


@pytest.mark.asyncio
async def test_save_and_list_all(repo: PurchaseOrderRepository) -> None:
    po = make_po("PO-20260101-0001")
    await repo.save(po)

    all_pos = await repo.list_pos()

    assert len(all_pos) == 1
    assert all_pos[0].id == po.id


@pytest.mark.asyncio
async def test_list_with_status_filter(repo: PurchaseOrderRepository) -> None:
    draft_po = make_po("PO-20260101-0001")
    await repo.save(draft_po)

    pending_po = make_po("PO-20260101-0002")
    pending_po.submit()
    await repo.save(pending_po)

    drafts = await repo.list_pos(status=POStatus.DRAFT)
    pending = await repo.list_pos(status=POStatus.PENDING)

    assert len(drafts) == 1
    assert drafts[0].id == draft_po.id
    assert len(pending) == 1
    assert pending[0].id == pending_po.id


@pytest.mark.asyncio
async def test_next_po_number_sequential(repo: PurchaseOrderRepository) -> None:
    today = datetime.now(UTC).strftime("%Y%m%d")
    expected_first = f"PO-{today}-0001"
    expected_second = f"PO-{today}-0002"

    first = await repo.next_po_number()
    assert first == expected_first

    po = make_po(first)
    await repo.save(po)

    second = await repo.next_po_number()
    assert second == expected_second


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(repo: PurchaseOrderRepository) -> None:
    result = await repo.get("nonexistent-id-that-does-not-exist")
    assert result is None


# ---------------------------------------------------------------------------
# Iter 056: round_count, MODIFIED status, REMOVED line status, line_edit_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_round_count_persists_through_save_and_get(repo: PurchaseOrderRepository) -> None:
    items = [make_line_item(part_number="A"), make_line_item(part_number="B")]
    po = make_po("PO-20260101-RC01", line_items=items)
    po.submit()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    await repo.save(po)

    retrieved = await repo.get(po.id)
    assert retrieved is not None
    assert retrieved.round_count == 1
    assert retrieved.last_actor_role is UserRole.VENDOR


@pytest.mark.asyncio
async def test_modified_po_status_round_trips(repo: PurchaseOrderRepository) -> None:
    items = [make_line_item(part_number="A"), make_line_item(part_number="B")]
    po = make_po("PO-20260101-MOD1", line_items=items)
    po.submit()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    await repo.save(po)

    retrieved = await repo.get(po.id)
    assert retrieved is not None
    assert retrieved.status is POStatus.MODIFIED


@pytest.mark.asyncio
async def test_removed_line_status_round_trips(repo: PurchaseOrderRepository) -> None:
    items = [make_line_item(part_number="A"), make_line_item(part_number="B")]
    po = make_po("PO-20260101-REM1", line_items=items)
    po.submit()
    po.remove_line("A", UserRole.VENDOR)
    await repo.save(po)

    retrieved = await repo.get(po.id)
    assert retrieved is not None
    line_a = next(li for li in retrieved.line_items if li.part_number == "A")
    assert line_a.status is LineItemStatus.REMOVED


@pytest.mark.asyncio
async def test_line_edit_history_persists_in_order(repo: PurchaseOrderRepository) -> None:
    items = [make_line_item(part_number="A"), make_line_item(part_number="B")]
    po = make_po("PO-20260101-HIS1", line_items=items)
    po.submit()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    po.modify_line("A", UserRole.SM, {"quantity": 8})
    await repo.save(po)

    retrieved = await repo.get(po.id)
    assert retrieved is not None
    rounds = [e.round for e in retrieved.line_edit_history]
    assert rounds == [0, 1]
    actors = [e.actor_role for e in retrieved.line_edit_history]
    assert actors == [UserRole.VENDOR, UserRole.SM]


@pytest.mark.asyncio
async def test_list_pagination_returns_round_count(repo: PurchaseOrderRepository) -> None:
    items = [make_line_item(part_number="A"), make_line_item(part_number="B")]
    po = make_po("PO-20260101-LST1", line_items=items)
    po.submit()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    await repo.save(po)

    rows, _ = await repo.list_pos_paginated(page=1, page_size=20)
    assert len(rows) == 1
    assert rows[0]["round_count"] == 1
