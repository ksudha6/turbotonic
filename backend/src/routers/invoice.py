from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException

from src.db import get_db
from src.domain.invoice import Invoice, InvoiceLineItem
from src.dto import (
    DisputeRequest,
    InvoiceCreate,
    InvoiceListItem,
    InvoiceResponse,
    invoice_to_list_item,
    invoice_to_response,
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
