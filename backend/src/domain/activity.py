from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ActivityEvent(Enum):
    PO_CREATED = "PO_CREATED"
    PO_SUBMITTED = "PO_SUBMITTED"
    PO_ACCEPTED = "PO_ACCEPTED"
    PO_REJECTED = "PO_REJECTED"
    PO_REVISED = "PO_REVISED"
    # Iter 058: per-line negotiation events.
    PO_LINE_MODIFIED = "PO_LINE_MODIFIED"
    PO_LINE_ACCEPTED = "PO_LINE_ACCEPTED"
    PO_LINE_REMOVED = "PO_LINE_REMOVED"
    PO_FORCE_ACCEPTED = "PO_FORCE_ACCEPTED"
    PO_FORCE_REMOVED = "PO_FORCE_REMOVED"
    # Iter 058: PO-level hand-off and convergence events.
    PO_MODIFIED = "PO_MODIFIED"
    PO_CONVERGED = "PO_CONVERGED"
    # Iter 059: advance-payment gate and post-acceptance line mutations.
    PO_ADVANCE_PAID = "PO_ADVANCE_PAID"
    PO_LINE_ADDED_POST_ACCEPT = "PO_LINE_ADDED_POST_ACCEPT"
    PO_LINE_REMOVED_POST_ACCEPT = "PO_LINE_REMOVED_POST_ACCEPT"
    INVOICE_CREATED = "INVOICE_CREATED"
    INVOICE_SUBMITTED = "INVOICE_SUBMITTED"
    INVOICE_APPROVED = "INVOICE_APPROVED"
    INVOICE_PAID = "INVOICE_PAID"
    INVOICE_DISPUTED = "INVOICE_DISPUTED"
    MILESTONE_POSTED = "MILESTONE_POSTED"
    MILESTONE_OVERDUE = "MILESTONE_OVERDUE"
    CERT_UPLOADED = "CERT_UPLOADED"
    CERT_REQUESTED = "CERT_REQUESTED"
    PACKAGING_COLLECTED = "PACKAGING_COLLECTED"
    PACKAGING_MISSING = "PACKAGING_MISSING"
    # Iter 060: emitted when the notification dispatcher catches a send failure.
    # Operator can replay from activity_log; no automatic retry.
    EMAIL_SEND_FAILED = "EMAIL_SEND_FAILED"
    # Iter 046: document uploaded against a shipment document requirement.
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    # Iter 084: signed/countersigned PO copy or agreement attached to a PO.
    PO_DOCUMENT_UPLOADED = "PO_DOCUMENT_UPLOADED"
    # Iter 074: shipment booking lifecycle. FM records carrier + booking; SM observes.
    SHIPMENT_BOOKED = "SHIPMENT_BOOKED"
    SHIPMENT_SHIPPED = "SHIPMENT_SHIPPED"
    # Iter 099: ADMIN user-lifecycle audit events. Iter 107 assigns TargetRole.ADMIN so
    # these rows appear only in ADMIN feeds, not in SM, VENDOR, or other operational feeds.
    USER_INVITED = "USER_INVITED"
    USER_UPDATED = "USER_UPDATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_REACTIVATED = "USER_REACTIVATED"
    USER_CREDENTIALS_RESET = "USER_CREDENTIALS_RESET"
    USER_INVITE_REISSUED = "USER_INVITE_REISSUED"


class NotificationCategory(Enum):
    LIVE = "LIVE"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    DELAYED = "DELAYED"


class EntityType(Enum):
    PO = "PO"
    INVOICE = "INVOICE"
    CERTIFICATE = "CERTIFICATE"
    PACKAGING = "PACKAGING"
    SHIPMENT = "SHIPMENT"
    USER = "USER"


class TargetRole(Enum):
    SM = "SM"
    VENDOR = "VENDOR"
    QUALITY_LAB = "QUALITY_LAB"
    FREIGHT_MANAGER = "FREIGHT_MANAGER"
    PROCUREMENT_MANAGER = "PROCUREMENT_MANAGER"
    # Iter 107: ADMIN-scoped events route exclusively to ADMIN users via
    # dispatcher fan-out. Only user-lifecycle events carry this target.
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class ActivityLogEntry:
    id: str
    entity_type: EntityType
    entity_id: str
    event: ActivityEvent
    category: NotificationCategory
    target_role: TargetRole | None
    actor_id: str | None
    detail: str | None
    read_at: datetime | None
    created_at: datetime


