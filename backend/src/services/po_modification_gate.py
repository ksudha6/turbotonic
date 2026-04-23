from __future__ import annotations

from datetime import datetime

from src.milestone_repository import MilestoneRepository


async def first_milestone_posted_at(
    milestone_repo: MilestoneRepository, po_id: str
) -> datetime | None:
    """Return the timestamp of the earliest milestone posted on this PO, or None.

    A single milestone is enough to close the post-acceptance modification window,
    so the earliest one owns the gate-close time. `list_by_po` returns updates
    ordered by posted_at ascending; the first row is the earliest.
    """
    milestones = await milestone_repo.list_by_po(po_id)
    if not milestones:
        return None
    return milestones[0].posted_at
