from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import check_vendor_access, require_auth, require_role
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.purchase_order import LineItem, POStatus, POType, PurchaseOrder
from src.domain.user import User, UserRole
from src.domain.vendor import VendorStatus
from src.dto import (
    BulkTransitionItemResult,
    BulkTransitionRequest,
    BulkTransitionResult,
    InvoiceListItem,
    PaginatedPOList,
    PurchaseOrderCreate,
    PurchaseOrderListItem,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    RejectRequest,
    invoice_to_list_item,
    po_to_list_item,
    po_to_response,
)
from src.invoice_repository import InvoiceRepository
from src.repository import PurchaseOrderRepository
from src.schema import init_db
from src.services.po_pdf import generate_po_pdf
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/po", tags=["purchase-orders"])


async def get_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        yield PurchaseOrderRepository(conn)


RepoDep = Annotated[PurchaseOrderRepository, Depends(get_repo)]


async def get_vendor_repo() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        yield VendorRepository(conn)


VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo)]


async def get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
    async with get_db() as conn:
        yield InvoiceRepository(conn)


InvoiceRepoDep = Annotated[InvoiceRepository, Depends(get_invoice_repo)]


async def get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo)]


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
            product_id=item.product_id,
        )
        for item in data.line_items
    ]


@router.post("/", response_model=PurchaseOrderResponse, status_code=201)
async def create_po(body: PurchaseOrderCreate, repo: RepoDep, vendor_repo: VendorRepoDep, activity_repo: ActivityRepoDep, _user: User = require_role(UserRole.SM)) -> PurchaseOrderResponse:
    vendor = await vendor_repo.get_by_id(body.vendor_id)
    if vendor is None:
        raise HTTPException(status_code=422, detail="Vendor not found")
    if vendor.status is not VendorStatus.ACTIVE:
        raise HTTPException(status_code=422, detail="Vendor is not active")
    po_type = POType(body.po_type)
    if vendor.vendor_type.value != po_type.value:
        raise HTTPException(
            status_code=422,
            detail=f"Vendor type {vendor.vendor_type.value} does not match PO type {po_type.value}",
        )
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
            po_type=po_type,
            marketplace=body.marketplace,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repo.save(po)
    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_CREATED)
    return po_to_response(po, vendor_name=vendor.name, vendor_country=vendor.country)


@router.get("/", response_model=PaginatedPOList)
async def list_pos(
    repo: RepoDep,
    status: str | None = None,
    search: str | None = None,
    vendor_id: str | None = None,
    currency: str | None = None,
    milestone: str | None = None,
    marketplace: str | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 20,
    user: User = require_auth,
) -> PaginatedPOList:
    if user.role is UserRole.VENDOR:
        vendor_id = user.vendor_id
    if page < 1:
        raise HTTPException(status_code=422, detail="page must be >= 1")
    if not (1 <= page_size <= 200):
        raise HTTPException(status_code=422, detail="page_size must be between 1 and 200")
    if sort_dir not in ("asc", "desc"):
        raise HTTPException(status_code=422, detail=f"Invalid sort_dir value: {sort_dir!r}")

    po_status: POStatus | None = None
    if status is not None:
        try:
            po_status = POStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status value: {status!r}")

    if milestone is not None:
        from src.domain.milestone import ProductionMilestone  # noqa: PLC0415
        try:
            ProductionMilestone(milestone.upper())
            milestone = milestone.upper()
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid milestone value: {milestone!r}")

    try:
        rows, total = await repo.list_pos_paginated(
            status=po_status,
            vendor_id=vendor_id,
            currency=currency,
            milestone=milestone,
            marketplace=marketplace,
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
            po_type=row["po_type"],
            vendor_id=row["vendor_id"],
            buyer_name=row["buyer_name"],
            buyer_country=row["buyer_country"],
            vendor_name=row["vendor_name"] or "",
            vendor_country=row["vendor_country"] or "",
            issued_date=row["issued_date"],
            required_delivery_date=row["required_delivery_date"],
            total_value=str(row["total_value"]),
            currency=row["currency"],
            current_milestone=row["current_milestone"],
            marketplace=row.get("marketplace"),
        )
        for row in rows
    ]
    return PaginatedPOList(items=items, total=total, page=page, page_size=page_size)


