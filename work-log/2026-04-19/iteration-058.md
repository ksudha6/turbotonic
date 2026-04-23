# Iteration 058 -- PO PDF scoping and negotiation activity events

## Context

Iter 056 lands REMOVED lines and the MODIFIED PO status. The PO PDF must reflect agreed scope only, the PO list's Partial pill must switch to the new semantic, and the activity log needs dedicated event types per negotiation action. This iter is the consumer-facing payoff of 056.

## JTBD (Jobs To Be Done)

- As either party, when I download a PO PDF after convergence, I want only ACCEPTED lines in the document so the contract reflects what was agreed.
- As an SM scanning the PO list, I want POs with partial removals flagged with a clear pill so I can triage at a glance.
- As either party, when I read the activity feed, I want distinct entries for modifications, acceptances, removals, and force-overrides so the trail is not collapsed into one generic event.
- As either party, when a round completes, I want a single MODIFIED event so I see progress without noise from per-line events.
- As either party, when convergence happens, I want a PO_CONVERGED summary event so I know the loop is done.

## Tasks

### Backend -- PDF (`src/services/po_pdf.py` or equivalent)

- [ ] Filter line items by `status == ACCEPTED` before rendering.
- [ ] Add a `MODIFIED` label/stamp in the PDF header when the PO has `round_count >= 1` and any line was modified.
- [ ] Optional: footnote when a line's final values differ from its original values (delta note).

### Backend -- Activity events (`src/domain/activity.py` and EVENT_METADATA)

- [ ] Add event enum values:
  - `PO_LINE_MODIFIED`
  - `PO_LINE_ACCEPTED`
  - `PO_LINE_REMOVED`
  - `PO_FORCE_ACCEPTED`
  - `PO_FORCE_REMOVED`
  - `PO_MODIFIED` (hand-off)
  - `PO_CONVERGED` (terminal convergence)
- [ ] EVENT_METADATA:
  - target_role alternates based on hand-off direction: SM events target VENDOR, VENDOR events target SM.
  - Category LIVE for all line-level events; ACTION_REQUIRED for PO_MODIFIED to the counterparty.
  - PO_CONVERGED category LIVE to both roles.

### Backend -- Router wiring (`src/routers/purchase_order.py`)

- [ ] On `/modify` success: append `PO_LINE_MODIFIED` with field delta in detail.
- [ ] On `/accept` success: append `PO_LINE_ACCEPTED`.
- [ ] On `/remove` success: append `PO_LINE_REMOVED`.
- [ ] On `/force-accept` success: append `PO_FORCE_ACCEPTED`.
- [ ] On `/force-remove` success: append `PO_FORCE_REMOVED`.
- [ ] On `/submit-response`: append `PO_MODIFIED` if not converged; append `PO_CONVERGED` when PO reaches ACCEPTED or REJECTED via convergence.

### Frontend -- List pill (`routes/po/+page.svelte`)

- [ ] Redefine "Partial" pill: PO is Partial iff status is ACCEPTED AND at least one line has status REMOVED.
- [ ] New pill "Modified" when PO status is MODIFIED.
- [ ] Color mapping: Partial = warning, Modified = primary, ACCEPTED = success, REJECTED = error, PENDING = neutral.

### Frontend -- Activity feed (`ActivityTimeline.svelte`)

- [ ] Add icon and copy mapping for each of the seven new events.
- [ ] PO_LINE_MODIFIED: show part_number + a short list of changed field names.
- [ ] PO_FORCE_ACCEPTED / PO_FORCE_REMOVED: prefix with "Override:" in copy.

## Tests (permanent)

### Existing test impact

- `backend/tests/test_activity_log.py` (or equivalent): any assertion firing on `PO_REJECTED` from the old `accept_lines` flow is deleted or replaced. Update to expect PO_LINE_REMOVED plus PO_CONVERGED.
- PDF snapshot tests (if any): regenerate snapshots. REMOVED lines absent. MODIFIED stamp present when `round_count >= 1`.
- Playwright "Partial" pill spec: update fixture to use REMOVED lines instead of REJECTED; expect new copy.

### New activity tests (~10 tests in `backend/tests/test_activity_log.py`)

- Each of the seven new events appends exactly once per triggering action.
- PO_LINE_MODIFIED records field delta in detail.
- PO_MODIFIED target_role alternates correctly across rounds.
- PO_CONVERGED fires only on terminal convergence, never mid-loop.
- PO_MODIFIED does NOT fire per line edit, only on submit_response.
- ACTION_REQUIRED category only on PO_MODIFIED.
- target_role correct for SM-triggered vs VENDOR-triggered events.
- Event sequence through a full round-1 + round-2 flow matches expected list.

### New PDF tests (~3 tests in `backend/tests/test_po_pdf.py`)

- REMOVED line excluded from rendered PDF.
- MODIFIED stamp appears only with `round_count >= 1`.
- PDF with only ACCEPTED lines matches baseline count.

### New frontend Playwright tests (~2 specs in `frontend/tests/po-negotiation-events.spec.ts`)

- PO list renders new Partial and Modified pills correctly based on backend data.
- Activity timeline displays all seven new event types with correct icons and copy.

## Tests (scratch)

Screenshots under `frontend/tests/scratch/iteration-058/screenshots/`:

- PO list with Modified and Partial pills visible on different rows.
- Activity feed showing full negotiation sequence (round-1, round-2, converged).
- PDF export preview (backend snapshot) with MODIFIED stamp and REMOVED lines absent.

## Notes

- Decision: PO_MODIFIED does not collapse across multiple submit_response calls. Each hand-off is a distinct event.
- Detail payload on PO_LINE_MODIFIED is a list of changed field names, not the full old/new values. The full diff is in line_edit_history.
- Force events use their own types for clean audit; do not collapse into PO_LINE_ACCEPTED or PO_LINE_REMOVED.

Closing summary. `ActivityLogRepository.append` now accepts an optional `target_role` override via a `_Unset` sentinel so callers can distinguish "use EVENT_METADATA default" from "surface to both roles". Vendor-triggered events dynamically target SM; SM-triggered events target VENDOR; `None` means surface to both roles and is used by `PO_CONVERGED`. `submit_response` emits `PO_CONVERGED` with detail set to the final PO status on terminal convergence, replacing the old direct `PO_ACCEPTED`/`PO_REJECTED` emission from that path, while mid-loop hand-offs emit `PO_MODIFIED` in the ACTION_REQUIRED category. The PDF filter rule is asymmetric: `POStatus.ACCEPTED` renders only ACCEPTED lines, every other status renders all non-REMOVED lines, which keeps DRAFT/PENDING PDFs usable while matching the post-convergence JTBD. The footer total recomputes from rendered lines so the PDF reflects the agreed contract, not the original totals. A `has_removed_line` flag was added to `PurchaseOrderListItem` and derived directly in the paginated SQL so the frontend list pill renders Partial without a second query. One scratch test suite (`backend/tests/scratch/iteration-025`) was running under `make test` despite being gitignored; a `[tool.pytest.ini_options] norecursedirs` entry in `pyproject.toml` now matches the .gitignore contract so scratch tests stay out of the permanent suite.

## Acceptance criteria

- [ ] PO PDF filters to ACCEPTED lines only.
- [ ] MODIFIED stamp appears when round_count >= 1.
- [ ] All seven new activity event types added with correct metadata.
- [ ] Router endpoints append the correct event on success.
- [ ] List pill logic flipped: Partial iff ACCEPTED plus any REMOVED.
- [ ] Activity timeline renders all new event types.
- [ ] All existing permanent tests pass or are updated.
- [ ] All new permanent tests pass.
