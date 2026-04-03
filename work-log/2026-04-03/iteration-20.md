# Iteration 20 — Cosmetic fixes

## Context

I want to make some cosmetic changes across the portal. 

## JTBD

1. When I download a PO as PDF, I want currency stated once in the header rather than repeated on every line so the document follows standard commercial PO formatting and stays uncluttered.
2. When I create or edit a vendor, I want to pick the country from a dropdown so entries are consistent (no "In" vs "India" vs "Ind").
3. When I enter an HS code on a line item, I want basic format validation (digits/dots, 4+ characters) so obviously wrong codes are caught early.

## Acceptance Criteria

### PDF currency cleanup
1. The PDF header contains the currency code and name once (e.g. "Currency: USD — United States Dollar").
2. Unit Price and Line Total cells show numeric values only; no currency code suffix on individual rows.
3. Column headers read "Unit Price" and "Line Total" with no currency annotation.

### Vendor country dropdown
1. Vendor create and edit forms render a dropdown for the country field populated from the countries reference data.
2. Submitting a vendor with a country code not in the reference data returns a 422.
3. Existing vendor records with free-text country values are migrated to matching reference data codes. Unmatched values are set to null and logged.

### HS code validation
1. Backend rejects any line item HS code that does not match the pattern: digits and dots only, minimum 4 characters. Returns 422 with a message identifying the field.
2. Frontend shows an inline error message on the HS code input when the value does not match the pattern.
3. The form cannot be submitted while any HS code field has a validation error.

## Tasks

### PDF currency cleanup
- [ ] Remove currency code from per-cell values in PDF (unit price, line total, grand total)
- [ ] Currency in header ("Currency: USD — United States Dollar") remains the single source
- [ ] Column headers stay plain: "Unit Price", "Line Total"

### Vendor country dropdown
- [ ] Add country reference data (seed list of countries)
- [ ] Replace free-text country field with dropdown on vendor create/edit
- [ ] Migrate existing free-text values to reference data IDs

### HS code validation
- [ ] Backend: validate HS code format (digits and dots only, minimum 4 characters)
- [ ] Frontend: show validation error on line item entry
- [ ] Reject save if any line item has an invalid HS code

## Tests

### Permanent backend
- PDF bytes for a PO with USD currency do not contain "USD" in any line item cell; the header section contains "USD" exactly once.
- Vendor creation with a valid country code from reference data returns 201.
- Vendor creation with a country code absent from reference data returns 422.
- Line item creation with HS code "AB" (too short, non-digit) returns 422.
- Line item creation with HS code "7318.15" returns 201.
- Line item creation with HS code "1234" (minimum length, digits only) returns 201.

### Permanent frontend
- Vendor create form renders a `<select>` element for the country field.
- Vendor edit form renders the same `<select>` with the existing value pre-selected.
- Line item HS code input shows an inline error message when the entered value is invalid format.
- Submit button is disabled while any HS code field has a validation error.

### Scratch
- Screenshot: vendor create form with country dropdown visible.
- Screenshot: vendor create form with country selected.
- Screenshot: line item form with HS code validation error shown.

## Notes

