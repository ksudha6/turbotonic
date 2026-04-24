from __future__ import annotations

import re
from decimal import Decimal
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response

from src.auth.dependencies import require_role
from src.db import get_db
from src.domain.shipment import Shipment, ShipmentLineItem, ShipmentStatus, validate_shipment_quantities
from src.domain.user import User, UserRole
from src.repository import PurchaseOrderRepository
from src.shipment_dto import (
    RemainingShipmentQuantity,
    RemainingShipmentQuantityResponse,
    ShipmentCreate,
    ShipmentResponse,
    ShipmentUpdate,
    shipment_to_response,
)
from src.shipment_repository import ShipmentRepository
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/shipments", tags=["shipments"])

SHIPMENT_NUMBER_RE = re.compile(r"^SHP-\d{8}-[0-9A-F]{4}$")


async def get_shipment_repo() -> AsyncIterator[ShipmentRepository]:
    async with get_db() as conn:
        yield ShipmentRepository(conn)


async def get_po_repo_for_shipment() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        yield PurchaseOrderRepository(conn)


async def get_vendor_repo_for_shipment() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        yield VendorRepository(conn)


ShipmentRepoDep = Annotated[ShipmentRepository, Depends(get_shipment_repo)]
PORepoDep = Annotated[PurchaseOrderRepository, Depends(get_po_repo_for_shipment)]
VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo_for_shipment)]


@router.post("/", response_model=ShipmentResponse, status_code=201)
async def create_shipment(
    body: ShipmentCreate,
    repo: ShipmentRepoDep,
    po_repo: PORepoDep,
    _user: User = require_role(UserRole.SM, UserRole.FREIGHT_MANAGER),
) -> ShipmentResponse:
    po = await po_repo.get(body.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="PO not found")

    from src.domain.purchase_order import POStatus
    if po.status is not POStatus.ACCEPTED:
        raise HTTPException(status_code=409, detail="PO must be in ACCEPTED status to create a shipment")

    # Build domain line items from DTO
    try:
        new_line_items = [
            ShipmentLineItem(
                part_number=li.part_number,
                product_id=li.product_id,
                description=li.description,
                quantity=li.quantity,
                uom=li.uom,
            )
            for li in body.line_items
        ]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Build po_line_items as list[dict] for the guard
    po_line_items: list[dict[str, object]] = [
        {
            "part_number": item.part_number,
            "quantity": item.quantity,
            "status": item.status.value,
        }
        for item in po.line_items
    ]

    existing_shipments = await repo.list_by_po(body.po_id)

    try:
        validate_shipment_quantities(po_line_items, existing_shipments, new_line_items)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    marketplace = po.marketplace or ""
    try:
        shipment = Shipment.create(
            po_id=body.po_id,
            marketplace=marketplace,
            line_items=new_line_items,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await repo.save(shipment)
    line_item_rows = await repo.get_line_item_rows(shipment.id)
    return shipment_to_response(shipment, line_item_rows)


@router.get("/remaining-quantities/{po_id}", response_model=RemainingShipmentQuantityResponse)
async def remaining_quantities(
    po_id: str,
    repo: ShipmentRepoDep,
    po_repo: PORepoDep,
    _user: User = require_role(UserRole.SM, UserRole.FREIGHT_MANAGER),
) -> RemainingShipmentQuantityResponse:
    po = await po_repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="PO not found")

    shipped = await repo.get_shipped_quantities(po_id)

    items: list[RemainingShipmentQuantity] = []
    for li in po.line_items:
        from src.domain.purchase_order import LineItemStatus
        if li.status is not LineItemStatus.ACCEPTED:
            continue
        shipped_qty = shipped.get(li.part_number, 0)
        items.append(
            RemainingShipmentQuantity(
                part_number=li.part_number,
                po_quantity=li.quantity,
                shipped_quantity=shipped_qty,
                remaining_quantity=li.quantity - shipped_qty,
            )
        )

    return RemainingShipmentQuantityResponse(po_id=po_id, items=items)


