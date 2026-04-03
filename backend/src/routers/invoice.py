from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException

from src.db import get_db
from src.domain.invoice import Invoice, InvoiceLineItem
from src.dto import (
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

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


async def get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield InvoiceRepository(conn)


async def get_po_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield PurchaseOrderRepository(conn)


InvoiceRepoDep = Annotated[InvoiceRepository, Depends(get_invoice_repo)]
PORepoDep = Annotated[PurchaseOrderRepository, Depends(get_po_repo)]


@router.get("/po/{po_id}/remaining", response_model=RemainingQuantityResponse)
async def get_remaining_quantities(
    po_id: str,
    invoice_repo: InvoiceRepoDep,
    po_repo: PORepoDep,
) -> RemainingQuantityResponse:
    po = await po_repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    invoiced = await invoice_repo.invoiced_quantities(po_id)

    lines = [
        RemainingLineItem(
            part_number=item.part_number,
            description=item.description,
            ordered=item.quantity,
            invoiced=invoiced.get(item.part_number, 0),
            remaining=item.quantity - invoiced.get(item.part_number, 0),
        )
        for item in po.line_items
    ]

    return RemainingQuantityResponse(po_id=po_id, lines=lines)


@router.post("/", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    invoice_repo: InvoiceRepoDep,
    po_repo: PORepoDep,
) -> InvoiceResponse:
    po = await po_repo.get(body.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status.value != "ACCEPTED":
        raise HTTPException(status_code=409, detail="PO must be in ACCEPTED status to create an invoice")
    if po.po_type.value != "PROCUREMENT":
        raise HTTPException(status_code=409, detail="Invoice creation is limited to Procurement POs")

    invoice_number = await invoice_repo.next_invoice_number()
    invoiced = await invoice_repo.invoiced_quantities(po.id)

    po_lines_by_part = {item.part_number: item for item in po.line_items}

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
        for po_line in po.line_items:
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
            for item in po.line_items
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
) -> PaginatedInvoiceList:
    rows, total = await invoice_repo.list_all(
        status=status,
        po_number=po_number,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    items = [invoice_row_to_list_item_with_context(r) for r in rows]
    return PaginatedInvoiceList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, invoice_repo: InvoiceRepoDep) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/submit", response_model=InvoiceResponse)
async def submit_invoice(invoice_id: str, invoice_repo: InvoiceRepoDep) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.submit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/approve", response_model=InvoiceResponse)
async def approve_invoice(invoice_id: str, invoice_repo: InvoiceRepoDep) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.approve()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/pay", response_model=InvoiceResponse)
async def pay_invoice(invoice_id: str, invoice_repo: InvoiceRepoDep) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.pay()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/dispute", response_model=InvoiceResponse)
async def dispute_invoice(
    invoice_id: str,
    body: DisputeRequest,
    invoice_repo: InvoiceRepoDep,
) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.dispute(body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    return invoice_to_response(invoice)


@router.post("/{invoice_id}/resolve", response_model=InvoiceResponse)
async def resolve_invoice(invoice_id: str, invoice_repo: InvoiceRepoDep) -> InvoiceResponse:
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice.resolve()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await invoice_repo.save(invoice)
    return invoice_to_response(invoice)
