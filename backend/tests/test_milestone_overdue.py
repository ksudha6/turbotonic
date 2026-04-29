"""Permanent tests for the compute_days_overdue domain helper.

Iter 082: the helper computes days past per-milestone threshold and is the
single source of truth for both the dashboard /overdue_pos derivation and the
per-row is_overdue / days_overdue indicators on the milestone list response.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.domain.milestone import (
    MILESTONE_OVERDUE_THRESHOLDS,
    ProductionMilestone,
    compute_days_overdue,
)


_NOW = datetime(2026, 4, 29, 12, 0, 0, tzinfo=UTC)


def test_compute_days_overdue_returns_none_for_shipped() -> None:
    # SHIPPED is terminal; no overdue threshold regardless of how long ago it
    # was posted.
    posted = _NOW - timedelta(days=999)
    result = compute_days_overdue(ProductionMilestone.SHIPPED, posted, _NOW)
    assert result is None, f"SHIPPED must return None; got {result}"


def test_compute_days_overdue_returns_zero_or_negative_within_threshold() -> None:
    # RAW_MATERIALS threshold is 7. Posted 5 days ago → 5 - 7 = -2 (not overdue).
    posted = _NOW - timedelta(days=5)
    result = compute_days_overdue(ProductionMilestone.RAW_MATERIALS, posted, _NOW)
    assert result == -2, f"5 days vs 7-day threshold must return -2; got {result}"


def test_compute_days_overdue_returns_positive_past_threshold() -> None:
    # RAW_MATERIALS threshold is 7. Posted 10 days ago → 10 - 7 = 3 (overdue).
    posted = _NOW - timedelta(days=10)
    result = compute_days_overdue(ProductionMilestone.RAW_MATERIALS, posted, _NOW)
    assert result == 3, f"10 days vs 7-day threshold must return 3; got {result}"


@pytest.mark.parametrize(
    "milestone,expected_threshold",
    [
        (ProductionMilestone.RAW_MATERIALS, 7),
        (ProductionMilestone.PRODUCTION_STARTED, 7),
        (ProductionMilestone.QC_PASSED, 3),
        (ProductionMilestone.READY_FOR_SHIPMENT, 3),
    ],
)
def test_compute_days_overdue_handles_all_non_terminal_milestones(
    milestone: ProductionMilestone, expected_threshold: int
) -> None:
    # Each non-terminal milestone must be present in the threshold map and
    # produce ``days_since - threshold`` from compute_days_overdue.
    assert MILESTONE_OVERDUE_THRESHOLDS[milestone.value] == expected_threshold

    days_since = expected_threshold + 4
    posted = _NOW - timedelta(days=days_since)
    result = compute_days_overdue(milestone, posted, _NOW)
    assert result == 4, (
        f"{milestone.value}: posted {days_since}d ago vs {expected_threshold}d "
        f"threshold must return 4; got {result}"
    )
