# Iteration 094 — Phase 4.5 Tier 4: certificate management UI on `/products/[id]/edit`

## Context

The iter 040 plan bundled four cert-UI pieces:

1. Product detail qualification list (shipped iter 092 as `ProductQualificationsPanel`).
2. PO-creation cert-warning banner (shipped iter 077 as `PoCertWarningsBanner`).
3. Certificate upload + management UI (this iter).
4. Dashboard expiry alerts (deferred to a separate iter).

Backend cert surface is complete (iter 038):
- Domain: `Certificate` aggregate with `CertificateStatus` (PENDING, VALID, with computed EXPIRED when `expiry_date < now`).
- DTO: `CertificateCreate`, `CertificateUpdate`, `CertificateResponse`, `CertificateListItem` in `backend/src/certificate_dto.py`. List item carries id, product_id, qualification_type_id, cert_number, issuer, target_market, status (computed string), expiry_date.
- Endpoints under `/api/v1/certificates`:
  - `POST /`: SM only; creates cert with metadata (cert_number, issuer, testing_lab, test_date, issue_date, expiry_date, target_market).
  - `GET /?product_id=X[&target_market=Y]`: SM/VENDOR; product_id required.
  - `GET /{id}`: SM/VENDOR.
  - `PATCH /{id}`: SM only; supports PENDING → VALID transition via `status: 'VALID'`.
  - `POST /{id}/document`: SM/VENDOR; PDF upload (10MB) emits `CERT_UPLOADED` activity (LIVE → SM).

Frontend has type stubs only:
- `frontend/src/lib/types.ts:479-492` exports `CertWarning` + `CertWarningReason` for the iter-077 banner. **No `Certificate` / `CertificateListItem` types.**
- `frontend/src/lib/api.ts` has zero cert-related functions.
- No cert routes, no cert components.

Permissions: SM and ADMIN can fully manage certs; VENDOR can list and upload documents. The product edit page is already gated to SM/ADMIN at the route level (iter 092). VENDOR cert UX lands on a vendor-side page that does not exist yet (out of scope).

The cert vocabulary on the product edit page is populated: `ProductQualificationsPanel` shows the assigned qualifications with `target_market` per qual. A cert is per `(product, qualification_type, target_market)`. The cert form surfaces qualification + target_market as paired-but-editable fields (default target_market from the selected qualification, editable because the backend permits divergence).

Iter 094 ships **list + create + document upload**. Edit (PATCH metadata) and approve (PATCH status=VALID) are deferred to iter 095.

## JTBD

As an SM owning a product, I want to attach certificates against the qualifications the product needs so that future PO submits stop returning MISSING cert warnings for accepted line items. As an SM uploading a cert, I want to attach the PDF in the same flow so the cert isn't left orphaned without a supporting document. As an SM viewing the product, I want to see at a glance which certificates exist, which qualifications still lack one, and which certificates are about to expire — so the next PO submit doesn't fail the quality gate.

## Tasks

1. **API client** — add to [frontend/src/lib/api.ts](frontend/src/lib/api.ts):
   - `listCertificates(productId: string, targetMarket?: string): Promise<CertificateListItem[]>` — `GET /api/v1/certificates/?product_id=...[&target_market=...]`.
   - `createCertificate(input: CertificateCreateInput): Promise<Certificate>` — `POST /api/v1/certificates/`.
   - `uploadCertificateDocument(certId: string, file: File): Promise<Certificate>` — `POST /api/v1/certificates/{id}/document` (multipart/form-data, single `file` field — same shape as `uploadPackagingSpecDocument` in iter 042).
   - Types in [frontend/src/lib/types.ts](frontend/src/lib/types.ts):
     - `CertificateStatus = 'PENDING' | 'VALID' | 'EXPIRED'` (string union, EXPIRED is computed server-side).
     - `CertificateListItem` mirroring backend DTO (id, product_id, qualification_type_id, cert_number, issuer, target_market, status, expiry_date as ISO string).
     - `Certificate` mirroring `CertificateResponse` (full record with testing_lab, test_date, issue_date, expiry_date, document_id).
     - `CertificateCreateInput` matching `CertificateCreate` (dates as ISO strings, testing_lab optional defaulting to '').

