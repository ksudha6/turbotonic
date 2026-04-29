# Iteration 082 — `/po/[id]` post-acceptance + production status revamp (Phase 4.2 Tier 4)

## Context

Phase 4.2 PO detail tier rollout. Tier 2 (iter 077) shipped the header + role-aware action rail + advance payment panel + cert warnings banner. Tier 3 (iter 081) shipped per-line negotiation cards (PENDING/MODIFIED states) + the sticky submit-response bar. The remaining ACCEPTED-PO surfaces on [(nexus)/po/[id]/+page.svelte](frontend/src/routes/(nexus)/po/[id]/+page.svelte) still render in pre-revamp shape:

- ACCEPTED line items table at [`+page.svelte:583-648`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L583) — legacy `<table class="table">` with `btn btn-secondary` + `badge badge-cert` + `badge badge-line-status` class selectors.
- Add Line dialog at [`+page.svelte:770-820`](frontend/src/routes/(nexus)/po/[id]/+page.svelte) — seven free-text inputs with no reference-data validation for UoM, HS code, or Country.
- Per-row Remove button at [`+page.svelte:631-637`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L631) — disabled with attribute tooltip when post-acceptance gate is closed.
- Production Status section at [`+page.svelte:661-668`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L661) — legacy [MilestoneTimeline](frontend/src/lib/components/MilestoneTimeline.svelte) component, separate from the Phase 4.0 [Timeline](frontend/src/lib/ui/Timeline.svelte) primitive.

These surfaces are catalogued as G-18 (post-acceptance line add/remove dialogs) and G-19 (milestone timeline placement and post-action) in the Phase 4.2 mock-clarity inventory. Decisions agreed there: hide gated controls instead of disabling them, route Country/UoM/HS code through reference-data Selects, retire `MilestoneTimeline` in favor of the Phase 4.0 primitive, surface overdue as a red dot + "Overdue" label, keep VENDOR as the only role posting milestones.

After this iter the only remaining pre-revamp sections on `(nexus)/po/[id]` are the invoice table, rejection history, activity timeline, and the metadata grid (Terms / Country / Marketplace / etc.). Those are Tier 5 scope.

## JTBD

When I am viewing an ACCEPTED PO as SM or ADMIN, I want to add or remove lines while the post-acceptance gate is open without typing free-form country codes and without seeing dead controls when the gate closes, so my edits stay valid against reference data and the UI does not advertise capabilities that are no longer reachable.

When I am viewing an ACCEPTED PROCUREMENT PO as a vendor, I want to see production progress in the same Timeline pattern used elsewhere in the app, with the next-milestone post action inline and any overdue stage marked, so I post against a single visual primitive.

## Tasks

1. Backend: extract `_OVERDUE_THRESHOLDS` from [backend/src/routers/dashboard.py](backend/src/routers/dashboard.py) to [backend/src/domain/milestone.py](backend/src/domain/milestone.py) as `MILESTONE_OVERDUE_THRESHOLDS: dict[str, int]`. Add a `compute_days_overdue(milestone: ProductionMilestone, posted_at: datetime, now: datetime) -> int | None` helper next to it: returns `None` for `SHIPPED` (terminal), and an integer days past threshold otherwise (`<= 0` when not yet overdue, positive when overdue).
2. Backend: extend `MilestoneResponse` in [backend/src/routers/milestone.py](backend/src/routers/milestone.py) with `is_overdue: bool` and `days_overdue: int | None`. Computed only for the latest milestone in the list (the "stuck" stage is always the most recent posted one); earlier milestones in the response are always `is_overdue=False, days_overdue=None`.
3. Backend: dashboard.py imports `MILESTONE_OVERDUE_THRESHOLDS` from `domain.milestone` instead of defining its own copy. Same values, single source.
4. Frontend: extend [Timeline](frontend/src/lib/ui/Timeline.svelte) primitive's `StepState` with a 4th value `'overdue'`. Marker uses `--dot-red` token; detail rendering unchanged. Add one primitives.spec.ts test for the new state.
5. Frontend: new `frontend/src/lib/po/PoMilestoneTimelinePanel.svelte` wrapping `PanelCard` + `Timeline`. Maps `MilestoneResponse[]` to Timeline steps:
   - Posted + `is_overdue=true` → `state='overdue'`, detail `"Overdue {days_overdue}d"`
   - Posted + not overdue → `state='done'`, detail = formatted posted_at
   - Next-expected (per `MILESTONE_ORDER`) → `state='current'`
   - Remaining → `state='upcoming'`
   - Inline "Post next milestone" Button (Phase 4.0 primitive) renders below the Timeline only when `canPostMilestone(role)` AND a next-expected milestone exists (i.e. not all 5 posted). Click opens the existing post-milestone form (kept as a small inline form in the panel footer slot, not a modal — matches the legacy MilestoneTimeline UX).
   - testid: `po-milestone-timeline`, `po-post-next-milestone-btn`, `po-milestone-step-{milestone}`
