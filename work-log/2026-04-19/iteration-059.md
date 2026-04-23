# Iteration 059 -- Advance payment gate and post-acceptance line modification

## Context

After a PO is ACCEPTED, scope sometimes still needs to change: a buyer adds a forgotten SKU, a vendor reports a line that cannot ship. This iter adds two capabilities: (a) the advance-payment gate driven by `payment_terms.has_advance` reference metadata plus a `mark-advance-paid` action, and (b) post-acceptance add-line and remove-line flows scoped to SM, gated by "first milestone not yet posted" or "advance not yet paid" (whichever fires first closes the window), and per-line blocked when downstream artifacts (invoice or shipment line references) exist.

## JTBD (Jobs To Be Done)

- As an SM, when a buyer notifies me of a missing SKU right after acceptance, I want to add a line without cancelling and recreating the PO.
- As an SM, when a vendor reports a line that cannot ship, I want to remove it post-acceptance provided no invoice or shipment has consumed it.
- As either party, when a PO requires advance payment, I want the system to know so a non-advance action cannot proceed before the advance is recorded.
- As an SM, when I confirm the advance is received, I want to mark it paid on the PO so the post-acceptance modification window closes.
- As either party, when the first production milestone is posted, I want to see that scope is now locked.

## Tasks

### Reference data (`src/domain/reference_data.py`)
- [ ] Expand payment-terms representation: add `PAYMENT_TERMS_METADATA: dict[str, dict[str, object]]` with a `has_advance: bool` field per entry.
- [ ] Set `has_advance = True` for two entries: `50_PCT_ADVANCE_50_PCT_BL` and `100_PCT_ADVANCE`. All others False.
- [ ] Keep `VALID_PAYMENT_TERMS: tuple[str, ...]` as a tuple view over the metadata keys, for backward compatibility with existing validators.
- [ ] Reference data GET endpoint exposes `has_advance` per entry.

### Backend -- Schema (`src/schema.py`)
- [ ] Add `advance_paid_at TIMESTAMPTZ NULL` to `purchase_orders`.
- [ ] Idempotent ALTER.
- [ ] No `advance_required` column; derived from payment_terms metadata.

### Backend -- Domain (`src/domain/purchase_order.py`)
- [ ] Property `requires_advance` on `PurchaseOrder` returns the `has_advance` flag of its payment_terms.
- [ ] Field `advance_paid_at: datetime | None`.
- [ ] Method `mark_advance_paid(actor_id: str) -> None`. Idempotent when already set (no-op, does not advance updated_at). Raises if `status not in {ACCEPTED, MODIFIED}`. Raises if `requires_advance` is False.
- [ ] Method `first_milestone_posted_at() -> datetime | None` reads from milestone repo or cached field. Accept either pattern; document the choice.
- [ ] Method `can_modify_post_acceptance() -> bool` returns True iff: `status is ACCEPTED`, AND `first_milestone_posted_at()` is None, AND (`requires_advance is False` OR `advance_paid_at is None`).
- [ ] Method `add_line_post_acceptance(line: LineItem, actor_id: str) -> None`. Validates gate; line added with status `ACCEPTED` directly since SM is adder and no negotiation.
- [ ] Method `remove_line_post_acceptance(part_number: str, actor_id: str) -> None`. Validates gate and calls downstream artifact check.

### Backend -- Downstream artifact check (`src/services/downstream_artifacts.py` or similar)
- [ ] Function `line_has_downstream_artifacts(po_id, line_item_id) -> bool`. True if any row in `invoice_line_items` or `shipment_line_items` references the line_item_id.
- [ ] `remove_line_post_acceptance` calls this and raises `LineHasDownstreamArtifactError` when True. Router returns 409.

### Backend -- API
- [ ] `POST /api/v1/po/{po_id}/mark-advance-paid` role SM. 409 when precondition fails. 200 on success, returns updated PO.
- [ ] `POST /api/v1/po/{po_id}/lines` role SM. 409 when gate closed. 422 on validation error. 201 on create; returns updated PO.
- [ ] `DELETE /api/v1/po/{po_id}/lines/{part_number}` role SM. 409 when gate closed or downstream artifact exists. 200 on success; returns updated PO.

### Backend -- Activity events
- [ ] New events: `PO_ADVANCE_PAID`, `PO_LINE_ADDED_POST_ACCEPT`, `PO_LINE_REMOVED_POST_ACCEPT`.
- [ ] Event metadata: target_role VENDOR for PO_ADVANCE_PAID (to notify vendor production can start); both SM and VENDOR for line events. Category LIVE for all.

### Frontend
- [ ] PO detail header: Advance Paid toggle (SM only, hidden when payment_terms.has_advance is False; shows "Mark advance paid" button; after click shows "Advance paid on {date}").
- [ ] Line Items tab: post-accept add-line control (SM only, enabled only when gate open).
- [ ] Line Items tab: per-line remove button (SM only, post-accept); disabled with tooltip when gate closed or line has downstream artifacts.
- [ ] Tooltip copy: "Cannot remove: line has invoice or shipment reference" or "Cannot remove: advance paid / first milestone posted".

## Tests (permanent)

