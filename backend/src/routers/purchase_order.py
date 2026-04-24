from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import check_vendor_access, require_auth, require_role
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType, TargetRole
from src.domain.purchase_order import (
    LineHasDownstreamArtifactError,
    LineItem,
    POStatus,
    POType,
    PurchaseOrder,
)
from src.domain.user import User, UserRole
from src.domain.vendor import VendorStatus
from src.services.email import EmailService
from src.services.notifications import DispatchContext, NotificationDispatcher
from src.user_repository import UserRepository
from src.dto import (
    AcceptLineRequest,
    AddLinePostAcceptRequest,
    BulkTransitionItemResult,
    BulkTransitionRequest,
    BulkTransitionResult,
    CertWarningResponse,
    ForceAcceptRequest,
    ForceRemoveRequest,
    InvoiceListItem,
    MarkAdvancePaidRequest,
    ModifyLineRequest,
    POSubmitResponse,
    PaginatedPOList,
    PurchaseOrderCreate,
    PurchaseOrderListItem,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    RemoveLineRequest,
    SubmitResponseRequest,
    invoice_to_list_item,
    po_to_list_item,
    po_to_response,
)
from src.certificate_repository import CertificateRepository
from src.invoice_repository import InvoiceRepository
from src.milestone_repository import MilestoneRepository
from src.product_repository import ProductRepository
from src.qualification_type_repository import QualificationTypeRepository
from src.repository import PurchaseOrderRepository
from src.schema import init_db
from src.services.downstream_artifacts import line_has_downstream_artifacts
from src.services.po_modification_gate import first_milestone_posted_at
from src.services.po_pdf import generate_po_pdf
from src.services.quality_gate import CertWarning, check_po_qualifications
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


async def get_product_repo() -> AsyncIterator[ProductRepository]:
    async with get_db() as conn:
        yield ProductRepository(conn)


ProductRepoDep = Annotated[ProductRepository, Depends(get_product_repo)]


async def get_qualification_repo() -> AsyncIterator[QualificationTypeRepository]:
    async with get_db() as conn:
        yield QualificationTypeRepository(conn)


QualificationRepoDep = Annotated[QualificationTypeRepository, Depends(get_qualification_repo)]


async def get_cert_repo() -> AsyncIterator[CertificateRepository]:
    async with get_db() as conn:
        yield CertificateRepository(conn)


CertRepoDep = Annotated[CertificateRepository, Depends(get_cert_repo)]


def get_email_service() -> EmailService:
    # Single shared EmailService instance per request scope. Env-driven config is
    # read at construction; tests override this dep with a fake in conftest.
    return EmailService()


EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]


async def get_notification_dispatcher(
    email_service: EmailServiceDep,
    activity_repo: ActivityRepoDep,
) -> AsyncIterator[NotificationDispatcher]:
    # Dispatcher binds the EmailService, UserRepository, and ActivityRepository
    # into one unit so routers can call `dispatch` without wiring three reps.
    async with get_db() as conn:
        yield NotificationDispatcher(
            email_service=email_service,
            user_repo=UserRepository(conn),
            activity_repo=activity_repo,
        )


NotificationDispatcherDep = Annotated[
    NotificationDispatcher, Depends(get_notification_dispatcher)
]


def _po_url(po_id: str) -> str:
    # Single-source for the portal URL a recipient should open. The base URL
    # is env-configured for deployment; tests read the default and assert on the
    # suffix rather than the absolute URL.
    import os as _os
    base = _os.getenv("APP_BASE_URL", "http://localhost:5174")
    return f"{base}/po/{po_id}"


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
            round_count=row.get("round_count") or 0,
            has_removed_line=bool(row.get("has_removed_line")),
        )
        for row in rows
    ]
    return PaginatedPOList(items=items, total=total, page=page, page_size=page_size)


@router.post("/bulk/transition", response_model=BulkTransitionResult)
async def bulk_transition(body: BulkTransitionRequest, user: User = require_role(UserRole.SM, UserRole.VENDOR)) -> BulkTransitionResult:
    # Iter 056 dropped the 'reject' branch; DTO validation already narrows to submit/accept/resubmit.
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


def _warnings_to_response(warnings: list[CertWarning]) -> list[CertWarningResponse]:
    return [
        CertWarningResponse(
            line_item_index=w.line_item_index,
            part_number=w.part_number,
            product_id=w.product_id,
            qualification_name=w.qualification_name,
            reason=w.reason.value,
        )
        for w in warnings
    ]


@router.post("/{po_id}/submit", response_model=POSubmitResponse)
async def submit_po(
    po_id: str,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    product_repo: ProductRepoDep,
    qualification_repo: QualificationRepoDep,
    cert_repo: CertRepoDep,
    user: User = require_role(UserRole.SM),
) -> POSubmitResponse:
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
    warnings = await check_po_qualifications(po, product_repo, qualification_repo, cert_repo)
    return POSubmitResponse(
        po=po_to_response(po, vendor_name=vname, vendor_country=vcountry),
        cert_warnings=_warnings_to_response(warnings),
    )


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


