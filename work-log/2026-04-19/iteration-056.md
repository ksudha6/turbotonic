# Iteration 056 -- Line-level negotiation domain and API

## Context

The current `accept_lines` from iter 037 is one-shot: vendor accepts or rejects each line, PO transitions to ACCEPTED or REJECTED, no counter-proposal path. Iter 056 replaces that with a two-round negotiation loop where vendor modifies lines, SM counters, and convergence requires every line to end ACCEPTED or REMOVED. Round counter is PO-scoped with a max of 2. After round 2 SM has force-accept and force-remove overrides.

## JTBD (Jobs To Be Done)

- As a vendor, when I cannot fulfil a line at the proposed price or quantity, I want to counter-propose a modification so the buyer can decide without rejecting the whole PO.
- As an SM, when a vendor's modification is unacceptable, I want to counter back with my revised terms so we converge on agreed fields.
- As an SM, when negotiation stalls after two rounds, I want to force-accept or force-remove a disputed line so the PO can close.
- As a vendor, when a line is unworkable at any price, I want to set qty=0 and have it removed cleanly without aborting the whole PO.
- As either party, when I review a line under negotiation, I want to see every field edit in round order so I know what I am agreeing to.

## Tasks

### Backend -- Schema
- [ ] Add columns to `purchase_orders`: `round_count INTEGER NOT NULL DEFAULT 0`, `last_actor_role TEXT`. CHECK `round_count BETWEEN 0 AND 2`.
- [ ] Extend `line_items.status` enum to include `MODIFIED_BY_VENDOR`, `MODIFIED_BY_SM`, `REMOVED`. Drop `REJECTED` from line-item status.
- [ ] Migration: `UPDATE line_items SET status = 'REMOVED' WHERE status = 'REJECTED'`.
- [ ] New table `line_edit_history(id, po_id, line_item_id, part_number, round, actor_role, field, old_value TEXT, new_value TEXT, edited_at)`. Index on `(po_id, round, line_item_id)`.
- [ ] Add `required_delivery_date TIMESTAMPTZ NULL` to `line_items` (per-line override; null means inherit from PO).

### Backend -- Domain (`src/domain/purchase_order.py`)
- [ ] Extend `LineItemStatus` with `MODIFIED_BY_VENDOR`, `MODIFIED_BY_SM`, `REMOVED`. Remove `REJECTED`.
- [ ] Extend `POStatus` with `MODIFIED`. `REJECTED` kept but only reachable via convergence.
- [ ] New `LineEditHistoryEntry` dataclass: `round: int`, `actor_role: UserRole`, `field: str`, `old_value: str`, `new_value: str`, `edited_at: datetime`.
- [ ] Add to `PurchaseOrder`: `round_count: int = 0`, `last_actor_role: UserRole | None = None`, `line_edit_history: list[LineEditHistoryEntry]`.
- [ ] Editable field whitelist: tuple `EDITABLE_LINE_FIELDS = ("quantity", "unit_price", "uom", "description", "hs_code", "country_of_origin", "required_delivery_date")`.
- [ ] New methods:
  - `modify_line(part_number: str, actor_role: UserRole, fields: dict[str, object]) -> None`
    - Rejects if PO status not in {PENDING, MODIFIED}; rejects if line already ACCEPTED or REMOVED; rejects if any field not in EDITABLE_LINE_FIELDS; rejects if `part_number` present in fields.
    - Setting `quantity == 0` sets status REMOVED and skips MODIFIED_BY_*.
    - Otherwise status becomes MODIFIED_BY_VENDOR or MODIFIED_BY_SM based on actor_role.
    - Appends one LineEditHistoryEntry per changed field.
  - `accept_line(part_number: str, actor_role: UserRole) -> None`
    - Rejects if line status not in {PENDING, MODIFIED_BY_VENDOR, MODIFIED_BY_SM} or if the current actor_role is the same as last modifier.
    - Sets line status ACCEPTED.
  - `remove_line(part_number: str, actor_role: UserRole) -> None`
    - Pre-acceptance removal. Status becomes REMOVED.
  - `force_accept_line(part_number: str, actor_id: str) -> None`
    - Only valid when `round_count == 2` and caller is SM. Sets line ACCEPTED.
  - `force_remove_line(part_number: str, actor_id: str) -> None`
    - Only valid when `round_count == 2` and caller is SM. Sets line REMOVED.
  - `submit_response(actor_role: UserRole) -> None`
    - Flips hand-off, increments `round_count` by 1, sets `last_actor_role`.
    - Rejects if `round_count` already at 2 and no forced actions used.
    - Convergence check: if every line is ACCEPTED or REMOVED and at least one ACCEPTED, transitions PO to ACCEPTED. If every line REMOVED, transitions to REJECTED. Otherwise PO stays MODIFIED.
