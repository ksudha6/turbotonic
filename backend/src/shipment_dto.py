from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from src.domain.shipment import Shipment, ShipmentLineItem, ShipmentStatus


class ShipmentLineItemCreate(BaseModel):
    part_number: str
    product_id: str | None = None
    description: str = ""
    quantity: int
    uom: str

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


class ShipmentCreate(BaseModel):
    po_id: str
    line_items: list[ShipmentLineItemCreate]

    @field_validator("line_items")
    @classmethod
    def line_items_not_empty(cls, v: list[ShipmentLineItemCreate]) -> list[ShipmentLineItemCreate]:
        if not v:
            raise ValueError("at least one line item is required")
        return v


class ShipmentLineItemUpdate(BaseModel):
    part_number: str
    net_weight: Decimal | None = None
    gross_weight: Decimal | None = None
    package_count: int | None = None
    dimensions: str | None = None
    country_of_origin: str | None = None

    @field_validator("part_number")
    @classmethod
    def part_number_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("part_number must not be empty or whitespace-only")
        return v

    @field_validator("dimensions", "country_of_origin", mode="before")
    @classmethod
    def reject_whitespace_only(cls, v: str | None) -> str | None:
        if isinstance(v, str) and not v.strip():
            raise ValueError("field must not be whitespace-only")
        return v


class ShipmentUpdate(BaseModel):
    line_items: list[ShipmentLineItemUpdate]


class ShipmentLineItemResponse(BaseModel):
    id: str
    shipment_id: str
    part_number: str
    product_id: str | None
    description: str
    quantity: int
    uom: str
    sort_order: int
    net_weight: Decimal | None = None
    gross_weight: Decimal | None = None
    package_count: int | None = None
    dimensions: str | None = None
    country_of_origin: str | None = None


class ShipmentResponse(BaseModel):
    id: str
    po_id: str
    shipment_number: str
    marketplace: str
    status: str
    line_items: list[ShipmentLineItemResponse]
    created_at: datetime
    updated_at: datetime
    carrier: str | None = None
    booking_reference: str | None = None
    pickup_date: date | None = None
    shipped_at: datetime | None = None


class ShipmentBookRequest(BaseModel):
    carrier: str
    booking_reference: str
    pickup_date: date

    @field_validator("carrier", "booking_reference")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace-only")
        return v.strip()


class RemainingShipmentQuantity(BaseModel):
    part_number: str
    po_quantity: int
    shipped_quantity: int
    remaining_quantity: int


class RemainingShipmentQuantityResponse(BaseModel):
    po_id: str
    items: list[RemainingShipmentQuantity]


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def shipment_to_response(
    shipment: Shipment,
    line_item_rows: list[dict[str, object]],
) -> ShipmentResponse:
    items = [
        ShipmentLineItemResponse(
            id=str(row["id"]),
            shipment_id=str(row["shipment_id"]),
            part_number=str(row["part_number"]),
            product_id=row["product_id"] if row["product_id"] is not None else None,  # type: ignore[arg-type]
            description=str(row["description"] or ""),
            quantity=int(row["quantity"]),  # type: ignore[arg-type]
            uom=str(row["uom"]),
            sort_order=int(row["sort_order"]),  # type: ignore[arg-type]
            net_weight=_decimal_or_none(row.get("net_weight")),
            gross_weight=_decimal_or_none(row.get("gross_weight")),
            package_count=int(row["package_count"]) if row.get("package_count") is not None else None,  # type: ignore[arg-type]
            dimensions=str(row["dimensions"]) if row.get("dimensions") is not None else None,
            country_of_origin=str(row["country_of_origin"]) if row.get("country_of_origin") is not None else None,
        )
        for row in line_item_rows
    ]
    return ShipmentResponse(
        id=shipment.id,
        po_id=shipment.po_id,
        shipment_number=shipment.shipment_number,
        marketplace=shipment.marketplace,
        status=shipment.status.value,
        line_items=items,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
        carrier=shipment.carrier,
        booking_reference=shipment.booking_reference,
        pickup_date=shipment.pickup_date,
        shipped_at=shipment.shipped_at,
    )