6. Frontend: replace the `MilestoneTimeline` import + usage at [`(nexus)/po/[id]/+page.svelte:31`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L31) and [line 664](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L664) with `PoMilestoneTimelinePanel`. Delete [frontend/src/lib/components/MilestoneTimeline.svelte](frontend/src/lib/components/MilestoneTimeline.svelte) after no consumers remain (grep all usages).
7. Frontend: new `frontend/src/lib/po/PoLineAcceptedTable.svelte` rendering ACCEPTED-PO line items as cards (matches the visual rhythm of `PoLineNegotiationTable` from iter 081). Per-line fields: part_number, description, qty, UoM, unit_price, hs_code, resolved country_of_origin label, cert badge when `cert_required.has(part_number)`, status pill, and for `po_type === 'PROCUREMENT'`: invoiced + remaining columns sourced from `remainingMap`. SM/ADMIN with `canModifyPostAccept(role)` AND gate open see a per-line Remove Button (Phase 4.0 primitive). Per-line error renders inline below the row from `errors: Map<string, string>` prop.
   - testid: `po-accepted-line-{part_number}`, `po-accepted-remove-{part_number}`
8. Frontend: gate-closed behavior changes from "disabled with tooltip" to "hidden":
   - Add Line button is omitted entirely when `postAcceptGateClosed()` (was: `<button disabled title="...">`).
   - Per-line Remove buttons are omitted entirely when `postAcceptGateClosed()`.
   - A single panel-level note renders above the line list when SM/ADMIN viewing AND gate closed: `"Post-acceptance line edits closed: advance paid or first milestone posted."` Rendered as a styled `<p data-testid="po-post-accept-gate-closed-note">` inside the Line Items section header.
9. Frontend: new `frontend/src/lib/po/PoAddLineDialog.svelte` replacing the inline `<dialog>` block at `(nexus)/po/[id]/+page.svelte:770-820`. Inputs:
   - Part number, Description, Qty, Unit price → [Input](frontend/src/lib/ui/Input.svelte) primitives wrapped in [FormField](frontend/src/lib/ui/FormField.svelte).
   - UoM → [Select](frontend/src/lib/ui/Select.svelte) sourced from `referenceData.uomCodes`.
   - HS code → [Select](frontend/src/lib/ui/Select.svelte) sourced from `referenceData.hsCodes` (free-form fallback acceptable if the reference list is sparse — confirm by reading the form pattern in [POForm.svelte](frontend/src/lib/components/POForm.svelte)).
   - Country of origin → [Select](frontend/src/lib/ui/Select.svelte) sourced from `referenceData.countries`.
   - Cancel + Submit footer Buttons (Phase 4.0 primitive). Submit calls `addLinePostAccept` and closes on success; server-error string surfaces in a `role="alert"` block at the top of the dialog.
   - testid: `po-add-line-dialog`, `po-add-line-submit`, `po-add-line-cancel`, `po-add-line-error`
10. Frontend: replace the legacy `<table class="table">` block at [`+page.svelte:583-648`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L583) with `<PoLineAcceptedTable />`. Delete the inline `<dialog>` block (now owned by `PoAddLineDialog`). Keep the `addLine`, `handleRemoveLinePostAccept`, and post-accept state declarations in the page; pass them as props.
11. Frontend: new `/ui-demo/po-accepted` mock route hosting togglable role × gate × milestone-progress matrix:
    - Role toggle: VENDOR / SM / PROCUREMENT_MANAGER
    - Gate toggle: open / closed-by-advance / closed-by-milestone
    - Milestone toggle: 0 posted / 2 posted / 4 posted / overdue (RAW_MATERIALS stuck) / SHIPPED terminal
    - PO type toggle: PROCUREMENT / OPEX (OPEX hides the milestone panel)
    - Auth-free, pure visual. Pattern matches `/ui-demo/po-line-negotiation` from iter 081.
12. Scope-fence: this iter does NOT touch invoice table, rejection history, activity timeline, or metadata grids. Those remain pre-revamp shape for Tier 5. This iter does NOT touch [permissions.ts](frontend/src/lib/permissions.ts); `canModifyPostAccept` and `canPostMilestone` are correct as-is. This iter does NOT touch the Tier 3 negotiation table, modify modal, edit-history timeline, diff component, or submit-response bar — those are PENDING/MODIFIED-only and ship through iter 081.

## Tests

### Existing test impact