### Existing test impact
- Tests or fixtures that assume `payment_terms` is a plain set must switch to the metadata-backed view. Read `VALID_PAYMENT_TERMS` as a tuple still works; any set operations break.
- Tests or seeds that create a PO with `50_PCT_ADVANCE_50_PCT_BL` and immediately post a milestone: still work because milestone-posted closes the gate. But any test that relies on post-accept modification after that fails. Update to use `NET_30` or equivalent without advance.
- No tests break from iter 057 or 058 directly.

### New domain tests (~12 tests in `test_purchase_order.py`)
- `requires_advance` returns True for 100_PCT_ADVANCE, 50_PCT_ADVANCE_50_PCT_BL.
- `requires_advance` returns False for NET_30, TT, etc.
- `mark_advance_paid` idempotent when already set.
- `mark_advance_paid` raises when PO status is DRAFT or PENDING.
- `mark_advance_paid` raises when requires_advance is False.
- `can_modify_post_acceptance` True when ACCEPTED, no milestone, advance not applicable.
- `can_modify_post_acceptance` False when first milestone posted.
- `can_modify_post_acceptance` False when advance required and paid.
- `can_modify_post_acceptance` True when advance required but not paid.
- `add_line_post_acceptance` adds a line with status ACCEPTED.
- `remove_line_post_acceptance` raises on downstream artifact.
- `remove_line_post_acceptance` raises when gate closed.

### New API tests (~6 tests in `test_api_purchase_order.py`)
- POST /mark-advance-paid returns 200, 409 on bad state.
- POST /lines adds a line, 409 when gate closed, 403 for non-SM.
- DELETE /lines/{part_number} removes the line, 409 on downstream artifact.
- Role guard checks on all three endpoints.

### New migration tests (~2 tests)
- Existing ACCEPTED POs post-migration have `advance_paid_at = None`.
- `requires_advance` derives correctly after migration.

## Tests (scratch)

Screenshots under `frontend/tests/scratch/iteration-059/screenshots/`:
- PO detail showing Mark Advance Paid button (SM, advance-required PO, not yet paid).
- PO detail after marking paid: "Advance paid on ..." label.
- Post-accept add-line modal open.
- Post-accept remove button disabled with tooltip (downstream artifact case).

## Notes

- `PO_LINE_ADDED_POST_ACCEPT` does NOT reset round_count. The added line is ACCEPTED directly because SM is the adder. Vendor is notified via activity event and optional email (iter 060).
- Data migration note: ACCEPTED POs with payment_terms that have `has_advance = True` get `advance_paid_at = created_at` to preserve existing behaviour (treat already-flowing production as implicitly-paid). Flag to ops; otherwise migration-day UIs will show "advance not paid" on live POs.
- If SM wants an emergency override to the gate, it is out of scope for this iter. A separate `advance_override` flag is documented in the plan but not implemented here.

### Closing

Advance gate is derived from `payment_terms.has_advance` metadata rather than a per-PO `advance_required` flag; payment terms remain the single source of truth. Four payment-term codes carry `has_advance = True`: `ADV`, `CIA`, `50_PCT_ADVANCE_50_PCT_BL`, and `100_PCT_ADVANCE`, with the last two added in this iter. `mark_advance_paid` is idempotent: calling it when already set is a no-op and does not bump `updated_at`. The post-acceptance gate logic `can_modify_post_acceptance(first_milestone_posted_at)` returns True iff status is ACCEPTED AND first_milestone is None AND (not requires_advance OR advance_paid_at is None); whichever event fires first closes the window. The downstream artifact check lives as a service function (`backend/src/services/downstream_artifacts.py`) rather than inlined in the domain, probing `invoice_line_items` and `shipment_line_items` with the shipment table guarded behind an information_schema probe for environments that do not yet have iter 043. `LineHasDownstreamArtifactError` carries the reason string through to the router for 409 detail so the frontend can surface it as a tooltip. `add_line_post_acceptance` inserts the new line directly in ACCEPTED status since SM is the adder and no negotiation round occurs; it fires `PO_LINE_ADDED_POST_ACCEPT` to both roles. Data migration backfills ACCEPTED POs whose payment_terms has `has_advance = True` with `advance_paid_at = created_at` to preserve existing behaviour. The frontend stays minimal: Mark Advance Paid button in header, Add Line + per-row Remove under Line Items; iter 057 rebuilds the negotiation surface, and iter 053 (deferred) does the full detail redesign.

## Acceptance criteria

- [ ] `payment_terms` metadata includes `has_advance` per entry.
- [ ] Reference data GET endpoint returns `has_advance`.
- [ ] `PurchaseOrder.requires_advance` derives correctly.
- [ ] `advance_paid_at` column added and migrated.
- [ ] `mark_advance_paid` idempotent and gated by status.
- [ ] `can_modify_post_acceptance` logic correct per above matrix.
- [ ] Post-accept add-line and remove-line endpoints present with role guards.
- [ ] Downstream artifact check blocks removal.
- [ ] New activity events registered and fired.
- [ ] Frontend advance-paid toggle and post-accept controls land.
- [ ] All new tests pass.
- [ ] Existing tests updated where reference data representation changed.
