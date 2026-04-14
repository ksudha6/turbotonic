# Iteration 044 -- Packing list generation (PDF)

## Context

Shipments (iter 043) have line items but no weight/dimension fields and no packing list output. This iteration adds weight, dimension, and package count fields to shipment line items, then generates a packing list PDF using the same ReportLab pattern as `po_pdf.py` and `invoice_pdf.py`. The packing list is required by customs and freight forwarders to verify shipment contents.

## JTBD

- When a shipment is ready, I want to generate a packing list PDF so that it can accompany the physical shipment and be presented to customs.
- When I prepare a shipment, I want to enter weight, dimensions, and package count per line item so that the packing list has accurate data.

## Tasks

### Backend -- Schema
- [ ] Add columns to `shipment_line_items` table:
  - `net_weight TEXT` (nullable, stored as Decimal string)
  - `gross_weight TEXT` (nullable, stored as Decimal string)
  - `package_count INTEGER` (nullable)
  - `dimensions TEXT` (nullable, free-form string e.g. "40x30x20 cm")
  - `country_of_origin TEXT` (nullable, inherited from PO line item at creation or set manually)

### Backend -- Domain
- [ ] Add fields to `ShipmentLineItem` dataclass:
  - `net_weight: Decimal | None = None`
  - `gross_weight: Decimal | None = None`
  - `package_count: int | None = None`
  - `dimensions: str | None = None`
  - `country_of_origin: str | None = None`
- [ ] Add `update_line_items(updates: list[dict])` method to `Shipment`:
  - Each dict: `{"part_number": str, "net_weight": Decimal | None, "gross_weight": Decimal | None, "package_count": int | None, "dimensions": str | None, "country_of_origin": str | None}`
  - Matches by `part_number`; raises `ValueError` if part_number not found in shipment
  - Updates `updated_at`
  - Only allowed in DRAFT or DOCUMENTS_PENDING status

### Backend -- DTO
- [ ] `ShipmentLineItemUpdate` (Pydantic): `part_number: str`, `net_weight: Decimal | None = None`, `gross_weight: Decimal | None = None`, `package_count: int | None = None`, `dimensions: str | None = None`, `country_of_origin: str | None = None`
- [ ] `ShipmentUpdate` (Pydantic): `line_items: list[ShipmentLineItemUpdate]`
- [ ] Update `ShipmentLineItemResponse` to include new fields

### Backend -- Repository
- [ ] Update `ShipmentRepository.save()` to persist new fields on shipment_line_items
- [ ] Update reconstruction to read new fields

### Backend -- Router
- [ ] `PATCH /api/v1/shipments/{shipment_id}` -- update shipment line item weights/dimensions
  - Request body: `{"line_items": [{"part_number": "PN-001", "net_weight": "5.5", "gross_weight": "6.2", "package_count": 2, "dimensions": "40x30x20 cm", "country_of_origin": "CN"}]}`
  - Returns updated shipment
  - Returns 404 if shipment not found
  - Returns 409 if shipment is in READY_TO_SHIP status
  - Returns 422 if part_number not found in shipment
  - Role guard: SM and FREIGHT_MANAGER
- [ ] `GET /api/v1/shipments/{shipment_id}/packing-list` -- generate and return packing list PDF
  - Returns PDF bytes with `Content-Type: application/pdf`
  - Returns 404 if shipment not found
  - Role guard: SM, VENDOR, FREIGHT_MANAGER

### Backend -- PDF service
- [ ] New file: `src/services/packing_list_pdf.py`
- [ ] Function: `generate_packing_list_pdf(shipment: Shipment, po: PurchaseOrder, vendor_name: str, vendor_address: str, buyer_name: str, buyer_address: str) -> bytes`
- [ ] Follow same ReportLab pattern as `po_pdf.py`:
  - `SimpleDocTemplate` with Letter page size, 0.75-inch margins
  - `io.BytesIO` buffer, return `buf.getvalue()`
- [ ] PDF sections:
  1. **Title**: "PACKING LIST" centered
  2. **Header**: shipment number, PO number, date, marketplace
  3. **Parties**: Shipper (vendor name + address) and Consignee (buyer name + address) in side-by-side boxes
  4. **Line items table**: columns: #, Description, Quantity, UOM, Package Count, Net Weight, Gross Weight, Dimensions, Country of Origin
  5. **Summary**: Total Packages (sum of package_count), Total Net Weight (sum of net_weight), Total Gross Weight (sum of gross_weight)
- [ ] Handle None values for weight/dimension fields: display as "-" in PDF

### Frontend
- [ ] Shipment detail page: editable fields for net_weight, gross_weight, package_count, dimensions, country_of_origin per line item
  - Inline editing or edit modal
  - Save button calls PATCH endpoint
- [ ] "Download Packing List" button on shipment detail page
  - Calls GET packing-list endpoint, triggers browser PDF download
  - Filename: `packing-list-{shipment_number}.pdf`

### Tests (permanent)
- [ ] PATCH shipment with weights/dimensions: fields persisted, returned in response
- [ ] PATCH with unknown part_number: returns 422
- [ ] PATCH on READY_TO_SHIP shipment: returns 409
- [ ] PATCH on DRAFT shipment: works
- [ ] PATCH on DOCUMENTS_PENDING shipment: works
- [ ] Generate packing list PDF: returns 200 with content-type application/pdf, non-empty body
- [ ] Generate packing list for nonexistent shipment: returns 404
- [ ] PDF contains correct shipment number and PO number (parse or byte check)
- [ ] Summary totals computed correctly from line items

### Tests (scratch)
- [ ] Screenshot: shipment detail page with weight/dimension fields filled in
- [ ] Save generated packing list PDF and verify layout

## Acceptance criteria
- [ ] ShipmentLineItem has net_weight, gross_weight, package_count, dimensions, country_of_origin fields
- [ ] PATCH endpoint updates line item weights/dimensions, blocked on READY_TO_SHIP
- [ ] GET packing-list returns a valid PDF following the existing ReportLab pattern
- [ ] PDF contains: shipper, consignee, shipment number, PO number, line items with weights, summary totals
- [ ] None values display as "-" in PDF
- [ ] Frontend allows editing weights/dimensions and downloading packing list
- [ ] Role guards: SM and FREIGHT_MANAGER for PATCH; all authenticated for PDF download
- [ ] All permanent tests pass
