# Iteration 25 — Vendor country validation at domain layer

## Context

Iteration 20 added a country dropdown to the vendor create form and DTO-level validation against `VALID_COUNTRIES`. The frontend enforces dropdown-only selection (no free text). But the domain model (`Vendor.create()`) only checks non-empty. A direct domain call can write any string. The PO domain already validates all country fields against `VALID_COUNTRIES` in its factory method. This iteration brings the Vendor domain to parity.

All 7 existing vendors have `country = "US"`, so no data migration is needed.

## JTBD

1. **When** a vendor is created via any path (API, test, internal caller), **I want** the domain to reject country values not in the reference data **so that** invalid country codes cannot exist in the system regardless of the entry point.

## Acceptance Criteria

1. `Vendor.create()` raises `ValueError` if `country` is not in `VALID_COUNTRIES`
2. `Vendor.create()` accepts any valid country code from `VALID_COUNTRIES`
3. The existing DTO validation remains as the first line of defense (no change)
4. Existing permanent tests pass
5. PO domain and Vendor domain validate country codes using the same `VALID_COUNTRIES` set

## Tasks

### Backend
- [x] Import `VALID_COUNTRIES` in `domain/vendor.py` and add validation to `Vendor.create()`
- [x] Add permanent test: `Vendor.create(country="INVALID")` raises `ValueError`
- [x] Add permanent test: `Vendor.create(country="CN")` works (sanity check)
- [x] Verify existing permanent tests pass (`make test`) — 183 passed, 1 pre-existing failure (unrelated date hardcoding in invoice test)

### Scratch tests
- [x] API-level: `POST /api/v1/vendors/` with invalid country returns 422 (DTO catches first, confirmed)

## Notes

Added `VALID_COUNTRIES` validation to `Vendor.create()`, matching the pattern already used by `PurchaseOrder.create()`. No new domain terms emerged. The ddd-vocab.md Vendor entry already describes country as a "validated reference data code", which is now enforced at both DTO and domain layers. The pre-existing test failure in `test_list_invoices_filter_by_date_range` is a hardcoded date issue (`2026-04-03`), unrelated to this change.
