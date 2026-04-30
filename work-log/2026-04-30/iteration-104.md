# Iteration 104 — PL/CI PDF Customs Fields (No-Migration Joins)

## Context

Iter 102 added the frontend for shipment documents, readiness, and mark-ready. During that iter the PL/CI PDF generators were identified as missing several customs-required fields. The fields fall into two groups: (a) joinable today from existing schema via vendor, PO, and line-item data; (b) fields that require new columns (e.g. dedicated manufacturer entity, signatory details) deferred to iter 106. This iter delivers group (a).

The generators (`packing_list_pdf.py` and `commercial_invoice_pdf.py`) currently show shipper/consignee parties, line items with weights, and a header. They lack ports, origin country header line, HS code on PL, manufacturer block, marketplace on CI header, and a shipper's declaration. All of these can be sourced from the `PurchaseOrder` (which already stores `port_of_loading`, `port_of_discharge`, `country_of_origin`, `marketplace`) and the `Vendor` aggregate (which stores `name`, `address`, `country`). No schema changes are needed.

## JTBD

- As the person generating shipment docs (SM or FM), I need the PL and CI PDFs to include manufacturer info, marketplace, HS code on PL, ports, origin country header, and a shipper's declaration so the documents are customs-acceptable using only the existing schema.

## Tasks

1. Add to PL:
   a. Port of Loading + Port of Discharge row in header (from `po.port_of_loading` / `po.port_of_discharge`, resolved to labels).
   b. Country of Origin row in header (from `po.country_of_origin`, resolved to label).
   c. HS Code column in the line items table.
   d. Manufacturer block in the Parties section (vendor name + address + country, labelled "Manufacturer").
2. Add to CI:
   a. Marketplace row in header (from `shipment.marketplace`).
   b. Port of Loading + Port of Discharge row in header.
   c. Manufacturer block already present as "Seller" — enrich with vendor country line.
   d. Declaration text block at document bottom: "I declare that the information on this invoice is true and correct."
3. Update generator signatures if needed (pass `po` data already available — no new params required; all fields come from existing `po` and `shipment` args).
4. Add backend pytests covering the new fields.

### Deferred to iter 106

- Per-line manufacturer (distinct manufacturer entity with its own ID column on products).
- Signatory name and declaration date (no signatory column on users or shipments).
- Vessel name / booking reference on PL (available on BOOKED+ shipments, but not yet surfaced in PL which is generated pre-booking).

## Tests

### Existing test impact

No existing tests break. The generators' signatures are unchanged. Existing tests assert on fields that remain present. The new columns/rows are additive.

### New tests

- PL contains port of loading and port of discharge labels.
- PL contains country of origin label in header.
- PL HS code per line item is present in PDF text.
- PL manufacturer block (vendor name) appears in PDF text.
- CI contains marketplace in PDF text.
- CI contains port of loading and port of discharge labels.
- CI contains declaration text.
- CI vendor country is present in parties block.

## Notes

PL now includes ports of loading/discharge (resolved to city, country labels), country of origin in the header, HS code column per line item sourced from ACCEPTED PO line items, and a "Shipper / Manufacturer" block carrying vendor name, address, and country. CI now includes marketplace, ports, vendor country in the Seller block, and a declaration paragraph. Signature is extended with an optional `vendor_country: str = ""` param on both generators; all existing callers continue to work unchanged (the router passes the new param). Fields deferred to iter 106: per-line manufacturer from a distinct Manufacturer entity (no such entity or manufacturer_id column exists today); signatory name and declaration date (no signatory column on users or shipments); vessel/booking reference on PL (shipments are pre-booking at document generation time). 775 pytests pass, 398 Playwright specs pass.
