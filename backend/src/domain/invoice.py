from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4


class InvoiceStatus(Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    DISPUTED = "DISPUTED"


@dataclass
class InvoiceLineItem:
    part_number: str
    description: str
    quantity: int
    uom: str
    unit_price: Decimal


class Invoice:
    # id owns the aggregate identity; invoice_number owns the business reference
    def __init__(
        self,
        *,
        id: str,
        invoice_number: str,
        po_id: str,
        status: InvoiceStatus,
        payment_terms: str,
        currency: str,
        line_items: list[InvoiceLineItem],
        dispute_reason: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._invoice_number = invoice_number
        self.po_id = po_id
        self.status = status
        self.payment_terms = payment_terms
        self.currency = currency
        self.line_items = line_items
        self.dispute_reason = dispute_reason
        self._created_at = created_at
        self.updated_at = updated_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def invoice_number(self) -> str:
        return self._invoice_number

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def subtotal(self) -> Decimal:
        return sum(
            (item.quantity * item.unit_price for item in self.line_items),
            Decimal("0"),
        )

    @classmethod
    def create(
        cls,
        *,
        invoice_number: str,
        po_id: str,
        po_status: str,
        po_type: str,
        payment_terms: str,
        currency: str,
        line_items: list[InvoiceLineItem],
    ) -> Invoice:
        if po_status != "ACCEPTED":
            raise ValueError("invoice creation requires PO status ACCEPTED")
        if po_type not in ("PROCUREMENT", "OPEX"):
            raise ValueError(f"invoice creation is not supported for PO type {po_type}")
        if not line_items:
            raise ValueError("at least one line item is required")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            invoice_number=invoice_number,
            po_id=po_id,
            status=InvoiceStatus.DRAFT,
            payment_terms=payment_terms,
            currency=currency,
            line_items=list(line_items),
            dispute_reason="",
            created_at=now,
            updated_at=now,
        )

    def submit(self) -> None:
        # DRAFT is the only state from which an invoice enters the approval pipeline
        if self.status is not InvoiceStatus.DRAFT:
            raise ValueError(f"submit requires DRAFT status; current status is {self.status.value}")
        self.status = InvoiceStatus.SUBMITTED
        self.updated_at = datetime.now(UTC)

    def approve(self) -> None:
        # Buyer approval is only valid on a submitted invoice
        if self.status is not InvoiceStatus.SUBMITTED:
            raise ValueError(f"approve requires SUBMITTED status; current status is {self.status.value}")
        self.status = InvoiceStatus.APPROVED
        self.updated_at = datetime.now(UTC)

    def pay(self) -> None:
        # Payment is only valid on an approved invoice
        if self.status is not InvoiceStatus.APPROVED:
            raise ValueError(f"pay requires APPROVED status; current status is {self.status.value}")
        self.status = InvoiceStatus.PAID
        self.updated_at = datetime.now(UTC)

    def dispute(self, reason: str) -> None:
        # dispute_reason captures the buyer's objection; reason is mandatory for audit trail
        if not reason or not reason.strip():
            raise ValueError("dispute reason must not be empty or whitespace-only")
        if self.status is not InvoiceStatus.SUBMITTED:
            raise ValueError(f"dispute requires SUBMITTED status; current status is {self.status.value}")
        self.dispute_reason = reason.strip()
        self.status = InvoiceStatus.DISPUTED
        self.updated_at = datetime.now(UTC)

    def resolve(self) -> None:
        # Resolution re-enters the invoice into the approval pipeline as SUBMITTED
        if self.status is not InvoiceStatus.DISPUTED:
            raise ValueError(f"resolve requires DISPUTED status; current status is {self.status.value}")
        self.status = InvoiceStatus.SUBMITTED
        self.updated_at = datetime.now(UTC)
