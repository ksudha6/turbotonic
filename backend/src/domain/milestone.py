from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProductionMilestone(Enum):
    RAW_MATERIALS = "RAW_MATERIALS"
    PRODUCTION_STARTED = "PRODUCTION_STARTED"
    QC_PASSED = "QC_PASSED"
    READY_TO_SHIP = "READY_TO_SHIP"
    SHIPPED = "SHIPPED"


# Position in the tuple determines sequence; milestones must be posted in this order.
MILESTONE_ORDER: tuple[ProductionMilestone, ...] = (
    ProductionMilestone.RAW_MATERIALS,
    ProductionMilestone.PRODUCTION_STARTED,
    ProductionMilestone.QC_PASSED,
    ProductionMilestone.READY_TO_SHIP,
    ProductionMilestone.SHIPPED,
)


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
