"""Domain unit tests for po_attachment — iter 084 task 13 (domain layer)."""
from __future__ import annotations

import pytest

from src.domain.po_attachment import (
    OPEX_ATTACHMENT_TYPES,
    POAttachmentType,
    PROCUREMENT_ATTACHMENT_TYPES,
    allowed_attachment_types,
    validate_attachment_type,
)
from src.domain.purchase_order import POType

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_ALL_PROCUREMENT_VALUES: tuple[str, ...] = (
    "SIGNED_PO",
    "COUNTERSIGNED_PO",
    "AMENDMENT",
    "ADDENDUM",
)

_ALL_OPEX_VALUES: tuple[str, ...] = (
    "SIGNED_AGREEMENT",
    "AMENDMENT",
    "ADDENDUM",
)

# Cross-rejection pairs: (file_type_string, po_type_that_should_reject_it)
_CROSS_REJECTIONS: tuple[tuple[str, POType], ...] = (
    ("SIGNED_AGREEMENT", POType.PROCUREMENT),
    ("SIGNED_PO", POType.OPEX),
    ("COUNTERSIGNED_PO", POType.OPEX),
)

_EMPTY_AND_WHITESPACE: tuple[str, ...] = ("", "   ", "\t", "\n")


# ---------------------------------------------------------------------------
# allowed_attachment_types
# ---------------------------------------------------------------------------


def test_allowed_attachment_types_procurement_returns_correct_frozenset() -> None:
    # Verifies the single source of truth matches the module constant exactly.
    result = allowed_attachment_types(POType.PROCUREMENT)
    assert result == PROCUREMENT_ATTACHMENT_TYPES


def test_allowed_attachment_types_opex_returns_correct_frozenset() -> None:
    result = allowed_attachment_types(POType.OPEX)
    assert result == OPEX_ATTACHMENT_TYPES


def test_procurement_attachment_types_contains_exactly_expected_values() -> None:
    # Freeze the full set so any accidental addition or removal fails the test.
    expected = frozenset({
        POAttachmentType.SIGNED_PO,
        POAttachmentType.COUNTERSIGNED_PO,
        POAttachmentType.AMENDMENT,
        POAttachmentType.ADDENDUM,
    })
    assert PROCUREMENT_ATTACHMENT_TYPES == expected


def test_opex_attachment_types_contains_exactly_expected_values() -> None:
    expected = frozenset({
        POAttachmentType.SIGNED_AGREEMENT,
        POAttachmentType.AMENDMENT,
        POAttachmentType.ADDENDUM,
    })
    assert OPEX_ATTACHMENT_TYPES == expected


# ---------------------------------------------------------------------------
# validate_attachment_type — happy path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("file_type_str", _ALL_PROCUREMENT_VALUES)
def test_validate_attachment_type_accepts_each_procurement_type(file_type_str: str) -> None:
    result = validate_attachment_type(POType.PROCUREMENT, file_type_str)
    assert result == POAttachmentType(file_type_str)


@pytest.mark.parametrize("file_type_str", _ALL_OPEX_VALUES)
def test_validate_attachment_type_accepts_each_opex_type(file_type_str: str) -> None:
    result = validate_attachment_type(POType.OPEX, file_type_str)
    assert result == POAttachmentType(file_type_str)


# ---------------------------------------------------------------------------
# validate_attachment_type — cross-rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("file_type_str,po_type", _CROSS_REJECTIONS)
def test_validate_attachment_type_rejects_cross_po_type_value(
    file_type_str: str, po_type: POType
) -> None:
    # Guards that OPEX-only types are blocked on PROCUREMENT and vice versa.
    with pytest.raises(ValueError):
        validate_attachment_type(po_type, file_type_str)


# ---------------------------------------------------------------------------
# validate_attachment_type — empty / whitespace
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("blank", _EMPTY_AND_WHITESPACE)
def test_validate_attachment_type_rejects_empty_and_whitespace_strings(blank: str) -> None:
    with pytest.raises(ValueError, match="empty or whitespace"):
        validate_attachment_type(POType.PROCUREMENT, blank)


# ---------------------------------------------------------------------------
# validate_attachment_type — unknown enum value
# ---------------------------------------------------------------------------


def test_validate_attachment_type_rejects_unknown_string_with_chained_exception() -> None:
    # Guards that an unrecognised string raises ValueError with __cause__ set
    # (chained via `from`), so callers can inspect the root cause.
    with pytest.raises(ValueError) as exc_info:
        validate_attachment_type(POType.PROCUREMENT, "FOO")
    assert exc_info.value.__cause__ is not None, (
        "expected ValueError chained with `from` for unrecognised enum value"
    )
