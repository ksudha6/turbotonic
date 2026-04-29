# Iteration 085 — `POForm` retrofit covering `/po/new` + `/po/[id]/edit` (Phase 4.2 close-out)

## Context

Phase 4.2 has shipped `/po` (list, iter 076) and `/po/[id]` (detail Tiers 2-5 + documents, iters 077, 081-084). The remaining surface in the Phase 4.2 plan is the create + edit flow: `/po/new` and `/po/[id]/edit`. Per the [v2 design spec L184-192](docs/superpowers/specs/2026-04-24-ui-revamp-v2-design.md#L184-L192), these are the last `/po/*` routes that still render under the pre-revamp top-nav layout, and the spec calls `POForm.svelte` "the biggest single retrofit" — both routes share one component, so a half-port breaks the past-flow gate.

The mock-clarity inventory ([phase-4.2-mock-clarity-inventory.md](tools/phase-4-research/phase-4.2-mock-clarity-inventory.md)) closes the create/edit decisions across G-08 through G-12 (`/po/new`), G-26 (`/po/[id]/edit`), and G-27 (the cross-cutting retrofit strategy):

- **G-27 ruling:** keep `POForm.svelte` as a single component; gate field disability by mode; port to primitives in one iter so both routes stay green at every commit.
- **G-08:** tabular at >=1024px, stacked-card per Line Item below 1024px; "Add Line Item" Button below last row at every breakpoint; HS Code errors inline via `FormField`.
- **G-09:** vendor `Select` disabled until PO Type is chosen; silent vendor clear shows inline `FormField` hint; Marketplace stays a hardcoded enum and is hidden entirely on OPEX; PO Type is read-only on edit.
- **G-10:** Buyer block stays visible inside its own `PanelCard` with `DEFAULT_BUYER_NAME`/`DEFAULT_BUYER_COUNTRY` editable in place; Buyer Country shares the country reference-data `Select` with Country of Origin.
- **G-11:** native `Select` stays for all reference-data fields; Payment Terms options append an "advance required" suffix when `has_advance` is true; closed state shows `code — label` parity with the PDF Reference Label resolver.
- **G-12:** Cancel routes back to `/po/[id]` when editing and `/po` when creating; confirm-on-discard fires only when dirty via a lightweight in-app modal; errors land per-field via `FormField` with a top banner for non-field-scoped failures; footer sticks to viewport at 390px and stays bottom-of-flow at >=768px.
- **G-26:** edit page accepts both DRAFT and REJECTED per ddd-vocab "mutable only in Draft and Rejected"; non-matching statuses render `ErrorState` inside the `FormCard` frame with a back link to detail; submit label branches to "Save & Revise" (REJECTED) vs "Save Draft" (DRAFT); REJECTED edit renders a `RejectionHistoryPanel` above the form.

After this iter the entire `/po/*` surface lives under `(nexus)` on Phase 4.0 primitives, the pre-revamp `frontend/src/lib/components/POForm.svelte` is retired (or moved/renamed under `frontend/src/lib/po/`), `isRevampRoute` no longer needs the `/po*` prefix special-case (every PO route is already `(nexus)`-mounted), and Phase 4.2 closes pending only the cross-cutting items G-28 (role-matrix audit) and G-29 (bulk-action + row-click spec migration) which the plan budgets at phase close.

## JTBD

When I (SM) start a new purchase order, I want the create form to feel like the rest of the revamped PO page — `PanelCard` rhythm, `FormField` per input, primitives I have already learned on detail and list — so my eye does not retrain on a fourth layout style on the same aggregate.

When I (SM) am entering five or more line items on a tablet, I want the line-item region to stack each line into a card I can read top-to-bottom instead of forcing horizontal scroll across nine columns, so I can verify part numbers and HS codes without losing my place.

When I (SM) get pulled into a different tab while editing a PO and accidentally hit Cancel, I want the form to stop me before discarding so I do not lose ten minutes of typing, but if I have not changed anything I want Cancel to navigate without a prompt.

When I (SM) revise a Rejected PO, I want the rejection history visible above the form so I see what to address while editing, and I want the Cancel button to take me back to the PO detail rather than the list since detail is where I came from.

When I (SM) edit a Draft PO that I started yesterday and never submitted, I want the edit page to load the form with my draft values rather than a "only Rejected POs can be edited" error so I can finish the draft. The PO type is fixed (it drives downstream cert/marketplace flow) but every other mutable field opens.

When I (any non-mutating role: VENDOR / FREIGHT_MANAGER / QUALITY_LAB / PROCUREMENT_MANAGER) hit `/po/new` or `/po/[id]/edit` directly, the route guard redirects me out without flashing the form, so I never see surface I cannot use.

## Tasks

### Frontend

1. **Port `POForm.svelte` to primitives** as `frontend/src/lib/po/PoForm.svelte`. Keep one component for both create and edit per G-27 #1. Mode prop: `mode: 'create' | 'edit-draft' | 'edit-revise'` derived by the page from `po?.status`. Existing legacy file `frontend/src/lib/components/POForm.svelte` deleted in the same iter.
   - Outer shell: a `<form>` (no `FormCard`, since the page's `PageHeader` already supplies the H1 and we need multiple titled sections + a sticky footer that `FormCard` does not provide). Skipping `FormCard` is a documented deviation from G-27 #4; rationale captured in Notes.
   - Five `PanelCard` sections in order: **Purchase Order Details** (po_type / vendor / marketplace / buyer_name / buyer_country / currency / issued_date / required_delivery_date / ship_to_address / payment_terms), **Trade Details** (incoterm / port_of_loading / port_of_discharge / country_of_origin / country_of_destination), **Terms & Conditions** (single textarea), **Line Items**, plus the sticky footer below the last panel.
   - Each form control wraps in `FormField` with `label` + optional `required` + per-field `error` slot. Inputs render via `Input` / `Select` / `DateInput` primitives. Textareas (ship-to, terms) stay as native `<textarea>` inside `FormField` (no Textarea primitive yet — note in backlog).
   - PO Type `Select` is `disabled` when `mode !== 'create'` per G-09 #5 + G-27 #2. The disabled select still shows the value.
   - Vendor `Select` is `disabled` until po_type is chosen (G-09 #1). Hint copy under the field via `FormField`'s `hint` prop reads "Select a PO type first" when disabled. When po_type changes and vendor_id no longer matches a vendor, `vendor_id` clears AND the hint becomes "Vendor cleared because it does not match the selected PO type." (G-09 #2 — inline hint, not toast).
   - Marketplace `Select` is hidden entirely when `po_type === 'OPEX'` per G-09 #4. Options: `[None, AMZ, 3PL_1, 3PL_2, 3PL_3]` (matches existing pre-revamp values; the `(nexus)/po` list uses a different marketplace vocabulary `AMAZON_US/AMAZON_EU/WALMART_US/EBAY_US` — the form value passed to backend uses the existing `AMZ/3PL_*` enum that the backend accepts; do NOT touch the list-page vocabulary in this iter).
   - Payment Terms `Select`: each option's label appends " — advance required" when `has_advance` is true on the reference-data row per G-11 #2. Iter 059 added `has_advance` to payment-term metadata; check whether reference-data API surfaces it. If it does not, skip the suffix and add a backlog item; do not extend the API in this iter.
   - All reference-data `Select`s (currency, country, port, payment_terms, incoterm) show closed state as `code — label` per G-11 #3. Native `<select>` only — no combobox.
   - Buyer block (`buyer_name`, `buyer_country`) lives inside the **Purchase Order Details** `PanelCard`, not its own panel, since splitting it into a separate panel for two fields hurts vertical scanning. (Documents G-10 #1 deviation: same-panel rather than dedicated `PanelCard`. Rationale: `PanelCard` overhead for 2 fields is heavy; the panel already carries 10 fields and the buyer prefill is visible inline.)
   - Buyer Country `Select` is the same primitive instance as Country of Origin / Destination — they share `refData.countries`. (G-10 #3.)
   - HS Code per-line error: each line's HS Code `Input` wraps in `FormField` with the existing pattern check. Submit Button stays disabled when `hasHsCodeErrors`.
   - Line Items section has its own header with "Add Line Item" `Button` (variant `secondary`) per G-08 #2. At `>=1024px`, render rows in a 9-column grid (matches pre-revamp table). At `<1024px`, switch to stacked-card mode where each line renders as a vertical block with field labels visible (G-08 #1, #4). Per-line Remove `Button` (variant `ghost`) sits at the row's right edge in tabular mode and at the card's bottom-right in stacked mode (G-08 #4).
   - Sticky footer: a `<div class="po-form-footer">` containing per-line + non-field error banner (top of footer, only when present), Cancel + Submit `Button`s (right-aligned). Footer is `position: sticky; bottom: 0` at `<=767px` with `env(safe-area-inset-bottom)` padding (matches iter 081 `PoSubmitResponseBar` pattern). At `>=768px`, footer is bottom-of-flow (not sticky). Submit Button `disabled` when `submitting || hasHsCodeErrors`.
   - Cancel routes to `/po/[id]` when `mode === 'edit-draft' | 'edit-revise'` (G-12 #1) and `/po` when `mode === 'create'`. The page passes the `cancelHref` prop; PoForm calls a callback if dirty triggers the discard modal first.
   - Dirty tracking: a `dirty` `$derived` boolean comparing current form state against initial snapshot (deep-equal for line items array; shallow-equal for header fields). When `dirty && cancel pressed`, render an inline `<dialog>` confirm-discard modal with "Discard changes?" title, "Keep editing" + "Discard" buttons. When `!dirty`, Cancel navigates immediately (G-12 #2).
   - testids: `po-form`, `po-form-section-{details|trade|terms|line-items}`, `po-form-po-type`, `po-form-vendor`, `po-form-marketplace`, `po-form-buyer-name`, `po-form-buyer-country`, `po-form-currency`, `po-form-issued-date`, `po-form-required-delivery-date`, `po-form-ship-to-address`, `po-form-payment-terms`, `po-form-incoterm`, `po-form-port-loading`, `po-form-port-discharge`, `po-form-country-origin`, `po-form-country-destination`, `po-form-terms-and-conditions`, `po-form-line-{i}-{field}`, `po-form-line-{i}-remove`, `po-form-add-line`, `po-form-error-banner`, `po-form-cancel`, `po-form-submit`, `po-form-discard-modal`, `po-form-discard-keep`, `po-form-discard-confirm`.

2. **Move `/po/new` under `(nexus)`**. New file: `frontend/src/routes/(nexus)/po/new/+page.svelte` + `+page.ts`. The page mounts `AppShell` + `UserMenu` + `PageHeader` (title "Create Purchase Order") + `PoForm` (mode='create', `cancelHref="/po"`). The old files at `frontend/src/routes/po/new/+page.svelte` and `+page.ts` get deleted in the same commit. Permission gate stays the same (`canCreatePO` redirect to `/po`).

3. **Move `/po/[id]/edit` under `(nexus)`**. New files: `frontend/src/routes/(nexus)/po/[id]/edit/+page.svelte` + `+page.ts`. The page mounts `AppShell` + `UserMenu` + `PageHeader` (title "Edit Purchase Order", subtitle = po_number) + `PoForm` (mode='edit-draft' | 'edit-revise' depending on `po.status`, `cancelHref={\`/po/\${id}\`}`). Old files deleted in same commit.
   - Status branches: `DRAFT` → mode='edit-draft', submitLabel="Save Draft" (G-26 #3 + G-26 #1).
   - `REJECTED` → mode='edit-revise', submitLabel="Save & Revise". Above the `PoForm` render `PoRejectionHistoryPanel` (already exists, iter 083) so the SM sees what to address (G-26 #5).
   - Any other status → render `ErrorState` inside the page with `message="This PO is not editable in its current status."` and a back link to detail (G-26 #2). Use `Button` variant ghost with onclick `goto(\`/po/\${id}\`)`.

4. **`isRevampRoute` simplification** in `frontend/src/routes/+layout.svelte`: drop the comment block (lines 24-27) noting the `/po/new` + `/po/[id]/edit` carve-out, since after this iter ALL `/po/*` are `(nexus)`-mounted. The `startsWith('/po/')` check stays as-is — it now covers every PO route uniformly.

5. **Backlog hygiene**: remove `Textarea` mention from any prior backlog reference if it does not exist; add a backlog entry for the missing `Textarea` primitive (current code uses native `<textarea>` inside `FormField`).

### Tests

#### Existing test impact

- `frontend/tests/po-lifecycle.spec.ts` has ~10 tests touching `/po/new` (lines 264, 304, 394, 422, 449, 493, 542, 557). They use `#vendor_id`, `#currency`, `#issued_date`, `#required_delivery_date`, `#marketplace`, `input[placeholder="Part No."]`, `input[placeholder="Qty"]`, `input[placeholder="HS Code"]`, `.error-message`, `.hs-code-cell .error-message`, `getByRole('button', { name: 'Create PO' })`. After the retrofit:
  - `#vendor_id` etc. by id no longer apply (Select primitive emits a `<select>` without that id). Migrate every selector to the new testid (`po-form-vendor`, `po-form-currency`, etc.) or to `getByRole('combobox', { name: '<label>' })`.
  - `getByRole('button', { name: 'Create PO' })` still works because the Submit `Button` renders text "Create PO".
  - `.error-message` and `.hs-code-cell .error-message` migrate to the new `FormField`-driven error testid (`po-form-line-{i}-hs-code-error`, `po-form-error-banner`).
  - Net change: rewrite per-field selectors in roughly 10 tests; assertion structure stays the same.
- `frontend/tests/role-rendering.spec.ts:347-353` (`VENDOR visiting /po/new redirects to /po`) keeps working — the redirect stays in `+page.ts` for the new route. No change needed.
- `frontend/tests/vendor.spec.ts:171` calls `page.goto('/po/new')` — verify selector updates if it asserts on form fields.
- No backend tests break (no backend changes in this iter).

#### New permanent Playwright tests in `frontend/tests/po-form.spec.ts`

1. `/po/new` mounts AppShell (sidebar + topbar visible).
2. Create form with default `po_type='PROCUREMENT'` shows vendor select enabled and marketplace select visible.
3. Switching `po_type` to `OPEX` hides marketplace select.
4. Switching `po_type` from PROCUREMENT to OPEX with a vendor selected clears `vendor_id` and shows the inline hint "Vendor cleared because it does not match the selected PO type."
5. HS code with letters shows inline `FormField` error and disables submit.
6. Submit with empty part_number on line 1 shows `po-form-error-banner` with "Part Number is required".
7. Submit with valid data POSTs body including the chosen marketplace, navigates to `/po/{id}`.
8. Cancel on a pristine form navigates to `/po` without a prompt.
9. Cancel on a dirty form opens the discard modal; "Keep editing" closes it; "Discard" navigates.
10. `/po/{id}/edit` for a REJECTED PO renders the form with initial values populated, submitLabel = "Save & Revise", and `PoRejectionHistoryPanel` above the form.
11. `/po/{id}/edit` for a DRAFT PO renders the form, submitLabel = "Save Draft", and PO Type `Select` is disabled.
12. `/po/{id}/edit` for an ACCEPTED PO renders the `ErrorState` with back-to-detail button.
13. Cancel from `/po/{id}/edit` (pristine) navigates to `/po/{id}`, not `/po`.

#### Scratch tests

None planned. Iteration is a port + structural change with no novel visual surface beyond what the primitives gallery already covers. Skip the scratch capture.

## Notes

POForm retrofit closed Phase 4.2's remaining mock-clarity gaps G-08, G-09, G-10, G-11, G-12, G-26, G-27 in a single commit so neither `/po/new` nor `/po/[id]/edit` regressed mid-flight. Both routes now mount under `(nexus)/po/` with `AppShell + UserMenu + PageHeader`. The legacy `frontend/src/lib/components/POForm.svelte` (532 lines, native `<input class="input">` + `<select class="select">` markup) is replaced by [frontend/src/lib/po/PoForm.svelte](frontend/src/lib/po/PoForm.svelte) (1 single-component port using Phase 4.0 `PanelCard` / `FormField` / `Input` / `Select` / `DateInput` / `Button`).

Mode discrimination (`'create' | 'edit-draft' | 'edit-revise'`) is a new prop. PO Type `Select` disables when `mode !== 'create'` (G-09 #5 + G-27 #2). Marketplace `Select` is hidden entirely when `po_type === 'OPEX'` (G-09 #4) — the form omits the panel rather than disabling it, since the OPEX cert/packaging fan-out skips marketplace altogether. Vendor `Select` disables until PO Type is chosen (G-09 #1); when a po_type switch invalidates the current vendor, the vendor clears and a `FormField` hint reads "Vendor cleared because it does not match the selected PO type." inline rather than via toast (G-09 #2).

G-27 #4 nominally puts everything inside one `FormCard`. I deviated: there is no `FormCard` — the page renders `PageHeader` + a `<form>` containing four `PanelCard` sections (Details / Trade / Terms / Line Items) + a custom sticky-on-mobile footer. Reason: `FormCard` requires a single title and renders a non-sticky Cancel/Submit footer, which would either duplicate the page H1 or force an awkward inner H3 + ignore G-12 #4's mobile-sticky requirement. Same outcome architecturally: one form, one submit, one cancel. Keeping this deviation documented so primitives don't churn.

Internal line state shape diverges from `LineItemInput`: a parallel `LineFormState` with string-typed numeric fields (`quantity`, `unit_price` as strings) so the `Input` primitive's string-only `value` contract two-way binds without `as unknown as string` casts. `LineItemInput.quantity: number` is reconstructed at submit via `Number.parseInt(...)`. Mirrors the iter 081 `PoLineModifyModal` pattern. Notable behavior change: pre-revamp form coerced `<input type="number">` directly onto `quantity: number`; new form parses on submit. Net effect identical for valid input; for invalid input (letters, empty), pre-revamp browser refused submission via HTML constraint, new form parses to `NaN` and the validator catches it via the `Number.isFinite + qty > 0` branch.

Dirty-tracking uses `untrack(() => JSON.stringify({...all fields...}))` for the initial snapshot and `$derived(JSON.stringify(...))` for the current snapshot. JSON.stringify deep-equals well enough for line items because LineFormState contains only string fields and arrays. Cancel pressed while `dirty` opens an in-page `<dialog>`-style backdrop modal (`po-form-discard-modal`) with "Keep editing" + "Discard" buttons. Pristine cancel navigates immediately. Cancel destination branches by mode: `/po/[id]` when editing, `/po` when creating (G-12 #1).

Edit page status branches: DRAFT and REJECTED both render the form (DRAFT was previously locked-out; the legacy edit page returned "Only rejected POs can be edited."). Per ddd-vocab "PO mutable only in Draft and Rejected", DRAFT-edit was a long-standing gap. Other statuses render a not-editable message with a "Back to detail" `Button` rather than `ErrorState` — `ErrorState` only supports an `onRetry` slot and the visual signal of "retry" is wrong here. Submit label also branches: "Save Draft" for DRAFT vs "Save & Revise" for REJECTED (G-26 #3). REJECTED edits render `PoRejectionHistoryPanel` above the form so the SM sees what to address (G-26 #5).

Test migration: 8 `/po/new` tests in [po-lifecycle.spec.ts](frontend/tests/po-lifecycle.spec.ts) ported from `#vendor_id`/`#currency`/`input[placeholder=...]`/`.error-message` selectors to the new `po-form-*` testid namespace. The legacy `evaluate(() => form.setAttribute('novalidate'))` JS hops are gone — the new form already declares `novalidate` since validation runs in JS, not the browser. One test in [vendor.spec.ts](frontend/tests/vendor.spec.ts) similarly migrated. New permanent specs land in [po-form.spec.ts](frontend/tests/po-form.spec.ts) covering AppShell mount, po_type / marketplace dependency, vendor-clear hint, payment-terms `has_advance` suffix, HS code error display + submit gating, Add Line, valid POST, dirty-state Cancel modal, REJECTED + DRAFT edit happy paths, ACCEPTED not-editable branch, and pristine-edit Cancel navigation. Net Playwright: 257 → 275 (+18). Backend: 696 → 696 (no backend changes).

Phase 4.2 mock-clarity gap inventory: G-22 (iter 084) and G-08 / G-09 / G-10 / G-11 / G-12 / G-26 / G-27 (this iter) close. Open from the inventory: G-28 (role-coverage matrix audit — cross-cutting, deferred per the plan) and G-29 (99-spec Playwright migration plan — only the touched specs migrated this iter; the rest are queued at phase close). With the create/edit form ported, every page under `/po/*` lives under `(nexus)` and follows Phase 4.0 primitives. The pre-revamp `/po*` carve-out comment in `frontend/src/routes/+layout.svelte:24-27` is removed; the existing `startsWith('/po/')` check in `isRevampRoute` already covers every PO route uniformly.

Backlog opens: native `<textarea>` is still inside `FormField` (no `Textarea` primitive yet) — the form uses three textareas (ship-to, terms, plus dialog body); promote when a fourth consumer appears. Submit-while-dirty discard modal is bespoke; promoting `Dialog` to a primitive (already on the iter 081 backlog) would let it reuse here.
