# Iteration 045 -- Export commercial invoice generation (PDF)

## Context

The billing Invoice entity handles buyer-vendor payments but is not a customs document. This iteration adds the export commercial invoice (CI), a separate PDF generated from shipment + PO data that includes HS codes, trade terms, weights, and values for customs clearance. It follows the same ReportLab pattern as the packing list (iter 044) and uses weight/dimension fields added in that iteration.

## JTBD

- When a shipment is being prepared for export, I want to generate a commercial invoice PDF so that customs authorities have the required trade documentation.
- When customs reviews the commercial invoice, they need HS codes, values, weights, and country of origin per line item so that they can assess duties and clear the shipment.

## Tasks

### Backend -- Schema
- [ ] No new tables. CI number is auto-generated at PDF generation time, not persisted.

### Backend -- Domain
- [ ] Add `generate_ci_number(shipment_number: str) -> str` helper function:
  - Format: `CI-{shipment_number}` (e.g. `CI-SHP-20260414-A3F2`)
  - Deterministic from shipment number; no separate counter needed

### Backend -- DTO
- [ ] No new DTOs needed. The endpoint returns PDF bytes directly.

### Backend -- Router
- [ ] `GET /api/v1/shipments/{shipment_id}/commercial-invoice` -- generate and return export CI PDF
  - Returns PDF bytes with `Content-Type: application/pdf`
  - Returns 404 if shipment not found
  - Loads PO (for incoterm, payment terms, currency, buyer info, line item HS codes and unit prices) and vendor (for seller info) alongside shipment
  - Role guard: SM, VENDOR, FREIGHT_MANAGER

### Backend -- PDF service
- [ ] New file: `src/services/commercial_invoice_pdf.py`
- [ ] Function: `generate_commercial_invoice_pdf(shipment: Shipment, po: PurchaseOrder, vendor_name: str, vendor_address: str, buyer_name: str, buyer_address: str) -> bytes`
- [ ] Follow same ReportLab pattern as `po_pdf.py` and `packing_list_pdf.py`:
  - `SimpleDocTemplate` with Letter page size, 0.75-inch margins
  - `io.BytesIO` buffer, return `buf.getvalue()`
- [ ] PDF sections:
  1. **Title**: "COMMERCIAL INVOICE" centered
  2. **Header row 1**: CI Number (left), Date (right, current date)
  3. **Header row 2**: PO Number (left), Shipment Number (right)
  4. **Trade terms row**: Incoterm with label (left), Payment Terms with label (right)
  5. **Currency row**: Currency with label
  6. **Parties**: Seller (vendor name + address) and Buyer (buyer name + address + country) in side-by-side boxes. Add "Consignee" row under buyer with ship_to_address.
  7. **Line items table**: columns: #, Description, HS Code, Quantity, UOM, Unit Price, Net Weight, Gross Weight, Country of Origin, Line Value
     - Unit price comes from PO line item (matched by part_number)
     - HS code comes from PO line item (matched by part_number)
     - Weights come from shipment line item (from iter 044)
     - Line Value = quantity * unit_price
  8. **Summary**:
     - Total Quantity (sum of quantities)
     - Total Value (sum of line values) with currency
     - Total Net Weight (sum of net_weight)
     - Total Gross Weight (sum of gross_weight)
     - Total Packages (sum of package_count)
     - Marks and Numbers: shipment_number
- [ ] Handle None values for weight fields: display as "-" in PDF
- [ ] Use `reference_labels` for incoterm, payment terms, currency, country labels (same as PO PDF)

### Frontend
- [ ] "Download Commercial Invoice" button on shipment detail page
  - Calls GET commercial-invoice endpoint, triggers browser PDF download
  - Filename: `commercial-invoice-{shipment_number}.pdf`
- [ ] Button visible alongside "Download Packing List" button

### Tests (permanent)
- [ ] Generate commercial invoice PDF: returns 200 with content-type application/pdf, non-empty body
- [ ] Generate CI for nonexistent shipment: returns 404
- [ ] CI number follows format CI-SHP-YYYYMMDD-XXXX
- [ ] PDF contains correct PO number, shipment number, CI number
- [ ] Line item values computed from PO unit_price * shipment quantity
- [ ] Summary totals computed correctly
- [ ] HS codes pulled from PO line items, not shipment line items

### Tests (scratch)
- [ ] Save generated commercial invoice PDF and verify layout
- [ ] Verify all fields present: seller, buyer, consignee, incoterm, payment terms, HS codes, weights, totals

## Acceptance criteria
- [ ] GET endpoint returns a valid PDF with Content-Type application/pdf
- [ ] CI number auto-generated from shipment number (format CI-SHP-...)
- [ ] PDF contains: seller, buyer, consignee, CI number, date, PO ref, shipment ref, incoterm, payment terms, currency
- [ ] Per-line: description, HS code (from PO), quantity (from shipment), unit price (from PO), weights (from shipment), country of origin, line value
- [ ] Summary: total quantity, total value with currency, total net weight, total gross weight, total packages, marks and numbers
- [ ] Uses reference_labels for human-readable incoterm, payment terms, currency, country names
- [ ] None weight values display as "-"
- [ ] Role guard: SM, VENDOR, FREIGHT_MANAGER
- [ ] This is NOT the billing Invoice -- it's a customs document
- [ ] All permanent tests pass
