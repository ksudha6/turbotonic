from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.domain.purchase_order import (
    LineItem,
    POStatus,
    PurchaseOrder,
    RejectionRecord,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

ISSUED = datetime(2026, 1, 1, tzinfo=UTC)
DELIVERY = datetime(2026, 3, 1, tzinfo=UTC)

BASE_PO_KWARGS = dict(
    po_number="PO-001",
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

REVISED_PO_KWARGS = dict(
    po_number="PO-001",
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
    description: str = "Widget",
    quantity: int = 10,
    uom: str = "EA",
    unit_price: Decimal = Decimal("5.00"),
    hs_code: str = "8471.30",
    country_of_origin: str = "CN",
) -> LineItem:
    return LineItem(
        part_number=part_number,
        description=description,
        quantity=quantity,
        uom=uom,
        unit_price=unit_price,
        hs_code=hs_code,
        country_of_origin=country_of_origin,
    )


def make_po(line_items: list[LineItem] | None = None) -> PurchaseOrder:
    items = line_items if line_items is not None else [make_line_item()]
    return PurchaseOrder.create(**BASE_PO_KWARGS, line_items=items)


# ---------------------------------------------------------------------------
# LineItem validation
# ---------------------------------------------------------------------------


def test_line_item_rejects_zero_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        make_line_item(quantity=0)


def test_line_item_rejects_negative_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        make_line_item(quantity=-1)


def test_line_item_rejects_negative_unit_price() -> None:
    with pytest.raises(ValueError, match="unit_price"):
        make_line_item(unit_price=Decimal("-0.01"))


def test_line_item_allows_zero_unit_price() -> None:
    # Free items are valid (samples, no-charge lines)
    item = make_line_item(unit_price=Decimal("0"))
    assert item.unit_price == Decimal("0")


def test_line_item_rejects_empty_part_number() -> None:
    with pytest.raises(ValueError, match="part_number"):
        make_line_item(part_number="")


def test_line_item_rejects_whitespace_part_number() -> None:
    with pytest.raises(ValueError, match="part_number"):
        make_line_item(part_number="   ")


# ---------------------------------------------------------------------------
# PurchaseOrder.create
# ---------------------------------------------------------------------------


def test_create_produces_draft_status() -> None:
    po = make_po()
    assert po.status is POStatus.DRAFT


def test_create_assigns_id() -> None:
    po = make_po()
    assert po.id and len(po.id) == 36  # uuid4 canonical form


def test_create_sets_timestamps() -> None:
    po = make_po()
    # created_at and updated_at are set to the same moment on creation
    assert po.created_at == po.updated_at


def test_create_with_no_line_items_raises() -> None:
    with pytest.raises(ValueError, match="line item"):
        make_po(line_items=[])


def test_create_with_invalid_quantity_raises() -> None:
    # LineItem validation fires before PurchaseOrder.create validates item count
    with pytest.raises(ValueError, match="quantity"):
        make_po(line_items=[make_line_item(quantity=0)])


def test_create_with_negative_unit_price_raises() -> None:
    with pytest.raises(ValueError, match="unit_price"):
        make_po(line_items=[make_line_item(unit_price=Decimal("-1"))])


def test_create_with_empty_part_number_raises() -> None:
    with pytest.raises(ValueError, match="part_number"):
        make_po(line_items=[make_line_item(part_number="")])


# ---------------------------------------------------------------------------
# total_value
# ---------------------------------------------------------------------------


def test_total_value_single_line() -> None:
    item = make_line_item(quantity=3, unit_price=Decimal("10.00"))
    po = make_po(line_items=[item])
    assert po.total_value == Decimal("30.00")


def test_total_value_multiple_lines() -> None:
    items = [
        make_line_item(part_number="A", quantity=2, unit_price=Decimal("5.00")),
        make_line_item(part_number="B", quantity=4, unit_price=Decimal("2.50")),
    ]
    po = make_po(line_items=items)
    # 2*5 + 4*2.5 = 10 + 10 = 20
    assert po.total_value == Decimal("20.00")


# ---------------------------------------------------------------------------
# Status transitions: happy paths
# ---------------------------------------------------------------------------


def test_submit_draft_to_pending() -> None:
    po = make_po()
    po.submit()
    assert po.status is POStatus.PENDING


def test_accept_pending_to_accepted() -> None:
    po = make_po()
    po.submit()
    po.accept()
    assert po.status is POStatus.ACCEPTED


def test_reject_pending_to_rejected() -> None:
    po = make_po()
    po.submit()
    po.reject("Price too high")
    assert po.status is POStatus.REJECTED


def test_reject_appends_rejection_record() -> None:
    comment = "Delivery date unacceptable"
    po = make_po()
    po.submit()
    po.reject(comment)
    assert len(po.rejection_history) == 1
    record = po.rejection_history[0]
    assert record.comment == comment
    assert isinstance(record.rejected_at, datetime)


def test_revise_rejected_to_revised() -> None:
    po = make_po()
    po.submit()
    po.reject("Too expensive")
    new_item = make_line_item(part_number="PN-002", unit_price=Decimal("3.00"))
    po.revise(**{k: v for k, v in REVISED_PO_KWARGS.items() if k != "po_number"}, line_items=[new_item])
    assert po.status is POStatus.REVISED


def test_revise_updates_fields() -> None:
    po = make_po()
    po.submit()
    po.reject("Too expensive")
    new_item = make_line_item(part_number="PN-002", unit_price=Decimal("3.00"))
    po.revise(
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
        line_items=[new_item],
    )
    assert po.vendor_id == "vendor-xyz"
    assert po.ship_to_address == "456 New Ave"
    assert po.payment_terms == "Net 60"
    assert po.incoterm == "CIF"
    assert po.line_items == [new_item]


def test_resubmit_revised_to_pending() -> None:
    po = make_po()
    po.submit()
    po.reject("Too expensive")
    new_item = make_line_item(part_number="PN-002", unit_price=Decimal("3.00"))
    po.revise(
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
        line_items=[new_item],
    )
    po.resubmit()
    assert po.status is POStatus.PENDING


# ---------------------------------------------------------------------------
# Reject comment validation
# ---------------------------------------------------------------------------


def test_reject_with_empty_comment_raises() -> None:
    po = make_po()
    po.submit()
    with pytest.raises(ValueError, match="comment"):
        po.reject("")


def test_reject_with_whitespace_comment_raises() -> None:
    po = make_po()
    po.submit()
    with pytest.raises(ValueError, match="comment"):
        po.reject("   ")


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------


def test_accept_from_draft_raises() -> None:
    po = make_po()
    with pytest.raises(ValueError, match="PENDING"):
        po.accept()


def test_submit_from_pending_raises() -> None:
    po = make_po()
    po.submit()
    with pytest.raises(ValueError, match="DRAFT"):
        po.submit()


def test_reject_from_draft_raises() -> None:
    po = make_po()
    with pytest.raises(ValueError, match="PENDING"):
        po.reject("some reason")


def test_submit_from_accepted_raises() -> None:
    po = make_po()
    po.submit()
    po.accept()
    with pytest.raises(ValueError, match="DRAFT"):
        po.submit()


def test_reject_from_accepted_raises() -> None:
    po = make_po()
    po.submit()
    po.accept()
    with pytest.raises(ValueError, match="PENDING"):
        po.reject("too late")


def test_revise_from_draft_raises() -> None:
    po = make_po()
    with pytest.raises(ValueError, match="REJECTED"):
        po.revise(
            vendor_id="v",
            buyer_name="TurboTonic Ltd",
            buyer_country="US",
            ship_to_address="a",
            payment_terms="t",
            currency="USD",
            issued_date=ISSUED,
            required_delivery_date=DELIVERY,
            terms_and_conditions="tc",
            incoterm="FOB",
            port_of_loading="x",
            port_of_discharge="y",
            country_of_origin="CN",
            country_of_destination="US",
            line_items=[make_line_item()],
        )


def test_resubmit_from_draft_raises() -> None:
    po = make_po()
    with pytest.raises(ValueError, match="REVISED"):
        po.resubmit()


# ---------------------------------------------------------------------------
# Revise validation
# ---------------------------------------------------------------------------


def test_revise_with_no_line_items_raises() -> None:
    po = make_po()
    po.submit()
    po.reject("Too expensive")
    with pytest.raises(ValueError, match="line item"):
        po.revise(
            vendor_id="v",
            buyer_name="TurboTonic Ltd",
            buyer_country="US",
            ship_to_address="a",
            payment_terms="t",
            currency="USD",
            issued_date=ISSUED,
            required_delivery_date=DELIVERY,
            terms_and_conditions="tc",
            incoterm="FOB",
            port_of_loading="x",
            port_of_discharge="y",
            country_of_origin="CN",
            country_of_destination="US",
            line_items=[],
        )


# ---------------------------------------------------------------------------
# Full happy path
# ---------------------------------------------------------------------------


def test_happy_path_create_submit_accept() -> None:
    po = make_po()
    assert po.status is POStatus.DRAFT

    po.submit()
    assert po.status is POStatus.PENDING

    po.accept()
    assert po.status is POStatus.ACCEPTED

    # Rejection history must be empty throughout a clean approval
    assert po.rejection_history == []


# ---------------------------------------------------------------------------
# Full reject/revise path
# ---------------------------------------------------------------------------


def test_reject_revise_resubmit_accept_path() -> None:
    po = make_po()
    po.submit()
    po.reject("Price too high")

    assert po.status is POStatus.REJECTED
    assert len(po.rejection_history) == 1

    new_item = make_line_item(part_number="PN-002", unit_price=Decimal("3.00"))
    po.revise(
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
        line_items=[new_item],
    )
    assert po.status is POStatus.REVISED

    po.resubmit()
    assert po.status is POStatus.PENDING

    po.accept()
    assert po.status is POStatus.ACCEPTED

    # Rejection record from the first cycle persists
    assert len(po.rejection_history) == 1
    assert po.rejection_history[0].comment == "Price too high"


# ---------------------------------------------------------------------------
# Rejection history accumulates across multiple cycles
# ---------------------------------------------------------------------------


def test_rejection_history_accumulates() -> None:
    po = make_po()
    po.submit()
    po.reject("First rejection")

    revision_item = make_line_item(part_number="PN-002", unit_price=Decimal("4.00"))
    po.revise(
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
        line_items=[revision_item],
    )
    po.resubmit()
    po.reject("Second rejection")

    comments = [r.comment for r in po.rejection_history]
    assert comments == ["First rejection", "Second rejection"], (
        "rejection history must contain all rejection records in order"
    )


# ---------------------------------------------------------------------------
# Immutability: identity and audit fields are read-only
# ---------------------------------------------------------------------------


def test_id_is_read_only() -> None:
    po = make_po()
    with pytest.raises(AttributeError):
        po.id = "new-id"  # type: ignore[misc]


def test_po_number_is_read_only() -> None:
    po = make_po()
    with pytest.raises(AttributeError):
        po.po_number = "new"  # type: ignore[misc]


def test_created_at_is_read_only() -> None:
    po = make_po()
    with pytest.raises(AttributeError):
        po.created_at = datetime.now(UTC)  # type: ignore[misc]
