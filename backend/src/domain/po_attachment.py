from __future__ import annotations

from enum import Enum

from src.domain.purchase_order import POType


class POAttachmentType(str, Enum):
    SIGNED_PO = "SIGNED_PO"
    COUNTERSIGNED_PO = "COUNTERSIGNED_PO"
    SIGNED_AGREEMENT = "SIGNED_AGREEMENT"
    AMENDMENT = "AMENDMENT"
    ADDENDUM = "ADDENDUM"


# PROCUREMENT POs accept four attachment types; frozenset enforces immutability.
PROCUREMENT_ATTACHMENT_TYPES: frozenset[POAttachmentType] = frozenset({
    POAttachmentType.SIGNED_PO,
    POAttachmentType.COUNTERSIGNED_PO,
    POAttachmentType.AMENDMENT,
    POAttachmentType.ADDENDUM,
})

# OPEX POs accept three attachment types; SIGNED_PO and COUNTERSIGNED_PO are
# procurement-specific concepts that do not apply to service/utility agreements.
OPEX_ATTACHMENT_TYPES: frozenset[POAttachmentType] = frozenset({
    POAttachmentType.SIGNED_AGREEMENT,
    POAttachmentType.AMENDMENT,
    POAttachmentType.ADDENDUM,
})


def allowed_attachment_types(po_type: POType) -> frozenset[POAttachmentType]:
    """Return the allowed attachment types for the given PO type.

    Single source of truth used by validate_attachment_type and the frontend
    vocabulary mirror. Raises ValueError for unknown po_type values.
    """
    if po_type is POType.PROCUREMENT:
        return PROCUREMENT_ATTACHMENT_TYPES
    if po_type is POType.OPEX:
        return OPEX_ATTACHMENT_TYPES
    raise ValueError(f"unknown po_type: {po_type!r}")


def validate_attachment_type(po_type: POType, file_type: str) -> POAttachmentType:
    """Parse file_type string and verify it is allowed for po_type.

    Strips leading/trailing whitespace before parsing. Raises ValueError if the
    string is empty/whitespace-only, is not a recognised POAttachmentType value,
    or is not in the allowed set for po_type. Exceptions are chained with `from`
    so callers can inspect the root cause.
    """
    if not file_type or not file_type.strip():
        raise ValueError("file_type must not be empty or whitespace-only")

    stripped = file_type.strip()
    try:
        parsed = POAttachmentType(stripped)
    except ValueError as exc:
        raise ValueError(
            f"{stripped!r} is not a valid POAttachmentType value"
        ) from exc

    allowed = allowed_attachment_types(po_type)
    if parsed not in allowed:
        raise ValueError(
            f"{parsed.value!r} is not allowed for {po_type.value} POs; "
            f"allowed types: {sorted(t.value for t in allowed)}"
        )

    return parsed
