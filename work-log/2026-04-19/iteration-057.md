# Iteration 057 -- Negotiation UI

## Context

Iter 056 exposes modify/accept/remove/force-* endpoints and per-line edit history, but the PO detail page still uses the binary accept/reject toggles from iter 037. This iter builds the vendor modify form, SM review with counter-propose, round-2 remove prompt, force-override buttons, a line diff view, and an edit-history timeline. It builds on the current inline-CSS PO detail. Iter 053 (PO detail redesign) has not landed yet; once it does, this UI moves to DetailLayout and DataTable in a follow-up.

## JTBD (Jobs To Be Done)

- As a vendor, when I open a PENDING PO, I want per-line controls to accept, modify, or remove so I express my response without leaving the detail page.
- As an SM, when I review a vendor's modifications, I want a field-by-field diff so I can tell at a glance what changed.
- As either party, when I am about to submit my response, I want a confirmation summarizing my edits so I do not send an unintended change.
- As an SM at round 2, when a line stays contested, I want force-accept and force-remove buttons on the row so I can close the negotiation.
- As either party, when I revisit a converged line, I want the edit history collapsed to a one-line summary to reduce noise.

## Tasks

### Frontend -- Components

#### LineNegotiationRow (`frontend/src/lib/components/LineNegotiationRow.svelte`)
- [ ] Props: `line`, `role`, `round_count`, `on_modify`, `on_accept`, `on_remove`, `on_force_accept`, `on_force_remove`.
- [ ] Renders line fields read-only, plus a status pill (PENDING, MODIFIED_BY_VENDOR, MODIFIED_BY_SM, ACCEPTED, REMOVED).
- [ ] Shows action buttons based on role and current line status:
  - VENDOR: Modify, Accept (when MODIFIED_BY_SM), Remove on line in PENDING/MODIFIED state
  - SM: Modify, Accept (when MODIFIED_BY_VENDOR), Remove on line in PENDING/MODIFIED state
  - SM at round_count == 2 AND line still MODIFIED: Force Accept, Force Remove
- [ ] Clicking Modify opens ModifyLineModal.
- [ ] Buttons disabled when line is in a terminal state (ACCEPTED or REMOVED).

#### ModifyLineModal (`frontend/src/lib/components/ModifyLineModal.svelte`)
- [ ] Shared Modal wrapper.
- [ ] Pre-fills form with current line values.
- [ ] Editable inputs: quantity (int), unit_price (decimal), uom, description, hs_code, country_of_origin, required_delivery_date.
- [ ] Inline validation mirroring backend: quantity >= 0, unit_price > 0 unless quantity == 0, HS code format.
- [ ] Setting quantity to 0 shows an explanation: "This will remove the line from the PO."
- [ ] Save emits a modify request with only changed fields.
- [ ] part_number is shown read-only with tooltip: "Part number is immutable".

#### LineDiff (`frontend/src/lib/components/LineDiff.svelte`)
- [ ] Two-column before/after.
- [ ] Highlights changed fields.
- [ ] Reads `line.history`, shows latest round's delta on top.

#### EditHistoryTimeline (`frontend/src/lib/components/EditHistoryTimeline.svelte`)
- [ ] Collapsible panel.
- [ ] Expanded by default when PO status is MODIFIED or line is not converged.
- [ ] Collapses to single-line summary ("Modified N times across K rounds; final values shown above") when line is ACCEPTED or REMOVED.
- [ ] Expand toggle on click.

#### SubmitResponseBar (`frontend/src/lib/components/SubmitResponseBar.svelte`)
- [ ] Sticky bar at bottom of Line Items tab.
- [ ] Shows round indicator: "Round 1 of 2" or "Round 2 of 2".
- [ ] Submit Response button enabled when every line has a decision or counter (no PENDING lines remain unaddressed by current actor).
- [ ] Confirmation dialog summarises what will be submitted: line counts per status.

### Frontend -- API client (`frontend/src/lib/api.ts`)
- [ ] `modifyLine(poId, partNumber, fields)`
- [ ] `acceptLine(poId, partNumber)`
- [ ] `removeLine(poId, partNumber)`
- [ ] `forceAcceptLine(poId, partNumber)`
- [ ] `forceRemoveLine(poId, partNumber)`
- [ ] `submitResponse(poId)`
- [ ] All send `credentials: "include"` per iter 033.
- [ ] All redirect to /login on 401.

