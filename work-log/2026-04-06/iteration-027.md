# Iteration 27 — Field-level mutability rules tied to lifecycle status

## Context

Currently only REJECTED POs can be edited (via `revise()`), and all fields are replaceable at once. DRAFT POs cannot be edited at all, which forces users to delete and recreate. There are no per-field restrictions: once in REJECTED, every field is open, including fields that arguably shouldn't change after initial creation (like `po_type`). The DDD vocab states: `id`, `po_number`, `created_at` are immutable after creation; all other fields are mutable only in Draft and Rejected.

## JTBD

1. **When** I have a Draft PO, **I want to** edit its fields **so that** I can correct mistakes before submitting.
2. **When** I have a Rejected PO, **I want to** edit only the fields the vendor objected to **so that** I don't accidentally change terms that were already agreed upon.
3. **When** a PO is in Pending, Accepted, or Revised status, **I want** the system to block all edits **so that** the version under review stays stable.

## Acceptance Criteria

### DRAFT editing
1. `PUT /api/v1/po/{id}` works on DRAFT POs (currently 409, needs to be fixed).
2. Domain model gets an `edit()` method for DRAFT state (distinct from `revise()` which is for REJECTED).
3. `edit()` allows changing all fields except `id`, `po_number`, `po_type`, `created_at`.
4. Status remains DRAFT after edit.

### REJECTED editing (revise)
5. `revise()` continues to work on REJECTED POs only.
6. `po_type` cannot be changed during revise (it's immutable after creation).
7. `vendor_id` can change during revise (vendor might be swapped).

### Immutability enforcement
8. `po_type` is immutable after creation in both `edit()` and `revise()`.
9. Attempting to change `po_type` returns 422.
10. Pending, Accepted, Revised statuses reject all edits with 409.

### Frontend
11. PO detail page shows an "Edit" button for DRAFT and REJECTED POs only.
12. The edit form pre-populates with current values.
13. `po_type` field is disabled/read-only on the edit form.

## Tasks

### Backend — Domain
- [ ] Add `edit()` method to PurchaseOrder for DRAFT state
- [ ] Make `po_type` immutable in both `edit()` and `revise()`
- [ ] Update `update_po` router to call `edit()` for DRAFT, `revise()` for REJECTED

### Backend — Tests
- [ ] DRAFT PO can be edited via PUT, status stays DRAFT
- [ ] REJECTED PO can be revised via PUT, status becomes REVISED
- [ ] PENDING PO edit returns 409
- [ ] Changing po_type on DRAFT returns 422
- [ ] Changing po_type on REJECTED returns 422

### Frontend
- [ ] Show Edit button on DRAFT and REJECTED PO detail pages
- [ ] Disable po_type field on edit form
- [ ] Hide Edit button on PENDING, ACCEPTED, REVISED

### Tests (scratch)
- [ ] Screenshot: DRAFT PO detail with Edit button
- [ ] Screenshot: edit form with po_type disabled
