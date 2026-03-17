from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4


class POStatus(Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    REVISED = "REVISED"


@dataclass
class LineItem:
    part_number: str
    description: str
    quantity: int
    uom: str
    unit_price: Decimal
    hs_code: str
    country_of_origin: str

    def __post_init__(self) -> None:
        if not self.part_number or not self.part_number.strip():
            raise ValueError("part_number must not be empty or whitespace-only")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        if self.unit_price < Decimal("0"):
            raise ValueError("unit_price must be >= 0")


@dataclass
class RejectionRecord:
    comment: str
    rejected_at: datetime


class PurchaseOrder:
    # id owns the aggregate identity; po_number owns the business reference
    def __init__(
        self,
        *,
        id: str,
        po_number: str,
        status: POStatus,
        vendor_id: str,
        buyer_name: str,
        buyer_country: str,
        ship_to_address: str,
        payment_terms: str,
        currency: str,
        issued_date: datetime,
        required_delivery_date: datetime,
        terms_and_conditions: str,
        incoterm: str,
        port_of_loading: str,
        port_of_discharge: str,
        country_of_origin: str,
        country_of_destination: str,
        line_items: list[LineItem],
        rejection_history: list[RejectionRecord],
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._po_number = po_number
        self.status = status
        self.vendor_id = vendor_id
        self.buyer_name = buyer_name
        self.buyer_country = buyer_country
        self.ship_to_address = ship_to_address
        self.payment_terms = payment_terms
        self.currency = currency
        self.issued_date = issued_date
        self.required_delivery_date = required_delivery_date
        self.terms_and_conditions = terms_and_conditions
        self.incoterm = incoterm
        self.port_of_loading = port_of_loading
        self.port_of_discharge = port_of_discharge
        self.country_of_origin = country_of_origin
        self.country_of_destination = country_of_destination
        self.line_items = line_items
        self.rejection_history = rejection_history
        self._created_at = created_at
        self.updated_at = updated_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def po_number(self) -> str:
        return self._po_number

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def total_value(self) -> Decimal:
        return sum(
            (item.quantity * item.unit_price for item in self.line_items),
            Decimal("0"),
        )

    @classmethod
    def create(
        cls,
        *,
        po_number: str,
        vendor_id: str,
        buyer_name: str,
        buyer_country: str,
        ship_to_address: str,
        payment_terms: str,
        currency: str,
        issued_date: datetime,
        required_delivery_date: datetime,
        terms_and_conditions: str,
        incoterm: str,
        port_of_loading: str,
        port_of_discharge: str,
        country_of_origin: str,
        country_of_destination: str,
        line_items: list[LineItem],
    ) -> PurchaseOrder:
        if not line_items:
            raise ValueError("at least one line item is required")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            po_number=po_number,
            status=POStatus.DRAFT,
            vendor_id=vendor_id,
            buyer_name=buyer_name,
            buyer_country=buyer_country,
            ship_to_address=ship_to_address,
            payment_terms=payment_terms,
            currency=currency,
            issued_date=issued_date,
            required_delivery_date=required_delivery_date,
            terms_and_conditions=terms_and_conditions,
            incoterm=incoterm,
            port_of_loading=port_of_loading,
            port_of_discharge=port_of_discharge,
            country_of_origin=country_of_origin,
            country_of_destination=country_of_destination,
            line_items=list(line_items),
            rejection_history=[],
            created_at=now,
            updated_at=now,
        )

    def submit(self) -> None:
        # DRAFT is the only state from which a PO may enter the review pipeline
        if self.status is not POStatus.DRAFT:
            raise ValueError(
                f"submit requires DRAFT status; current status is {self.status.value}"
            )
        self.status = POStatus.PENDING
        self.updated_at = datetime.now(UTC)

    def accept(self) -> None:
        # Buyer acceptance is only valid on a PO that is under review
        if self.status is not POStatus.PENDING:
            raise ValueError(
                f"accept requires PENDING status; current status is {self.status.value}"
            )
        self.status = POStatus.ACCEPTED
        self.updated_at = datetime.now(UTC)

    def reject(self, comment: str) -> None:
        # Rejection records the reason; comment is mandatory for audit trail
        if not comment or not comment.strip():
            raise ValueError("rejection comment must not be empty or whitespace-only")
        if self.status is not POStatus.PENDING:
            raise ValueError(
                f"reject requires PENDING status; current status is {self.status.value}"
            )
        self.rejection_history.append(
            RejectionRecord(comment=comment, rejected_at=datetime.now(UTC))
        )
        self.status = POStatus.REJECTED
        self.updated_at = datetime.now(UTC)

    def revise(
        self,
        *,
        vendor_id: str,
        buyer_name: str,
        buyer_country: str,
        ship_to_address: str,
        payment_terms: str,
        currency: str,
        issued_date: datetime,
        required_delivery_date: datetime,
        terms_and_conditions: str,
        incoterm: str,
        port_of_loading: str,
        port_of_discharge: str,
        country_of_origin: str,
        country_of_destination: str,
        line_items: list[LineItem],
    ) -> None:
        # Revision is the vendor's response to a rejection; only valid after REJECTED
        if self.status is not POStatus.REJECTED:
            raise ValueError(
                f"revise requires REJECTED status; current status is {self.status.value}"
            )
        if not line_items:
            raise ValueError("at least one line item is required")
        self.vendor_id = vendor_id
        self.buyer_name = buyer_name
        self.buyer_country = buyer_country
        self.ship_to_address = ship_to_address
        self.payment_terms = payment_terms
        self.currency = currency
        self.issued_date = issued_date
        self.required_delivery_date = required_delivery_date
        self.terms_and_conditions = terms_and_conditions
        self.incoterm = incoterm
        self.port_of_loading = port_of_loading
        self.port_of_discharge = port_of_discharge
        self.country_of_origin = country_of_origin
        self.country_of_destination = country_of_destination
        self.line_items = list(line_items)
        self.status = POStatus.REVISED
        self.updated_at = datetime.now(UTC)

    def resubmit(self) -> None:
        # REVISED re-enters the review pipeline as PENDING
        if self.status is not POStatus.REVISED:
            raise ValueError(
                f"resubmit requires REVISED status; current status is {self.status.value}"
            )
        self.status = POStatus.PENDING
        self.updated_at = datetime.now(UTC)