### Frontend -- Page integration (`frontend/src/routes/po/[id]/+page.svelte`)
- [ ] Replace existing line-items table with a list of `LineNegotiationRow`s.
- [ ] Fetch PO via existing endpoint; new fields `round_count`, `last_actor_role`, and per-line `history` present from iter 056.
- [ ] Render `SubmitResponseBar` only when PO status is PENDING or MODIFIED and current actor role can act (VENDOR when last_actor_role was SM, or vice versa; PENDING always VENDOR).
- [ ] Remove the existing RejectDialog and any code paths that call the removed `/reject` endpoint.
- [ ] Remove the existing CreateInvoiceDialog's access to non-ACCEPTED lines; it already filters, verify.

## Tests (permanent)

### Existing test impact
- `frontend/tests/po-detail*.spec.ts`: selectors for "Submit Response", per-line Accept/Reject toggles, RejectDialog all break. Update fixtures to mock new endpoints: `/modify`, `/accept`, `/remove`, `/submit-response`.
- `frontend/tests/po-lifecycle.spec.ts`: reject path is removed; update any flow that calls Reject to use Modify-with-qty-0.
- Permanent Playwright tests asserting the PO-level "Partial" pill: logic changes in iter 058. Coordinate with that iter.

### New Playwright specs (~8 specs in `frontend/tests/po-negotiation.spec.ts`)
- Vendor modifies a line, sees status pill MODIFIED_BY_VENDOR, submits response, round_count goes to 1.
- SM counter-proposes, line status becomes MODIFIED_BY_SM, vendor's next action options change.
- Vendor sets qty=0, line goes to REMOVED without intermediate MODIFIED_BY_VENDOR status.
- SM accepts all lines at round 0 via bulk convenience action if present, PO converges to ACCEPTED.
- At round 2, Force Accept and Force Remove buttons visible only for SM; hidden for VENDOR.
- Line diff view renders with correct before/after after one modification.
- Edit history timeline collapses when line reaches ACCEPTED; expandable on click.
- Submit Response confirmation dialog shows the delta summary.

## Tests (scratch)

Screenshots at 1280x800 and 375x812, saved under `frontend/tests/scratch/iteration-057/screenshots/`:
- Vendor PENDING PO with 3 lines: one modified, one accepted, one set to qty=0.
- SM reviewing MODIFIED_BY_VENDOR lines with diff visible.
- Round 2 SM view with Force Accept and Force Remove buttons.
- Edit history timeline expanded, then collapsed.
- Modify modal open with pre-filled values.

## Notes

- Built on current inline-CSS PO detail. When iter 053 lands, this UI moves to DetailLayout and Tabs. Follow-up iter will do that rewire.
- No new CSS tokens introduced. Reuses colors from `global.css`.
- All new components land in `frontend/src/lib/components/`. No co-location under routes.
- Confirmation dialog for Force Accept and Force Remove is required; the force actions are terminal and must not be single-click.

Built on the current inline-CSS PO detail as flagged in Context; iter 053 will rewire to DetailLayout/Tabs/DataTable when that lands. `canActOnNegotiation` derives "whose turn" from `po.last_actor_role`: PENDING belongs to VENDOR, MODIFIED belongs to the non-last-actor, ADMIN acts as SM to match the backend mapping. `ModifyLineFields` is a typed union sent sparsely so only fields that actually differ from the current value are transmitted, keeping line_edit_history entries minimal. Force Accept and Force Remove require an explicit confirmation dialog before hitting the backend per the iter doc mandate to prevent single-click foot-guns. The old accept-lines table path still renders for DRAFT/ACCEPTED/REJECTED/REVISED so iter 059's post-accept Remove column remains intact. 8 new permanent Playwright specs plus scratch screenshots at 1280x800 and 375x812 under `frontend/tests/scratch/iteration-057/screenshots/`. A preexisting type error on `requires_certification` in the PO detail page and `/products` page was noted but not fixed; unrelated to this iter.

## Acceptance criteria

- [ ] LineNegotiationRow renders correct actions per role and round.
- [ ] ModifyLineModal validates all fields inline, writes only changed fields to the backend.
- [ ] qty=0 in ModifyLineModal submits a modify call; backend routes to REMOVED (056 behavior).
- [ ] SM sees Force Accept and Force Remove only at round_count == 2.
- [ ] Submit Response bar enables only when the current actor has addressed every line.
- [ ] Line diff highlights changed fields.
- [ ] Edit history timeline collapses on converged lines.
- [ ] All new Playwright specs pass.
- [ ] Existing Playwright specs updated and pass.
- [ ] No reference in the frontend to the removed /reject or /accept-lines endpoints.
