# Iteration 084 — `/po/[id]` document attachments (Phase 4.2 G-22)

## Context

Phase 4.2 PO detail shipped Tier 2 (iter 077), Tier 3 (iter 081), Tier 4 (iter 082), and Tier 5 (iter 083). The remaining Phase 4.2 PO-detail item is G-22: a Documents panel for attaching signed/countersigned PO copies, amendments, and addendums so the artifact lives next to the data.

The iter 035 file storage layer supports the mechanics: `files` table with entity_type/entity_id index, multipart upload (PDF-only, 10MB, filename sanitization, path traversal protection), download with Content-Disposition, delete, and list-by-entity. Certificate (iter 038), PackagingSpec (iter 042), and ShipmentDocumentRequirement (iter 046) wire it for their entity types. This iter wires it for `entity_type='PO'` for the first time.

Iter 035's generic endpoints (`/api/v1/files/...`) are still any-authed. This iter does not widen those guards. Four new PO-scoped endpoints under `/api/v1/po/{po_id}/documents/...` wrap `FileStorageService` with PO-aware role + ownership + PO-type checks.

Attachment types by PO type:
- PROCUREMENT: `SIGNED_PO`, `COUNTERSIGNED_PO`, `AMENDMENT`, `ADDENDUM`.
- OPEX: `SIGNED_AGREEMENT`, `AMENDMENT`, `ADDENDUM`.

Permission matrix:
- **PROCUREMENT** — view: ADMIN / SM / VENDOR (own) / PROCUREMENT_MANAGER / FREIGHT_MANAGER / QUALITY_LAB. Manage: ADMIN / SM / VENDOR (own).
- **OPEX** — view: ADMIN / FREIGHT_MANAGER / VENDOR (own, read-only). Manage: ADMIN / FREIGHT_MANAGER. SM / PM / QL hidden entirely.

Rationale: the procurement fan-out (FM for shipping, QL for cert traceability) needs read access. OPEX has no shipment/quality fan-out, and FM owns OPEX/FREIGHT operational flow per the iter 073 dashboard split.

## JTBD

When I (SM) finish negotiating a procurement PO and the vendor sends back a countersigned PDF, I want to attach it to the PO record so future viewers (FM planning the shipment, QL tracing certs against the contract) can pull the signed artifact without asking me for it.

When I (VENDOR) want my customer to know I have actually signed the PO they sent me, I want to upload my countersigned copy directly to the PO so I do not have to email it through a separate channel that loses traceability.

When I (FM) am responsible for booking the shipment for an accepted procurement PO, I want to download the countersigned PO copy from the PO record so I have evidence-of-contract for the carrier and customs broker.

When I (FM) approve an OPEX vendor agreement (utility, freight billing, miscellaneous service contract), I want to attach the executed agreement PDF to the OPEX PO so the operational record carries the artifact alongside the line items and invoices, without involving SM in the procurement-only role.

When I (any role) view a PO that has documents attached, I want the attachment list to look and behave like the rest of the revamped PO page — `PanelCard` rhythm, `StatusPill` for type, click-to-download, role-aware action affordances — so my eye does not retrain on a new pattern.

## Tasks

### Backend

1. Domain: new `backend/src/domain/po_attachment.py`.
   - `POAttachmentType(str, Enum)` with five values: `SIGNED_PO`, `COUNTERSIGNED_PO`, `SIGNED_AGREEMENT`, `AMENDMENT`, `ADDENDUM`.
   - `PROCUREMENT_ATTACHMENT_TYPES: frozenset[POAttachmentType]` = `{SIGNED_PO, COUNTERSIGNED_PO, AMENDMENT, ADDENDUM}`.
   - `OPEX_ATTACHMENT_TYPES: frozenset[POAttachmentType]` = `{SIGNED_AGREEMENT, AMENDMENT, ADDENDUM}`.
   - `allowed_attachment_types(po_type: POType) -> frozenset[POAttachmentType]` — single source of truth used by validators and frontend type vocabulary.
   - `validate_attachment_type(po_type: POType, file_type: str) -> POAttachmentType` — raises `ValueError` if `file_type` is not in the allowed set for the PO type. Chain with `from` per CLAUDE.md.

