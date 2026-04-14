# Iteration 040 -- Certificate UI

## Context

The certificate API exists (iter 038) but has no frontend. This iteration adds certificate UI across three surfaces: status pills (VALID/EXPIRED/MISSING) and an upload form on the product detail page, expiry alerts on the dashboard, and a warning banner on PO create/edit when products lack certs for the chosen marketplace. It also adds a backend `GET /api/v1/certificates/expiring` endpoint to power the dashboard alerts.

## JTBD (Jobs To Be Done)

- When I view a product, I want to see each required qualification and whether it has a valid, expired, or missing certificate, so that I can identify compliance gaps at a glance
- When I need to upload a certificate for a product, I want a form on the product detail page that handles file upload and certificate metadata, so that I don't need to use separate API calls
- When certificates are about to expire, I want to see alerts on the dashboard, so that I can initiate re-certification before they lapse
- When I create or edit a PO, I want to see warnings for products that lack required certificates for the selected marketplace, so that I can make informed decisions about proceeding

## Tasks

### Product detail -- certificate status display

#### `frontend/src/routes/products/[id]/edit/+page.svelte`
- [ ] Add "Certificates" section below qualifications
- [ ] For each qualification assigned to the product:
  - Fetch certificates via `GET /api/v1/certificates?product_id={id}`
  - Match certificates to qualifications by `qualification_type_id`
  - Display status per qualification:
    - Green "VALID" pill if a VALID, non-expired certificate exists
    - Red "EXPIRED" pill if a certificate exists but is expired
    - Gray "MISSING" pill if no certificate exists for this qualification
  - Show cert details when available: cert_number, issuer, issue_date, expiry_date
  - Show download link if document_id is present (link to `GET /api/v1/files/{document_id}`)

### Certificate upload form

