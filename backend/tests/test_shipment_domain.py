from __future__ import annotations

import re

import pytest

from src.domain.shipment import (
    Shipment,
    ShipmentLineItem,
    ShipmentStatus,
    validate_shipment_quantities,
)

SHIPMENT_NUMBER_RE = re.compile(r"^SHP-\d{8}-[0-9A-F]{4}$")
PO_ID = "po-001"
MARKETPLACE = "AMAZON"
PART_A = "PART-A"
PART_B = "PART-B"


def _make_item(part_number: str = PART_A, quantity: int = 10) -> ShipmentLineItem:
    return ShipmentLineItem(
        part_number=part_number,
        product_id=None,
        description="desc",
        quantity=quantity,
        uom="PCS",
    )


def _make_shipment(line_items: list[ShipmentLineItem] | None = None) -> Shipment:
    return Shipment.create(
        po_id=PO_ID,
        marketplace=MARKETPLACE,
        line_items=line_items or [_make_item()],
    )


# --- ShipmentLineItem validation ---

def test_line_item_rejects_empty_part_number():
    with pytest.raises(ValueError, match="part_number"):
        ShipmentLineItem(part_number="", product_id=None, description="", quantity=1, uom="PCS")


def test_line_item_rejects_whitespace_part_number():
    with pytest.raises(ValueError, match="part_number"):
        ShipmentLineItem(part_number="   ", product_id=None, description="", quantity=1, uom="PCS")


def test_line_item_rejects_zero_quantity():
    with pytest.raises(ValueError, match="quantity"):
        ShipmentLineItem(part_number=PART_A, product_id=None, description="", quantity=0, uom="PCS")


def test_line_item_rejects_negative_quantity():
    with pytest.raises(ValueError, match="quantity"):
        ShipmentLineItem(part_number=PART_A, product_id=None, description="", quantity=-5, uom="PCS")


# --- Shipment.create ---

def test_create_generates_shipment_number():
    s = _make_shipment()
    assert SHIPMENT_NUMBER_RE.match(s.shipment_number), f"bad format: {s.shipment_number}"


def test_create_starts_in_draft():
    s = _make_shipment()
    assert s.status is ShipmentStatus.DRAFT


def test_create_sets_immutable_fields():
    s = _make_shipment()
    assert s.id is not None
    assert s.created_at is not None
    original_id = s.id
    original_number = s.shipment_number
    original_created_at = s.created_at
    # Confirm properties are immutable (setting raises AttributeError)
    with pytest.raises(AttributeError):
        s.id = "new-id"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        s.shipment_number = "new-num"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        s.created_at = s.created_at  # type: ignore[misc]
    assert s.id == original_id
    assert s.shipment_number == original_number
    assert s.created_at == original_created_at


def test_create_rejects_empty_line_items():
    with pytest.raises(ValueError, match="at least one line item"):
        Shipment.create(po_id=PO_ID, marketplace=MARKETPLACE, line_items=[])


# --- Status transitions ---

def test_submit_for_documents_transitions_draft_to_documents_pending():
    s = _make_shipment()
    s.submit_for_documents()
    assert s.status is ShipmentStatus.DOCUMENTS_PENDING


def test_submit_for_documents_rejects_non_draft():
    s = _make_shipment()
    s.submit_for_documents()
    with pytest.raises(ValueError, match="DRAFT"):
        s.submit_for_documents()


def test_mark_ready_transitions_documents_pending_to_ready():
    s = _make_shipment()
    s.submit_for_documents()
    s.mark_ready()
    assert s.status is ShipmentStatus.READY_TO_SHIP


def test_mark_ready_rejects_draft():
    s = _make_shipment()
    with pytest.raises(ValueError, match="DOCUMENTS_PENDING"):
        s.mark_ready()


def test_mark_ready_rejects_ready_to_ship():
    s = _make_shipment()
    s.submit_for_documents()
    s.mark_ready()
    with pytest.raises(ValueError, match="DOCUMENTS_PENDING"):
        s.mark_ready()


# --- validate_shipment_quantities ---

def _po_items(
    part_number: str = PART_A,
    quantity: int = 100,
    status: str = "ACCEPTED",
) -> list[dict[str, object]]:
    return [{"part_number": part_number, "quantity": quantity, "status": status}]


def test_validate_passes_within_accepted_qty():
    validate_shipment_quantities(
        _po_items(quantity=100),
        [],
        [_make_item(quantity=50)],
    )  # should not raise


def test_validate_passes_exact_accepted_qty():
    validate_shipment_quantities(
        _po_items(quantity=100),
        [],
        [_make_item(quantity=100)],
    )


def test_validate_rejects_over_accepted_qty():
    with pytest.raises(ValueError, match=PART_A):
        validate_shipment_quantities(
            _po_items(quantity=50),
            [],
            [_make_item(quantity=51)],
        )


def test_validate_cumulative_over_accepted_qty():
    existing = _make_shipment([_make_item(quantity=80)])
    with pytest.raises(ValueError, match=PART_A):
        validate_shipment_quantities(
            _po_items(quantity=100),
            [existing],
            [_make_item(quantity=21)],
        )


def test_validate_cumulative_within_accepted_qty():
    existing = _make_shipment([_make_item(quantity=80)])
    validate_shipment_quantities(
        _po_items(quantity=100),
        [existing],
        [_make_item(quantity=20)],
    )  # should not raise


def test_validate_rejects_removed_line_item():
    # Iter 056: REMOVED replaces REJECTED at the line level.
    po_items: list[dict[str, object]] = [
        {"part_number": PART_A, "quantity": 100, "status": "REMOVED"}
    ]
    with pytest.raises(ValueError, match="REMOVED"):
        validate_shipment_quantities(po_items, [], [_make_item()])


def test_validate_rejects_pending_line_item():
    po_items: list[dict[str, object]] = [
        {"part_number": PART_A, "quantity": 100, "status": "PENDING"}
    ]
    with pytest.raises(ValueError, match="PENDING"):
        validate_shipment_quantities(po_items, [], [_make_item()])


def test_validate_rejects_unknown_part_number():
    with pytest.raises(ValueError, match="not found"):
        validate_shipment_quantities(
            _po_items(),
            [],
            [_make_item(part_number="UNKNOWN")],
        )
