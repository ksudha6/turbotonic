from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException

from src.db import get_db
from src.domain.purchase_order import LineItem, POStatus, PurchaseOrder
from src.domain.vendor import VendorStatus
from src.dto import (
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
    await repo.save(po)
    return po_to_response(po, vendor_name=vendor.name, vendor_country=vendor.country)


@router.get("/", response_model=list[PurchaseOrderListItem])
async def list_pos(
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    status: str | None = None,
) -> list[PurchaseOrderListItem]:
    po_status: POStatus | None = None
    if status is not None:
        try:
            po_status = POStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status value: {status!r}")
    pos = await repo.list_pos(po_status)
    vendors = await vendor_repo.list_vendors()
    vendor_map: dict[str, tuple[str, str]] = {
        v.id: (v.name, v.country) for v in vendors
    }
    return [
        po_to_list_item(
            po,
            vendor_name=vendor_map.get(po.vendor_id, ("", ""))[0],
            vendor_country=vendor_map.get(po.vendor_id, ("", ""))[1],
        )
        for po in pos
    ]


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


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
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
