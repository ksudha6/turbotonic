from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.domain.purchase_order import (
    EDITABLE_LINE_FIELDS,
    LineEditHistoryEntry,
    LineHasDownstreamArtifactError,
    LineItem,
    LineItemStatus,
    POStatus,
    PurchaseOrder,
    RejectionRecord,
)
from src.domain.user import UserRole

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

REVISED_PO_KWARGS = dict(
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


def make_pending_po(line_items: list[LineItem] | None = None) -> PurchaseOrder:
    po = make_po(line_items)
    po.submit()
    return po


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
    assert po.created_at == po.updated_at


def test_create_initialises_negotiation_fields() -> None:
    po = make_po()
    assert po.round_count == 0
    assert po.last_actor_role is None
    assert po.line_edit_history == []


def test_create_with_no_line_items_raises() -> None:
    with pytest.raises(ValueError, match="line item"):
        make_po(line_items=[])


def test_create_with_invalid_quantity_raises() -> None:
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
    assert po.total_value == Decimal("20.00")


# ---------------------------------------------------------------------------
# Status transitions: happy paths
# ---------------------------------------------------------------------------


def test_submit_draft_to_pending() -> None:
    po = make_po()
    po.submit()
    assert po.status is POStatus.PENDING


def test_accept_pending_to_accepted() -> None:
    po = make_pending_po()
    po.accept()
    assert po.status is POStatus.ACCEPTED


def test_accept_sets_all_line_items_accepted() -> None:
    items = [
        make_line_item(part_number="A"),
        make_line_item(part_number="B"),
    ]
    po = make_pending_po(line_items=items)
    po.accept()
    statuses = {item.part_number: item.status for item in po.line_items}
    assert statuses == {"A": LineItemStatus.ACCEPTED, "B": LineItemStatus.ACCEPTED}


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------


def test_accept_from_draft_raises() -> None:
    po = make_po()
    with pytest.raises(ValueError, match="PENDING"):
        po.accept()


def test_submit_from_pending_raises() -> None:
    po = make_pending_po()
    with pytest.raises(ValueError, match="DRAFT"):
        po.submit()


def test_submit_from_accepted_raises() -> None:
    po = make_pending_po()
    po.accept()
    with pytest.raises(ValueError, match="DRAFT"):
        po.submit()


def test_resubmit_from_draft_raises() -> None:
    po = make_po()
    with pytest.raises(ValueError, match="REVISED"):
        po.resubmit()


# ---------------------------------------------------------------------------
# Immutability
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


def test_line_item_default_status_is_pending() -> None:
    item = make_line_item()
    assert item.status is LineItemStatus.PENDING


# ---------------------------------------------------------------------------
# EDITABLE_LINE_FIELDS constant
# ---------------------------------------------------------------------------


def test_editable_line_fields_is_tuple() -> None:
    assert isinstance(EDITABLE_LINE_FIELDS, tuple)


def test_editable_line_fields_content() -> None:
    expected = (
        "quantity",
        "unit_price",
        "uom",
        "description",
        "hs_code",
        "country_of_origin",
        "required_delivery_date",
    )
    assert EDITABLE_LINE_FIELDS == expected


def test_editable_line_fields_excludes_part_number() -> None:
    assert "part_number" not in EDITABLE_LINE_FIELDS


# ---------------------------------------------------------------------------
# modify_line
# ---------------------------------------------------------------------------


def test_modify_line_rejects_non_editable_field() -> None:
    po = make_pending_po()
    with pytest.raises(ValueError, match="not editable"):
        po.modify_line("PN-001", UserRole.VENDOR, {"po_number": "PO-999"})


def test_modify_line_rejects_part_number_change() -> None:
    po = make_pending_po()
    with pytest.raises(ValueError, match="part_number is immutable"):
        po.modify_line("PN-001", UserRole.VENDOR, {"part_number": "PN-999"})


def test_modify_line_quantity_zero_sets_removed() -> None:
    po = make_pending_po()
    po.modify_line("PN-001", UserRole.VENDOR, {"quantity": 0})
    line = po.line_items[0]
    assert line.status is LineItemStatus.REMOVED
    assert line.quantity == 0


def test_modify_line_unknown_part_number_raises() -> None:
    po = make_pending_po()
    with pytest.raises(ValueError, match="unknown part_number"):
        po.modify_line("NOPE", UserRole.VENDOR, {"quantity": 5})


def test_modify_line_rejects_in_draft() -> None:
    po = make_po()
    with pytest.raises(ValueError, match="PENDING or MODIFIED"):
        po.modify_line("PN-001", UserRole.VENDOR, {"quantity": 5})


def test_modify_line_rejects_after_accept_line() -> None:
    po = make_pending_po()
    po.accept_line("PN-001", UserRole.VENDOR)
    with pytest.raises(ValueError, match="terminal status ACCEPTED"):
        po.modify_line("PN-001", UserRole.VENDOR, {"quantity": 5})


def test_modify_line_rejects_after_remove_line() -> None:
    po = make_pending_po()
    po.remove_line("PN-001", UserRole.VENDOR)
    with pytest.raises(ValueError, match="terminal status REMOVED"):
        po.modify_line("PN-001", UserRole.VENDOR, {"quantity": 5})


def test_modify_line_sets_vendor_modified_status() -> None:
    po = make_pending_po()
    po.modify_line("PN-001", UserRole.VENDOR, {"quantity": 7})
    assert po.line_items[0].status is LineItemStatus.MODIFIED_BY_VENDOR


def test_modify_line_sets_sm_modified_status() -> None:
    po = make_pending_po()
    po.modify_line("PN-001", UserRole.SM, {"quantity": 7})
    assert po.line_items[0].status is LineItemStatus.MODIFIED_BY_SM


def test_modify_line_appends_history_per_field() -> None:
    po = make_pending_po()
    po.modify_line(
        "PN-001",
        UserRole.VENDOR,
        {"quantity": 7, "unit_price": Decimal("6.00"), "uom": "BOX"},
    )
    assert len(po.line_edit_history) == 3
    fields_changed = {e.field for e in po.line_edit_history}
    assert fields_changed == {"quantity", "unit_price", "uom"}
    assert all(e.round == 0 for e in po.line_edit_history)
    assert all(e.actor_role is UserRole.VENDOR for e in po.line_edit_history)


def test_modify_line_skips_history_for_unchanged_fields() -> None:
    po = make_pending_po()
    original_uom = po.line_items[0].uom
    po.modify_line("PN-001", UserRole.VENDOR, {"quantity": 7, "uom": original_uom})
    # Only quantity actually changed
    assert len(po.line_edit_history) == 1
    assert po.line_edit_history[0].field == "quantity"


# ---------------------------------------------------------------------------
# accept_line
# ---------------------------------------------------------------------------


def test_accept_line_transitions_to_accepted() -> None:
    po = make_pending_po()
    po.accept_line("PN-001", UserRole.VENDOR)
    assert po.line_items[0].status is LineItemStatus.ACCEPTED


def test_accept_line_rejects_same_role_as_last_modifier() -> None:
    po = make_pending_po()
    po.modify_line("PN-001", UserRole.VENDOR, {"quantity": 7})
    with pytest.raises(ValueError, match="counterpart must accept"):
        po.accept_line("PN-001", UserRole.VENDOR)


def test_accept_line_counterpart_can_accept_vendor_modification() -> None:
    po = make_pending_po()
    po.modify_line("PN-001", UserRole.VENDOR, {"quantity": 7})
    po.accept_line("PN-001", UserRole.SM)
    assert po.line_items[0].status is LineItemStatus.ACCEPTED


def test_accept_line_rejects_already_removed_line() -> None:
    po = make_pending_po()
    po.remove_line("PN-001", UserRole.VENDOR)
    with pytest.raises(ValueError, match="cannot accept"):
        po.accept_line("PN-001", UserRole.SM)


def test_accept_line_unknown_part_number() -> None:
    po = make_pending_po()
    with pytest.raises(ValueError, match="unknown part_number"):
        po.accept_line("NOPE", UserRole.SM)


# ---------------------------------------------------------------------------
# remove_line
# ---------------------------------------------------------------------------


def test_remove_line_transitions_to_removed() -> None:
    po = make_pending_po()
    po.remove_line("PN-001", UserRole.VENDOR)
    assert po.line_items[0].status is LineItemStatus.REMOVED


def test_remove_line_rejects_already_accepted() -> None:
    po = make_pending_po()
    po.accept_line("PN-001", UserRole.VENDOR)
    with pytest.raises(ValueError, match="terminal status ACCEPTED"):
        po.remove_line("PN-001", UserRole.VENDOR)


# ---------------------------------------------------------------------------
# submit_response and convergence
# ---------------------------------------------------------------------------


def _two_line_pending_po() -> PurchaseOrder:
    items = [
        make_line_item(part_number="A"),
        make_line_item(part_number="B"),
    ]
    return make_pending_po(line_items=items)


def test_submit_response_increments_round_count() -> None:
    po = _two_line_pending_po()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    assert po.round_count == 1


def test_submit_response_flips_last_actor_role() -> None:
    po = _two_line_pending_po()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    assert po.last_actor_role is UserRole.VENDOR


def test_submit_response_non_terminal_sets_modified() -> None:
    po = _two_line_pending_po()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    assert po.status is POStatus.MODIFIED


def test_submit_response_convergence_all_accepted() -> None:
    po = _two_line_pending_po()
    po.accept_line("A", UserRole.VENDOR)
    po.accept_line("B", UserRole.VENDOR)
    po.submit_response(UserRole.VENDOR)
    assert po.status is POStatus.ACCEPTED


def test_submit_response_convergence_mix_accepted_and_removed() -> None:
    po = _two_line_pending_po()
    po.accept_line("A", UserRole.VENDOR)
    po.remove_line("B", UserRole.VENDOR)
    po.submit_response(UserRole.VENDOR)
    assert po.status is POStatus.ACCEPTED


def test_submit_response_convergence_all_removed_gives_rejected() -> None:
    po = _two_line_pending_po()
    po.remove_line("A", UserRole.VENDOR)
    po.remove_line("B", UserRole.VENDOR)
    po.submit_response(UserRole.VENDOR)
    assert po.status is POStatus.REJECTED


def test_submit_response_pending_lines_stays_modified() -> None:
    po = _two_line_pending_po()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    assert po.status is POStatus.MODIFIED


def test_submit_response_round_cap_enforced() -> None:
    po = _two_line_pending_po()
    # Round 1
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    # Round 2
    po.modify_line("A", UserRole.SM, {"quantity": 8})
    po.submit_response(UserRole.SM)
    assert po.round_count == 2
    # Further submit_response while lines are still non-terminal must raise.
    po.modify_line("A", UserRole.VENDOR, {"quantity": 9})
    with pytest.raises(ValueError, match="round cap"):
        po.submit_response(UserRole.VENDOR)


# ---------------------------------------------------------------------------
# force_accept_line / force_remove_line
# ---------------------------------------------------------------------------


def _po_at_round_two() -> PurchaseOrder:
    po = _two_line_pending_po()
    # Round 1
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    # Round 2
    po.modify_line("A", UserRole.SM, {"quantity": 8})
    po.submit_response(UserRole.SM)
    # Still contested on line A
    po.modify_line("A", UserRole.VENDOR, {"quantity": 9})
    return po


def test_force_accept_line_rejects_before_round_two() -> None:
    po = _two_line_pending_po()
    with pytest.raises(ValueError, match="round 2"):
        po.force_accept_line("A", UserRole.SM)


def test_force_accept_line_rejects_non_sm_role() -> None:
    po = _po_at_round_two()
    with pytest.raises(ValueError, match="SM role"):
        po.force_accept_line("A", UserRole.VENDOR)


def test_force_accept_line_at_round_two_succeeds() -> None:
    po = _po_at_round_two()
    po.force_accept_line("A", UserRole.SM)
    line_a = next(li for li in po.line_items if li.part_number == "A")
    assert line_a.status is LineItemStatus.ACCEPTED


def test_force_remove_line_rejects_before_round_two() -> None:
    po = _two_line_pending_po()
    with pytest.raises(ValueError, match="round 2"):
        po.force_remove_line("A", UserRole.SM)


def test_force_remove_line_at_round_two_succeeds() -> None:
    po = _po_at_round_two()
    po.force_remove_line("A", UserRole.SM)
    line_a = next(li for li in po.line_items if li.part_number == "A")
    assert line_a.status is LineItemStatus.REMOVED


# ---------------------------------------------------------------------------
# History ordering across rounds
# ---------------------------------------------------------------------------


def test_line_edit_history_preserved_across_rounds() -> None:
    po = _two_line_pending_po()
    po.modify_line("A", UserRole.VENDOR, {"quantity": 7})
    po.submit_response(UserRole.VENDOR)
    po.modify_line("A", UserRole.SM, {"quantity": 8})

    rounds_in_order = [e.round for e in po.line_edit_history]
    assert rounds_in_order == [0, 1]
    assert po.line_edit_history[0].actor_role is UserRole.VENDOR
    assert po.line_edit_history[1].actor_role is UserRole.SM


# ---------------------------------------------------------------------------
# Integration: full round-1 + round-2 + force accept scenario
# ---------------------------------------------------------------------------


def test_full_round_two_with_force_accept() -> None:
    po = _two_line_pending_po()

    # Round 1: vendor modifies A, accepts B, submits
    po.modify_line("A", UserRole.VENDOR, {"quantity": 8})
    po.accept_line("B", UserRole.VENDOR)
    po.submit_response(UserRole.VENDOR)
    assert po.status is POStatus.MODIFIED
    assert po.round_count == 1

    # Round 2: SM counters on A, submits
    po.modify_line("A", UserRole.SM, {"quantity": 9})
    po.submit_response(UserRole.SM)
    assert po.status is POStatus.MODIFIED
    assert po.round_count == 2

    # Vendor still disputes A: submit_response should refuse until forced
    po.modify_line("A", UserRole.VENDOR, {"quantity": 10})
    with pytest.raises(ValueError, match="round cap"):
        po.submit_response(UserRole.VENDOR)

    # SM force-accepts A; then submit_response converges to ACCEPTED
    po.force_accept_line("A", UserRole.SM)
    po.submit_response(UserRole.SM)
    assert po.status is POStatus.ACCEPTED


# ---------------------------------------------------------------------------
# Rejection history accumulates when rejected via convergence
# ---------------------------------------------------------------------------


def test_all_removed_convergence_sets_rejected() -> None:
    items = [
        make_line_item(part_number="A"),
        make_line_item(part_number="B"),
    ]
    po = make_pending_po(line_items=items)
    po.remove_line("A", UserRole.VENDOR)
    po.remove_line("B", UserRole.VENDOR)
    po.submit_response(UserRole.VENDOR)
    assert po.status is POStatus.REJECTED


# ---------------------------------------------------------------------------
# Full happy path (accept convenience)
# ---------------------------------------------------------------------------


def test_happy_path_create_submit_accept() -> None:
    po = make_po()
    assert po.status is POStatus.DRAFT

    po.submit()
    assert po.status is POStatus.PENDING

    po.accept()
    assert po.status is POStatus.ACCEPTED

    assert po.rejection_history == []


# ---------------------------------------------------------------------------
# Iter 059: advance-payment gate and post-acceptance line mutations
# ---------------------------------------------------------------------------


_ADVANCE_KWARGS: dict = {**BASE_PO_KWARGS, "payment_terms": "50_PCT_ADVANCE_50_PCT_BL"}
_FULL_ADVANCE_KWARGS: dict = {**BASE_PO_KWARGS, "payment_terms": "100_PCT_ADVANCE"}


def _make_po_with_terms(payment_terms: str, lines: list[LineItem] | None = None) -> PurchaseOrder:
    kwargs = {**BASE_PO_KWARGS, "payment_terms": payment_terms}
    return PurchaseOrder.create(**kwargs, line_items=lines or [make_line_item()])


def _make_accepted_po(
    payment_terms: str = "TT", lines: list[LineItem] | None = None
) -> PurchaseOrder:
    po = _make_po_with_terms(payment_terms, lines)
    po.submit()
    po.accept()
    return po


def test_requires_advance_true_for_full_advance() -> None:
    po = _make_po_with_terms("100_PCT_ADVANCE")
    assert po.requires_advance is True


def test_requires_advance_true_for_split_advance() -> None:
    po = _make_po_with_terms("50_PCT_ADVANCE_50_PCT_BL")
    assert po.requires_advance is True


def test_requires_advance_false_for_net_terms() -> None:
    po = _make_po_with_terms("NET30")
    assert po.requires_advance is False


def test_requires_advance_false_for_tt() -> None:
    po = _make_po_with_terms("TT")
    assert po.requires_advance is False


def test_mark_advance_paid_sets_timestamp() -> None:
    po = _make_accepted_po("100_PCT_ADVANCE")
    assert po.advance_paid_at is None
    po.mark_advance_paid("actor-1")
    assert po.advance_paid_at is not None


def test_mark_advance_paid_is_idempotent() -> None:
    po = _make_accepted_po("100_PCT_ADVANCE")
    po.mark_advance_paid("actor-1")
    first_ts = po.advance_paid_at
    first_updated = po.updated_at
    po.mark_advance_paid("actor-2")
    # Idempotent: timestamp does not change and updated_at is not bumped.
    assert po.advance_paid_at == first_ts
    assert po.updated_at == first_updated


def test_mark_advance_paid_rejects_draft() -> None:
    po = _make_po_with_terms("100_PCT_ADVANCE")
    with pytest.raises(ValueError, match="ACCEPTED or MODIFIED"):
        po.mark_advance_paid("actor-1")


def test_mark_advance_paid_rejects_pending() -> None:
    po = _make_po_with_terms("100_PCT_ADVANCE")
    po.submit()
    with pytest.raises(ValueError, match="ACCEPTED or MODIFIED"):
        po.mark_advance_paid("actor-1")


def test_mark_advance_paid_rejects_non_advance_terms() -> None:
    po = _make_accepted_po("NET30")
    with pytest.raises(ValueError, match="does not require an advance"):
        po.mark_advance_paid("actor-1")


def test_can_modify_post_acceptance_true_when_clean() -> None:
    po = _make_accepted_po("NET30")
    assert po.can_modify_post_acceptance(first_milestone_posted_at=None) is True


def test_can_modify_post_acceptance_false_when_milestone_posted() -> None:
    po = _make_accepted_po("NET30")
    assert po.can_modify_post_acceptance(first_milestone_posted_at=ISSUED) is False


def test_can_modify_post_acceptance_false_when_advance_paid() -> None:
    po = _make_accepted_po("100_PCT_ADVANCE")
    po.mark_advance_paid("actor-1")
    assert po.can_modify_post_acceptance(first_milestone_posted_at=None) is False


def test_can_modify_post_acceptance_true_advance_required_but_unpaid() -> None:
    po = _make_accepted_po("100_PCT_ADVANCE")
    assert po.can_modify_post_acceptance(first_milestone_posted_at=None) is True


def test_can_modify_post_acceptance_false_when_status_not_accepted() -> None:
    po = _make_po_with_terms("NET30")
    assert po.can_modify_post_acceptance(first_milestone_posted_at=None) is False
    po.submit()
    assert po.can_modify_post_acceptance(first_milestone_posted_at=None) is False


def test_add_line_post_acceptance_adds_line_with_accepted_status() -> None:
    po = _make_accepted_po("NET30")
    new_line = make_line_item(part_number="PN-NEW", quantity=3, unit_price=Decimal("2.00"))
    po.add_line_post_acceptance(new_line, actor_id="actor-1", first_milestone_posted_at=None)
    assert len(po.line_items) == 2
    added = next(li for li in po.line_items if li.part_number == "PN-NEW")
    assert added.status is LineItemStatus.ACCEPTED


def test_add_line_post_acceptance_rejects_when_gate_closed() -> None:
    po = _make_accepted_po("NET30")
    new_line = make_line_item(part_number="PN-NEW")
    with pytest.raises(ValueError, match="modification window is closed"):
        po.add_line_post_acceptance(new_line, actor_id="actor-1", first_milestone_posted_at=ISSUED)


def test_add_line_post_acceptance_rejects_duplicate_part_number() -> None:
    po = _make_accepted_po("NET30")
    dup = make_line_item(part_number="PN-001", quantity=1, unit_price=Decimal("1.00"))
    with pytest.raises(ValueError, match="already exists"):
        po.add_line_post_acceptance(dup, actor_id="actor-1", first_milestone_posted_at=None)


def test_remove_line_post_acceptance_sets_removed() -> None:
    lines = [make_line_item(part_number="A"), make_line_item(part_number="B")]
    po = _make_accepted_po("NET30", lines=lines)
    po.remove_line_post_acceptance(
        "A",
        actor_id="actor-1",
        first_milestone_posted_at=None,
        has_downstream_artifact=False,
    )
    removed = next(li for li in po.line_items if li.part_number == "A")
    assert removed.status is LineItemStatus.REMOVED


def test_remove_line_post_acceptance_blocks_on_downstream_artifact() -> None:
    po = _make_accepted_po("NET30")
    with pytest.raises(LineHasDownstreamArtifactError, match="invoice or shipment"):
        po.remove_line_post_acceptance(
            "PN-001",
            actor_id="actor-1",
            first_milestone_posted_at=None,
            has_downstream_artifact=True,
        )


def test_remove_line_post_acceptance_blocks_when_gate_closed() -> None:
    po = _make_accepted_po("NET30")
    with pytest.raises(ValueError, match="modification window is closed"):
        po.remove_line_post_acceptance(
            "PN-001",
            actor_id="actor-1",
            first_milestone_posted_at=ISSUED,
            has_downstream_artifact=False,
        )


def test_remove_line_post_acceptance_unknown_part_number_raises() -> None:
    po = _make_accepted_po("NET30")
    with pytest.raises(ValueError, match="unknown part_number"):
        po.remove_line_post_acceptance(
            "NOPE",
            actor_id="actor-1",
            first_milestone_posted_at=None,
            has_downstream_artifact=False,
        )


# ---------------------------------------------------------------------------
# PAYMENT_TERMS_METADATA structure
# ---------------------------------------------------------------------------


def test_payment_terms_metadata_advance_flag() -> None:
    from src.domain.reference_data import PAYMENT_TERMS_METADATA
    advance_codes: tuple[str, ...] = (
        "ADV",
        "CIA",
        "50_PCT_ADVANCE_50_PCT_BL",
        "100_PCT_ADVANCE",
    )
    for code in advance_codes:
        assert PAYMENT_TERMS_METADATA[code]["has_advance"] is True, (
            f"{code} must have has_advance=True"
        )
    non_advance_codes: tuple[str, ...] = ("NET30", "TT", "OA", "LC")
    for code in non_advance_codes:
        assert PAYMENT_TERMS_METADATA[code]["has_advance"] is False, (
            f"{code} must have has_advance=False"
        )


def test_valid_payment_terms_is_tuple() -> None:
    from src.domain.reference_data import PAYMENT_TERMS_METADATA, VALID_PAYMENT_TERMS
    assert isinstance(VALID_PAYMENT_TERMS, tuple)
    # Tuple mirrors metadata keys exactly.
    assert set(VALID_PAYMENT_TERMS) == set(PAYMENT_TERMS_METADATA.keys())
