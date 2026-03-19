# Iteration 04 — 2026-03-19

## Context

Vendor reactivation: add `reactivate()` to the Vendor aggregate, symmetric to `deactivate()`. Guard: must be INACTIVE. Backend endpoint `POST /api/v1/vendors/{id}/reactivate`. Frontend: reactivate button visible for Inactive vendors on the vendor list page.

Vendor UUID display: show the vendor `id` field on the vendor list page.

Reference data dropdowns: replace free-text inputs with constrained dropdowns for currency, incoterms, payment terms, buyer country, country of origin, country of destination, port of loading, and port of discharge. Values served from a new reference data API endpoint. Backend validates submitted values against the reference data sets. No free-text entry; custom value approval deferred to a future iteration.

## Jobs to Be Done

1. **When** I deactivate a vendor by mistake, **I want to** reactivate them from the vendor list, **so that** they can be assigned to new POs again.
2. **When** I view the vendor list, **I want to** see each vendor's UUID, **so that** I can reference it in external systems.
3. **When** I create or edit a PO, **I want to** select field values from constrained dropdowns, **so that** data entry is consistent and free of typos.
4. **When** I submit a PO with a field value not in the reference data, **I want** the system to reject it, **so that** only validated data enters the system.

## Acceptance Criteria

**JTBD 1 — Vendor Reactivation**
- AC1.1: `POST /api/v1/vendors/{id}/reactivate` returns 200 and sets status to ACTIVE when vendor is INACTIVE
- AC1.2: Reactivate returns 409 if vendor is already ACTIVE
- AC1.3: Vendor list page shows a "Reactivate" button for Inactive vendors
- AC1.4: After reactivation, the vendor can be assigned to new POs

**JTBD 2 — Vendor UUID Display**
- AC2.1: Vendor list page shows the vendor UUID in each row
- AC2.2: UUID is displayed in a truncated or monospace format suitable for copying

**JTBD 3 — Reference Data Dropdowns**
- AC3.1: `GET /api/v1/reference-data` returns all value sets (currencies, incoterms, payment_terms, countries, ports)
- AC3.2: PO form renders `<select>` dropdowns for all 8 fields, populated from the reference data endpoint
- AC3.3: No free-text input is possible for these fields
- AC3.4: Dropdowns show human-readable labels (e.g., "USD — US Dollar", "CNSHA — Shanghai")

**JTBD 4 — Backend Validation**
- AC4.1: PO create rejects values not in the reference data sets with 422 and a field-specific error message
- AC4.2: PO update/revise rejects invalid values with the same behavior
- AC4.3: Existing POs with legacy free-text values remain readable (no migration of old data)

## Tasks

### Backend — Domain
- T1: Add `reactivate()` method to Vendor aggregate with INACTIVE guard
- T2: Create `backend/src/domain/reference_data.py` with all value sets (currencies, incoterms, payment terms, countries, ports)
- T3: Add validation to PO aggregate — reject create/update if field values not in reference data

### Backend — API
- T4: Add `POST /api/v1/vendors/{id}/reactivate` endpoint
- T5: Add `GET /api/v1/reference-data` endpoint returning all value sets
- T6: Wire validation errors from T3 into 422 responses with field-specific messages

### Frontend — Components
- T7: Add "Reactivate" button for Inactive vendors on vendor list page
- T8: Show vendor UUID in vendor list rows (monospace, truncated)
- T9: Replace 8 free-text inputs in POForm with `<select>` dropdowns, populated from reference data endpoint

### Frontend — API
- T10: Add `reactivateVendor(id)` and `fetchReferenceData()` to `api.ts` and types to `types.ts`

### Tests — Permanent Backend
- T11: Test `reactivate()` domain method (happy path + already-active guard)
- T12: Test reactivate API endpoint (200, 409, 404)
- T13: Test reference data endpoint returns all sets
- T14: Test PO create/update rejects invalid reference data values (422)

### Tests — Permanent Frontend
- T15: Playwright test — reactivate vendor flow
- T16: Playwright test — PO form dropdowns populated and submittable

### Tests — Scratch
- T17: Screenshot vendor list with UUID and reactivate button
- T18: Screenshot PO form with dropdown fields

## Notes

Vendor status is now bidirectional (ACTIVE <-> INACTIVE) rather than terminal. Reference data lives in a single Python module (`backend/src/domain/reference_data.py`) with frozen tuples and frozenset lookups, served via `GET /api/v1/reference-data`. The PO aggregate validates all 8 constrained fields on both `create()` and `revise()`, with `revise()` checking status before reference data to preserve existing test semantics. The PO detail page displays raw codes (e.g., "CNSHA") rather than resolved labels; label resolution on the detail view is deferred. Existing POs with legacy free-text values are unaffected (no data migration). The curated reference data set uses 30 countries, 30 currencies, 11 incoterms, 4 payment terms, and 56 ports. Custom value entry requires an approval mechanism, deferred to a future iteration.