@router.post("/bulk/transition", response_model=BulkTransitionResult)
async def bulk_transition(body: BulkTransitionRequest, user: User = require_role(UserRole.SM, UserRole.VENDOR)) -> BulkTransitionResult:
    if user.role is UserRole.VENDOR and body.action in ("submit", "resubmit"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    results: list[BulkTransitionItemResult] = []
    for po_id in body.po_ids:
        async with get_db() as conn:
            repo = PurchaseOrderRepository(conn)
            activity_repo = ActivityLogRepository(conn)
            po = await repo.get(po_id)
            if po is None:
                results.append(BulkTransitionItemResult(po_id=po_id, success=False, error="Purchase order not found"))
                continue
            if user.role is UserRole.VENDOR and po.vendor_id != user.vendor_id:
                results.append(BulkTransitionItemResult(po_id=po_id, success=False, error="Not found"))
                continue
            try:
                if body.action == "submit":
                    po.submit()
                    await repo.save(po)
                    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_SUBMITTED)
                elif body.action == "accept":
                    po.accept()
                    await repo.save(po)
                    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_ACCEPTED)
                elif body.action == "reject":
                    po.reject(body.comment)
                    await repo.save(po)
                    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_REJECTED, detail=body.comment)
                elif body.action == "resubmit":
                    po.resubmit()
                    await repo.save(po)
                    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_SUBMITTED)
                results.append(BulkTransitionItemResult(po_id=po_id, success=True, new_status=po.status.value))
            except ValueError as exc:
                results.append(BulkTransitionItemResult(po_id=po_id, success=False, error=str(exc)))
    return BulkTransitionResult(results=results)


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep, user: User = require_auth) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.get("/{po_id}/pdf")
async def get_po_pdf(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep, user: User = require_auth) -> Response:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
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


@router.get("/{po_id}/invoices", response_model=list[InvoiceListItem])
async def list_po_invoices(po_id: str, repo: RepoDep, invoice_repo: InvoiceRepoDep, user: User = require_role(UserRole.SM, UserRole.VENDOR)) -> list[InvoiceListItem]:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    invoices = await invoice_repo.list_by_po(po_id)
    return [invoice_to_list_item(inv) for inv in invoices]


@router.post("/{po_id}/submit", response_model=PurchaseOrderResponse)
async def submit_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep, activity_repo: ActivityRepoDep, user: User = require_role(UserRole.SM)) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    try:
        po.submit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_SUBMITTED)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/accept", response_model=PurchaseOrderResponse)
async def accept_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep, activity_repo: ActivityRepoDep, user: User = require_role(UserRole.VENDOR, UserRole.SM)) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    try:
        po.accept()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_ACCEPTED)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/reject", response_model=PurchaseOrderResponse)
async def reject_po(po_id: str, body: RejectRequest, repo: RepoDep, vendor_repo: VendorRepoDep, activity_repo: ActivityRepoDep, user: User = require_role(UserRole.VENDOR, UserRole.SM)) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    try:
        po.reject(body.comment)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_REJECTED, detail=body.comment)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.put("/{po_id}", response_model=PurchaseOrderResponse)
async def update_po(po_id: str, body: PurchaseOrderUpdate, repo: RepoDep, vendor_repo: VendorRepoDep, activity_repo: ActivityRepoDep, user: User = require_role(UserRole.SM)) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    vendor = await vendor_repo.get_by_id(body.vendor_id)
    if vendor is None:
        raise HTTPException(status_code=422, detail="Vendor not found")
    if vendor.status is not VendorStatus.ACTIVE:
        raise HTTPException(status_code=422, detail="Vendor is not active")
    if vendor.vendor_type.value != po.po_type.value:
        raise HTTPException(
            status_code=422,
            detail=f"Vendor type {vendor.vendor_type.value} does not match PO type {po.po_type.value}",
        )
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
            marketplace=body.marketplace,
        )
    except ValueError as exc:
        status_code = 422 if str(exc).startswith("invalid ") else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    await repo.save(po)
    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_REVISED)
    return po_to_response(po, vendor_name=vendor.name, vendor_country=vendor.country)


@router.post("/{po_id}/resubmit", response_model=PurchaseOrderResponse)
async def resubmit_po(po_id: str, repo: RepoDep, vendor_repo: VendorRepoDep, activity_repo: ActivityRepoDep, user: User = require_role(UserRole.SM)) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    try:
        po.resubmit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    await activity_repo.append(EntityType.PO, po.id, ActivityEvent.PO_SUBMITTED)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)
