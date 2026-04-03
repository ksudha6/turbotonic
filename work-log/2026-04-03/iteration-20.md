# Iteration 20 — Cosmetic fixes

## Context

Collecting cosmetic/polish issues found during testing of iterations 13-19. To be worked after iterations 14-19 are complete.

## JTBD

1. When I download a PO as PDF, I want currency stated once in the header rather than repeated on every line so the document follows standard commercial PO formatting and stays uncluttered.
2. When I create or edit a vendor, I want to pick the country from a dropdown so entries are consistent (no "In" vs "India" vs "Ind").
3. When I enter an HS code on a line item, I want basic format validation (digits/dots, 4+ characters) so obviously wrong codes are caught early.

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
