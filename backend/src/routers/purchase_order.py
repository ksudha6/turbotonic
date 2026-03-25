from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from src.db import get_db
from src.domain.purchase_order import LineItem, POStatus, PurchaseOrder
from src.domain.vendor import VendorStatus
from src.dto import (
    PaginatedPOList,
    PurchaseOrderCreate,
    PurchaseOrderListItem,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    RejectRequest,
    po_to_list_item,
    po_to_response,
)
from src.repository import PurchaseOrderRepository
from src.schema import init_db
from src.services.po_pdf import generate_po_pdf
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/po", tags=["purchase-orders"])


async def get_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield PurchaseOrderRepository(conn)


RepoDep = Annotated[PurchaseOrderRepository, Depends(get_repo)]


async def get_vendor_repo() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield VendorRepository(conn)


VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo)]


def _build_line_items(data: PurchaseOrderCreate | PurchaseOrderUpdate) -> list[LineItem]:
    return [
        LineItem(
            part_number=item.part_number,
            description=item.description,
            quantity=item.quantity,
            uom=item.uom,
            unit_price=item.unit_price,
            hs_code=item.hs_code,
            country_of_origin=item.country_of_origin,
        )
        for item in data.line_items
    ]


@router.post("/", response_model=PurchaseOrderResponse, status_code=201)
async def create_po(body: PurchaseOrderCreate, repo: RepoDep, vendor_repo: VendorRepoDep) -> PurchaseOrderResponse:
    vendor = await vendor_repo.get_by_id(body.vendor_id)
    if vendor is None:
        raise HTTPException(status_code=422, detail="Vendor not found")
    if vendor.status is not VendorStatus.ACTIVE:
        raise HTTPException(status_code=422, detail="Vendor is not active")
    po_number = await repo.next_po_number()
    line_items = _build_line_items(body)
    try:
        po = PurchaseOrder.create(
            po_number=po_number,
            vendor_id=body.vendor_id,
            buyer_name=body.buyer_name,
            buyer_country=body.buyer_country,
            ship_to_address=body.ship_to_address,
            payment_terms=body.payment_terms,
            currency=body.currency,
            issued_date=body.issued_date,
            required_delivery_date=body.required_delivery_date,
            terms_and_conditions=body.terms_and_conditions,
            incoterm=body.incoterm,
            port_of_loading=body.port_of_loading,
            port_of_discharge=body.port_of_discharge,
            country_of_origin=body.country_of_origin,
            country_of_destination=body.country_of_destination,
            line_items=line_items,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repo.save(po)
    return po_to_response(po, vendor_name=vendor.name, vendor_country=vendor.country)


@router.get("/", response_model=PaginatedPOList)
async def list_pos(
    repo: RepoDep,
    status: str | None = None,
    search: str | None = None,
    vendor_id: str | None = None,
    currency: str | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> PaginatedPOList:
    if page < 1:
        raise HTTPException(status_code=422, detail="page must be >= 1")
    if not (1 <= page_size <= 100):
        raise HTTPException(status_code=422, detail="page_size must be between 1 and 100")
    if sort_dir not in ("asc", "desc"):
        raise HTTPException(status_code=422, detail=f"Invalid sort_dir value: {sort_dir!r}")

    po_status: POStatus | None = None
    if status is not None:
        try:
            po_status = POStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status value: {status!r}")

    try:
        rows, total = await repo.list_pos_paginated(
            status=po_status,
            vendor_id=vendor_id,
            currency=currency,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    items = [
        PurchaseOrderListItem(
            id=row["id"],
            po_number=row["po_number"],
            status=row["status"],
            vendor_id=row["vendor_id"],
            buyer_name=row["buyer_name"],
            buyer_country=row["buyer_country"],
            vendor_name=row["vendor_name"] or "",
            vendor_country=row["vendor_country"] or "",
            issued_date=row["issued_date"],
            required_delivery_date=row["required_delivery_date"],
            total_value=str(row["total_value"]),
            currency=row["currency"],
        )
        for row in rows
    ]
    return PaginatedPOList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.get("/{po_id}/pdf")
async def get_po_pdf(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep) -> Response:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    pdf_bytes = generate_po_pdf(po, vendor_name=vname, vendor_country=vcountry)
    filename = f"{po.po_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{po_id}/submit", response_model=PurchaseOrderResponse)
async def submit_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    try:
        po.submit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/accept", response_model=PurchaseOrderResponse)
async def accept_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    try:
        po.accept()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/reject", response_model=PurchaseOrderResponse)
async def reject_po(po_id: str, body: RejectRequest, repo: RepoDep, vendor_repo: VendorRepoDep) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    try:
        po.reject(body.comment)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.put("/{po_id}", response_model=PurchaseOrderResponse)
async def update_po(po_id: str, body: PurchaseOrderUpdate, repo: RepoDep, vendor_repo: VendorRepoDep) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    vendor = await vendor_repo.get_by_id(body.vendor_id)
    if vendor is None:
        raise HTTPException(status_code=422, detail="Vendor not found")
    if vendor.status is not VendorStatus.ACTIVE:
        raise HTTPException(status_code=422, detail="Vendor is not active")
    line_items = _build_line_items(body)
    try:
        po.revise(
            vendor_id=body.vendor_id,
            buyer_name=body.buyer_name,
            buyer_country=body.buyer_country,
            ship_to_address=body.ship_to_address,
            payment_terms=body.payment_terms,
            currency=body.currency,
            issued_date=body.issued_date,
            required_delivery_date=body.required_delivery_date,
            terms_and_conditions=body.terms_and_conditions,
            incoterm=body.incoterm,
            port_of_loading=body.port_of_loading,
            port_of_discharge=body.port_of_discharge,
            country_of_origin=body.country_of_origin,
            country_of_destination=body.country_of_destination,
            line_items=line_items,
        )
    except ValueError as exc:
        status_code = 422 if str(exc).startswith("invalid ") else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    await repo.save(po)
    return po_to_response(po, vendor_name=vendor.name, vendor_country=vendor.country)


@router.post("/{po_id}/resubmit", response_model=PurchaseOrderResponse)
async def resubmit_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    try:
        po.resubmit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)
