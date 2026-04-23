from __future__ import annotations

from datetime import datetime

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


class ShipmentLineItemResponse(BaseModel):
    id: str
    shipment_id: str
    part_number: str
    product_id: str | None
    description: str
    quantity: int
    uom: str
    sort_order: int


class ShipmentResponse(BaseModel):
    id: str
    po_id: str
    shipment_number: str
    marketplace: str
    status: str
    line_items: list[ShipmentLineItemResponse]
    created_at: datetime
    updated_at: datetime


class RemainingShipmentQuantity(BaseModel):
    part_number: str
    po_quantity: int
    shipped_quantity: int
    remaining_quantity: int


class RemainingShipmentQuantityResponse(BaseModel):
    po_id: str
    items: list[RemainingShipmentQuantity]


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
    )
