from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

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


class PurchaseOrderUpdate(BaseModel):
    vendor_id: str
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
    vendor_id: str
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
    vendor_id: str
    issued_date: datetime
    required_delivery_date: datetime
    total_value: str
    currency: str


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


def po_to_response(po: PurchaseOrder) -> PurchaseOrderResponse:
    return PurchaseOrderResponse(
        id=po.id,
        po_number=po.po_number,
        status=po.status.value,
        vendor_id=po.vendor_id,
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


def po_to_list_item(po: PurchaseOrder) -> PurchaseOrderListItem:
    return PurchaseOrderListItem(
        id=po.id,
        po_number=po.po_number,
        status=po.status.value,
        vendor_id=po.vendor_id,
        issued_date=po.issued_date,
        required_delivery_date=po.required_delivery_date,
        total_value=str(po.total_value),
        currency=po.currency,
    )
