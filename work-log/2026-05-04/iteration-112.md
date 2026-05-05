# Iteration 112 — Vendor-uploaded invoice file

## Context

The system generates invoice PDFs from structured data (`backend/src/services/invoice_pdf.py`)
but cannot accept a vendor's own paper or PDF invoice. Roadmap item 4 (post-confirmation)
calls for accepting vendor-uploaded invoice files. Roadmap item 5 (invoice-validation agent)
requires a corpus of uploaded documents to operate on; this iter is its prerequisite.

The PO-documents pattern (iter 084) already solved scoped file uploads: entity-scoped
endpoints, `InvoiceAttachmentType` vocabulary, `validate_invoice_attachment_type`, per-call
activity event, denormalized `uploaded_by_username` on list responses, and VENDOR-scoped
access via `check_vendor_access`. This iter mirrors that pattern at the invoice level.

## JTBD

- A VENDOR needs to attach their own invoice PDF (or supporting credit/debit note) to a
  submitted or approved invoice so the buyer can compare it against the system-generated
  document before approving payment.
- SM needs to view and, when necessary, delete any uploaded invoice document.
- ADMIN needs full management (view + delete) over all invoice documents.
- The buyer-side finance roles (PROCUREMENT_MANAGER) need read access to uploaded invoice
  documents for reconciliation.
- FREIGHT_MANAGER and QUALITY_LAB have no use case for invoice documents and are excluded.

## Tasks

### Domain

1. New domain module `backend/src/domain/invoice_attachment.py`:
   - `InvoiceAttachmentType(str, Enum)`: `VENDOR_INVOICE_PDF`, `CREDIT_NOTE`,
     `DEBIT_NOTE`, `OTHER`.
   - `INVOICE_ATTACHMENT_TYPES: frozenset[InvoiceAttachmentType]` — the full allowed set
     (all four values). Enforces immutability via `frozenset`.
   - `validate_invoice_attachment_type(file_type: str) -> InvoiceAttachmentType`:
     strip whitespace, reject empty/whitespace-only, reject unrecognised values, return
     parsed enum. Chain exceptions with `from`. Mirrors `validate_attachment_type` in
     `backend/src/domain/po_attachment.py`.

2. Add `INVOICE_DOCUMENT_UPLOADED` to `ActivityEvent` in
   `backend/src/domain/activity.py`. Add `EntityType.INVOICE` entry to `EVENT_METADATA`:
   `(NotificationCategory.LIVE, TargetRole.SM)`. This follows the same precedent as
   `PO_DOCUMENT_UPLOADED` routing to SM and `DOCUMENT_UPLOADED` (shipment) routing to SM.

### DTO

3. New `backend/src/invoice_document_dto.py`:
   - `InvoiceFileUploadResponse(BaseModel)`: `id`, `entity_type`, `entity_id`,
     `file_type`, `original_name`, `content_type`, `size_bytes`, `uploaded_at`,
     `uploaded_by`, `uploaded_by_username`. Mirrors `POFileUploadResponse`.
   - `InvoiceFileListItem = InvoiceFileUploadResponse` (same shape, upload response
     and list items are identical).

### Repository

No new repository class needed. The existing `DocumentRepository` (`list_by_entity`,
`save`, `get_by_id`, `delete`) is entity-type-agnostic and handles `"INVOICE"` without
modification. The invoice router fetches the parent invoice via `InvoiceRepository`
(existing) to verify existence and resolve `vendor_id` for the vendor-access guard.

### Auth helpers

4. Add two helpers to `backend/src/auth/dependencies.py`:
   - `can_view_invoice_attachments(user: User, invoice_vendor_id: str) -> bool`:
     returns `True` for ADMIN, SM, PROCUREMENT_MANAGER, and VENDOR whose
     `user.vendor_id == invoice_vendor_id`. Returns `False` for inactive/pending users,
     FREIGHT_MANAGER, and QUALITY_LAB.
   - `can_manage_invoice_attachments(user: User, invoice_vendor_id: str) -> bool`:
     returns `True` for ADMIN, SM, and VENDOR whose `user.vendor_id == invoice_vendor_id`.
     Returns `False` for all other roles including inactive/pending users.

   The `invoice_vendor_id` is resolved by joining through the invoice's `po_id` to the
   PO's `vendor_id`. The invoice router is responsible for that join before calling these
   helpers; the helpers themselves are pure functions with no DB access.

### Router

