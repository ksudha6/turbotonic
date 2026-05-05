# Iteration 102 — Phase 4.6 Tier 2: shipment documents + readiness + mark-ready UI

> Drafted locally as iter 099. Origin's main acquired iters 099 (user-lifecycle activity events), 100 (`/users` ADMIN page), and 101 (`/login` / `/register` / `/setup` Phase 4 port) in parallel before this work was pushed. Renumbered to iter 102 and rebased onto origin/main.

## Context

Iter 097 ported `/shipments/[id]` under `(nexus)` and rebuilt header + meta + line items on Phase 4.0 primitives. It skipped every iter 046 / iter 074 transition. The page today cannot move a shipment past DRAFT.

Iter 046 backend ([backend/src/routers/shipment.py](backend/src/routers/shipment.py)) is live and pytest-covered:

- `POST /shipments/{id}/submit-for-documents` (SM, FM) — DRAFT → DOCUMENTS_PENDING. Auto-seeds `PACKING_LIST` + `COMMERCIAL_INVOICE` requirements (`is_auto_generated=True`, always pass the readiness gate; PDFs render on demand).
- `GET /shipments/{id}/requirements` (SM, VENDOR, FM) — list requirements.
- `POST /shipments/{id}/requirements` (SM, FM) — add a user-defined `document_type` (e.g. `BILL_OF_LADING`). 409 on READY_TO_SHIP.
- `POST /shipments/{id}/documents/{requirement_id}/upload` (SM, VENDOR, FM) — multipart, transitions to COLLECTED, fires `DOCUMENT_UPLOADED`. 409 on READY_TO_SHIP.
- `GET /shipments/{id}/readiness` (SM, FM) — `documents_ready` + `certificates_ready` + `packaging_ready` with missing-item lists. `missing_certificates` and `missing_packaging` are `{product_id, ...}` dicts; the page resolves `product_id` to part_number via the already-loaded `shipment.line_items`.
- `POST /shipments/{id}/mark-ready` (SM, FM) — DOCUMENTS_PENDING → READY_TO_SHIP. 409 carries the `ReadinessResult` in `detail` when not ready.

[frontend/src/lib/api.ts](frontend/src/lib/api.ts) currently has shipment CRUD + PDF downloads only; document / readiness / transition clients do not exist. Greenfield UI on existing backend.

Patterns follow: iter 077 `PoActionRail` for the transition surface; iter 094 `ProductCertificatesPanel` for the upload-bearing list (`PanelCard` + PENDING/COLLECTED `StatusPill` + 10MB / PDF-MIME client guard + inline add form with `wasAdding` `$effect`); backend `ReadinessResult` shape for the readiness panel.

Iter 074 frontend (booking + mark-shipped) is out of scope; Phase 4.6 Tier 3 follow-up.

## JTBD

As an SM closing out a DRAFT shipment, I want a "Submit for documents" action that transitions to DOCUMENTS_PENDING and seeds the requirement checklist, so VENDOR knows what to upload.

As a VENDOR on a DOCUMENTS_PENDING shipment, I want to see the requirement checklist with PENDING / COLLECTED status pills and an Upload PDF action per pending row, so I can deliver the documents the FREIGHT_MANAGER needs to ship the order. Auto-generated rows (PACKING_LIST, COMMERCIAL_INVOICE) render read-only — the system generates those PDFs on demand from PO + shipment data.

As a FREIGHT_MANAGER on a DOCUMENTS_PENDING shipment, I want to review what VENDOR uploaded against the readiness panel and either Add a missing requirement (e.g. `BILL_OF_LADING`) or click Mark Ready to Ship once everything is in. FM does not upload documents — Mark Ready is FM's approval step.

As a FREIGHT_MANAGER (or SM), I want the Readiness panel to split into Documents / Certificates / Packaging pass-or-fail with the specific missing items, and a Mark Ready action gated visually by the readiness state plus an inline surface for the backend's structured 409 readiness payload, so I never click Mark Ready and watch it silently fail.

