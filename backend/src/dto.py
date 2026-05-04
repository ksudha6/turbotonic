from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

import asyncpg
from pydantic import BaseModel, field_validator

from src.domain.invoice import Invoice
from src.domain.invoice import InvoiceLineItem as DomainInvoiceLineItem
from src.domain.purchase_order import (
    EDITABLE_LINE_FIELDS,
    LineEditHistoryEntry,
    LineItem,
    PurchaseOrder,
    RejectionRecord,
)


# HS code must contain only digits and dots and be at least 4 characters long.
_HS_CODE_PATTERN: re.Pattern[str] = re.compile(r"[\d.]+")


class LineItemCreate(BaseModel):
    part_number: str
    description: str
    quantity: int
    uom: str
    unit_price: Decimal
    hs_code: str
    country_of_origin: str
    product_id: str | None = None

    @field_validator("part_number")
    @classmethod
    def part_number_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("part_number must not be empty or whitespace-only")
        return v

    @field_validator("hs_code")
    @classmethod
    def hs_code_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("hs_code must be at least 4 characters and contain only digits and dots")
        if len(v) < 4 or not _HS_CODE_PATTERN.fullmatch(v):
            raise ValueError("hs_code must be at least 4 characters and contain only digits and dots")
        return v

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be greater than 0")
        return v

    @field_validator("unit_price")
    @classmethod
    def unit_price_non_negative(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("unit_price must be >= 0")
        return v


class PurchaseOrderCreate(BaseModel):
    vendor_id: str
    brand_id: str
    buyer_name: str
    buyer_country: str
    ship_to_address: str
    payment_terms: str
    currency: str
    issued_date: datetime
    required_delivery_date: datetime
    terms_and_conditions: str
    incoterm: str
    port_of_loading: str
    port_of_discharge: str
    country_of_origin: str
    country_of_destination: str
    line_items: list[LineItemCreate]
    po_type: str = "PROCUREMENT"
    marketplace: str | None = None

    @field_validator("line_items")
    @classmethod
    def line_items_not_empty(cls, v: list[LineItemCreate]) -> list[LineItemCreate]:
        if not v:
            raise ValueError("at least one line item is required")
        return v

    @field_validator("po_type")
    @classmethod
    def po_type_valid(cls, v: str) -> str:
        upper = v.upper()
        if upper not in {"PROCUREMENT", "OPEX"}:
            raise ValueError("po_type must be one of: PROCUREMENT, OPEX")
        return upper


class PurchaseOrderUpdate(BaseModel):
    vendor_id: str
    buyer_name: str
    buyer_country: str
    ship_to_address: str
    payment_terms: str
    currency: str
    issued_date: datetime
    required_delivery_date: datetime
    terms_and_conditions: str
    incoterm: str
    port_of_loading: str
    port_of_discharge: str
    country_of_origin: str
    country_of_destination: str
    line_items: list[LineItemCreate]
    marketplace: str | None = None
    # brand_id is present only to reject mutation attempts; the value on the PO is immutable.
    brand_id: str | None = None

    @field_validator("line_items")
    @classmethod
    def line_items_not_empty(cls, v: list[LineItemCreate]) -> list[LineItemCreate]:
        if not v:
            raise ValueError("at least one line item is required")
        return v


# Iter 056: 'reject' dropped — PO-level rejection is no longer a direct action.
# REJECTED is only reachable via convergence when every line ends REMOVED.
_VALID_BULK_ACTIONS: tuple[str, ...] = ("submit", "accept", "resubmit")


class BulkTransitionRequest(BaseModel):
    po_ids: list[str]
    action: str  # one of: submit, accept, resubmit
    comment: str | None = None

    @field_validator("action")
    @classmethod
    def action_must_be_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("action must not be empty or whitespace-only")
        if v not in _VALID_BULK_ACTIONS:
            raise ValueError(f"action must be one of: {', '.join(_VALID_BULK_ACTIONS)}")
        return v

    @field_validator("po_ids")
    @classmethod
    def po_ids_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("po_ids must not be empty")
        if len(v) > 200:
            raise ValueError("po_ids must contain at most 200 items")
        return v


class BulkTransitionItemResult(BaseModel):
    po_id: str
    success: bool
    error: str | None = None
    new_status: str | None = None


class BulkTransitionResult(BaseModel):
    results: list[BulkTransitionItemResult]


# Iter 056: line-level negotiation request DTOs.


class ModifyLineRequest(BaseModel):
    # Only fields in EDITABLE_LINE_FIELDS are accepted; part_number is immutable.
    fields: dict[str, object]

    @field_validator("fields")
    @classmethod
    def fields_editable(cls, v: dict[str, object]) -> dict[str, object]:
        if not v:
            raise ValueError("fields must not be empty")
        if "part_number" in v:
            raise ValueError("part_number is immutable and cannot be modified")
        invalid = [name for name in v if name not in EDITABLE_LINE_FIELDS]
        if invalid:
            raise ValueError(
                f"fields not editable: {sorted(invalid)}; "
                f"editable fields are {list(EDITABLE_LINE_FIELDS)}"
            )
        return v


class AcceptLineRequest(BaseModel):
    # Empty body; the actor is derived from the authenticated user.
    pass


class RemoveLineRequest(BaseModel):
    pass


class ForceAcceptRequest(BaseModel):
    pass


class ForceRemoveRequest(BaseModel):
    pass


class SubmitResponseRequest(BaseModel):
    pass


class MarkAdvancePaidRequest(BaseModel):
    # Empty body; the actor is derived from the authenticated user.
    pass


class AddLinePostAcceptRequest(BaseModel):
    # SM-only post-acceptance line addition. Reuses the LineItemCreate shape so
    # validation (hs_code pattern, quantity > 0, part_number non-empty) matches.
    line: LineItemCreate


class LineEditEntryDTO(BaseModel):
    part_number: str
    round: int
    actor_role: str
    field: str
    old_value: str
    new_value: str
    edited_at: datetime


class LineItemResponse(BaseModel):
    part_number: str
    description: str
    quantity: int
    uom: str
    unit_price: str
    hs_code: str
    country_of_origin: str
    product_id: str | None = None
    status: str = "PENDING"
    required_delivery_date: datetime | None = None
    history: list[LineEditEntryDTO] = []


class RejectionResponse(BaseModel):
    comment: str
    rejected_at: datetime


class PurchaseOrderResponse(BaseModel):
    id: str
    po_number: str
    status: str
    po_type: str
    vendor_id: str
    buyer_name: str
    buyer_country: str
    vendor_name: str
    vendor_country: str
    ship_to_address: str
    payment_terms: str
    currency: str
    issued_date: datetime
    required_delivery_date: datetime
    terms_and_conditions: str
    incoterm: str
    port_of_loading: str
    port_of_discharge: str
    country_of_origin: str
    country_of_destination: str
    marketplace: str | None = None
    line_items: list[LineItemResponse]
    rejection_history: list[RejectionResponse]
    total_value: str
    created_at: datetime
    updated_at: datetime
    round_count: int = 0
    last_actor_role: str | None = None
    # Iter 059: null when no advance recorded. UI uses this plus the reference
    # metadata's has_advance flag to decide when to show the "Mark Advance Paid" button.
    advance_paid_at: datetime | None = None
    # Iter 108: brand fields — id/name always present; full block on detail response.
    brand_id: str | None = None
    brand_name: str | None = None
    brand_legal_name: str | None = None
    brand_address: str | None = None
    brand_country: str | None = None
    brand_tax_id: str | None = None


class PurchaseOrderListItem(BaseModel):
    id: str
    po_number: str
    status: str
    po_type: str
    vendor_id: str
    buyer_name: str
    buyer_country: str
    vendor_name: str
    vendor_country: str
    issued_date: datetime
    required_delivery_date: datetime
    total_value: str
    currency: str
    current_milestone: str | None = None
    marketplace: str | None = None
    round_count: int = 0
    # Iter 058: flags the "Partial" PO pill on the list page — an ACCEPTED PO with
    # one or more REMOVED lines is partial, because some originally-ordered scope
    # was agreed-out during negotiation.
    has_removed_line: bool = False
    # Iter 108: brand fields on list items.
    brand_id: str | None = None
    brand_name: str | None = None


class PaginatedPOList(BaseModel):
    items: list[PurchaseOrderListItem]
    total: int
    page: int
    page_size: int


def _line_edit_entry_to_dto(entry: LineEditHistoryEntry) -> LineEditEntryDTO:
    return LineEditEntryDTO(
        part_number=entry.part_number,
        round=entry.round,
        actor_role=entry.actor_role.value,
        field=entry.field,
        old_value=entry.old_value,
        new_value=entry.new_value,
        edited_at=entry.edited_at,
    )


def _line_item_to_response(item: LineItem, history: list[LineEditHistoryEntry]) -> LineItemResponse:
    relevant = [e for e in history if e.part_number == item.part_number]
    return LineItemResponse(
        part_number=item.part_number,
        description=item.description,
        quantity=item.quantity,
        uom=item.uom,
        unit_price=str(item.unit_price),
        hs_code=item.hs_code,
        country_of_origin=item.country_of_origin,
        product_id=item.product_id,
        status=item.status.value,
        required_delivery_date=item.required_delivery_date,
        history=[_line_edit_entry_to_dto(e) for e in relevant],
    )


def _rejection_record_to_response(record: RejectionRecord) -> RejectionResponse:
    return RejectionResponse(
        comment=record.comment,
        rejected_at=record.rejected_at,
    )


def po_to_response(po: PurchaseOrder, vendor_name: str = "", vendor_country: str = "") -> PurchaseOrderResponse:
    return PurchaseOrderResponse(
        id=po.id,
        po_number=po.po_number,
        status=po.status.value,
        po_type=po.po_type.value,
        vendor_id=po.vendor_id,
        buyer_name=po.buyer_name,
        buyer_country=po.buyer_country,
        vendor_name=vendor_name,
        vendor_country=vendor_country,
        ship_to_address=po.ship_to_address,
        payment_terms=po.payment_terms,
        currency=po.currency,
        issued_date=po.issued_date,
        required_delivery_date=po.required_delivery_date,
        terms_and_conditions=po.terms_and_conditions,
        incoterm=po.incoterm,
        port_of_loading=po.port_of_loading,
        port_of_discharge=po.port_of_discharge,
        country_of_origin=po.country_of_origin,
        country_of_destination=po.country_of_destination,
        marketplace=po.marketplace,
        line_items=[_line_item_to_response(i, po.line_edit_history) for i in po.line_items],
        rejection_history=[_rejection_record_to_response(r) for r in po.rejection_history],
        total_value=str(po.total_value),
        created_at=po.created_at,
        updated_at=po.updated_at,
        round_count=po.round_count,
        last_actor_role=po.last_actor_role.value if po.last_actor_role else None,
        advance_paid_at=po.advance_paid_at,
        brand_id=po.brand_id,
        brand_name=po.brand_name,
        brand_legal_name=po.brand_legal_name,
        brand_address=po.brand_address,
        brand_country=po.brand_country,
        brand_tax_id=po.brand_tax_id,
    )


def po_to_list_item(po: PurchaseOrder, vendor_name: str = "", vendor_country: str = "") -> PurchaseOrderListItem:
    return PurchaseOrderListItem(
        id=po.id,
        po_number=po.po_number,
        status=po.status.value,
        po_type=po.po_type.value,
        vendor_id=po.vendor_id,
        buyer_name=po.buyer_name,
        buyer_country=po.buyer_country,
        vendor_name=vendor_name,
        vendor_country=vendor_country,
        issued_date=po.issued_date,
        required_delivery_date=po.required_delivery_date,
        total_value=str(po.total_value),
        currency=po.currency,
        marketplace=po.marketplace,
        round_count=po.round_count,
        brand_id=po.brand_id,
        brand_name=po.brand_name,
    )


class InvoiceLineItemCreate(BaseModel):
    part_number: str
    quantity: int

class InvoiceCreate(BaseModel):
    po_id: str
    line_items: list[InvoiceLineItemCreate] | None = None


class InvoiceLineItemResponse(BaseModel):
    part_number: str
    description: str
    quantity: int
    uom: str
    unit_price: str


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    po_id: str
    status: str
    payment_terms: str
    currency: str
    line_items: list[InvoiceLineItemResponse]
    subtotal: str
    dispute_reason: str
    created_at: datetime
    updated_at: datetime


class InvoiceListItem(BaseModel):
    id: str
    invoice_number: str
    status: str
    subtotal: str
    created_at: datetime


class InvoiceListItemWithContext(BaseModel):
    id: str
    invoice_number: str
    status: str
    subtotal: str
    created_at: datetime
    po_id: str
    po_number: str
    vendor_name: str


class PaginatedInvoiceList(BaseModel):
    items: list[InvoiceListItemWithContext]
    total: int
    page: int
    page_size: int


def invoice_row_to_list_item_with_context(row: asyncpg.Record) -> InvoiceListItemWithContext:
    raw_subtotal = row["subtotal"]
    subtotal_str = f"{Decimal(str(raw_subtotal if raw_subtotal is not None else 0)):.2f}"
    return InvoiceListItemWithContext(
        id=row["id"],
        invoice_number=row["invoice_number"],
        status=row["status"],
        subtotal=subtotal_str,
        created_at=row["created_at"],
        po_id=row["po_id"],
        po_number=row["po_number"],
        vendor_name=row["vendor_name"],
    )


class DisputeRequest(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("reason must not be empty or whitespace-only")
        return stripped


def invoice_to_response(inv: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=inv.id,
        invoice_number=inv.invoice_number,
        po_id=inv.po_id,
        status=inv.status.value,
        payment_terms=inv.payment_terms,
        currency=inv.currency,
        line_items=[
            InvoiceLineItemResponse(
                part_number=li.part_number,
                description=li.description,
                quantity=li.quantity,
                uom=li.uom,
                unit_price=str(li.unit_price),
            )
            for li in inv.line_items
        ],
        subtotal=str(inv.subtotal),
        dispute_reason=inv.dispute_reason,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
    )


class RemainingLineItem(BaseModel):
    part_number: str
    description: str
    ordered: int
    invoiced: int
    remaining: int


class RemainingQuantityResponse(BaseModel):
    po_id: str
    lines: list[RemainingLineItem]


def invoice_to_list_item(inv: Invoice) -> InvoiceListItem:
    return InvoiceListItem(
        id=inv.id,
        invoice_number=inv.invoice_number,
        status=inv.status.value,
        subtotal=str(inv.subtotal),
        created_at=inv.created_at,
    )


class BulkInvoicePdfRequest(BaseModel):
    invoice_ids: list[str]


# Iter 039: quality gate on PO submit. Warnings are transient (computed at
# submit time); they are not stored and are absent from all GET responses.
class CertWarningResponse(BaseModel):
    line_item_index: int
    part_number: str
    product_id: str
    qualification_name: str
    reason: str  # CertWarningReason.value — "MISSING" or "EXPIRED"


class POSubmitResponse(BaseModel):
    # Wraps the standard PO response plus advisory cert warnings from the quality gate.
    po: PurchaseOrderResponse
    cert_warnings: list[CertWarningResponse]
