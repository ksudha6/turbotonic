# Iteration 19 — 2026-03-30

## Context
Production overview and alerts. Production milestone visible on PO list, filterable. Dashboard shows POs by production stage and flags overdue production.

## JTBD
1. When I'm scanning the PO list, I want to see each PO's current production milestone so I can spot which orders are lagging without clicking into each one.
2. When I open the dashboard, I want to see how many POs are at each production stage so I have a pipeline view of manufacturing.
3. When a PO has been at the same milestone for too long, I want to see it flagged as overdue so I can follow up with the vendor.

## Acceptance Criteria
- PO list shows a "Production" column for ACCEPTED PROCUREMENT POs; blank for all others
- PO list is filterable by production milestone
- Dashboard shows a production stage breakdown: count per milestone
- Dashboard flags POs where the latest milestone is older than a threshold: 7 days for RAW_MATERIALS and PRODUCTION_STARTED, 3 days for QC_PASSED and READY_TO_SHIP
- Overdue POs are listed with PO number, vendor, milestone, and days since last update

## Tasks
- [x] Backend: Add `current_milestone` to PO list response via join or subquery on `milestone_updates`
- [x] Backend: Add `milestone` filter parameter to PO list endpoint
- [x] Backend: Add `production_summary` (count per milestone) and `overdue_pos` to dashboard endpoint
- [x] Frontend: "Production" column in PO list table (blank for non-ACCEPTED or non-PROCUREMENT rows)
- [x] Frontend: Milestone filter dropdown on PO list
- [x] Frontend: Production section on dashboard showing stage counts and overdue list
- [ ] Scratch tests: screenshots of PO list with production column, dashboard production section (carried forward)

## Tests
- [x] Backend: PO list response includes `current_milestone` field (null when no milestones posted)
- [x] Backend: Filter by milestone returns only POs at that milestone
- [x] Backend: Dashboard `production_summary` has correct counts per milestone
- [x] Backend: Overdue detection flags POs past the per-milestone threshold; does not flag POs within threshold
- [x] Frontend: PO list shows production column with correct milestone label
- [x] Frontend: Milestone filter dropdown filters the list
- [x] Frontend: Dashboard production section renders stage counts and overdue entries

## Notes

PO list adds `current_milestone` via LEFT JOIN on a subquery that gets the latest milestone per PO (MAX posted_at). Milestone filter restricts results to POs at a specific milestone stage. Dashboard adds `production_summary` (count per milestone for ACCEPTED PROCUREMENT POs) and `overdue_pos` with per-milestone thresholds (7 days for RAW_MATERIALS/PRODUCTION_STARTED, 3 days for QC_PASSED/READY_TO_SHIP, SHIPPED never overdue). Frontend dashboard production section links milestone counts to filtered PO list view.

