from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import aiosqlite
import pytest
import pytest_asyncio

from src.domain.purchase_order import (
    LineItem,
    POStatus,
    PurchaseOrder,
    RejectionRecord,
)
from src.repository import PurchaseOrderRepository
from src.schema import init_db

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
    payment_terms="Net 30",
    currency="USD",
    issued_date=ISSUED,
    required_delivery_date=DELIVERY,
    terms_and_conditions="Standard terms",
    incoterm="FOB",
    port_of_loading="Shanghai",
    port_of_discharge="Los Angeles",
    country_of_origin="CN",
    country_of_destination="US",
)

REVISE_KWARGS = dict(
    vendor_id="vendor-xyz",
    buyer_name="TurboTonic Ltd",
    buyer_country="US",
    ship_to_address="456 New Ave",
    payment_terms="Net 60",
    currency="USD",
    issued_date=ISSUED,
    required_delivery_date=DELIVERY,
    terms_and_conditions="Revised terms",
    incoterm="CIF",
    port_of_loading="Guangzhou",
    port_of_discharge="Long Beach",
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
async def repo() -> aiosqlite.Connection:
    async with aiosqlite.connect(":memory:") as conn:
        await init_db(conn)
        yield PurchaseOrderRepository(conn)


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
async def test_update_po_persists_rejection(repo: PurchaseOrderRepository) -> None:
    rejection_comment = "Price is too high"

    po = make_po("PO-20260101-0001")
    await repo.save(po)

    po.submit()
    po.reject(rejection_comment)
    await repo.save(po)

    retrieved = await repo.get(po.id)

    assert retrieved is not None
    assert retrieved.status is POStatus.REJECTED
    assert len(retrieved.rejection_history) == 1
    assert retrieved.rejection_history[0].comment == rejection_comment


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


@pytest.mark.asyncio
async def test_rejection_history_accumulates_across_cycles(
    repo: PurchaseOrderRepository,
) -> None:
    first_comment = "Price too high"
    second_comment = "Delivery date still unacceptable"

    po = make_po("PO-20260101-0001")
    await repo.save(po)

    # First rejection cycle.
    po.submit()
    po.reject(first_comment)
    await repo.save(po)

    revision_item = make_line_item(part_number="PN-002", unit_price=Decimal("3.00"))
    po.revise(**REVISE_KWARGS, line_items=[revision_item])
    po.resubmit()
    po.reject(second_comment)
    await repo.save(po)

    retrieved = await repo.get(po.id)

    assert retrieved is not None
    assert len(retrieved.rejection_history) == 2
    assert retrieved.rejection_history[0].comment == first_comment
    assert retrieved.rejection_history[1].comment == second_comment
