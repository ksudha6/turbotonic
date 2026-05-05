# Iteration 110

## Context

- `Vendor.tax_id` — vendor's tax identifier on the CI Shipper / Manufacturer block. Iter 108 placed `Brand.tax_id` on the CI Seller side (importer of record). The vendor side has no tax_id today; customs requires both.
- `Shipment.pallet_count` — pallet count on PL header. Currently absent; customs and carriers expect it.
- `Shipment.export_reason` — declared reason for export on CI (e.g. "Sale", "Sample", "Return"). Currently absent; required on commercial invoices for cross-border movement.

After this iter, the PL and CI PDFs carry every field iter 102 identified as missing for customs acceptance. Subsequent customs work (typed-doc entities, FTA / preference, restricted-party screening) is in `docs/backlog.md` under "Compliance depth" and is out of scope here.

## JTBD
