from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import Response

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import check_vendor_access, require_auth, require_role
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.invoice import Invoice, InvoiceLineItem
from src.domain.user import User, UserRole
from src.dto import (
    BulkInvoicePdfRequest,
    DisputeRequest,
    InvoiceCreate,
    InvoiceListItem,
    InvoiceListItemWithContext,
    InvoiceResponse,
    PaginatedInvoiceList,
    RemainingLineItem,
    RemainingQuantityResponse,
    invoice_row_to_list_item_with_context,
    invoice_to_list_item,
    invoice_to_response,
    InvoiceLineItemCreate,
)
from src.invoice_repository import InvoiceRepository
from src.repository import PurchaseOrderRepository
from src.services.invoice_pdf import generate_bulk_invoice_pdf, generate_invoice_pdf
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


async def get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
    async with get_db() as conn:
        yield InvoiceRepository(conn)


async def get_po_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        yield PurchaseOrderRepository(conn)


async def get_vendor_repo() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        yield VendorRepository(conn)


InvoiceRepoDep = Annotated[InvoiceRepository, Depends(get_invoice_repo)]
PORepoDep = Annotated[PurchaseOrderRepository, Depends(get_po_repo)]
VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo)]


async def get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo)]


@router.get("/po/{po_id}/remaining", response_model=RemainingQuantityResponse)
async def get_remaining_quantities(
    po_id: str,
    invoice_repo: InvoiceRepoDep,
    po_repo: PORepoDep,
    user: User = require_role(UserRole.SM, UserRole.VENDOR),
) -> RemainingQuantityResponse:
    po = await po_repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)

    invoiced = await invoice_repo.invoiced_quantities(po_id)

    lines = []
    for item in po.line_items:
        # REJECTED lines contribute zero remaining quantity
        if item.status.value == "REJECTED":
            lines.append(
                RemainingLineItem(
                    part_number=item.part_number,
                    description=item.description,
                    ordered=item.quantity,
                    invoiced=invoiced.get(item.part_number, 0),
                    remaining=0,
                )
            )
        else:
            lines.append(
                RemainingLineItem(
                    part_number=item.part_number,
                    description=item.description,
                    ordered=item.quantity,
                    invoiced=invoiced.get(item.part_number, 0),
                    remaining=item.quantity - invoiced.get(item.part_number, 0),
                )
            )

    return RemainingQuantityResponse(po_id=po_id, lines=lines)