- Backend: `test_dashboard_*.py` overdue assertions keep passing — `_OVERDUE_THRESHOLDS` move is a refactor with identical values.
- Backend: existing milestone list tests at [backend/tests/test_milestone_*.py](backend/tests/) that assert exact-match on `MilestoneResponse` dict shape need a fixture update — `is_overdue` and `days_overdue` keys will appear in every response. Update assertions to include both fields with default values (`False`, `None`) for non-stuck cases. Expected impact: 2-3 tests.
- Frontend: 4 specs in [po-detail.spec.ts](frontend/tests/po-detail.spec.ts) (iter 077) target `data-testid="po-milestone-timeline"` panel container — testid is preserved on the new panel, so they pass without change.
- Frontend: existing add-line/remove-line specs under [po-lifecycle.spec.ts](frontend/tests/po-lifecycle.spec.ts) targeting `data-testid="add-line-btn"` and `data-testid="remove-line-{pn}"` — testids preserved on the new components. Behavior change: gate-closed paths now assert "element is not visible" instead of "element is disabled". Expected impact: 1-3 specs need assertion shape updates.

### Permanent — backend

1. `test_milestone_overdue.py::compute_days_overdue returns None for SHIPPED` — terminal milestone never overdue regardless of posted_at.
2. `test_milestone_overdue.py::compute_days_overdue returns 0 or negative within threshold` — RAW_MATERIALS posted 5 days ago vs 7-day threshold returns -2.
3. `test_milestone_overdue.py::compute_days_overdue returns positive past threshold` — RAW_MATERIALS posted 10 days ago returns 3.
4. `test_milestone_overdue.py::compute_days_overdue handles all four non-terminal milestones` — table-driven test asserting the threshold map covers RAW_MATERIALS, PRODUCTION_STARTED, QC_PASSED, READY_FOR_SHIPMENT.
5. `test_milestone_response.py::list_milestones marks latest as overdue when stuck past threshold` — seed PO with RAW_MATERIALS posted 10 days ago via fixture, GET endpoint, assert response[0].is_overdue=True, days_overdue=3.
6. `test_milestone_response.py::list_milestones marks earlier rows is_overdue=False` — seed PO with RAW_MATERIALS 30 days ago + PRODUCTION_STARTED 2 days ago. Assert RAW_MATERIALS row is_overdue=False (not the latest), PRODUCTION_STARTED row is_overdue=False (within 7-day threshold).
7. `test_milestone_response.py::list_milestones returns empty list with no error for PO with no milestones` — sanity guard.

### Permanent — frontend

