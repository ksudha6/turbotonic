# Iteration 038 -- Certificate entity and lifecycle

## Context

Products declare required qualifications (iter 036a) but there is no entity to record that a qualification has been fulfilled. This iteration adds the Certificate aggregate, which links a product to a qualification type with certification details (issuer, test date, expiry), persists status as PENDING or VALID, computes EXPIRED on read from `expiry_date`, and attaches documents via file storage (iter 035). The quality gate (iter 039) will use certificates to check compliance at PO submission.

## JTBD (Jobs To Be Done)

- When a testing lab completes product testing, I want to create a certificate record with the test details and upload the document, so that the product's compliance status is tracked
- When I view a product's certificates, I want to see which qualifications are covered and whether each certificate is valid or expired, so that I can identify compliance gaps
- When a certificate approaches its expiry date, I want the system to show it as expired once past due, so that I know to re-certify

## Tasks

### Domain model

#### Create `backend/src/domain/certificate.py`
- [x] `CertificateStatus` enum: PENDING, VALID
  - EXPIRED is not a persisted status; it is computed on read
- [x] `Certificate` class:
  - Fields: id, product_id, qualification_type_id, cert_number, issuer, testing_lab, test_date (datetime | None), issue_date (datetime), expiry_date (datetime | None), target_market, document_id (str | None, FK to files), status (CertificateStatus), created_at, updated_at
  - `id`: UUID string
  - `cert_number`: str, non-empty
  - `issuer`: str, non-empty (who issued the certificate)
  - `testing_lab`: str, default "" (the lab that performed testing)
  - `test_date`: nullable (when testing was performed)
  - `expiry_date`: nullable (some certificates don't expire)
  - `document_id`: nullable (certificate may be created before document is uploaded)
  - `target_market`: str, non-empty (e.g. "US", "EU")
- [x] `Certificate.create(product_id, qualification_type_id, cert_number, issuer, testing_lab, test_date, issue_date, expiry_date, target_market) -> Certificate`
  - Validates: product_id, qualification_type_id, cert_number, issuer, target_market are non-empty
  - Initial status: PENDING
- [x] `Certificate.mark_valid() -> None`
  - Transitions PENDING -> VALID. Raises ValueError if already VALID.
- [x] `Certificate.attach_document(document_id: str) -> None`
  - Sets document_id. Raises ValueError if document_id is empty.
- [x] `Certificate.is_expired(as_of: datetime | None = None) -> bool`
  - Returns True if expiry_date is not None and expiry_date < (as_of or now)
- [x] `Certificate.display_status(as_of: datetime | None = None) -> str`
  - Returns "EXPIRED" if is_expired(as_of), else status.value

### Schema

#### `backend/src/schema.py`
- [x] Add `certificates` table:
  ```
  certificates (
      id                      TEXT PRIMARY KEY,
      product_id              TEXT NOT NULL REFERENCES products(id),
      qualification_type_id   TEXT NOT NULL REFERENCES qualification_types(id),
      cert_number             TEXT NOT NULL,
      issuer                  TEXT NOT NULL,
      testing_lab             TEXT NOT NULL DEFAULT '',
      test_date               TEXT,
      issue_date              TEXT NOT NULL,
      expiry_date             TEXT,
      target_market           TEXT NOT NULL,
      document_id             TEXT,
      status                  TEXT NOT NULL,
      created_at              TEXT NOT NULL,
      updated_at              TEXT NOT NULL
  )
  ```

### DTOs

#### Create `backend/src/certificate_dto.py`
- [x] `CertificateCreate(BaseModel)`:
  - product_id: str
  - qualification_type_id: str
  - cert_number: str
  - issuer: str
  - testing_lab: str = ""
  - test_date: datetime | None = None
  - issue_date: datetime
  - expiry_date: datetime | None = None
  - target_market: str
  - Validators: product_id, qualification_type_id, cert_number, issuer, target_market not empty
- [x] `CertificateUpdate(BaseModel)`:
  - cert_number: str | None = None
  - issuer: str | None = None
  - testing_lab: str | None = None
  - test_date: datetime | None = None
  - issue_date: datetime | None = None
  - expiry_date: datetime | None = None
  - target_market: str | None = None
  - status: str | None = None (only "VALID" transition allowed)
- [x] `CertificateResponse(BaseModel)`:
  - id, product_id, qualification_type_id, cert_number, issuer, testing_lab, test_date, issue_date, expiry_date, target_market, document_id, status (str -- includes computed EXPIRED), created_at, updated_at
- [x] `CertificateListItem(BaseModel)`:
  - id, product_id, qualification_type_id, cert_number, issuer, target_market, status (str), expiry_date
- [x] `certificate_to_response(cert: Certificate) -> CertificateResponse`
  - Uses `cert.display_status()` for the status field
- [x] `certificate_to_list_item(cert: Certificate) -> CertificateListItem`
  - Uses `cert.display_status()` for the status field

### Repository

#### Create `backend/src/certificate_repository.py`
- [x] `CertificateRepository.__init__(conn)`
- [x] `save(cert: Certificate) -> None` -- upsert
- [x] `get_by_id(cert_id: str) -> Certificate | None`
- [x] `list_by_product(product_id: str) -> list[Certificate]`
- [x] `list_by_product_and_market(product_id: str, target_market: str) -> list[Certificate]`
- [x] `list_by_qualification(qualification_type_id: str) -> list[Certificate]`
- [x] `_reconstruct(row) -> Certificate`

### Router

#### Create `backend/src/routers/certificate.py`
- [x] `POST /api/v1/certificates` -- create certificate
  - Validate product_id exists (query product repo)
  - Validate qualification_type_id exists (query qualification type repo)
  - Return CertificateResponse, 201
  - Log CERT_UPLOADED activity event (target: SM)
- [x] `GET /api/v1/certificates` -- list certificates
  - Query params: `product_id` (optional), `target_market` (optional)
  - Return list[CertificateListItem]
- [x] `GET /api/v1/certificates/{cert_id}` -- get by id
  - Return CertificateResponse, 404 if not found
- [x] `PATCH /api/v1/certificates/{cert_id}` -- update certificate fields
  - If status = "VALID" in body, call cert.mark_valid()
  - Update other fields as provided
  - Return CertificateResponse
- [x] `POST /api/v1/certificates/{cert_id}/document` -- upload document
  - Multipart form with file
  - Upload via file storage service (entity_type="CERTIFICATE", entity_id=cert_id, file_type="CERT_DOCUMENT")
  - Call cert.attach_document(file_metadata.id)
  - Save certificate
  - Return CertificateResponse
- [x] Register in `backend/src/main.py`

### Activity log extension

#### `backend/src/domain/activity.py`
- [x] Add `CERT_UPLOADED` to `ActivityEvent` enum
- [x] Add `CERTIFICATE` to `EntityType` enum
- [x] Add metadata entry: `CERT_UPLOADED -> (LIVE, TargetRole.SM)`

### Tests (permanent)
- [x] `backend/tests/test_certificate.py` -- domain model tests:
  - Certificate.create with valid inputs, verify initial status is PENDING
  - Reject empty cert_number, issuer, product_id, qualification_type_id, target_market
  - mark_valid transitions PENDING -> VALID; raises on already VALID
  - attach_document sets document_id; raises on empty document_id
  - is_expired returns True when expiry_date is in the past
  - is_expired returns False when expiry_date is None
  - is_expired returns False when expiry_date is in the future
  - display_status returns "EXPIRED" for expired cert, "VALID" or "PENDING" otherwise
- [x] `backend/tests/test_api_certificate.py` -- API tests:
  - Create certificate, verify 201 and response fields
  - Create with nonexistent product_id, verify 422
  - Create with nonexistent qualification_type_id, verify 422
  - List by product_id
  - Get by id, verify response includes computed status
  - Update cert_number, mark_valid
  - Upload document to certificate
  - Create expired certificate, verify display_status is "EXPIRED" in response

### Tests (scratch)
- [x] Create product with qualification, create certificate for it, verify linkage via API
- [x] Upload PDF as certificate document, verify download works

## Acceptance criteria
- [x] `POST /api/v1/certificates` creates certificate with PENDING status
- [x] `GET /api/v1/certificates?product_id=X` lists certificates for a product
- [x] `GET /api/v1/certificates/{id}` returns certificate with computed EXPIRED status when applicable
- [x] `PATCH /api/v1/certificates/{id}` updates fields; status="VALID" triggers mark_valid()
- [x] `POST /api/v1/certificates/{id}/document` uploads and attaches document via file storage
- [x] CERT_UPLOADED activity event is logged on creation
- [x] Expired certificates show status "EXPIRED" in all responses (not stored, computed from expiry_date)
- [x] All permanent tests pass via `make test`

## Files created
- `backend/src/domain/certificate.py`
- `backend/src/certificate_dto.py`
- `backend/src/certificate_repository.py`
- `backend/src/routers/certificate.py`
- `backend/tests/test_certificate.py`
- `backend/tests/test_api_certificate.py`

## Files modified
- `backend/src/schema.py` -- add certificates table
- `backend/src/domain/activity.py` -- add CERT_UPLOADED event, CERTIFICATE entity type
- `backend/src/main.py` -- register certificate router

## Notes

Certificate aggregate follows the same pattern as PackagingSpec: immutable id/created_at via property accessors, factory create() with validation, status enum. EXPIRED status is computed from expiry_date on read via display_status(), not persisted. Document upload reuses the file storage infrastructure from iter 035. 27 new tests (17 domain + 10 API). No existing tests broke.
