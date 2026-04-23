"""Notification dispatcher: map activity events to email templates + recipients.

The dispatcher is decoupled from ActivityLogRepository so callers can stub the
`EmailService` in tests without touching activity persistence. Each router that
emits an email-worthy event also calls `dispatch`, which:

  1. resolves recipients via UserRepository (SM+ADMIN or vendor-scoped),
  2. renders the appropriate template,
  3. sends via EmailService (or fake in tests), and
  4. on send failure, appends an EMAIL_SEND_FAILED row so operators can replay.

Only four event types trigger email in iter 060: PO_ACCEPTED convergence,
PO_MODIFIED hand-off, PO_LINE_MODIFIED hand-off, PO_ADVANCE_PAID. Other events
continue to fire in-app-only via ActivityLogRepository.append.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.activity_repository import ActivityLogRepository
from src.domain.activity import ActivityEvent, EntityType
from src.domain.purchase_order import PurchaseOrder
from src.domain.user import UserRole
from src.services.email import EmailService
from src.user_repository import UserRepository

logger = logging.getLogger(__name__)


# Map event -> template name. PO_LINE_MODIFIED and PO_MODIFIED go to the
# counterparty — which side depends on actor_role passed via DispatchContext —
# so the template is fixed but the recipient resolution is dynamic below.
_EVENT_TEMPLATE: dict[ActivityEvent, str] = {
    ActivityEvent.PO_CONVERGED: "po_accepted",
    ActivityEvent.PO_MODIFIED: "po_modified",
    ActivityEvent.PO_LINE_MODIFIED: "po_line_modified",
    ActivityEvent.PO_ADVANCE_PAID: "po_advance_paid",
}

# SM-targeted recipient roles for the SM-side of hand-offs. Iter 060 spec:
# "all ACTIVE users with role SM or ADMIN".
_SM_ROLES: tuple[str, ...] = ("SM", "ADMIN")


@dataclass(frozen=True)
class DispatchContext:
    """Payload carried alongside an activity event for email-side formatting.

    The router supplies the human-readable bits the template needs (line detail,
    round indicator text, URL). Keeping these off the ActivityLogEntry itself
    preserves the in-app audit trail's compact shape. `actor_role` is set for
    counterparty-targeted events so the dispatcher can pick the OPPOSITE side
    without reading PO state; when None the dispatcher falls back to vendor
    targeting.
    """
    po_url: str
    line_detail: str = ""
    round_indicator: str = ""
    actor_role: UserRole | None = None


class NotificationDispatcher:
    def __init__(
        self,
        *,
        email_service: EmailService,
        user_repo: UserRepository,
        activity_repo: ActivityLogRepository,
        vendor_name_lookup: "VendorNameLookup | None" = None,
    ) -> None:
        self._email = email_service
        self._users = user_repo
        self._activity = activity_repo
        # Vendor name is derived by the caller (router already fetches vendor);
        # dispatcher takes a pre-resolved string rather than a second repo dep.
        self._vendor_name_lookup = vendor_name_lookup

    async def dispatch(
        self,
        event: ActivityEvent,
        po: PurchaseOrder,
        *,
        vendor_name: str,
        context: DispatchContext,
    ) -> None:
        template_name = _EVENT_TEMPLATE.get(event)
        if template_name is None:
            # Event does not warrant an email; silently return so routers can
            # call dispatch unconditionally without branching per event.
            return

        recipients = await self._resolve_recipients(event, po, context.actor_role)
        if not recipients:
            logger.info(
                "notifications.dispatch: no recipients for event=%s po=%s",
                event.value, po.po_number,
            )
            return

        render_context: dict[str, Any] = {
            "po_number": po.po_number,
            "po_url": context.po_url,
            "vendor_name": vendor_name,
            "line_detail": context.line_detail,
            "round_indicator": context.round_indicator,
        }
        rendered = self._email.render(template_name, render_context)

        try:
            await self._email.send(
                to=recipients,
                subject=rendered.subject,
                body_html=rendered.body_html,
                body_text=rendered.body_text,
            )
        except Exception as exc:
            # Structured failure trail: record the event type and recipient list
            # in the activity log so operators can replay. No automatic retry.
            detail = f"{event.value}: to={recipients}"
            logger.warning(
                "notifications.dispatch: send failed for event=%s po=%s err=%r",
                event.value, po.po_number, exc,
            )
            await self._activity.append(
                EntityType.PO,
                po.id,
                ActivityEvent.EMAIL_SEND_FAILED,
                detail=detail,
            )

    async def _resolve_recipients(
        self,
        event: ActivityEvent,
        po: PurchaseOrder,
        actor_role: UserRole | None,
    ) -> list[str]:
        """Return the recipient email list for the given event.

        PO_ACCEPTED / PO_CONVERGED / PO_ADVANCE_PAID -> vendor-scoped.
        PO_LINE_MODIFIED / PO_MODIFIED -> counterpart of `actor_role`:
          actor=VENDOR -> SM+ADMIN recipients; actor=SM -> vendor recipients.
        When `actor_role` is None for a counterparty event the router failed to
        supply it; default to vendor targeting to match the common first-round
        path rather than silently sending nowhere.
        """
        if event in (
            ActivityEvent.PO_ACCEPTED,
            ActivityEvent.PO_CONVERGED,
            ActivityEvent.PO_ADVANCE_PAID,
        ):
            return await self._users.list_active_emails_by_vendor(po.vendor_id)

        if event in (ActivityEvent.PO_LINE_MODIFIED, ActivityEvent.PO_MODIFIED):
            if actor_role is UserRole.VENDOR:
                return await self._users.list_active_emails_by_roles(_SM_ROLES)
            # Actor is SM (or unspecified) -> vendor users receive.
            return await self._users.list_active_emails_by_vendor(po.vendor_id)

        return []


# Stubbed alias so type hints elsewhere can reference a vendor-name callback if
# a future iter wants to load it async instead of passing pre-resolved name.
VendorNameLookup = Any