#### `frontend/src/routes/products/[id]/edit/+page.svelte` (continued)
- [ ] Add "Upload Certificate" form within each qualification row (or as a modal/expandable section):
  - Fields: cert_number (text), issuer (text), testing_lab (text, optional), test_date (date, optional), issue_date (date), expiry_date (date, optional), target_market (text, pre-filled from qualification's target_market)
  - File input for certificate document (PDF, image)
  - Submit flow:
    1. `POST /api/v1/certificates` with metadata (returns cert with id)
    2. If file selected: `POST /api/v1/certificates/{cert_id}/document` with file
    3. Refresh certificate list
  - Validation: cert_number and issuer required
  - Show success/error feedback

#### Create `frontend/src/lib/components/CertificateUploadForm.svelte`
- [ ] Reusable component for certificate creation + document upload
- [ ] Props: product_id, qualification_type_id, target_market (pre-filled)
- [ ] Emits event on successful upload so parent can refresh

### Dashboard -- expiry alerts

#### `frontend/src/routes/dashboard/+page.svelte`
- [ ] Add "Certificate Expiry Alerts" section
- [ ] Fetch all certificates and filter client-side for those expiring within 30 days or already expired
  - Alternative: add a backend endpoint `GET /api/v1/certificates/expiring?days=30` to avoid fetching all certs
  - Preferred: add the backend endpoint for efficiency

#### `backend/src/routers/certificate.py`
- [ ] Add `GET /api/v1/certificates/expiring` endpoint
  - Query param: `days` (int, default 30)
  - Returns certificates where expiry_date is not null and expiry_date <= now + days
  - Include both already-expired and soon-to-expire
  - Return list[CertificateListItem] with enrichment: product part_number, qualification name

#### `backend/src/certificate_dto.py`
- [ ] Add `CertificateExpiryItem(BaseModel)`:
  - All CertificateListItem fields plus: product_part_number, qualification_name, days_until_expiry (int, negative if already expired)

#### `backend/src/certificate_repository.py`
- [ ] Add `list_expiring(days: int) -> list[tuple[Certificate, str, str]]`
  - Returns certificates with their product part_number and qualification name
  - Query joins certificates -> products, certificates -> qualification_types
  - WHERE expiry_date IS NOT NULL AND expiry_date <= date('now', '+{days} days')

#### `frontend/src/routes/dashboard/+page.svelte` (continued)
- [ ] Display expiry alerts table:
  - Columns: Product (part_number), Qualification, Certificate #, Expiry Date, Days Left, Status
  - Sort by days_until_expiry ascending (most urgent first)
  - Red row styling for expired (days_until_expiry < 0)
  - Yellow row styling for expiring soon (0 <= days_until_expiry <= 30)

#### `frontend/src/lib/api.ts`
- [ ] Add `listExpiringCertificates(days?: number)` function

#### `frontend/src/lib/types.ts`
- [ ] Add `CertificateExpiryItem` interface

### PO create/edit -- cert warning banner

#### `frontend/src/lib/components/POForm.svelte`
- [ ] When a marketplace is selected and line items have product_id values:
  - For each line item with a product_id, fetch the product's qualifications and certificates
  - Check if valid certificates exist for each qualification and the selected marketplace
  - If missing: display a warning banner above the line items section
  - Warning text: "Product {part_number} is missing {qualification_name} certificate for {marketplace}"
  - Banner is yellow/amber, dismissible but re-appears if line items change
- [ ] This check runs on:
  - Marketplace dropdown change
  - Product selection on a line item
  - Page load (for edit page with existing data)
- [ ] The check is client-side and advisory. It does not block form submission.

#### `frontend/src/lib/api.ts`
- [ ] Add `listCertificates(params: { product_id?: string, target_market?: string })` function
- [ ] Add `listProductQualifications(productId: string)` function (if not already added in 036a)

### Tests (permanent)
- [ ] `make test-browser` -- Playwright specs:
  - Product detail page shows qualification status pills (VALID/EXPIRED/MISSING)
  - Certificate upload form submits successfully and refreshes status
  - Dashboard shows expiry alerts section
- [ ] `backend/tests/test_api_certificate.py` (additions):
  - `GET /api/v1/certificates/expiring?days=30` returns expiring/expired certs
  - `GET /api/v1/certificates/expiring?days=0` returns only already-expired certs

### Tests (scratch)
- [ ] Screenshot: product detail page with mixed certificate statuses (valid, expired, missing)
- [ ] Screenshot: certificate upload form filled out
- [ ] Screenshot: dashboard with expiry alerts showing expired and soon-to-expire certs
- [ ] Screenshot: PO form with cert warning banner for product missing certification

## Acceptance criteria
- [ ] Product detail page shows certificate status (VALID/EXPIRED/MISSING) per qualification
- [ ] Certificate upload form creates certificate and attaches document
- [ ] Dashboard displays certificate expiry alerts sorted by urgency
- [ ] PO create/edit shows warning banner when products lack certs for selected marketplace
- [ ] Expiry alerts backend endpoint returns correct data
- [ ] All permanent tests pass via `make test` and `make test-browser`

## Files created
- `frontend/src/lib/components/CertificateUploadForm.svelte`

## Files modified

### Backend
- `backend/src/routers/certificate.py` -- add expiring endpoint
- `backend/src/certificate_dto.py` -- add CertificateExpiryItem
- `backend/src/certificate_repository.py` -- add list_expiring query
- `backend/tests/test_api_certificate.py` -- additional test cases for expiring endpoint

### Frontend
- `frontend/src/lib/types.ts` -- add CertificateExpiryItem, Certificate, CertificateListItem interfaces
- `frontend/src/lib/api.ts` -- add certificate and expiry API functions
- `frontend/src/routes/products/[id]/edit/+page.svelte` -- certificate status display and upload form
- `frontend/src/routes/dashboard/+page.svelte` -- expiry alerts section
- `frontend/src/lib/components/POForm.svelte` -- cert warning banner for marketplace + product combinations

### Tests
- New or extended Playwright specs in `frontend/tests/`
