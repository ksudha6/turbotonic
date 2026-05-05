from __future__ import annotations

from enum import Enum


class InvoiceAttachmentType(str, Enum):
    VENDOR_INVOICE_PDF = "VENDOR_INVOICE_PDF"
    CREDIT_NOTE = "CREDIT_NOTE"
    DEBIT_NOTE = "DEBIT_NOTE"
    OTHER = "OTHER"


# All attachment types are valid for any invoice; frozenset enforces immutability.
INVOICE_ATTACHMENT_TYPES: frozenset[InvoiceAttachmentType] = frozenset({
    InvoiceAttachmentType.VENDOR_INVOICE_PDF,
    InvoiceAttachmentType.CREDIT_NOTE,
    InvoiceAttachmentType.DEBIT_NOTE,
    InvoiceAttachmentType.OTHER,
})


def validate_invoice_attachment_type(file_type: str) -> InvoiceAttachmentType:
    """Parse file_type string and verify it is a known InvoiceAttachmentType.

    Strips leading/trailing whitespace before parsing. Raises ValueError if the
    string is empty/whitespace-only or is not a recognised InvoiceAttachmentType
    value. Exceptions are chained with `from` so callers can inspect the root cause.
    """
    if not file_type or not file_type.strip():
        raise ValueError("file_type must not be empty or whitespace-only")

    stripped = file_type.strip()
    try:
        parsed = InvoiceAttachmentType(stripped)
    except ValueError as exc:
        raise ValueError(
            f"{stripped!r} is not a valid InvoiceAttachmentType value; "
            f"allowed: {sorted(t.value for t in INVOICE_ATTACHMENT_TYPES)}"
        ) from exc

    return parsed