As any role with read access (PROCUREMENT_MANAGER, VENDOR-on-own-PO past upload window, etc.), I want the documents and readiness panels to render in read-only mode, so the same page is the source of truth for shipment readiness regardless of who is looking.

## Tasks

1. **Types + API client** ([frontend/src/lib/types.ts](frontend/src/lib/types.ts), [frontend/src/lib/api.ts](frontend/src/lib/api.ts)):
   - Add `DocumentRequirementStatus = 'PENDING' | 'COLLECTED'`, `ShipmentDocumentRequirement`, `ReadinessResult` (with `missing_documents: string[]`, `missing_certificates: { product_id: string; qualification_type: string }[]`, `missing_packaging: { product_id: string; marketplace: string }[]`).
   - Add `listShipmentRequirements(id)`, `addShipmentRequirement(id, document_type)`, `uploadShipmentDocument(id, requirementId, file)` (multipart, mirror `uploadCertificateDocument`), `getShipmentReadiness(id)`, `submitShipmentForDocuments(id)`, `markShipmentReady(id)`.
   - `markShipmentReady` must surface a 409 readiness payload distinguishably — throw a typed `MarkReadyNotReadyError extends Error` carrying the parsed `ReadinessResult` so the page can render it inline rather than as a flat string.

2. **Permissions** ([frontend/src/lib/permissions.ts](frontend/src/lib/permissions.ts)):
   - `canSubmitShipmentForDocuments(role, status)` → `is(role, 'SM') && status === 'DRAFT'`. (Backend allows SM, FM; SM is the natural owner of the PO-side handoff. Tightening here is UI-only.)
   - `canManageShipmentRequirements(role, status)` → `is(role, 'SM', 'FREIGHT_MANAGER') && status === 'DOCUMENTS_PENDING'`. FM drives the requirement list; SM included for ops.
   - `canUploadShipmentDocument(role, status)` → `is(role, 'VENDOR') && status === 'DOCUMENTS_PENDING'`. **VENDOR uploads, FM does not.** Backend permits SM/FM uploads (defense in depth) but the UI hides the affordance — FM's review step is Mark Ready, not upload.
   - `canMarkShipmentReady(role, status)` → `is(role, 'SM', 'FREIGHT_MANAGER') && status === 'DOCUMENTS_PENDING'`. Mark Ready is FM's implicit approval action over the uploaded set.
   - `canViewShipmentReadiness(role)` → `is(role, 'SM', 'FREIGHT_MANAGER', 'ADMIN')`. VENDOR sees the documents panel but not the readiness panel (backend forbids the GET).

3. **`ShipmentActionRail`** [frontend/src/lib/shipment/ShipmentActionRail.svelte](frontend/src/lib/shipment/ShipmentActionRail.svelte):
   - Mirrors [`InvoiceActionRail`](frontend/src/lib/invoice/InvoiceActionRail.svelte) shape. Inline at desktop ≥768px; sticky-bottom at <768px.
   - Status × role matrix:
     - DRAFT + (SM | FM): "Submit for documents" Button (`variant="primary"`).
     - DOCUMENTS_PENDING + (SM | FM): "Mark Ready to Ship" Button (`variant="primary"`), `disabled` when `readiness?.is_ready === false`. Tooltip / inline hint copy: "Resolve missing items in the readiness panel before marking ready."
     - All other statuses: rail collapses (return null). PDF download buttons stay in `ShipmentDetailHeader` and are unaffected.
   - Props: `status: ShipmentStatus`, `role: UserRole`, `readiness: ReadinessResult | null`, `submitting: boolean`, `marking: boolean`, `error: string | null`, callbacks `on_submit()`, `on_mark_ready()`.
   - testids: `shipment-action-rail`, `shipment-action-submit`, `shipment-action-mark-ready`, `shipment-action-error`.

