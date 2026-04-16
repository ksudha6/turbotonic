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
    INVOICE_CREATED = "INVOICE_CREATED"
    INVOICE_SUBMITTED = "INVOICE_SUBMITTED"
    INVOICE_APPROVED = "INVOICE_APPROVED"
    INVOICE_PAID = "INVOICE_PAID"
    INVOICE_DISPUTED = "INVOICE_DISPUTED"
    MILESTONE_POSTED = "MILESTONE_POSTED"
    MILESTONE_OVERDUE = "MILESTONE_OVERDUE"
    CERT_UPLOADED = "CERT_UPLOADED"
    PACKAGING_COLLECTED = "PACKAGING_COLLECTED"
    PACKAGING_MISSING = "PACKAGING_MISSING"


class NotificationCategory(Enum):
    LIVE = "LIVE"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    DELAYED = "DELAYED"


class EntityType(Enum):
    PO = "PO"
    INVOICE = "INVOICE"
    CERTIFICATE = "CERTIFICATE"
    PACKAGING = "PACKAGING"


class TargetRole(Enum):
    SM = "SM"
    VENDOR = "VENDOR"


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
    ActivityEvent.INVOICE_CREATED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.INVOICE_SUBMITTED: (NotificationCategory.ACTION_REQUIRED, TargetRole.SM),
    ActivityEvent.INVOICE_APPROVED: (NotificationCategory.LIVE, TargetRole.VENDOR),
    ActivityEvent.INVOICE_PAID: (NotificationCategory.LIVE, TargetRole.VENDOR),
    ActivityEvent.INVOICE_DISPUTED: (NotificationCategory.ACTION_REQUIRED, TargetRole.VENDOR),
    ActivityEvent.MILESTONE_POSTED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.MILESTONE_OVERDUE: (NotificationCategory.DELAYED, TargetRole.SM),
    ActivityEvent.CERT_UPLOADED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.PACKAGING_COLLECTED: (NotificationCategory.LIVE, TargetRole.SM),
    ActivityEvent.PACKAGING_MISSING: (NotificationCategory.ACTION_REQUIRED, TargetRole.SM),
}
