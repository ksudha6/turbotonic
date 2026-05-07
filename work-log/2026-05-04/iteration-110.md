# Iteration 110

## Context

- `Vendor.tax_id` — vendor's tax identifier on the CI Shipper / Manufacturer block. Iter 108 placed `Brand.tax_id` on the CI Seller side (importer of record). The vendor side has no tax_id today; customs requires both.
- `Shipment.pallet_count` — pallet count on PL header. Currently absent; customs and carriers expect it.
- `Shipment.export_reason` — declared reason for export on CI (e.g. "Sale", "Sample", "Return"). Currently absent; required on commercial invoices for cross-border movement.

After this iter, the PL and CI PDFs carry every field iter 102 identified as missing for customs acceptance. Subsequent customs work (typed-doc entities, FTA / preference, restricted-party screening) is in `docs/backlog.md` under "Compliance depth" and is out of scope here.

## JTBD

- ADMIN editing a Vendor needs a `tax_id` field; the value flows into the CI Shipper / Manufacturer block on the Commercial Invoice.
- SM / FM booking a Shipment needs to record `pallet_count` and `export_reason`; both flow into the auto-generated PL and CI PDFs.
- Customs brokers receiving the auto-generated PL and CI for any shipment under any brand must see vendor tax_id, pallet count, and export reason in the rendered output.
- Existing Vendors without a tax_id and existing Shipments without pallet_count / export_reason continue to work — the fields are optional. Empty values render as the existing PDF fallback (omitted line or "-").

## Tasks

### 1. Schema additions

In `backend/src/schema.py`, add idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for:
- `vendors.tax_id TEXT NOT NULL DEFAULT ''`
- `shipments.pallet_count INTEGER` (nullable; no default)
- `shipments.export_reason TEXT NOT NULL DEFAULT ''`

No migration tool yet; columns are nullable / defaulted so existing rows survive boot.

### 2. Domain

- `backend/src/domain/vendor.py`: add `tax_id: str = ""` to `Vendor.__init__`, `Vendor.create(...)`, and any update path. No validation beyond opaque-string acceptance (jurisdiction-specific tax-ID format is deferred — name in Notes at close).
- `backend/src/domain/shipment.py`: add `pallet_count: int | None = None` and `export_reason: str = ""` fields. Mutation method `Shipment.set_logistics(pallet_count?, export_reason?)` settable on any post-DRAFT status (DOCUMENTS_PENDING / READY_TO_SHIP / BOOKED / SHIPPED). `pallet_count` if provided must be a positive integer; raise `ValueError` on zero / negative. `export_reason` rejects whitespace-only when provided.

### 3. Repository

- `backend/src/vendor_repository.py`: thread `tax_id` through `save` (INSERT and UPDATE) and `_row_to_vendor`.
- `backend/src/shipment_repository.py`: thread `pallet_count` + `export_reason` through `save` and the row-to-domain mapper. Extend the existing `update_logistics(...)` method (or add a new one) to support partial updates.

### 4. DTOs

- `backend/src/vendor_dto.py`: add `tax_id: str = ""` to `VendorCreate` / `VendorUpdate` / `VendorResponse`.
- `backend/src/shipment_dto.py`: add `pallet_count: int | None` and `export_reason: str` to `ShipmentResponse`. New `ShipmentLogisticsRequest` Pydantic body for the new endpoint: `{ pallet_count: int | None, export_reason: str | None }` with `field_validator` rejecting `pallet_count <= 0` (→ 422) and whitespace-only `export_reason` (→ 422).

### 5. Routers

- `backend/src/routers/vendor.py`: PATCH endpoint accepts `tax_id`; create endpoint accepts `tax_id`. No new permission gates — same ADMIN/SM matrix as current.
- `backend/src/routers/shipment.py`: new `PATCH /api/v1/shipments/{id}/logistics` endpoint mirroring the iter 106 `PATCH /transport` shape. Accepts `ShipmentLogisticsRequest`. Allowed roles: SM, FREIGHT_MANAGER. Allowed statuses: DOCUMENTS_PENDING, READY_TO_SHIP, BOOKED, SHIPPED (i.e. any non-DRAFT). Returns the updated `ShipmentResponse`. No activity event emitted (matches transport / declare precedent — these are document-data fields, not lifecycle events).

### 6. PDF generators

- `backend/src/services/packing_list_pdf.py`: render `pallet_count` in the PL summary block alongside the existing total package count and total weights. Show "-" when null.
- `backend/src/services/commercial_invoice_pdf.py`:
  - Render `vendor.tax_id` in the Seller / Manufacturer block as a "Tax ID:" line, only when non-empty (mirrors the iter 108 brand tax_id rendering).
  - Render `shipment.export_reason` in the CI header as a "Reason for Export:" line. When empty, fall back to "Sale" (the most common default for procurement shipments) so the field is never blank on the rendered PDF — flag this default in Notes.

### 7. Frontend (small)