- [ ] Drop `accept_lines()` and `reject()` methods. Keep `accept()` as convenience (SM accepts all lines at round 0).

### Backend -- DTO (`src/dto.py`)
- [ ] New request DTOs: `ModifyLineRequest(fields: dict)`, `AcceptLineRequest`, `RemoveLineRequest`, `ForceAcceptRequest`, `ForceRemoveRequest`, `SubmitResponseRequest`.
- [ ] Expand `LineItemResponse` to include `history: list[LineEditEntryDTO]`.
- [ ] Add `PurchaseOrderResponse.round_count: int` and `PurchaseOrderResponse.last_actor_role: str | None`.

### Backend -- Repository (`src/repository.py`)
- [ ] Persist new columns on save and load.
- [ ] Persist line_edit_history delta on save. Load full history in `get`.
- [ ] Include `round_count` in list pagination projection.

### Backend -- Router (`src/routers/purchase_order.py`)
- [ ] Replace `/accept-lines` with:
  - `POST /api/v1/po/{po_id}/lines/{part_number}/modify` role VENDOR or SM
  - `POST /api/v1/po/{po_id}/lines/{part_number}/accept` role VENDOR or SM
  - `POST /api/v1/po/{po_id}/lines/{part_number}/remove` role VENDOR or SM
  - `POST /api/v1/po/{po_id}/lines/{part_number}/force-accept` role SM, requires round_count == 2
  - `POST /api/v1/po/{po_id}/lines/{part_number}/force-remove` role SM, requires round_count == 2
  - `POST /api/v1/po/{po_id}/submit-response` role VENDOR or SM
- [ ] Return 409 on wrong PO status; 422 on invalid fields; 403 on force action outside round 2; 404 on unknown part_number.
- [ ] Bulk transition endpoint: drop the `reject` branch, return 422 if requested.

### Migration
- [ ] Idempotent ALTERs in `schema.py`.
- [ ] Backfill `round_count = 0` for all existing POs.
- [ ] Map line-item `REJECTED` to `REMOVED`.

## Tests (permanent)

### Existing test impact
- `backend/tests/test_purchase_order.py`: delete `test_accept_lines_*` (6 tests) and `test_reject_*` tests relying on the old `reject()` method. Rewrite as per new permanent set below.
- `backend/tests/test_api_purchase_order.py`: delete six `/accept-lines` API tests and any `/reject` endpoint test. Rewrite against new endpoints.
- `backend/tests/test_api_shipment.py`: remove `xfail` markers once 056 merges (the rejected-line-item case now exercises a reachable state). Note to self: this is the iter 043 test that was blocked.
- `backend/tests/test_api_purchase_order.py::test_bulk_transition_*`: remove `reject` branch coverage or assert 422 response.
- Permanent Playwright spec asserting "Submit Response" button: selectors change when iter 057 rewrites the page; flag for that iter's sub-agent.

### New domain tests (~25 tests in `test_purchase_order.py`)
- `modify_line` rejects non-editable fields
- `modify_line` rejects part_number change attempts
- `modify_line` with quantity=0 routes line to REMOVED directly
- `modify_line` rejects unknown part_number
- `modify_line` rejects call when PO status not PENDING or MODIFIED
- `modify_line` rejects call when line status ACCEPTED or REMOVED
- `modify_line` appends one history entry per changed field
- `accept_line` rejects when same role modified last
- `accept_line` transitions line to ACCEPTED
- `remove_line` transitions line to REMOVED
- `force_accept_line` rejects at round_count < 2
- `force_accept_line` rejects non-SM role
- `force_remove_line` rejects at round_count < 2
- `submit_response` increments round_count
- `submit_response` rejects when round_count already 2 and no force used
- `submit_response` flips last_actor_role
- Convergence: all ACCEPTED -> PO ACCEPTED
- Convergence: mix of ACCEPTED and REMOVED -> PO ACCEPTED
- Convergence: all REMOVED -> PO REJECTED
- Convergence: pending lines -> PO stays MODIFIED
- Round cap enforcement at 2
- line_edit_history order preserved across rounds
- EDITABLE_LINE_FIELDS immutability: tuple, not list
- accept() convenience method still sets all lines ACCEPTED
- Integration: full round-1 + round-2 + force accept scenario