1. `primitives.spec.ts::Timeline overdue state renders red marker` — render Timeline with one `state='overdue'` step, assert via marker class or data attribute. Adds 1 test (188 → 189... actually 207 → 208 after iter 081's 206 + 1). [Recount at close.]
2. `po-detail.spec.ts::milestone timeline renders posted milestones as done steps` — mock 2 posted milestones (RAW_MATERIALS, PRODUCTION_STARTED), assert Timeline renders 5 steps with first 2 in done state, third in current state, last 2 in upcoming, and "Post next milestone" button visible to VENDOR.
3. `po-detail.spec.ts::milestone timeline marks latest as overdue when is_overdue=true` — mock latest milestone with is_overdue=true, days_overdue=4; assert step state and detail contains "Overdue 4d".
4. `po-detail.spec.ts::milestone timeline hides post button for SM` — same fixture as #2, role=SM, assert no `po-post-next-milestone-btn`.
5. `po-detail.spec.ts::milestone timeline hides post button at terminal SHIPPED` — fixture all 5 posted, assert no Post button.
6. `po-detail.spec.ts::milestone section omitted for OPEX` — mock OPEX accepted PO, assert `po-milestone-timeline` not visible.
7. `po-detail.spec.ts::accepted PO renders line items as cards via PoLineAcceptedTable` — mock ACCEPTED PROCUREMENT PO with 2 lines, assert `po-accepted-line-{pn}` rows visible with status pill role/text.
8. `po-detail.spec.ts::accepted PO line cards show invoiced + remaining for procurement` — mock with `/remaining-quantities`, assert numbers render in correct cells.
9. `po-detail.spec.ts::accepted PO line cards omit invoiced/remaining for opex` — mock OPEX, assert no invoiced/remaining text.
10. `po-detail.spec.ts::add line dialog uses reference-data selects for UoM HS code Country` — open Add Line dialog, assert each select resolves via `getByRole('combobox', { name: /uom|hs code|country/i })`.
11. `po-detail.spec.ts::add line dialog server error renders inline at top` — mock POST `/api/v1/po/{id}/lines` returns 409 with detail; submit; assert `po-add-line-error` visible inside dialog.
12. `po-detail.spec.ts::add line button hidden when gate closed by advance` — mock PO with advance_paid_at set + has_advance term, assert no `add-line-btn`.
13. `po-detail.spec.ts::add line button hidden when gate closed by milestone` — mock PO with first milestone posted, assert no `add-line-btn`.
14. `po-detail.spec.ts::remove line buttons hidden when gate closed` — same fixture, assert no `po-accepted-remove-{pn}` per row.
15. `po-detail.spec.ts::gate-closed note renders for SM` — same fixture, assert `po-post-accept-gate-closed-note` visible with copy "Post-acceptance line edits closed".
16. `po-detail.spec.ts::gate-closed note hidden for VENDOR` — same fixture, role=VENDOR, assert note not visible (vendor never has the affordance to begin with).
17. `po-detail.spec.ts::remove line server error renders inline below row` — mock remove returns 409 with detail "Cannot remove: invoice INV-1 references this line", click remove on a row, assert error visible scoped to that row only.

### Scratch

None. The 7 backend + 17 frontend permanent tests cover the role × gate × milestone matrix.

## Notes

Tier 4 closed two of the four remaining pre-revamp blocks on `(nexus)/po/[id]`: the ACCEPTED-PO line items table (G-18) and the production status timeline (G-19). The other two — invoices table and rejection history / activity timeline / metadata grid — are Tier 5.

Three decisions worth pinning:

1. **Hide-when-gate-closed beats disable-with-tooltip.** Add Line and per-line Remove are now omitted entirely when the post-acceptance gate is closed; SM/ADMIN see one panel-level note `"Post-acceptance line edits closed: advance paid or first milestone posted."` instead. Vendors never had the affordance and so never see the note. The legacy disabled-button-with-attribute-tooltip pattern lied about what was reachable; the new shape removes the falsehood.
2. **HS code and UoM stayed as `Input`, not `Select`.** `ReferenceData` does not carry HS-code or UoM lists — the existing `POForm.svelte` validates HS codes via regex and accepts free-form UoM. The Add Line dialog matches that pattern. Country of origin uses the reference-data `Select` since `referenceData.countries` exists. If we ever introduce reference-data lists for UoM or HS code, the dialog gains the `Select` swap automatically.
3. **`MILESTONE_OVERDUE_THRESHOLDS` is now single-sourced in `backend/src/domain/milestone.py`.** Dashboard router and milestone router both import the same dict, and `compute_days_overdue` is the only place the per-milestone threshold subtraction lives. The frontend mirrors `MILESTONE_ORDER` + labels in `frontend/src/lib/types.ts` for client-side step mapping; the threshold itself stays server-side and comes back attached to each `MilestoneResponse` as `is_overdue` / `days_overdue` fields. Earlier milestones in the response are always `is_overdue=False, days_overdue=None` — the "stuck" stage is always the most recent posted one.

Tier 4 also retires `frontend/src/lib/components/MilestoneTimeline.svelte` (189 lines deleted) and consolidates the post-milestone affordance into `PoMilestoneTimelinePanel`, which now derives the next-expected milestone internally and passes it as the typed `ProductionMilestone` enum value to the page's `handlePostMilestone`. The page no longer owns any milestone-form state.

Test growth: 619 → 629 backend pytest (+10), 206 → 223 Playwright (+17 plus +1 primitives Timeline overdue marker). Existing tests required no spec migrations — `is_overdue`/`days_overdue` are additive defaults, and no Playwright spec previously targeted the legacy `add-line-btn` / `remove-line-{pn}` / `MilestoneTimeline` selectors.

Domain terms emerging from this iter (proposed additions to `docs/ddd-vocab.md` pending confirmation):
- **Milestone Overdue Threshold** — per-milestone day count after which the latest posted milestone is considered overdue. Single-sourced in `backend/src/domain/milestone.py` as `MILESTONE_OVERDUE_THRESHOLDS`. Imported by dashboard and milestone routers.
- **Is Overdue** — boolean on `MilestoneResponse`. True only for the latest posted milestone when `(now - posted_at).days > threshold`. Earlier milestones always carry False.
- **Days Overdue** — integer days past threshold on `MilestoneResponse`. None for SHIPPED (terminal), negative when within threshold, positive when overdue. Returned alongside `is_overdue` per row.

Backlog opens: button-group primitive (carried from iter 081 — Tier 4's Add Line dialog footer composes Buttons inline rather than reusing a primitive); `Dialog` primitive (also carried from iter 081 — Tier 4's `PoAddLineDialog` follows the iter-081 modal pattern, not a shared primitive). These remain backlog because neither blocks Tier 5.
