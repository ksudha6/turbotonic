# Iteration 105: Certificate Approve Workflow

## Context

The certificate lifecycle ends at VALID (or computed EXPIRED) as of iter 094. There is no FM approval step after the vendor/SM uploads a certificate. Adding APPROVED status lets the Freight Manager sign off on a certificate explicitly, providing an auditable quality check before shipment. The existing state machine is: PENDING -> VALID (via mark_valid() on PATCH with status=VALID). This iter adds APPROVED as a new terminal state reachable from VALID only, via a dedicated POST endpoint.

Note: The domain status enum in iter 038 (backend) used PENDING and VALID. The frontend panel was introduced in iter 094.

## JTBD

- As a FREIGHT_MANAGER, I need to approve a certificate that has been uploaded and marked valid, so that quality sign-off is auditable and distinguishable from mere upload.

## Tasks

1. [x] Domain: add `APPROVED` to `CertificateStatus` enum; add `approve()` method on `Certificate` that requires `status === VALID`, transitions to `APPROVED`, raises `ValueError` otherwise.
2. [x] Activity: add `CERT_APPROVED` event to `ActivityEvent` and `EVENT_METADATA` (category LIVE, target_role SM).
3. [x] Endpoint: `POST /api/v1/certificates/{cert_id}/approve` — FREIGHT_MANAGER (plus ADMIN via `is()` bypass); returns updated `CertificateResponse`; 404 on unknown cert, 409 if not VALID.
4. [x] Pytest: domain unit tests (approve from VALID, reject from PENDING/APPROVED); endpoint tests (200 FM, 403 non-FM roles, 409 double-approve, 404 unknown, activity row).
5. [x] Frontend types: add `'APPROVED'` to `CertificateStatus` union.
6. [x] Frontend api: add `approveCertificate(productId, certId)` — POST, no body, returns `Certificate`.
7. [x] Frontend permissions: add `canApproveCertificate(role, status)` — FREIGHT_MANAGER + status === 'VALID'.
8. [x] Frontend UI: Approve button in `ProductCertificatesPanel.svelte` gated by `canApproveCertificate`; on click call `approveCertificate` and re-fetch; `data-testid='cert-approve-{cert.id}'`; StatusPill tone for APPROVED → green.
9. [x] Playwright: FM sees Approve on VALID cert; non-FM roles do not; Approve click transitions status; APPROVED row hides button.

## Tests

### Existing test impact

No existing cert tests break. `test_mark_valid_raises_when_already_valid` and `test_mark_valid_via_patch` are unaffected. The new APPROVED value is additive. No fixture updates needed.

### New tests

**Domain (test_certificate.py)**:
- `approve()` from VALID transitions to APPROVED
- `approve()` from PENDING raises ValueError
- `approve()` from APPROVED raises ValueError (double-approve)

**API (test_api_certificate.py)**:
- FM role: POST approve on VALID cert returns 200 with status=APPROVED
- 403 for VENDOR, SM, QUALITY_LAB, PROCUREMENT_MANAGER roles
- 409 double-approve
- 404 unknown cert_id
- Activity row: entity_type=CERTIFICATE, event=CERT_APPROVED, actor_id=FM user id

**Playwright (product.spec.ts)**:
- FM role: Approve button visible on VALID cert row
- SM role: Approve button not visible
- FM Approve click: status transitions to APPROVED, button disappears

## Notes

Backend: `CertificateStatus.APPROVED` added to domain enum; `Certificate.approve()` transitions VALID → APPROVED (raises ValueError otherwise); `CERT_APPROVED` activity event added with category LIVE, target_role SM; `POST /api/v1/certificates/{cert_id}/approve` endpoint gated to FREIGHT_MANAGER. Frontend: `'APPROVED'` added to `CertificateStatus` union in types.ts; `approveCertificate(certId)` added to api.ts (POST, no body, same auth/error pattern as uploadCertificateDocument); `canApproveCertificate(role, status)` added to permissions.ts (FREIGHT_MANAGER + VALID only); `ProductCertificatesPanel.svelte` now accepts a `role: UserRole` prop and renders an Approve button per VALID cert row gated by `canApproveCertificate`, with inline error handling and disabled-while-submitting; statusTone for APPROVED → green; `canViewProducts` extended to include FREIGHT_MANAGER so FM can access `/products/[id]/edit` (read-only — `canManage` remains SM-only, controlling add/upload affordances); `/products/[id]/edit/+page.ts` guard updated to allow `canViewProducts` through (not just `canManageProducts`). 5 new Playwright specs in product.spec.ts covering FM sees button, SM/VENDOR do not, FM click transitions status, APPROVED row hides button. Frontend completion: api.ts approveCertificate, permissions.ts canApproveCertificate, ProductCertificatesPanel.svelte Approve button, 5 new Playwright specs.