5. New `backend/src/routers/invoice_documents.py`, mounted at `/api/v1/invoices`:

   - `POST /{invoice_id}/documents` (201):
     - Resolve invoice via `InvoiceRepository.get(invoice_id)`; 404 if missing.
     - Resolve parent PO via `PurchaseOrderRepository.get(invoice.po_id)` to get
       `vendor_id`; 404 if PO missing.
     - Call `check_vendor_access(user, po.vendor_id)`.
     - Call `can_manage_invoice_attachments(user, po.vendor_id)`; 403 on failure.
     - Parse `file_type` via `validate_invoice_attachment_type`; 422 on failure.
     - Validate content type is `application/pdf`; 415 on failure.
     - Read body; 400 on empty, 413 on > 10 MB.
     - Sanitize filename (replace `/` and `\` with `_`).
     - Save via `FileStorageService.save_file("INVOICE", invoice.id, ...)`.
     - Create `FileMetadata` via `FileMetadata.create(entity_type="INVOICE", ...)`.
     - Persist via `DocumentRepository.save`.
     - Emit `ActivityEvent.INVOICE_DOCUMENT_UPLOADED` with `entity_type=EntityType.INVOICE`,
       `entity_id=invoice.id`, `target_role=TargetRole.SM`.
     - Return `InvoiceFileUploadResponse` with `uploaded_by_username=user.username`.

   - `GET /{invoice_id}/documents` (200):
     - Resolve invoice; 404 if missing.
     - Resolve PO for `vendor_id`.
     - Call `check_vendor_access(user, po.vendor_id)`.
     - Call `can_view_invoice_attachments(user, po.vendor_id)`; 403 on failure.
     - `DocumentRepository.list_by_entity("INVOICE", invoice.id, order="desc")`.
     - Batch-fetch uploader usernames in one query (same `_batch_usernames` pattern as
       `po_documents.py`).
     - Return `list[InvoiceFileListItem]`.

   - `GET /{invoice_id}/documents/{file_id}` (200 + FileResponse):
     - Resolve invoice and PO.
     - `check_vendor_access`.
     - `DocumentRepository.get_by_id(file_id)`; 404 if missing or entity mismatch.
     - `can_view_invoice_attachments`; 403 on failure.
     - `FileStorageService.read_file`; 404 on `FileNotFoundError`.
     - Return `FileResponse` with `Content-Disposition: attachment; filename="..."`.

   - `DELETE /{invoice_id}/documents/{file_id}` (204):
     - Resolve invoice and PO.
     - `check_vendor_access`.
     - `DocumentRepository.get_by_id(file_id)`; 404 if missing or entity mismatch.
     - `can_manage_invoice_attachments`; 403 on failure.
     - `DocumentRepository.delete` + best-effort `FileStorageService.delete_file`.

6. Mount `invoice_documents.router` in the main FastAPI app (`backend/src/main.py`).

### Frontend

7. New `frontend/src/lib/components/InvoiceDocumentsPanel.svelte`:
   - PanelCard with title "Invoice Documents".
   - Upload affordance (file input + file-type select + Upload button) rendered only
     when `canManage` is true (VENDOR own + SM + ADMIN). The `canManage` flag is
     derived from the current user's role using `permissions.ts`; do not re-derive it
     inline.
   - File-type `<Select>` lists the four `InvoiceAttachmentType` values with
     human-readable labels: "Vendor Invoice PDF", "Credit Note", "Debit Note", "Other".
   - Document list: each row shows `file_type`, `original_name` (truncated at 40 chars
     with title attribute), `uploaded_by_username`, `uploaded_at` (date only).
     Download icon-button visible to all roles with view access. Delete icon-button
     visible only when `canManage` is true.
   - Loading, empty ("No documents uploaded yet."), and error states use the existing
     `LoadingState`, `EmptyState`, and `ErrorState` primitives.
   - Props: `invoiceId: string`, `canManage: boolean`. Fetches its own data on mount
     via `GET /api/v1/invoices/{invoiceId}/documents`.
   - Upload calls `POST /api/v1/invoices/{invoiceId}/documents` as `multipart/form-data`
     with `file` and `file_type` fields, then refreshes the list on success.
   - Delete calls `DELETE /api/v1/invoices/{invoiceId}/documents/{fileId}`, then
     refreshes.
   - Download navigates to `GET /api/v1/invoices/{invoiceId}/documents/{fileId}` via
     `window.location.href` (triggers browser download via Content-Disposition).

8. Insert `InvoiceDocumentsPanel` into the invoice detail page
   (`frontend/src/routes/(nexus)/invoice/[id]/+page.svelte`) between the existing
   `InvoiceMetadataPanel` and `InvoiceLineItemsPanel`. Pass `invoiceId` from the route
   param and `canManage` derived from the current user's role.

### Seed

9. Update `backend/src/seed.py`:
   - For one seeded invoice, generate a minimal single-page PDF in-process with
     ReportLab (mirrors the iter 084 seed pattern for PO documents).
   - Call `FileStorageService.save_file("INVOICE", ...)` and `DocumentRepository.save`
     with `file_type=InvoiceAttachmentType.VENDOR_INVOICE_PDF.value`.
   - The seeded file records `uploaded_by` as the seeded VENDOR user's id.

## Tests

### Existing test impact

No existing tests break. The new `INVOICE_DOCUMENT_UPLOADED` event is an additive enum
value; `EVENT_METADATA` grows by one entry. The new `EntityType.INVOICE` entry is
already present in the enum (iter 023); no change to `EntityType`. The seed change adds
one new file row but does not alter existing assertions in `test_seed.py` because those
tests check variety thresholds (e.g. "at least N invoices"), not exact row counts for
files. Confirm `make test` is green after all changes.

### New tests

`backend/tests/test_invoice_documents.py`:

- `test_upload_invoice_document_vendor_own_succeeds`: POST as VENDOR who owns the
  invoice's PO vendor, assert 201 and response carries `id`, `file_type`,
  `original_name`, `uploaded_by_username`. Assert the dict has exactly these keys:
  `id`, `entity_type`, `entity_id`, `file_type`, `original_name`, `content_type`,
  `size_bytes`, `uploaded_at`, `uploaded_by`, `uploaded_by_username`.
- `test_upload_invoice_document_sm_succeeds`: POST as SM, assert 201.
- `test_upload_invoice_document_admin_succeeds`: POST as ADMIN, assert 201.
- `test_upload_invoice_document_vendor_wrong_403`: VENDOR whose `vendor_id` does not
  match the PO vendor gets 404 (vendor-access guard masks existence).
- `test_upload_invoice_document_freight_manager_403`: FREIGHT_MANAGER gets 403.
- `test_upload_invoice_document_quality_lab_403`: QUALITY_LAB gets 403.
- `test_upload_invoice_document_procurement_manager_403`: PROCUREMENT_MANAGER gets 403.
- `test_upload_invoice_document_unknown_invoice_404`: POST to nonexistent invoice_id,
  assert 404.
- `test_upload_invoice_document_bad_file_type_422`: file_type="NONSENSE", assert 422.
- `test_upload_invoice_document_empty_file_type_422`: file_type="  ", assert 422.
- `test_upload_invoice_document_non_pdf_415`: content_type="image/png", assert 415.
- `test_upload_invoice_document_empty_body_400`: zero-byte file, assert 400.
- `test_upload_invoice_document_over_10mb_413`: 10MB+1 body, assert 413.
- `test_list_invoice_documents_vendor_own`: upload one doc as VENDOR, GET list, assert
  list has exactly one item with correct shape and `uploaded_by_username` populated.
- `test_list_invoice_documents_sm`: upload as VENDOR, list as SM, assert accessible.
- `test_list_invoice_documents_procurement_manager`: upload as VENDOR, list as
  PROCUREMENT_MANAGER, assert accessible (read-only role).
- `test_list_invoice_documents_freight_manager_403`: GET list as FREIGHT_MANAGER,
  assert 403.
- `test_download_invoice_document_vendor_own`: upload then download as VENDOR, assert
  200 and `Content-Disposition` header present.
- `test_download_invoice_document_sm`: upload then download as SM, assert 200.
- `test_download_invoice_document_wrong_invoice_404`: GET download with a `file_id`
  that belongs to a different invoice, assert 404.
- `test_delete_invoice_document_vendor_own_succeeds`: upload then DELETE as VENDOR who
  owns, assert 204, then GET list asserts empty.
- `test_delete_invoice_document_sm_succeeds`: upload as VENDOR, DELETE as SM, assert 204.
- `test_delete_invoice_document_procurement_manager_403`: upload as VENDOR, DELETE
  attempt as PROCUREMENT_MANAGER, assert 403.
- `test_invoice_document_uploaded_activity_event`: upload a document, query activity
  log for `entity_type=INVOICE`, assert row carries `event=INVOICE_DOCUMENT_UPLOADED`,
  `target_role=SM`, and `actor_id` equal to the uploading user's id.

`backend/tests/test_invoice_attachment_type.py`:

- `test_validate_all_four_types_accepted`: iterate all four enum values, assert no
  exception.
- `test_validate_empty_string_raises`: assert ValueError.
- `test_validate_whitespace_only_raises`: assert ValueError.
- `test_validate_unknown_value_raises_with_chain`: catch ValueError, assert `__cause__`
  is also a ValueError (exception chain).

Playwright `frontend/tests/invoice-documents.spec.ts` (5 specs):

- `test_invoice_detail_shows_documents_panel`: mock GET `/api/v1/invoices/{id}`
  and GET `/api/v1/invoices/{id}/documents` returning empty list; assert panel heading
  "Invoice Documents" present and empty state message visible. Use `getByRole('heading',
  { name: 'Invoice Documents' })`.
- `test_vendor_sees_upload_affordance`: mock user as VENDOR role; assert file input and
  Upload button visible. Use `getByRole('button', { name: /upload/i })`.
- `test_non_vendor_sm_sees_upload_affordance`: mock user as SM; assert Upload button
  visible.
- `test_procurement_manager_hides_upload_affordance`: mock user as PROCUREMENT_MANAGER;
  assert no Upload button.
- `test_document_list_shows_rows`: mock GET `/api/v1/invoices/{id}/documents` returning
  two documents; assert two rows visible with `getByTestId('invoice-doc-row')`.

## Decisions

- **`InvoiceAttachmentType` vocabulary: four values.** `VENDOR_INVOICE_PDF` is the
  primary use case. `CREDIT_NOTE` and `DEBIT_NOTE` are standard counterparts issued by
  vendors in real procurement workflows (partial refunds, price adjustments). `OTHER`
  covers edge cases without requiring new enum values for every variation. A
  "proforma invoice" type is not included; proformas precede a PO and are not relevant
  here. Five or more values with further splits (e.g. `COMMERCIAL_INVOICE` vs
  `TAX_INVOICE`) are deferred until a concrete use case appears.

- **No invoice-status guard on upload.** Upload is allowed on any invoice status
  (DRAFT through RESOLVED). Restricting to SUBMITTED/APPROVED would block re-upload
  after a dispute resolution cycle and adds friction with no security benefit. The
  agent layer (iter 5+) applies its own validation regardless of upload timing.

- **PROCUREMENT_MANAGER: read-only, not hidden.** Finance/procurement roles need to
  reconcile the vendor's invoice PDF against payment records. They cannot upload or
  delete. This matches real-world role separation between finance viewers and operational
  uploaders.

- **FREIGHT_MANAGER and QUALITY_LAB: no access.** Neither role has an invoicing
  workflow. Giving them read access adds noise to their permission surface with no
  workflow benefit.

- **`check_vendor_access` before the manage/view check.** Same ordering as
  `po_documents.py`: the vendor-access guard fires first and returns 404 (masking
  existence for wrong-vendor access), then the role-based can_manage / can_view check
  fires and returns 403.

- **Single `invoice_vendor_id` argument to helpers, not the full Invoice object.**
  Invoice does not carry `vendor_id` directly; it must be resolved through the parent
  PO. The router owns that join. Passing the already-resolved `vendor_id` string keeps
  the helper functions pure and testable without DB access.

- **`EntityType.INVOICE` already exists.** No new `EntityType` value needed. The
  `INVOICE_DOCUMENT_UPLOADED` event uses `entity_type=EntityType.INVOICE` with
  `entity_id=invoice.id`.

- **Frontend panel position: after metadata, before line items.** Documents are
  contextual to the invoice identity (what it is) rather than its financial breakdown
  (what it charges). Placing the panel before line items follows the same ordering
  principle as the PO detail page (header context first, detailed breakdown below).

## Out of scope

- Image uploads (JPEG, PNG, TIFF). PDF-only in this iter; image support deferred until
  the invoice-validation agent needs it (agent iteration will drive the content-type
  expansion).
- Invoice status guard on upload. Deferred per the decision above.
- Bulk download of invoice documents. Deferred; no user request yet.
- `uploaded_by` attribution on the seed file beyond the VENDOR user id. Seed fidelity
  is sufficient; no audit requirement for seed rows.
- Brand-scoped document visibility. Cross-brand document access controls follow in a
  dedicated iter if multi-brand operators report a concern.
- Invoice-validation agent (roadmap item 5). This iter supplies the corpus; agent work
  is a separate iteration.

## Notes

(Filled at iteration close.)