2. Permissions: new helpers in `backend/src/permissions.py` (or co-located if no module exists).
   - `can_view_po_attachments(user: User, po: PurchaseOrder) -> bool` — branches on `po.po_type`. PROCUREMENT: True for ADMIN / SM / PROCUREMENT_MANAGER / FREIGHT_MANAGER / QUALITY_LAB; True for VENDOR iff `user.vendor_id == po.vendor_id`. OPEX: True for ADMIN / FREIGHT_MANAGER; True for VENDOR iff `user.vendor_id == po.vendor_id`. Else False.
   - `can_manage_po_attachments(user: User, po: PurchaseOrder) -> bool` — branches on `po.po_type`. PROCUREMENT: True for ADMIN / SM; True for VENDOR iff own. OPEX: True for ADMIN / FREIGHT_MANAGER. Else False.
   - Both helpers return False for INACTIVE / PENDING users (already enforced by session middleware but defense-in-depth).

3. Router: new `backend/src/routers/po_documents.py` mounted under `/api/v1/po/{po_id}/documents`.
   - `POST /` — multipart upload. Body: `file: UploadFile`, `file_type: str` (form field). Resolves PO (404 if missing), checks `can_manage_po_attachments` (403), validates `file_type` via `validate_attachment_type` (422), delegates to `FileStorageService.upload(entity_type='PO', entity_id=po.id, file_type=POAttachmentType, file=file, uploaded_by=user.id)`. Records `PO_DOCUMENT_UPLOADED` activity (see task 4). Returns `FileMetadata`.
   - `GET /` — list. Resolves PO, checks `can_view_po_attachments` (403), returns `list[FileMetadata]` for `entity_type='PO', entity_id=po.id`. List sorted by `uploaded_at DESC`.
   - `GET /{file_id}` — download. Resolves PO + file (404 if file's entity_type/entity_id does not match), checks `can_view_po_attachments` (403), streams via `FileStorageService.download` with Content-Disposition.
   - `DELETE /{file_id}` — delete. Resolves PO + file, checks `can_manage_po_attachments` (403), delegates to `FileStorageService.delete`. No activity event (matches iter 046 precedent of upload-only).
   - All four endpoints use `require_auth` and the new permission helpers; no `require_role` because role logic is PO-type-conditional.
   - Mount in `backend/src/main.py` next to the existing PO router.

4. Activity event: extend `ActivityEvent` enum with `PO_DOCUMENT_UPLOADED`. Update `EVENT_METADATA` to map it to category `LIVE`. Target role derived dynamically per call: SM for PROCUREMENT, FREIGHT_MANAGER for OPEX (since target is one role, not a per-event constant, the dispatcher pattern must accept a per-call override OR the event metadata records both candidates and the dispatcher picks at write time — pick whichever matches existing iter 060 NotificationDispatcher conventions; no email template needed in this iter).
   - Detail string: `f"{file_type.value} uploaded ({file.filename})"`.
   - Activity row references PO entity (entity_type=PO, entity_id=po.id).

5. Seed: extend `backend/src/seed.py` to attach one `SIGNED_PO` PDF to the first ACCEPTED PROCUREMENT PO and one `SIGNED_AGREEMENT` PDF to one OPEX PO. Use a fixture PDF committed under `backend/tests/fixtures/` (e.g. `signed_po_sample.pdf`, `signed_agreement_sample.pdf`) — generate with ReportLab at seed time if a static fixture is undesired, but the simplest path is committing two ~5KB sample PDFs. Seed inserts via `FileStorageService` so the file actually lands on disk under `uploads/`.

### Frontend

6. Permissions: extend `frontend/src/lib/permissions.ts` with `canViewPOAttachments(user, po)` and `canManagePOAttachments(user, po)` mirroring the backend matrix one-for-one. Both take `po: { po_type: POType; vendor_id: string }` shape (or full `PurchaseOrder`) and return boolean.

7. New `frontend/src/lib/po/PoDocumentsPanel.svelte`:
   - Props: `po: PurchaseOrder`, `user: User`. Internally fetches `GET /api/v1/po/{po.id}/documents` on mount (mirrors iter 083 `PoActivityPanel` self-fetch pattern).
   - Returns `null` (renders nothing) when `!canViewPOAttachments(user, po)`.
   - Wraps `PanelCard` titled "Documents". Action snippet: Upload `Button` (variant primary, label "Upload document") visible when `canManagePOAttachments`.
   - Body: hand-rolled `<table>` (DataTable's `render` is `string | number`; same precedent as `PoInvoicesPanel` from iter 083). Columns: File name (clickable link triggering download via `GET /{file_id}` — uses `<a href>` with the relative URL so the browser handles Content-Disposition), Type (plain text using `EVENT_LABELS`-style dictionary or just the enum value), Uploaded by (resolved username — needs a small `users_by_id` map fetched with the list, or the backend list endpoint returns a denormalized `uploaded_by_username`), Uploaded at (formatted via shared `formatDate`), Delete (trash `Button` variant ghost, manage-only).
   - Empty state: when `files.length === 0` AND `canManagePOAttachments`, render `EmptyState` inside the panel ("No documents attached.", action snippet pointing to the same Upload button). When empty AND view-only, return `null`.
   - Loading state: `LoadingState` inside the panel until first response.
   - Error state: `ErrorState` with Retry button on fetch failure.
   - Delete confirmation: native `confirm()` (matches iter 057 pattern for one-shot destructive actions; a real confirm dialog is on the backlog).
   - testid: `po-documents-panel`, `po-documents-row-{file_id}`, `po-documents-upload-btn`, `po-documents-delete-{file_id}-btn`, `po-documents-empty-state`.

8. New `frontend/src/lib/po/PoDocumentUploadDialog.svelte`:
   - Reuses the modal pattern from iter 081 `PoLineModifyModal` (`<dialog>` element + bind:open prop).
   - Props: `po: PurchaseOrder`, `open: boolean` (bindable), `onSubmit: (file: File, file_type: POAttachmentType) => Promise<void>`, `onClose: () => void`.
   - Body: `FormField` wrapping `Select` (file_type, options derived from `po.po_type` via a frontend-mirrored `allowedAttachmentTypes` helper — vocabulary lives in `frontend/src/lib/po/po-attachment-types.ts`); `FormField` wrapping native `<input type="file" accept="application/pdf">`; submit/cancel `Button`s.
   - Client-side validation: file required, file size <= 10MB, MIME type `application/pdf`. Surfaces inline error in FormField. Server still re-validates.
   - testid: `po-document-upload-dialog`, `po-document-type-select`, `po-document-file-input`, `po-document-upload-submit`, `po-document-upload-cancel`.

9. Integrate into `frontend/src/routes/(nexus)/po/[id]/+page.svelte`:
   - Mount `<PoDocumentsPanel {po} {user} />` between the Activity panel and the Rejection History panel (per backlog).
   - Page does no extra work — the panel self-fetches.

10. New `frontend/src/lib/po/po-attachment-types.ts`:
    - Exports `POAttachmentType` union and the two allowed-set helpers (`procurementAttachmentTypes`, `opexAttachmentTypes`, `allowedAttachmentTypes(poType)`). Mirrors backend domain module so the `Select` options stay in sync without a network roundtrip.

11. New `/ui-demo/po-documents` mock route hosting toggleable matrix:
    - PO type toggle: PROCUREMENT / OPEX.
    - Role toggle: ADMIN / SM / VENDOR (own) / VENDOR (other) / FM / PM / QL.
    - Files toggle: 0 / 1 / 3 attachments.
    - Auth-free, pure visual. Pattern matches `/ui-demo/po-finishing` from iter 083.

### Tests

12. Existing test impact:
    - `backend/tests/test_seed.py` thresholds expand by two assertions (PROCUREMENT PO has a SIGNED_PO file, OPEX PO has a SIGNED_AGREEMENT file). Existing thresholds are unchanged.
    - `frontend/tests/po-detail.spec.ts` mocks need `GET /api/v1/po/*/documents` to return `[]` for cells that don't assert on the panel (otherwise the panel's onMount fetch 404s and the loading spinner never resolves). Add a default mock alongside existing PO mocks.
    - No other backend tests break (the iter 035 generic endpoints stay any-authed, untouched).
    - No other frontend tests break (panel hidden for unauthenticated test paths, and the existing role-rendering tests don't assert on the post-Activity slot).

13. Backend pytest in `backend/tests/test_po_documents.py` (~20 tests):
    - Domain: `validate_attachment_type` accepts each PROCUREMENT type for procurement and rejects each OPEX-only type; mirror for OPEX.
    - Endpoint matrix: each of the 4 endpoints × each role × PROCUREMENT and OPEX. Shape: `(role, po_type, action) → expected_status`. Generated table-driven; ~14 rows after collapsing redundancy.
    - File-type mismatch: VENDOR uploads `SIGNED_AGREEMENT` to a PROCUREMENT PO → 422.
    - Non-PDF MIME: 400.
    - Oversize (>10MB): 413 (or whatever iter 035 returns).
    - Cross-vendor: VENDOR for vendor A reads/writes PROCUREMENT PO of vendor B → 404.
    - Cross-PO file id: file_id belongs to a different PO than the path → 404.

14. Backend pytest in `backend/tests/test_seed.py`:
    - Two new assertions: `procurement_pos_with_signed_pdf >= 1`, `opex_pos_with_signed_agreement_pdf >= 1`.

15. Frontend Playwright in `frontend/tests/po-documents.spec.ts` (~10 tests):
    - Panel visibility per `(role, po_type)` cell — six cells (ADMIN/PROC, SM/PROC, FM/PROC, FM/OPEX, SM/OPEX-hidden, QL/OPEX-hidden).
    - Upload button visibility per `(role, po_type)` cell.
    - Upload flow: click button → dialog opens → `Select` shows correct option set per PO type → submit succeeds → row appears in table.
    - Delete flow: click delete → confirm → row removed.
    - Empty state: empty + manage shows EmptyState; empty + view hides panel.
    - Cross-vendor VENDOR sees no panel (panel hidden, not error).

16. Permanent test suite invariants:
    - `make test` green (~629 + 20 = ~649 backend tests).
    - `make test-browser` green (~239 + 10 = ~249 Playwright specs).

### Scope fences

17. This iter does NOT widen iter 035 generic file-endpoint guards. The any-authed download surface at `/api/v1/files/{file_id}` stays open. PO-scoped endpoints provide the tightened surface for PO documents specifically; tightening generic endpoints is its own backlog item ("File endpoint role guards").

18. This iter does NOT add document versioning. Uploading a second `SIGNED_PO` to the same PO does not supersede the first — both rows persist, sorted by `uploaded_at DESC`. Cleanup is manual delete.

19. This iter does NOT add `PO_DOCUMENT_DELETED`. Activity records uploads only (matches iter 046 DOCUMENT_UPLOADED-only precedent for shipments).

20. This iter does NOT touch invoice or shipment document panels. Those have their own iter trajectories.

21. This iter does NOT extend `DataTable.render` to support snippet cells. The hand-rolled `<table>` precedent set by `PoListTable` (iter 076) and `PoInvoicesPanel` (iter 083) carries through. DataTable extension stays on the backlog.

22. This iter does NOT add bulk upload (single file per request) or drag-and-drop. Upload is a single-file `<input type="file">`.

23. This iter does NOT add an email template for `PO_DOCUMENT_UPLOADED`. Activity row records, dispatcher does not fan out to SMTP. Email template is a follow-up if anyone asks.

## Notes

Cross-vendor VENDOR returns 404, not 403. The permission helpers (`can_view_po_attachments` / `can_manage_po_attachments`) return False for cross-vendor and would naturally produce 403, which is the right shape for the frontend mirror. To preserve the iter 032 invariant (don't leak PO existence to vendor B), the router calls `check_vendor_access(user, po.vendor_id)` between PO fetch and the permission helper — that helper raises 404 for VENDOR mismatches and is a no-op for everyone else. Two-stage gate: 404 hides the PO from cross-vendor VENDOR; 403 denies role-deny within the vendor's own scope.

The backend `files.uploaded_by` column is nullable and added via idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` per the iter 044/060 pattern. Existing certificate / packaging / shipment uploads pre-dating this iter have `uploaded_by = NULL`, so the PO list endpoint's username denormalization tolerates a None value (`uploaded_by_username = None`). The generic `/api/v1/files` DTOs do NOT expose the new field — only the new PO-scoped DTOs do, so the four other entity-type consumers (CERTIFICATE / PACKAGING / SHIPMENT) keep their existing response shape and no test churn.

The list endpoint denormalizes `uploaded_by_username` via a single batch query (`WHERE id = ANY($1)` keyed on the distinct uploader ids in the result set). No N+1. Iter 083's PoActivityPanel paginates client-side over a single fetch; the same pattern applies here, with the same revisit-when-rows-exceed-100 caveat.

`PO_DOCUMENT_UPLOADED` is registered with `EVENT_METADATA = (LIVE, None)`. The None target_role lets the router pass a per-call override (SM for PROCUREMENT, FREIGHT_MANAGER for OPEX) per the `_counterpart_target` precedent from iter 056 and the `target_role=` kwarg pattern in [activity_repository.py](backend/src/activity_repository.py). No new email template; `NotificationDispatcher` is not invoked.

`PoDocumentsPanel` gained a `mockFiles?: POFileListItem[] | null` bypass prop matching iter 083's `PoActivityPanel.mockEntries` precedent. The `/ui-demo/po-documents` route uses it so the panel renders offline without intercepting `window.fetch`. The route still page-scopes a `globalThis.fetch` patch for the upload + delete demo flows, since those are imperative actions the panel triggers — that patch is restored on cleanup. A cleaner shared mock-fetch helper for the ui-demo gallery would reduce that one-off; logged to backlog.

Frontend permission helpers `canViewPOAttachments` / `canManagePOAttachments` take `(user, po)` rather than the existing `(role)` shape used by every prior helper in [permissions.ts](frontend/src/lib/permissions.ts). The OPEX-vs-PROCUREMENT branch needs `po.po_type` and the VENDOR scope check needs `po.vendor_id`, so `role` alone is insufficient. Helper naming stays in the existing `canX` family.

DataTable hand-rolled `<table>` again. Same precedent as iter 076 `PoListTable` and iter 083 `PoInvoicesPanel`: DataTable's `render` returns `string | number` and the Delete column needs a Button. Promoting snippet cells to the shared primitive stays on backlog.

Seed PDFs are generated in-process via ReportLab (Path A, ≤5KB each) rather than committed as binary fixtures. The first ACCEPTED PROCUREMENT PO gets a SIGNED_PO; the first OPEX PO gets a SIGNED_AGREEMENT; both `uploaded_by = users[0].id` (the seed admin).

Test count grew by more than estimated. The endpoint permission matrix collapsed cleanly into 28 parametrized rows (4 endpoints × 7 roles × 2 PO types — minus redundancies), and the spec naturally expanded the file-type vocabulary tests to one per allowed/forbidden cell. Final: 67 new pytest (629 → 696) and 18 new Playwright (239 → 257) — well beyond the iter's "~16" / "~10" estimates but the spec called the exercise "table-driven" so the parametrize arithmetic was always going to dominate.
