from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProductionMilestone(Enum):
    RAW_MATERIALS = "RAW_MATERIALS"
    PRODUCTION_STARTED = "PRODUCTION_STARTED"
    QC_PASSED = "QC_PASSED"
    # Renamed from READY_TO_SHIP in iter 074 to disambiguate from ShipmentStatus.READY_TO_SHIP.
    # READY_FOR_SHIPMENT is the FM hand-off signal: production + QC done, batch is packed.
    READY_FOR_SHIPMENT = "READY_FOR_SHIPMENT"
    SHIPPED = "SHIPPED"


# Position in the tuple determines sequence; milestones must be posted in this order.
MILESTONE_ORDER: tuple[ProductionMilestone, ...] = (
    ProductionMilestone.RAW_MATERIALS,
    ProductionMilestone.PRODUCTION_STARTED,
    ProductionMilestone.QC_PASSED,
    ProductionMilestone.READY_FOR_SHIPMENT,
    ProductionMilestone.SHIPPED,
)


# Days a PO may sit at a given milestone before it is considered overdue.
# SHIPPED is intentionally absent — it is terminal and never overdue.
# Iter 082: extracted from routers.dashboard so the milestone router can share
# the same thresholds when computing per-row is_overdue / days_overdue.
MILESTONE_OVERDUE_THRESHOLDS: dict[str, int] = {
    ProductionMilestone.RAW_MATERIALS.value: 7,
    ProductionMilestone.PRODUCTION_STARTED.value: 7,
    ProductionMilestone.QC_PASSED.value: 3,
    ProductionMilestone.READY_FOR_SHIPMENT.value: 3,
}


def compute_days_overdue(
    milestone: ProductionMilestone,
    posted_at: datetime,
    now: datetime,
) -> int | None:
    """Days past the per-milestone threshold; None for SHIPPED (terminal).

    Returns None when the milestone has no threshold (SHIPPED, or any future
    milestone added without a threshold entry). Otherwise returns
    ``(now - posted_at).days - threshold``: zero or negative when within
    threshold, positive when overdue.
    """
    threshold = MILESTONE_OVERDUE_THRESHOLDS.get(milestone.value)
    if threshold is None:
        return None
    days_since = (now - posted_at).days
    return days_since - threshold


@dataclass
class MilestoneUpdate:
    milestone: ProductionMilestone
    posted_at: datetime


def validate_next_milestone(
    existing: list[MilestoneUpdate],
    proposed: ProductionMilestone,
) -> None:
    # First milestone must be RAW_MATERIALS; subsequent milestones must be the next in sequence.
    if not existing:
        if proposed is not MILESTONE_ORDER[0]:
            raise ValueError(
                f"first milestone must be {MILESTONE_ORDER[0].value}; got {proposed.value}"
            )
        return

    latest = existing[-1].milestone
    latest_index = MILESTONE_ORDER.index(latest)

    if proposed is latest:
        raise ValueError(f"milestone {proposed.value} has already been posted")

    if latest_index >= len(MILESTONE_ORDER) - 1:
        raise ValueError("all milestones have already been posted")

    expected = MILESTONE_ORDER[latest_index + 1]
    if proposed is not expected:
        raise ValueError(
            f"expected next milestone {expected.value}; got {proposed.value}"
        )
