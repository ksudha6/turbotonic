# Iteration 13 — 2026-04-03

## Context
The PO detail page displays raw reference-data codes for payment terms (`DA`, `TT`, `LC`, `DP`) and incoterms (`FOB`, `CIF`, `CFR`, etc.) instead of human-readable labels. The backend already exposes a `/api/v1/reference-data/` endpoint with code-to-label mappings, and the PO create/edit forms already fetch this data. The detail view just never resolves the codes.

## JTBD
1. **When** I view a PO detail page, **I want to** see human-readable labels for payment terms, incoterms, currency, countries, and ports instead of raw codes **so that** I can understand the terms at a glance without memorizing abbreviations.

## Tasks

### Frontend — Label Resolution Utility (`frontend/src/lib/labels.ts`)
- [x] `buildLabelResolver(refData: ReferenceData)` builds `Map<string, string>` lookups from each reference data category
- [x] `resolve(category, code)` returns human-readable label; falls back to raw code for unknown values
- [x] Port resolution combines city name with country name (matching backend `port_label` behavior: "CNSHA" → "Shanghai, China")

### Frontend — PO Detail View (`frontend/src/routes/po/[id]/+page.svelte`)
- [x] Fetch reference data on mount alongside PO
- [x] Resolve payment_terms code to label (e.g. "DA" → "Documents against Acceptance")
- [x] Resolve incoterm code to label (e.g. "FOB" → "Free on Board")
- [x] Resolve currency code to label (e.g. "USD" → "US Dollar")
- [x] Resolve buyer_country and vendor_country codes to labels
- [x] Resolve country_of_origin and country_of_destination codes to labels
- [x] Resolve port_of_loading and port_of_discharge codes to labels (city, country format)
- [x] Resolve line item country_of_origin codes to labels

### Scratch Tests (`frontend/tests/scratch/iteration-13/`)
- [x] PO detail shows "Documents against Acceptance" for payment_terms code "DA"
- [x] PO detail shows "Free on Board" for incoterm code "FOB"
- [x] PO detail shows "US Dollar" for currency code "USD"
- [x] PO detail shows "India" for buyer_country and vendor_country code "IN"
- [x] PO detail shows "Shanghai, China" for port_of_loading code "CNSHA"
- [x] PO detail shows resolved country name for country_of_origin and country_of_destination
- [x] Line item country_of_origin shows resolved label
- [x] Unknown code falls back to displaying the raw code

## Notes
Label resolution done client-side via `buildLabelResolver` in `labels.ts`, which builds lookup maps from the existing `/api/v1/reference-data/` endpoint. PO detail page fetches reference data in parallel with the PO using `Promise.all`. Port labels combine city and country ("Shanghai, China"), matching the backend PDF behavior. Unknown codes fall back to raw value. Updated DDD vocab to note that Reference Label is now resolved both server-side (PDF) and client-side (detail views). Backlog item "Label resolution on PO detail view" is complete.