4. **`ShipmentDocumentsPanel`** [frontend/src/lib/shipment/ShipmentDocumentsPanel.svelte](frontend/src/lib/shipment/ShipmentDocumentsPanel.svelte):
   - `PanelCard` titled "Documents". `EmptyState` body when `requirements.length === 0` (DRAFT case before submit).
   - Each requirement row: document_type label + StatusPill (PENDING→gray, COLLECTED→green) + actions:
     - `is_auto_generated === true`: read-only "Generated on download" hint copy. No upload button. (PDFs come from the header buttons.)
     - `is_auto_generated === false && status === 'PENDING' && canUploadShipmentDocument`: "Upload PDF" Button opens a hidden `<input type="file" accept="application/pdf">`. Client-side guard: 10MB + PDF MIME (mirror `ProductCertificatesPanel`'s upload helper).
     - `is_auto_generated === false && status === 'COLLECTED'`: read-only "Uploaded" copy + (if `document_id`) a download anchor to `/api/v1/files/{document_id}/download`.
   - Inline Add Requirement form (visible only when `canManageShipmentRequirements`): single FormField + Input for `document_type`, Add Button. `wasAdding` `$effect` resets the input on success. Inline 422 / 409 error copy per the cert-add precedent.
   - Props: `requirements: ShipmentDocumentRequirement[]`, `role: UserRole`, `status: ShipmentStatus`, callbacks `on_upload(reqId, file)` and `on_add(documentType)`.
   - Document-type labels: dictionary in [frontend/src/lib/shipment/document-type-labels.ts](frontend/src/lib/shipment/document-type-labels.ts) mapping `PACKING_LIST`/`COMMERCIAL_INVOICE`/`BILL_OF_LADING`/`CERTIFICATE_OF_ORIGIN`/`INSURANCE_CERTIFICATE`/`EEI_AES` to friendly names; unknown user-defined types render the raw string as-is.
   - testids: `shipment-documents-panel`, `shipment-documents-empty`, `shipment-document-row-{requirement_id}`, `shipment-document-status-{requirement_id}`, `shipment-document-upload-{requirement_id}`, `shipment-documents-add-form`, `shipment-documents-add-input`, `shipment-documents-add-submit`, `shipment-documents-add-error`.

5. **`ShipmentReadinessPanel`** [frontend/src/lib/shipment/ShipmentReadinessPanel.svelte](frontend/src/lib/shipment/ShipmentReadinessPanel.svelte):
   - `PanelCard` titled "Readiness". Three sections: Documents / Certificates / Packaging.
   - Each section header: section name + StatusPill ("Ready"→green when the section bool is true, "Missing"→red otherwise).
   - When a section is `false`, list missing items below:
     - Documents: bullet list of `missing_documents` strings, resolved through the same `document-type-labels.ts` dictionary.
     - Certificates: rows of `{part_number} — {qualification_type}` resolved via the `productLookup: Map<product_id, { part_number, description }>` prop. Falls back to `product_id` when the lookup misses.
     - Packaging: rows of `{part_number} — {marketplace}` via the same lookup.
   - Composite "Ready to ship" tone pill in the panel header — green when `is_ready`, red otherwise.
   - Renders only when `canViewShipmentReadiness(role)` is true. VENDOR sees nothing here.
   - Props: `readiness: ReadinessResult`, `productLookup: Map<string, { part_number: string; description: string }>`, `loading: boolean`, `error: string | null`.
   - testids: `shipment-readiness-panel`, `shipment-readiness-overall`, `shipment-readiness-documents`, `shipment-readiness-certificates`, `shipment-readiness-packaging`, `shipment-readiness-missing-document-{document_type}`, `shipment-readiness-missing-cert-{product_id}-{qualification_type}`, `shipment-readiness-missing-packaging-{product_id}`.

6. **Page wiring** [frontend/src/routes/(nexus)/shipments/[id]/+page.svelte](frontend/src/routes/(nexus)/shipments/[id]/+page.svelte):
   - Concurrent fetch on mount: `getShipment(id)` first, then `Promise.all([listShipmentRequirements(id), canViewShipmentReadiness(role) && status !== 'DRAFT' ? getShipmentReadiness(id) : null])`.
   - Mount `ShipmentActionRail`, `ShipmentDocumentsPanel`, `ShipmentReadinessPanel` between the existing `ShipmentMetaPanel` and `ShipmentLineItemsPanel`.
   - `on_submit`: call `submitShipmentForDocuments(id)`, refetch shipment + requirements + readiness on success. Surface 409 inline on the action rail.
   - `on_mark_ready`: call `markShipmentReady(id)`. Catch `MarkReadyNotReadyError` → re-set `readiness` from the error payload (server's view supersedes the optimistic client view) and surface inline. Other errors → flat string on the action rail.
   - `on_upload(reqId, file)`: call `uploadShipmentDocument`, refetch requirements + readiness.
   - `on_add(document_type)`: call `addShipmentRequirement`, refetch requirements + readiness.
   - `productLookup` derived from `shipment.line_items` (already loaded; no extra fetches).

## Tests

### Existing test impact
- [frontend/tests/shipment-detail.spec.ts](frontend/tests/shipment-detail.spec.ts) (iter 097) currently mocks `GET /api/v1/shipments/{id}` only. Page-mount fetches will broaden in this iter to include `GET /requirements` and `GET /readiness`. Update fixtures to mock both new endpoints with default `[]` and `{is_ready: true, ...all-true}` payloads so the iter 097 specs still pass without asserting anything new. No assertion changes in the iter 097 specs.
- Backend pytest suite: no backend changes in this iter, so [backend/tests/test_api_shipment.py](backend/tests/test_api_shipment.py) is unaffected. `make test` should pass without edits.

### New permanent Playwright specs (append to [frontend/tests/shipment-detail.spec.ts](frontend/tests/shipment-detail.spec.ts))
1. **DRAFT + SM**: "Submit for documents" Button visible; documents and readiness panels do not render. Click submit → DOCUMENTS_PENDING UI appears.
2. **DRAFT + FREIGHT_MANAGER**: action rail collapses (FM cannot submit). DRAFT + VENDOR: same.
3. **DOCUMENTS_PENDING + FM, all-ready**: documents panel shows the two auto-generated rows read-only; readiness panel green across all three sections + green overall pill; "Mark Ready to Ship" enabled. Click → READY_TO_SHIP UI appears. Add Requirement form visible (FM owns the requirement list).
4. **DOCUMENTS_PENDING + FM, missing items**: readiness red, "Mark Ready to Ship" disabled. Stale-readiness 409 path: page reflects server payload after the failed call + inline error on the action rail.
5. **DOCUMENTS_PENDING + FM, no Upload affordance**: spec explicitly asserts `shipment-document-upload-{id}` testids do not appear for FM on user-defined PENDING rows. FM's review action is Mark Ready, not Upload.
6. **DOCUMENTS_PENDING + VENDOR, upload flow**: Upload Button visible on user-defined PENDING rows; file picker selects a stub PDF; row flips to COLLECTED; download link appears. Auto-generated rows still show no upload affordance for VENDOR. Add Requirement form hidden. Readiness panel hidden. Mark Ready button hidden.
7. **DOCUMENTS_PENDING + FM, add user-defined requirement**: submitting `BILL_OF_LADING` posts and the new row appears with PENDING. (No upload affordance for FM on the new row.)
8. **READY_TO_SHIP + SM**: action rail collapses; documents panel read-only; readiness panel hidden (no longer actionable).
9. **Document type labels**: `BILL_OF_LADING` → "Bill of Lading"; unknown user-defined string renders verbatim.

All selectors via `getByTestId` / `getByRole` / `getByLabel` per the project selector policy. Mock auth via `page.route("**/api/v1/me", ...)`.

### Scratch capture (optional)
JPEG q20 viewport screenshots of the four hero states for visual review under [frontend/tests/scratch/iteration-099/](frontend/tests/scratch/iteration-099/): DRAFT, DOCUMENTS_PENDING-not-ready, DOCUMENTS_PENDING-ready, READY_TO_SHIP. Logs at `frontend/tests/scratch/iteration-099/logs/`.

## Auto-generated PDF content (PL + CI)

The Documents panel claims `PACKING_LIST` and `COMMERCIAL_INVOICE` rows are "always ready" because the system generates them on demand. That claim only holds if the generated PDFs carry the fields a customs authority and a marketplace warehouse actually require. They don't today.

### Required content (canonical, per CBP 19 CFR 141.86 + ICC Incoterms 2020 + Maersk/DHL templates)

**Packing List** — header (shipper, manufacturer, consignee, notify party); shipment identity (PL number+date, PO ref, BL/AWB, vessel/flight+voyage, port of loading, port of discharge, final destination); per-line cargo (line #, description, SKU, HS code, country of origin, qty + UoM); per-package physical (carton # range, dimensions, net+gross weight per carton, marks and numbers, pallet ID); totals (cartons, pallets, net wt, gross wt, CBM); signatory.

**Commercial Invoice** — header (seller w/ tax ID, buyer w/ tax ID, ship-to if different, manufacturer); document identity (CI number+date, PO ref, Incoterms 2020 + named place, currency, payment terms, country of origin, country of export, country of destination); per-line commercial (line #, description, SKU, HS code, qty + UoM, unit price, extended value, net+gross wt); totals + declarations (subtotal, freight, insurance, total invoice value, reason for export, declaration-of-accuracy statement, authorised signatory).

### What the current generators render (as of iter 045)

[backend/src/services/packing_list_pdf.py](backend/src/services/packing_list_pdf.py): shipment_number, po_number, created_at, marketplace, vendor name+address (as shipper), buyer_name + ship_to_address (as consignee), per-line {part_number, description, qty, UoM, package_count, net_wt, gross_wt, dimensions, country_of_origin}, totals {package_count, net_wt, gross_wt}.

[backend/src/services/commercial_invoice_pdf.py](backend/src/services/commercial_invoice_pdf.py): CI-{shipment_number}, today's date, po_number, shipment_number, incoterm + label, payment_terms + label, currency + label, vendor name+address (as seller), buyer_name + ship_to_address + buyer_country (as consignee), per-line {description, hs_code, qty, UoM, unit_price, net_wt, gross_wt, country_of_origin, line value=qty*price}, totals {qty, value, net_wt, gross_wt, packages}, marks-and-numbers (= shipment_number).

### Gaps

**Available but not joined into the PDF** (zero schema work, generator-only fix):
- `Product.manufacturing_address` — for both PL and CI manufacturer block. Lookup: ShipmentLineItem.product_id → Product.
- `Shipment.booking_reference` (iter 074) — for PL booking/BL/AWB header. Currently rendered nowhere on the PDFs.
- `Shipment.carrier`, `Shipment.pickup_date` (iter 074) — PL header.
- `PurchaseOrder.port_of_loading`, `PurchaseOrder.port_of_discharge` — PL shipment-identity block.
- `LineItem.hs_code` — already on CI; missing from PL line table.
- `Shipment.marketplace` — already on PL header; missing from CI header.

**Schema additions required** (new fields before the generator can render them):
- Manufacturer **name** distinct from shipper. `Product.manufacturing_address` is address-only; there is no `manufacturer_name`. Either add `Product.manufacturer_name` or treat Vendor as manufacturer when shipper === manufacturer (most cases) and add an explicit override field for trader vendors.
- Vendor tax ID / VAT / IEC. `Vendor.account_details` exists as free-text (iter 036) but is unstructured — auditors will not accept "see account_details" as a tax-ID field. Add `Vendor.tax_id`.
- Buyer tax ID / EORI. No field anywhere. Add `PurchaseOrder.buyer_tax_id` (since buyer is hardcoded today; revisit when buyer becomes a first-class entity per the existing backlog item).
- Authorised signatory name + title — likely a per-tenant config rather than per-shipment. Add to a settings table or hardcode to the bootstrap admin profile until a settings surface exists.
- Declaration-of-accuracy statement copy — static template string, no schema needed.
- Reason for export — defaults to "Sale" for the procurement flow; add `Shipment.export_reason` enum (SALE / SAMPLE / RETURN) with default SALE if you want to support samples/returns later.
- Pallet count + total CBM — derive CBM from per-line dimensions if dimensions are stored as `LxWxH` parseable strings; otherwise add `ShipmentLineItem.volume_cbm`. Pallet count needs `Shipment.pallet_count`.
- Vessel / flight + voyage number — add to `Shipment` booking metadata (extends iter 074's `BookingMetadata` shape).
- Carton-number range, marks and numbers per package, pallet ID — currently `ShipmentLineItem.package_count` is a count without identifiers. Needs a separate `ShipmentPackage` child entity if marks/numbers matter; deferable since most marketplace shipments use SSCC labels generated externally.
- Incoterms **named place**. `PurchaseOrder.incoterm` is the 3-letter code only. The named place is conventionally derived as `port_of_discharge` for D-terms and `port_of_loading` for F-terms; add a derivation helper rather than a new field.
- FBA-specific fields (FBA Shipment ID, FNSKU, ASIN, FC code, appointment number) — separate iter, requires marketplace integration.

### Marketplace / FBA-specific (out of scope for iter 102 and the future PL/CI iters)

FBA Shipment ID, FNSKU, ASIN, fulfilment-centre code (e.g. ONT8), appointment / PRO number, delivery window. None of these have backend fields. Defer to a dedicated FBA-integration iter.

## Notes

VENDOR uploads documents and FREIGHT_MANAGER approves implicitly via Mark Ready rather than a per-document approval state — chose that over adding an APPROVED status because the audit benefit did not justify a new state machine. The readiness panel hides for VENDOR rather than rendering a partial view, matching the backend role guard. `MarkReadyNotReadyError` carries the structured 409 payload so the page can re-render the readiness panel from the server's view in the same update without an extra GET. `productLookup` is derived from already-loaded `shipment.line_items` instead of fetching products. The PL/CI generator extension splits into a future no-schema joins iter (manufacturing_address, booking_reference, ports, HS-on-PL, marketplace-on-CI) and a future schema-additions iter (Vendor.tax_id, PurchaseOrder.buyer_tax_id, vessel/voyage/pallet) so the smaller-blast-radius work can ship sooner. ddd-vocab gets a new Shipments section with the three iter 102 terms plus the three iter 046 foundations they reference. Test count: 767 pytest (no change after rebase) + 398 Playwright (+11 from iter 102). One environmental hiccup during green-up: a stale Vite dev server on port 5174 from a sibling project masked the new components — resolved by restarting the dev server from the correct directory.

### Decision

Iter 102 stays frontend-only. The PL/CI generator extension splits naturally into two future backend iters (numbered when scheduled — iter 100 / 101 were claimed by parallel work today):

- **No-schema joins iter**: join `Product.manufacturing_address`, `Shipment.booking_reference` + `Shipment.carrier` + `Shipment.pickup_date`, `PurchaseOrder.port_of_loading` + `port_of_discharge`, `LineItem.hs_code` (onto PL), `Shipment.marketplace` (onto CI), and a derived Incoterms named place into the existing generators. Static signatory + declaration-of-accuracy template strings. No DB changes. Closes the largest customs-readiness gap with the smallest blast radius.
- **Schema-additions iter**: add `Vendor.tax_id`, `PurchaseOrder.buyer_tax_id`, `Shipment.vessel_name` + `voyage_number`, `Shipment.pallet_count`, optional `Shipment.export_reason`, optional `Product.manufacturer_name`. Migration + DTO + form additions on `/vendors/[id]/edit` and `/po/new`. Render newly populated fields on PL + CI.

FBA-specific fields stay on the backlog as a separate marketplace-integration iter.

Until the no-schema joins iter ships, the auto-generated PDFs are not customs-ready, but the readiness gate (which doesn't inspect content) is unaffected. Flagged as a known gap; not blocking iter 102 ship.