def _actor_role_for_line(user: User) -> UserRole:
    # SM and VENDOR are the only line-negotiation actors. ADMIN acts as SM so tests
    # and operator overrides can drive negotiation without holding a VENDOR seat.
    if user.role is UserRole.ADMIN:
        return UserRole.SM
    return user.role


def _counterpart_target(actor: UserRole) -> TargetRole:
    # Line-level events notify the party that must act next. Vendor-triggered events
    # target SM; SM-triggered events target VENDOR.
    return TargetRole.SM if actor is UserRole.VENDOR else TargetRole.VENDOR


@router.post("/{po_id}/lines/{part_number}/modify", response_model=PurchaseOrderResponse)
async def modify_line_endpoint(
    po_id: str,
    part_number: str,
    body: ModifyLineRequest,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    dispatcher: NotificationDispatcherDep,
    user: User = require_role(UserRole.VENDOR, UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    actor = _actor_role_for_line(user)
    try:
        po.modify_line(part_number, actor, dict(body.fields))
    except ValueError as exc:
        msg = str(exc)
        if "unknown part_number" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        if "requires PENDING or MODIFIED status" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        # Editable-field violations, terminal-status rejections: treat as 422.
        raise HTTPException(status_code=422, detail=msg) from exc
    await repo.save(po)
    # Detail payload: part_number plus the sorted list of changed field names.
    # Full old/new values live in line_edit_history; keep activity rows compact.
    changed = sorted(body.fields.keys())
    detail = f"{part_number}: {', '.join(changed)}"
    await activity_repo.append(
        EntityType.PO,
        po.id,
        ActivityEvent.PO_LINE_MODIFIED,
        detail=detail,
        target_role=_counterpart_target(actor),
    )
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    await dispatcher.dispatch(
        ActivityEvent.PO_LINE_MODIFIED,
        po,
        vendor_name=vname,
        context=DispatchContext(
            po_url=_po_url(po.id),
            line_detail=detail,
            round_indicator=f"Round {po.round_count + 1}",
            actor_role=actor,
        ),
    )
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/lines/{part_number}/accept", response_model=PurchaseOrderResponse)
async def accept_line_endpoint(
    po_id: str,
    part_number: str,
    body: AcceptLineRequest,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.VENDOR, UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    actor = _actor_role_for_line(user)
    try:
        po.accept_line(part_number, actor)
    except ValueError as exc:
        msg = str(exc)
        if "unknown part_number" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    await repo.save(po)
    await activity_repo.append(
        EntityType.PO,
        po.id,
        ActivityEvent.PO_LINE_ACCEPTED,
        detail=part_number,
        target_role=_counterpart_target(actor),
    )
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/lines/{part_number}/remove", response_model=PurchaseOrderResponse)
async def remove_line_endpoint(
    po_id: str,
    part_number: str,
    body: RemoveLineRequest,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.VENDOR, UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    actor = _actor_role_for_line(user)
    try:
        po.remove_line(part_number, actor)
    except ValueError as exc:
        msg = str(exc)
        if "unknown part_number" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    await repo.save(po)
    await activity_repo.append(
        EntityType.PO,
        po.id,
        ActivityEvent.PO_LINE_REMOVED,
        detail=part_number,
        target_role=_counterpart_target(actor),
    )
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/lines/{part_number}/force-accept", response_model=PurchaseOrderResponse)
async def force_accept_line_endpoint(
    po_id: str,
    part_number: str,
    body: ForceAcceptRequest,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    try:
        po.force_accept_line(part_number, _actor_role_for_line(user))
    except ValueError as exc:
        msg = str(exc)
        if "unknown part_number" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        if "force actions are only permitted" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    await repo.save(po)
    # Force actions are SM-only; target the vendor with an action-history row.
    await activity_repo.append(
        EntityType.PO,
        po.id,
        ActivityEvent.PO_FORCE_ACCEPTED,
        detail=part_number,
    )
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/lines/{part_number}/force-remove", response_model=PurchaseOrderResponse)
async def force_remove_line_endpoint(
    po_id: str,
    part_number: str,
    body: ForceRemoveRequest,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    try:
        po.force_remove_line(part_number, _actor_role_for_line(user))
    except ValueError as exc:
        msg = str(exc)
        if "unknown part_number" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        if "force actions are only permitted" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    await repo.save(po)
    await activity_repo.append(
        EntityType.PO,
        po.id,
        ActivityEvent.PO_FORCE_REMOVED,
        detail=part_number,
    )
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.post("/{po_id}/submit-response", response_model=PurchaseOrderResponse)
async def submit_response_endpoint(
    po_id: str,
    body: SubmitResponseRequest,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    dispatcher: NotificationDispatcherDep,
    user: User = require_role(UserRole.VENDOR, UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    actor = _actor_role_for_line(user)
    try:
        po.submit_response(actor)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    # Convergence -> PO_CONVERGED (terminal). Otherwise -> PO_MODIFIED (hand-off).
    # Detail on PO_CONVERGED records the final PO status for quick scanning.
    if po.status in (POStatus.ACCEPTED, POStatus.REJECTED):
        await activity_repo.append(
            EntityType.PO,
            po.id,
            ActivityEvent.PO_CONVERGED,
            detail=po.status.value,
        )
        # Only the ACCEPTED convergence mails the vendor; REJECTED means no
        # production and nothing actionable to schedule.
        if po.status is POStatus.ACCEPTED:
            await dispatcher.dispatch(
                ActivityEvent.PO_CONVERGED,
                po,
                vendor_name=vname,
                context=DispatchContext(po_url=_po_url(po.id)),
            )
    else:
        await activity_repo.append(
            EntityType.PO,
            po.id,
            ActivityEvent.PO_MODIFIED,
            target_role=_counterpart_target(actor),
        )
        await dispatcher.dispatch(
            ActivityEvent.PO_MODIFIED,
            po,
            vendor_name=vname,
            context=DispatchContext(
                po_url=_po_url(po.id),
                round_indicator=f"Round {po.round_count}",
                actor_role=actor,
            ),
        )
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


# ---------------------------------------------------------------------------
# Iter 059: advance-payment gate + post-acceptance line mutations (SM-only)
# ---------------------------------------------------------------------------


@router.post("/{po_id}/mark-advance-paid", response_model=PurchaseOrderResponse)
async def mark_advance_paid_endpoint(
    po_id: str,
    body: MarkAdvancePaidRequest,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    dispatcher: NotificationDispatcherDep,
    user: User = require_role(UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    was_already_paid = po.advance_paid_at is not None
    try:
        po.mark_advance_paid(user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    # Idempotent: a repeat call does not emit another event or touch storage.
    if not was_already_paid:
        await repo.save(po)
        await activity_repo.append(
            EntityType.PO,
            po.id,
            ActivityEvent.PO_ADVANCE_PAID,
        )
        await dispatcher.dispatch(
            ActivityEvent.PO_ADVANCE_PAID,
            po,
            vendor_name=vname,
            context=DispatchContext(po_url=_po_url(po.id)),
        )
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


async def _get_first_milestone_ts(po_id: str) -> "datetime | None":
    # Resolves the gate-close "first milestone posted at" observation. The
    # router owns DB access; the domain stays pure.
    async with get_db() as conn:
        milestone_repo = MilestoneRepository(conn)
        return await first_milestone_posted_at(milestone_repo, po_id)


@router.post("/{po_id}/lines", response_model=PurchaseOrderResponse, status_code=201)
async def add_line_post_accept_endpoint(
    po_id: str,
    body: AddLinePostAcceptRequest,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    first_ms = await _get_first_milestone_ts(po_id)
    try:
        new_line = LineItem(
            part_number=body.line.part_number,
            description=body.line.description,
            quantity=body.line.quantity,
            uom=body.line.uom,
            unit_price=body.line.unit_price,
            hs_code=body.line.hs_code,
            country_of_origin=body.line.country_of_origin,
            product_id=body.line.product_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        po.add_line_post_acceptance(new_line, user.id, first_ms)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(po)
    await activity_repo.append(
        EntityType.PO,
        po.id,
        ActivityEvent.PO_LINE_ADDED_POST_ACCEPT,
        detail=new_line.part_number,
    )
    vendor = await vendor_repo.get_by_id(po.vendor_id)
    vname = vendor.name if vendor else ""
    vcountry = vendor.country if vendor else ""
    return po_to_response(po, vendor_name=vname, vendor_country=vcountry)


@router.delete("/{po_id}/lines/{part_number}", response_model=PurchaseOrderResponse)
async def remove_line_post_accept_endpoint(
    po_id: str,
    part_number: str,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.SM),
) -> PurchaseOrderResponse:
    po = await repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)
    first_ms = await _get_first_milestone_ts(po_id)
    async with get_db() as conn:
        has_artifact = await line_has_downstream_artifacts(conn, po_id, part_number)
    try:
        po.remove_line_post_acceptance(part_number, user.id, first_ms, has_artifact)
    except LineHasDownstreamArtifactError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        msg = str(exc)
        if "unknown part_number" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    await repo.save(po)
    await activity_repo.append(
        EntityType.PO,
        po.id,
        ActivityEvent.PO_LINE_REMOVED_POST_ACCEPT,
        detail=part_number,
    )
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


@router.post("/{po_id}/resubmit", response_model=POSubmitResponse)
async def resubmit_po(
    po_id: str,
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    product_repo: ProductRepoDep,
    qualification_repo: QualificationRepoDep,
    cert_repo: CertRepoDep,
    user: User = require_role(UserRole.SM),
) -> POSubmitResponse:
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
    warnings = await check_po_qualifications(po, product_repo, qualification_repo, cert_repo)
    return POSubmitResponse(
        po=po_to_response(po, vendor_name=vname, vendor_country=vcountry),
        cert_warnings=_warnings_to_response(warnings),
    )