- `frontend/src/lib/types.ts`: add `tax_id?: string` to `Vendor`; `pallet_count?: number | null`, `export_reason?: string` to `Shipment`. New `ShipmentLogisticsPayload`.
- `frontend/src/lib/api.ts`: new `updateShipmentLogistics(id, ShipmentLogisticsPayload)` (PATCH).
- `frontend/src/lib/permissions.ts`: new `canSetShipmentLogistics(role, status)` mirroring `canSetTransport` (SM/FM + non-DRAFT).
- `frontend/src/lib/vendor/VendorForm.svelte`: add Tax ID field below Country. Phase 4.0 `FormField` + `Input`. Empty allowed.
- `frontend/src/lib/shipment/ShipmentLogisticsPanel.svelte` (new): `PanelCard` "Logistics" with `Input type="number"` for pallet_count and `Input` for export_reason. Save button gated by dirty state; disabled while submitting; inline error on 422. Mounted on `/shipments/[id]` between `ShipmentTransportPanel` and `ShipmentDeclarePanel` when `canSetShipmentLogistics` matches.
- `frontend/src/lib/shipment/+page.svelte` page already loads shipment; just thread the new fields and panel.

### 8. Seed

- `backend/src/seed.py`: assign realistic tax_ids to seeded vendors; assign pallet_count + export_reason to seeded shipments past DRAFT.

## Tests

### Existing test impact

- `backend/tests/test_api_vendor.py`: vendor response now includes `tax_id`. Existing exact-shape assertions need the field; add `tax_id: ""` to the makeVendor factory.
- `backend/tests/test_api_shipment.py`: shipment response includes `pallet_count` and `export_reason`. Same fixture treatment.
- `backend/tests/test_brand_pdfs.py` and any PDF text-extraction test: assertions on PL summary block and CI header now include the new fields. Update expected text snippets where needed.
- `frontend/tests/vendor.spec.ts`: vendor form now has a Tax ID field. Update the form-fill helper to set or skip.
- `frontend/tests/shipment-detail.spec.ts`: response fixtures need the new fields.

### New tests

`backend/tests/test_vendor_tax_id.py`:
- test_vendor_create_accepts_tax_id
- test_vendor_create_defaults_tax_id_empty
- test_vendor_patch_updates_tax_id
- test_vendor_response_carries_tax_id

`backend/tests/test_shipment_logistics.py`:
- test_set_logistics_pallet_count_only
- test_set_logistics_export_reason_only
- test_set_logistics_both
- test_set_logistics_rejects_zero_pallet_count (→ 422)
- test_set_logistics_rejects_negative_pallet_count (→ 422)
- test_set_logistics_rejects_whitespace_export_reason (→ 422)
- test_set_logistics_403_on_vendor (only SM/FM allowed)
- test_set_logistics_409_on_draft_status
- test_logistics_response_carries_fields

`backend/tests/test_customs_paper_tail_pdfs.py`:
- test_packing_list_renders_pallet_count_in_summary
- test_packing_list_omits_pallet_count_when_null (renders "-")
- test_commercial_invoice_renders_vendor_tax_id_in_seller_block
- test_commercial_invoice_omits_vendor_tax_id_when_empty
- test_commercial_invoice_renders_export_reason
- test_commercial_invoice_falls_back_to_sale_when_export_reason_empty

`frontend/tests/shipment-logistics.spec.ts`:
- panel renders for SM + non-DRAFT
- panel renders for FM + non-DRAFT
- panel hidden for VENDOR
- panel hidden on DRAFT
- save fires PATCH with body
- 422 on whitespace export_reason → inline error
- 422 on zero pallet_count → inline error

`frontend/tests/vendor-tax-id.spec.ts`:
- create vendor form accepts Tax ID
- create vendor form allows empty Tax ID
- edit vendor form prefills Tax ID

## Decisions

- **`Vendor.tax_id` is opaque string with no jurisdiction validation.** EIN / VAT / GSTIN format reference data is a separate iter when format errors start showing up.
- **`Shipment.pallet_count` is nullable not zero-default.** Null means "unknown / not yet recorded"; rendered as "-" on the PDF. Zero would be semantically wrong (a shipment cannot have 0 pallets if it's being shipped) so we reject it.
- **`Shipment.export_reason` defaults to "Sale" on the rendered PDF when empty.** This avoids a blank field on customs-bound documents. Most procurement shipments are sales; sample / return / repair are explicit overrides. Flag in Notes that this default is rendering-time only — the database stores the empty string.
- **No activity event on logistics PATCH.** Mirrors `set_transport()` and `declare()` precedent. These are document-data fields, not lifecycle transitions; they don't need a feed entry.
- **No new role guard.** SM and FM already manage shipment lifecycle past booking; logistics fields fit the same matrix.

## Out of scope (subsequent iters)

- Bill of Lading / Certificate of Origin / Insurance Certificate / EEI as first-class typed documents. Roadmap item 2; lives in `docs/backlog.md` "Compliance depth".
- Trade preference / FTA classification (USMCA etc.). `docs/backlog.md` "Compliance depth".
- Restricted-party / denied-parties screening. `docs/backlog.md` "Compliance depth".
- Container number + equipment type + seal numbers. `docs/backlog.md` "Logistics depth".
- Cut-off date / VGM. `docs/backlog.md` "Logistics depth".
- Tax-ID format validation by country (EIN / VAT / GSTIN format).
- VendorParty multi-entity model (separate Manufacturer / Seller / Shipper / Remit-to). Iter 113.

## Notes

(Filled at iteration close.)
