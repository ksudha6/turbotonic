# Iteration 25 — Vendor country validation at domain layer

## Context

Iteration 20 added a country dropdown to the vendor create form and DTO-level validation against `VALID_COUNTRIES`. But the domain model (`Vendor.create()`) only checks non-empty. A direct repository save can write any string. The original plan included migrating existing free-text values, but all 7 vendors in the DB already have `country = "US"`, so migration is unnecessary. This iteration closes the gap by adding domain-level validation.

## JTBD

1. **When** a vendor is created or updated, **I want** the system to reject country values not in the reference data **so that** invalid entries can't bypass the DTO layer.

## Acceptance Criteria

1. `Vendor.create()` raises `ValueError` if `country` is not in `VALID_COUNTRIES`.
2. Any future `Vendor.update_country()` method validates the same way.
3. The existing DTO validation remains as the first line of defense (no change).
4. Existing tests continue to pass.

## Tasks

### Backend
- [ ] Add `VALID_COUNTRIES` import and validation to `Vendor.create()` in `domain/vendor.py`
- [ ] Add test: vendor creation with invalid country code raises ValueError

### Tests (permanent)
- [ ] Domain-level: `Vendor.create(country="INVALID")` raises ValueError
- [ ] API-level: `POST /api/v1/vendors/` with invalid country returns 422 (already exists, verify)