2. **New component** [frontend/src/lib/product/ProductCertificatesPanel.svelte](frontend/src/lib/product/ProductCertificatesPanel.svelte):
   - `PanelCard` ("Certificates") with SM-only "Add Certificate" trigger in the action snippet.
   - `EmptyState` ("No certificates uploaded yet.") when zero certs.
   - Cert rows grouped by qualification (use the qualification name + target_market from the product's `qualifications` array — pass it in as a prop). Within a group, list certs with cert_number, issuer, expiry_date (formatted), `StatusPill` (PENDING → gray, VALID → green, EXPIRED → red), and an "Upload PDF" button when `document_id` is null + the user is SM/ADMIN.
   - Add flow: trigger toggles inline form with FormField + Input fields:
     - Qualification (Select — options from the product's qualifications, label = `${qt.name} — ${qt.target_market}`).
     - Target Market (Input — defaults to selected qualification's target_market, editable since backend allows divergence).
     - Cert Number (Input, required).
     - Issuer (Input, required).
     - Testing Lab (Input, optional).
     - Issue Date (DateInput, required).
     - Expiry Date (DateInput, optional).
     - Test Date (DateInput, optional).
   - Submit + Cancel via `Button`. Auto-close-on-success via the same `wasAdding` `$effect` pattern from iter 093.
   - Upload PDF flow: button opens a hidden `<input type="file" accept="application/pdf">`; on change, posts via `uploadCertificateDocument` and on success refreshes the cert in place. Server error inline.
   - Native client-side validation: cert_number / issuer / target_market non-empty trim; issue_date present; PDF max 10MB + MIME check (mirror of [PoDocumentUploadDialog](frontend/src/lib/po/PoDocumentUploadDialog.svelte) from iter 084).
   - testids: `product-certificates-panel`, `product-certificates-add-trigger`, `product-certificates-add-form`, `product-certificates-add-qualification`, `product-certificates-add-target-market`, `product-certificates-add-cert-number`, `product-certificates-add-issuer`, `product-certificates-add-testing-lab`, `product-certificates-add-issue-date`, `product-certificates-add-expiry-date`, `product-certificates-add-test-date`, `product-certificates-add-submit`, `product-certificates-add-cancel`, `product-certificates-add-error`, `product-certificates-row-{id}`, `product-certificates-row-status-{id}`, `product-certificates-row-upload-{id}`, `product-certificates-row-upload-input-{id}`, `product-certificates-error`.

3. **Mount on edit page** — update [(nexus)/products/[id]/edit/+page.svelte](frontend/src/routes/(nexus)/products/[id]/edit/+page.svelte):
   - Add `certs: CertificateListItem[]` state and `loadCerts(productId)` helper that calls `listCertificates(productId)`.
   - In `onMount`, fetch certs in parallel with the existing fetches.
   - Mount `<ProductCertificatesPanel>` after `ProductPackagingSpecsPanel`.
   - `on_add_cert(input)` callback: calls `createCertificate`, prepends to `certs`, returns the new cert id so the panel can chain a doc upload if a PDF was selected in the form.
   - `on_upload_doc(certId, file)` callback: calls `uploadCertificateDocument`, replaces the cert in `certs`.
   - Pass `qualifications={currentQualifications}` so the panel can render the qualification-name and target_market labels without a second join.

## Tests

### Existing test impact

The 7 iter-093 packaging specs use `setupEditPage` / `setupEditPageWithSpecs`. Those helpers pre-mock `/api/v1/certificates/**` GET → `[]` to satisfy the new fetch in `onMount`. **All 23 existing edit-page specs need an additional catch-all certificates mock** in `setupEditPage`, otherwise the new `listCertificates` call hangs and breaks the page mount. Add it once in the helper; no per-spec changes required. Verify by re-running the suite after adding it.

### New permanent specs

8 specs in `frontend/tests/product.spec.ts`:

1. Certs panel mount + empty state copy when zero certs.
2. Certs render grouped by qualification with status pills (PENDING / VALID / EXPIRED tones).
3. Add flow: trigger → form visible.
4. Add flow: submit → row appears, form auto-closes.
5. Add form server error renders inline (POST 500).
6. Add form blocks submit when required fields empty (cert_number / issuer / issue_date).
7. Upload PDF flow: button visible only on certs with `document_id === null` for SM; click → file input → POST → row updates with new document_id.
8. Upload PDF rejects oversize (>10MB) client-side without firing the request.

## Notes

Cert UI ports cleanly on the iter-093 panel-pattern rhythm: parent fetches certs, panel renders + emits `on_add_cert` / `on_upload_doc` callbacks, `wasAdding` `$effect` handles auto-close-on-success. The biggest decision was extending backend `CertificateListItem` with `document_id: str | None` so the panel can decide upload-button visibility from a single list payload instead of fetching the full `CertificateResponse` per row; this is one extra column on the list endpoint and zero domain churn. Target market default-from-qualification done via a `$effect` on `qualification_type_id` change instead of a Select onchange callback (Phase 4.0 `Select` exposes `options` only, no event hooks). PDF client-side validation mirrors iter 084 `PoDocumentUploadDialog`: PDF MIME + 10MB ceiling, surface errors per-row in a `Record<string, string>` keyed by cert id. `CERT_UPLOADED` activity is recorded server-side but the panel doesn't surface it directly; the existing `PoActivityPanel` / `InvoiceActivityPanel` event-label dictionary will absorb it when an entity surface for product-scoped activity exists. Edit (PATCH metadata), approve (PATCH status=VALID), and dashboard expiry alerts deferred to follow-up iters — same split rhythm as iter 092 → iter 093. Pre-existing edit-form spec at line 233 broke on the new `listCertificates` call in `onMount`; fixed by adding `**/api/v1/certificates**` to the global `beforeEach` mock — same pattern packaging-specs already followed.