@router.post("/", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    invoice_repo: InvoiceRepoDep,
    po_repo: PORepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.VENDOR, UserRole.SM),
) -> InvoiceResponse:
    po = await po_repo.get(body.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    if po.status.value != "ACCEPTED":
        raise HTTPException(status_code=409, detail="PO must be in ACCEPTED status to create an invoice")

    invoice_number = await invoice_repo.next_invoice_number()
    invoiced = await invoice_repo.invoiced_quantities(po.id)

    if po.po_type.value == "OPEX":
        if body.line_items is not None:
            raise HTTPException(
                status_code=422,
                detail="OPEX invoices do not accept line_items; full PO quantity is used automatically",
            )
        if any(qty > 0 for qty in invoiced.values()):
            raise HTTPException(status_code=409, detail="An invoice already exists for this OPEX PO")

    # REJECTED line items are excluded from invoicing
    accepted_po_lines = [item for item in po.line_items if item.status.value != "REJECTED"]
    po_lines_by_part = {item.part_number: item for item in accepted_po_lines}

    if body.line_items is not None:
        requested_by_part: dict[str, int] = {item.part_number: item.quantity for item in body.line_items}

        unknown = [pn for pn in requested_by_part if pn not in po_lines_by_part]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown part numbers: {', '.join(unknown)}",
            )

        active = {pn: qty for pn, qty in requested_by_part.items() if qty > 0}
        if not active:
            raise HTTPException(status_code=400, detail="At least one line item must have quantity > 0")

        violations = []
        for part_number, requested_qty in active.items():
            po_line = po_lines_by_part[part_number]
            already_invoiced = invoiced.get(part_number, 0)
            if already_invoiced + requested_qty > po_line.quantity:
                violations.append({
                    "part_number": part_number,
                    "ordered": po_line.quantity,
                    "already_invoiced": already_invoiced,
                    "requested": requested_qty,
                })
        if violations:
            raise HTTPException(status_code=409, detail=violations)

        line_items = [
            InvoiceLineItem(
                part_number=part_number,
                description=po_lines_by_part[part_number].description,
                quantity=requested_qty,
                uom=po_lines_by_part[part_number].uom,
                unit_price=po_lines_by_part[part_number].unit_price,
            )
            for part_number, requested_qty in active.items()
        ]
    else:
        violations = []
        for po_line in accepted_po_lines:
            already_invoiced = invoiced.get(po_line.part_number, 0)
            if already_invoiced + po_line.quantity > po_line.quantity:
                violations.append({
                    "part_number": po_line.part_number,
                    "ordered": po_line.quantity,
                    "already_invoiced": already_invoiced,
                    "requested": po_line.quantity,
                })
        if violations:
            raise HTTPException(status_code=409, detail=violations)

        line_items = [
            InvoiceLineItem(
                part_number=item.part_number,
                description=item.description,
                quantity=item.quantity,
                uom=item.uom,
                unit_price=item.unit_price,
            )
            for item in accepted_po_lines
        ]

    try:
        invoice = Invoice.create(
            invoice_number=invoice_number,
            po_id=po.id,
            po_status=po.status.value,
            po_type=po.po_type.value,
            payment_terms=po.payment_terms,
            currency=po.currency,
            line_items=line_items,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await invoice_repo.save(invoice)
    await activity_repo.append(EntityType.INVOICE, invoice.id, ActivityEvent.INVOICE_CREATED)
    return invoice_to_response(invoice)


@router.get("/", response_model=PaginatedInvoiceList)
async def list_invoices(
    invoice_repo: InvoiceRepoDep,
    status: str | None = None,
    po_number: str | None = None,
    vendor_name: str | None = None,
    invoice_number: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = require_role(UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER),
) -> PaginatedInvoiceList:
    scoped_vendor_id = user.vendor_id if user.role is UserRole.VENDOR else None
    rows, total = await invoice_repo.list_all(
        status=status,
        po_number=po_number,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        vendor_id=scoped_vendor_id,
    )
    items = [invoice_row_to_list_item_with_context(r) for r in rows]
    return PaginatedInvoiceList(items=items, total=total, page=page, page_size=page_size)


@router.post("/bulk/pdf")
async def bulk_invoice_pdf(
    body: BulkInvoicePdfRequest,
    invoice_repo: InvoiceRepoDep,
    po_repo: PORepoDep,
    vendor_repo: VendorRepoDep,
    user: User = require_role(UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER),
) -> Response:
    if not body.invoice_ids:
        raise HTTPException(status_code=400, detail="invoice_ids must not be empty")

    invoices_with_context: list[tuple] = []
    for invoice_id in body.invoice_ids:
        invoice = await invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            continue
        po = await po_repo.get(invoice.po_id)
        if po is None:
            continue
        # VENDOR users only see invoices on their own POs; skip others silently.
        if user.role is UserRole.VENDOR and user.vendor_id != po.vendor_id:
            continue
        vendor = await vendor_repo.get_by_id(po.vendor_id)
        vendor_name = vendor.name if vendor is not None else ""
        vendor_country = vendor.country if vendor is not None else ""
        invoices_with_context.append((invoice, po, vendor_name, vendor_country))

    pdf_bytes = generate_bulk_invoice_pdf(invoices_with_context)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=\"invoices-bulk.pdf\""},
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    invoice_repo: InvoiceRepoDep,
    po_repo: PORepoDep,
    user: User = require_role(UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER),
) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    po = await po_repo.get(invoice.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    return invoice_to_response(invoice)


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    invoice_repo: InvoiceRepoDep,
    po_repo: PORepoDep,
    vendor_repo: VendorRepoDep,
    user: User = require_role(UserRole.SM, UserRole.VENDOR, UserRole.FREIGHT_MANAGER),
) -> Response:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    po = await po_repo.get(invoice.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)

    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vendor_name = vendor.name if vendor is not None else ""
    vendor_country = vendor.country if vendor is not None else ""

    # Filename uses invoice_number with date prefix stripped of separators.
    date_part = invoice.created_at.strftime("%Y%m%d")
    filename = f"{invoice.invoice_number}-{date_part}.pdf"

    pdf_bytes = generate_invoice_pdf(invoice, po, vendor_name, vendor_country)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.post("/{invoice_id}/submit", response_model=InvoiceResponse)
async def submit_invoice(
    invoice_id: str,
    invoice_repo: InvoiceRepoDep,
    po_repo: PORepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.VENDOR, UserRole.SM),
) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    po = await po_repo.get(invoice.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    try:
        invoice.submit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    await activity_repo.append(EntityType.INVOICE, invoice.id, ActivityEvent.INVOICE_SUBMITTED)
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/approve", response_model=InvoiceResponse)
async def approve_invoice(invoice_id: str, invoice_repo: InvoiceRepoDep, activity_repo: ActivityRepoDep, _user: User = require_role(UserRole.SM)) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.approve()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    await activity_repo.append(EntityType.INVOICE, invoice.id, ActivityEvent.INVOICE_APPROVED)
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/pay", response_model=InvoiceResponse)
async def pay_invoice(invoice_id: str, invoice_repo: InvoiceRepoDep, activity_repo: ActivityRepoDep, _user: User = require_role(UserRole.SM)) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.pay()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    await activity_repo.append(EntityType.INVOICE, invoice.id, ActivityEvent.INVOICE_PAID)
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/dispute", response_model=InvoiceResponse)
async def dispute_invoice(
    invoice_id: str,
    body: DisputeRequest,
    invoice_repo: InvoiceRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.SM),
) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.dispute(body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    await activity_repo.append(EntityType.INVOICE, invoice.id, ActivityEvent.INVOICE_DISPUTED, detail=body.reason)
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/resolve", response_model=InvoiceResponse)
async def resolve_invoice(invoice_id: str, invoice_repo: InvoiceRepoDep, activity_repo: ActivityRepoDep, _user: User = require_role(UserRole.SM)) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.resolve()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    await activity_repo.append(EntityType.INVOICE, invoice.id, ActivityEvent.INVOICE_SUBMITTED)
    return invoice_to_response(invoice)