EVENT_METADATA: dict[ActivityEvent, tuple[NotificationCategory, TargetRole | None]] = {
    ActivityEvent.PO_CREATED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.PO_SUBMITTED: (NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
    ActivityEvent.PO_ACCEPTED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.PO_REJECTED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.PO_REVISED: (NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
    # Iter 058: line-level negotiation events. Category is LIVE; target_role is
    # the counterparty and is supplied per-append by the router (VENDOR action
    # targets SM; SM action targets VENDOR). The default below matches the most
    # common SM-triggered case and is overridable in ActivityLogRepository.append.
    ActivityEvent.PO_LINE_MODIFIED: (NotificationCategory.LIVE, TargetRole.VENDOR),
    ActivityEvent.PO_LINE_ACCEPTED: (NotificationCategory.LIVE, TargetRole.VENDOR),
    ActivityEvent.PO_LINE_REMOVED: (NotificationCategory.LIVE, TargetRole.VENDOR),
    # Force events are SM-only by preconditions, so they always target VENDOR.
    ActivityEvent.PO_FORCE_ACCEPTED: (NotificationCategory.LIVE, TargetRole.VENDOR),
    ActivityEvent.PO_FORCE_REMOVED: (NotificationCategory.LIVE, TargetRole.VENDOR),
    # PO_MODIFIED is the round hand-off: the counterparty must now act.
    ActivityEvent.PO_MODIFIED: (NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
    # PO_CONVERGED terminates the loop; both parties should see it. target_role=None
    # means the row is surfaced to every role in list_recent / unread_count queries.
    ActivityEvent.PO_CONVERGED: (NotificationCategory.LIVE, None),
    # Iter 059. PO_ADVANCE_PAID notifies the vendor production can start; the
    # other two events are SM-triggered scope adjustments and surface to both roles
    # (target_role=None) so vendor and SM both see the line list change.
    ActivityEvent.PO_ADVANCE_PAID: (NotificationCategory.LIVE, TargetRole.VENDOR),
    ActivityEvent.PO_LINE_ADDED_POST_ACCEPT: (NotificationCategory.LIVE, None),
    ActivityEvent.PO_LINE_REMOVED_POST_ACCEPT: (NotificationCategory.LIVE, None),
    ActivityEvent.INVOICE_CREATED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.INVOICE_SUBMITTED: (NotificationCategory.ACTION_REQUIRED, TargetRole.SM),
    ActivityEvent.INVOICE_APPROVED: (NotificationCategory.LIVE, TargetRole.VENDOR),
    ActivityEvent.INVOICE_PAID: (NotificationCategory.LIVE, TargetRole.VENDOR),
    ActivityEvent.INVOICE_DISPUTED: (NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
    ActivityEvent.MILESTONE_POSTED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.MILESTONE_OVERDUE: (NotificationCategory.DELAYED, TargetRole.SM),
    ActivityEvent.CERT_UPLOADED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.CERT_REQUESTED: (NotificationCategory.ACTION_REQUIRED, TargetRole.QUALITY_LAB),
    ActivityEvent.PACKAGING_COLLECTED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.PACKAGING_MISSING: (NotificationCategory.ACTION_REQUIRED, TargetRole.SM),
    # Iter 060: DELAYED because an operator must intervene; surfaced to every role.
    ActivityEvent.EMAIL_SEND_FAILED: (NotificationCategory.DELAYED, None),
    # Iter 046: document uploaded against shipment requirement; SM is notified.
    ActivityEvent.DOCUMENT_UPLOADED: (NotificationCategory.LIVE, TargetRole.SM),
    # Iter 084: PO document uploaded. target_role is None (default broadcast); the
    # router supplies a per-call override: SM for PROCUREMENT, FM for OPEX.
    ActivityEvent.PO_DOCUMENT_UPLOADED: (NotificationCategory.LIVE, None),
    # Iter 074: SM observes FM bookings and dispatches.
    ActivityEvent.SHIPMENT_BOOKED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.SHIPMENT_SHIPPED: (NotificationCategory.LIVE, TargetRole.SM),
    # Iter 107: user-lifecycle events target TargetRole.ADMIN so they appear only
    # in ADMIN notification feeds. The dispatcher fans these out to all ACTIVE
    # ADMIN users via a single role-scoped query (no per-user iteration).
    ActivityEvent.USER_INVITED: (NotificationCategory.LIVE, TargetRole.ADMIN),
    ActivityEvent.USER_UPDATED: (NotificationCategory.LIVE, TargetRole.ADMIN),
    ActivityEvent.USER_DEACTIVATED: (NotificationCategory.LIVE, TargetRole.ADMIN),
    ActivityEvent.USER_REACTIVATED: (NotificationCategory.LIVE, TargetRole.ADMIN),
    ActivityEvent.USER_CREDENTIALS_RESET: (NotificationCategory.LIVE, TargetRole.ADMIN),
    ActivityEvent.USER_INVITE_REISSUED: (NotificationCategory.LIVE, TargetRole.ADMIN),
}
