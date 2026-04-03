from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

from src.domain.invoice import Invoice
from src.domain.invoice import InvoiceLineItem as DomainInvoiceLineItem
from src.domain.purchase_order import LineItem, PurchaseOrder, RejectionRecord


class LineItemCreate(BaseModel):
    part_number: str
    description: str
    quantity: int
    uom: str
    unit_price: Decimal
    hs_code: str
    country_of_origin: str

    @field_validator("part_number")
    @classmethod
    def part_number_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("part_number must not be empty or whitespace-only")
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

    @field_validator("line_items")
    @classmethod
    def line_items_not_empty(cls, v: list[LineItemCreate]) -> list[LineItemCreate]:
        if not v:
            raise ValueError("at least one line item is required")
        return v


_VALID_BULK_ACTIONS: tuple[str, ...] = ("submit", "accept", "reject", "resubmit")


class BulkTransitionRequest(BaseModel):
    po_ids: list[str]
    action: str  # one of: submit, accept, reject, resubmit
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

    @model_validator(mode="after")
    def reject_requires_comment(self) -> BulkTransitionRequest:
        if self.action == "reject":
            if not self.comment or not self.comment.strip():
                raise ValueError("comment is required and must not be empty when action is 'reject'")
        return self


class BulkTransitionItemResult(BaseModel):
    po_id: str
    success: bool
    error: str | None = None
    new_status: str | None = None


class BulkTransitionResult(BaseModel):
    results: list[BulkTransitionItemResult]


class RejectRequest(BaseModel):
    comment: str

    @field_validator("comment")
    @classmethod
    def comment_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("comment must not be empty or whitespace-only")
        return stripped


class LineItemResponse(BaseModel):
    part_number: str
    description: str
    quantity: int
    uom: str
    unit_price: str
    hs_code: str
    country_of_origin: str


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
    line_items: list[LineItemResponse]
    rejection_history: list[RejectionResponse]
    total_value: str
    created_at: datetime
    updated_at: datetime


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


class PaginatedPOList(BaseModel):
    items: list[PurchaseOrderListItem]
    total: int
    page: int
    page_size: int


def _line_item_to_response(item: LineItem) -> LineItemResponse:
    return LineItemResponse(
        part_number=item.part_number,
        description=item.description,
        quantity=item.quantity,
        uom=item.uom,
        unit_price=str(item.unit_price),
        hs_code=item.hs_code,
        country_of_origin=item.country_of_origin,
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
        line_items=[_line_item_to_response(i) for i in po.line_items],
        rejection_history=[_rejection_record_to_response(r) for r in po.rejection_history],
        total_value=str(po.total_value),
        created_at=po.created_at,
        updated_at=po.updated_at,
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