### New API tests (~15 tests in `test_api_purchase_order.py`)
- POST /modify returns 200, persists change, appends history
- POST /modify returns 422 on non-editable field
- POST /accept returns 200, 409 on bad precondition
- POST /remove returns 200
- POST /force-accept returns 403 at round 1
- POST /force-accept returns 200 at round 2 for SM
- POST /force-accept returns 403 for non-SM
- POST /force-remove returns 200 at round 2 for SM
- POST /submit-response increments round, returns updated PO
- POST /submit-response convergence sets PO ACCEPTED
- Role guard on /modify (VENDOR + SM allowed)
- Role guard rejects OTHER roles
- 404 on unknown part_number
- Bulk transition reject branch returns 422
- `accept_lines` endpoint removed (returns 404)

### New repository tests (~5 tests in `test_repository.py`)
- round_count persists through save + get
- line_edit_history persists in order
- MODIFIED PO status round-trips
- REMOVED line status round-trips
- List pagination returns round_count

## Tests (scratch)

None for iter 056. UI lands in iter 057.

## Notes

- `modify_line` is append-only on history: every call appends rows for every changed field, even if the same vendor modifies twice in one round. Simpler audit, smaller invariants.
- `required_delivery_date` becomes a per-line nullable field. Null means inherit from PO. Additive migration.
- `accept_lines` endpoint and method fully removed. Any remaining references in seed scripts are updated to call the new per-line endpoints or `accept()`.
- `reject()` is removed. A PO becomes REJECTED only when all lines are REMOVED through the loop.
- Iter 043 shipment xfailed test is unblocked after this iter; marker removal tracked there.
- Iter 028 backlog "Partial PO acceptance" closes with this iter.

### Closing summary

Dropped `PurchaseOrder.reject()` and the `/reject` endpoint entirely; REJECTED is now reachable only by convergence when every line ends REMOVED. Dropped `accept_lines()` and `/accept-lines` in favour of per-line endpoints for modify, accept, remove, force-accept, force-remove, and submit-response. `EDITABLE_LINE_FIELDS` is a tuple of (quantity, unit_price, uom, description, hs_code, country_of_origin, required_delivery_date); `part_number` is excluded. `modify_line` is append-only on history: every call appends one row per changed field. qty=0 on `modify_line` routes the line directly to REMOVED and skips the MODIFIED_BY_* intermediate. `force_accept_line` and `force_remove_line` are valid only at `round_count == 2` and only for the SM role; ADMIN is treated as SM for these line actions, matching the existing ADMIN bypass on other endpoints. `required_delivery_date` is now a per-line nullable field with null meaning inherit from the PO. Line-level REJECTED was renamed to REMOVED via an idempotent migration. Pre-existing tz-dependent flake in `test_list_invoices_filter_by_date_range` fixed in this iter (switched from local date to UTC date) to meet the "no closed iter fails" mandate.

## Acceptance criteria

- [ ] `LineItemStatus` includes MODIFIED_BY_VENDOR, MODIFIED_BY_SM, REMOVED; no REJECTED.
- [ ] `POStatus` includes MODIFIED.
- [ ] `modify_line`, `accept_line`, `remove_line`, `force_accept_line`, `force_remove_line`, `submit_response` all implemented with preconditions.
- [ ] EDITABLE_LINE_FIELDS is a tuple.
- [ ] qty=0 shortcut routes to REMOVED.
- [ ] round_count enforced at 2, force actions only at 2.
- [ ] Convergence produces correct PO status.
- [ ] line_edit_history appended per field change with correct round and actor.
- [ ] All new endpoints present with correct role guards and status codes.
- [ ] `/accept-lines` and `/reject` endpoints removed.
- [ ] Existing tests updated; all permanent tests pass.
- [ ] Seed data still loads without referencing removed methods.
