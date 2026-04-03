# Iteration 18 — 2026-03-30

## Context
Production timeline UI on the PO detail page. Visual step indicator for milestones, update action for vendors, timestamps per milestone.

## JTBD
1. When I view an accepted procurement PO, I want to see a visual timeline of production milestones so I can quickly see progress at a glance.
2. When I'm tracking production, I want to post the next milestone from the PO detail page so I don't need a separate workflow.

## Acceptance Criteria
- PO detail shows a horizontal step indicator for all 5 milestones
- Completed milestones show a checkmark and timestamp
- The current (latest posted) milestone is highlighted
- Future milestones are grayed out
- "Post Next Milestone" button is visible only when there is a next milestone to post
- Button label shows the next milestone name (e.g. "Mark QC Passed")
- After posting, the timeline updates without a page reload
- Timeline section only renders on ACCEPTED PROCUREMENT POs

## Tasks
- Frontend: `MilestoneTimeline` component with horizontal step indicator; accepts milestone list and next milestone as props
- Frontend: Fetch milestones from `GET /api/v1/po/{po_id}/milestones` on PO detail page load
- Frontend: "Post Next Milestone" button calls `POST /api/v1/po/{po_id}/milestones` and refreshes milestone list on success
- Frontend: Conditional render gate (only ACCEPTED PROCUREMENT POs show the timeline)
- Scratch tests: screenshots of timeline at 0 milestones, 2 milestones, and fully completed

## Tests
- Timeline renders with correct completed/pending states given a milestone list
- Post button label matches the next milestone name
- Post button is absent when all milestones are posted
- Timeline is absent on non-ACCEPTED or non-PROCUREMENT POs
- Clicking Post Next Milestone advances the timeline (integration)

## Notes

