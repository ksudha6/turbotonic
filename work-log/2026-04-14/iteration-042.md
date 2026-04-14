# Iteration 042 -- Packaging file collection and reuse

## Context

PackagingSpec (iter 041) defines what files are needed per product per marketplace but has no file attachment. This iteration adds file upload against specs, transitioning status from PENDING to COLLECTED, plus a readiness endpoint that reports collection progress. Files persist at the product level and carry forward across POs and shipments without re-upload.

## JTBD

- When a packaging spec exists for my product, I want to upload the required file so that the spec is marked as collected.
- When I check packaging readiness for a product and marketplace, I want to see which specs have files and which are still missing so that I can track collection progress.
- When I ship the same product again, I want the previously collected packaging files to carry forward so that I don't re-upload files that haven't changed.

## Tasks

### Backend -- Schema
- [ ] Add `document_id TEXT REFERENCES files(id)` column to `packaging_specs` table (nullable, default NULL)
- [ ] Update `status` column: now uses both `PENDING` and `COLLECTED` values

### Backend -- Domain
- [ ] Add `COLLECTED` to `PackagingSpecStatus` enum
- [ ] Add `document_id: str | None` field to `PackagingSpec` (default None)
- [ ] Add `collect(document_id: str)` method to `PackagingSpec`:
  - Sets `document_id` to the provided value
  - Transitions `status` from `PENDING` to `COLLECTED`
  - Updates `updated_at`
  - Raises `ValueError` if `document_id` is empty or whitespace-only
- [ ] Add `uncollect()` method to `PackagingSpec`:
  - Clears `document_id` to None
  - Transitions `status` from `COLLECTED` back to `PENDING`
  - Updates `updated_at`
  - Raises `ValueError` if status is not `COLLECTED`

### Backend -- Repository
- [ ] Update `PackagingSpecRepository.save()` to persist `document_id`
- [ ] Update reconstruction to read `document_id` from DB row

### Backend -- Router
- [ ] `POST /api/v1/packaging-specs/{spec_id}/upload` -- upload a file against a spec
  - Accepts multipart file upload
  - Stores file via file storage service (from iter 035)
  - Calls `spec.collect(document_id)` to transition status
  - Returns updated spec with status COLLECTED and document_id populated
  - Role guard: SM and VENDOR
  - Returns 404 if spec not found
  - Replaces existing file if re-uploaded (updates document_id, status stays COLLECTED)
- [ ] `GET /api/v1/products/{product_id}/packaging-readiness` -- packaging readiness check
  - Query param: `marketplace` (required)
  - Returns: `{"product_id": str, "marketplace": str, "total_specs": int, "collected_specs": int, "is_ready": bool, "specs": [{"spec_id": str, "spec_name": str, "status": "PENDING" | "COLLECTED", "document_id": str | null}]}`
  - `is_ready` is true when `total_specs > 0` and `collected_specs == total_specs`
  - Returns 422 if `marketplace` not provided
  - Role guard: SM and VENDOR

### Backend -- Activity log
- [ ] Add `PACKAGING_COLLECTED` to `ActivityEvent` enum
- [ ] Add `PACKAGING_MISSING` to `ActivityEvent` enum
- [ ] Add `PACKAGING` to `EntityType` enum
- [ ] Add EVENT_METADATA entries:
  - `PACKAGING_COLLECTED`: category `LIVE`, target_role `SM`
  - `PACKAGING_MISSING`: category `ACTION_REQUIRED`, target_role `SM`
- [ ] Record `PACKAGING_COLLECTED` event when file uploaded against a spec
- [ ] Record `PACKAGING_MISSING` event when readiness check finds missing specs (optional: only on explicit check, not on every list)

### Frontend
- [ ] Packaging spec list: show file upload button per spec (SM and VENDOR roles)
- [ ] Upload flow: file picker, upload, spec status pill updates to COLLECTED (green)
- [ ] Show uploaded file name and download link on collected specs
- [ ] Re-upload button to replace an existing file
- [ ] Product detail: packaging readiness summary per marketplace ("3 of 5 collected")
- [ ] Visual: PENDING specs show grey pill; COLLECTED specs show green pill

### Tests (permanent)
- [ ] Upload file against PENDING spec: status becomes COLLECTED, document_id set
- [ ] Upload file against already-COLLECTED spec: file replaced, status stays COLLECTED
- [ ] Upload with empty file: returns 422
- [ ] Upload against nonexistent spec: returns 404
- [ ] Packaging readiness with all specs collected: is_ready is true
- [ ] Packaging readiness with some specs missing: is_ready is false, correct counts
- [ ] Packaging readiness with no specs defined: total_specs is 0, is_ready is false
- [ ] Packaging readiness with missing marketplace param: returns 422
- [ ] Delete of COLLECTED spec: returns 409 (status is not PENDING)
- [ ] Uncollect a COLLECTED spec: status returns to PENDING, document_id cleared
- [ ] Activity log: PACKAGING_COLLECTED event recorded on upload

### Tests (scratch)
- [ ] Screenshot: packaging spec list with mix of PENDING and COLLECTED status pills
- [ ] Screenshot: file upload flow on a packaging spec
- [ ] Screenshot: product packaging readiness summary

## Acceptance criteria
- [ ] `PackagingSpec` has `document_id` field and `COLLECTED` status
- [ ] File upload against a spec transitions status from PENDING to COLLECTED
- [ ] Files persist at product level, reusable across POs/shipments
- [ ] Packaging readiness endpoint returns correct counts and `is_ready` flag
- [ ] `is_ready` requires total_specs > 0 and all specs collected
- [ ] Re-upload replaces the existing file
- [ ] Activity log records PACKAGING_COLLECTED on upload
- [ ] Role guard: SM and VENDOR can upload
- [ ] COLLECTED specs cannot be deleted (returns 409)
- [ ] All permanent tests pass