@router.get("/", response_model=list[ShipmentResponse])
async def list_shipments(
    repo: ShipmentRepoDep,
    po_id: str | None = None,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER),
) -> list[ShipmentResponse]:
    if po_id is not None:
        shipments = await repo.list_by_po(po_id)
    else:
        shipments = await repo.list_all()

    result: list[ShipmentResponse] = []
    for s in shipments:
        rows = await repo.get_line_item_rows(s.id)
        result.append(shipment_to_response(s, rows))
    return result


@router.get("/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: str,
    repo: ShipmentRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER),
) -> ShipmentResponse:
    shipment = await repo.get(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    rows = await repo.get_line_item_rows(shipment_id)
    return shipment_to_response(shipment, rows)


@router.post("/{shipment_id}/submit-for-documents", response_model=ShipmentResponse)
async def submit_for_documents(
    shipment_id: str,
    repo: ShipmentRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.FREIGHT_MANAGER),
) -> ShipmentResponse:
    shipment = await repo.get(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    try:
        shipment.submit_for_documents()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(shipment)
    rows = await repo.get_line_item_rows(shipment_id)
    return shipment_to_response(shipment, rows)


@router.post("/{shipment_id}/mark-ready", response_model=ShipmentResponse)
async def mark_ready(
    shipment_id: str,
    repo: ShipmentRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.FREIGHT_MANAGER),
) -> ShipmentResponse:
    shipment = await repo.get(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    try:
        shipment.mark_ready()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(shipment)
    rows = await repo.get_line_item_rows(shipment_id)
    return shipment_to_response(shipment, rows)


@router.patch("/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: str,
    body: ShipmentUpdate,
    repo: ShipmentRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.FREIGHT_MANAGER),
) -> ShipmentResponse:
    shipment = await repo.get(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Convert DTO list to plain dicts for the domain method
    updates: list[dict[str, object]] = [
        {
            "part_number": li.part_number,
            "net_weight": li.net_weight,
            "gross_weight": li.gross_weight,
            "package_count": li.package_count,
            "dimensions": li.dimensions,
            "country_of_origin": li.country_of_origin,
        }
        for li in body.line_items
    ]

    try:
        shipment.update_line_items(updates)
    except ValueError as exc:
        # READY_TO_SHIP status raises ValueError → 409 conflict
        # Unknown part_number raises ValueError → 422 unprocessable
        msg = str(exc)
        if "not allowed" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        raise HTTPException(status_code=422, detail=msg) from exc

    await repo.save(shipment)
    rows = await repo.get_line_item_rows(shipment_id)
    return shipment_to_response(shipment, rows)


@router.get("/{shipment_id}/packing-list")
async def get_packing_list(
    shipment_id: str,
    repo: ShipmentRepoDep,
    po_repo: PORepoDep,
    vendor_repo: VendorRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER),
) -> Response:
    from src.services.packing_list_pdf import generate_packing_list_pdf

    shipment = await repo.get(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    po = await po_repo.get(shipment.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vendor_name = vendor.name if vendor is not None else ""
    vendor_address = vendor.address if vendor is not None else ""

    # Buyer info is owned by the PO; no standalone Buyer entity exists yet
    buyer_name = po.buyer_name
    buyer_address = po.ship_to_address

    pdf_bytes = generate_packing_list_pdf(
        shipment=shipment,
        po=po,
        vendor_name=vendor_name,
        vendor_address=vendor_address,
        buyer_name=buyer_name,
        buyer_address=buyer_address,
    )

    filename = f"packing-list-{shipment.shipment_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.get("/{shipment_id}/commercial-invoice")
async def get_commercial_invoice(
    shipment_id: str,
    repo: ShipmentRepoDep,
    po_repo: PORepoDep,
    vendor_repo: VendorRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER),
) -> Response:
    from src.services.commercial_invoice_pdf import generate_commercial_invoice_pdf

    shipment = await repo.get(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    po = await po_repo.get(shipment.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vendor_name = vendor.name if vendor is not None else ""
    vendor_address = vendor.address if vendor is not None else ""

    buyer_name = po.buyer_name
    buyer_address = po.ship_to_address

    pdf_bytes = generate_commercial_invoice_pdf(
        shipment=shipment,
        po=po,
        vendor_name=vendor_name,
        vendor_address=vendor_address,
        buyer_name=buyer_name,
        buyer_address=buyer_address,
    )

    filename = f"commercial-invoice-{shipment.shipment_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )
