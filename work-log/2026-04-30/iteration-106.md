# Iteration 106 — PL/CI Schema Additions for Customs Completion

## Context

Iter 104 enriched PL/CI PDFs with all customs fields available from existing schema joins. The iter 104 Notes section explicitly deferred three categories to this iter because they require new schema columns:

1. Per-line manufacturer — distinct from the vendor (product's manufacturer, potentially different per line from the shipping vendor).
2. Signatory name + declaration date — the CI declaration currently says "I declare..." with no named signatory or date.
3. Vessel name + voyage number on PL — shipping vessel and voyage details available post-booking but not yet surfaced on the PL.

## JTBD

- As the person generating shipment docs (SM or FM), I need the PL and CI to include vessel/voyage on the PL, and signatory + declaration date on the CI, so the documents are fully customs-acceptable without manual annotation.
- As the shipment manager or freight manager, I need to record vessel name and voyage number after booking so the PL can reference them.
- As the shipment manager or freight manager, I need to record a signatory name + title on a shipment so the CI carries a named declaration with a date.

## Tasks

### Backend

1. Schema migration: add `vessel_name TEXT`, `voyage_number TEXT`, `signatory_name TEXT`, `signatory_title TEXT`, `declared_at TEXT` to `shipments`; add `manufacturer_name TEXT`, `manufacturer_address TEXT`, `manufacturer_country TEXT` to `products`.
2. Domain: add fields to `Shipment.__init__`; add `set_transport(vessel_name, voyage_number)` method (BOOKED status only, nullable fields); add `declare(signatory_name, signatory_title)` method (DOCUMENTS_PENDING, READY_TO_SHIP, BOOKED, SHIPPED — any post-DRAFT status); raise ValueError on empty/whitespace strings.
3. DTO: extend `ShipmentResponse`; add `ShipmentTransportRequest` and `ShipmentDeclareRequest`; update `shipment_to_response`.
4. Repository: persist + reconstruct the five new columns in `save` and `_reconstruct`.
5. Router: add `PATCH /{id}/transport` (vessel_name + voyage_number; SM/FM; BOOKED+); add `POST /{id}/declare` (signatory_name + signatory_title; SM/FM; post-DRAFT).
6. PL generator: render vessel + voyage in header after carrier/booking_reference row when present.
7. CI generator: render signatory_name + signatory_title + declared_at below the declaration text.
8. PL generator: render per-line manufacturer block from product manufacturer fields when present (fall back to vendor when empty).

### Frontend

9. `types.ts`: extend `Shipment` with the five new nullable fields; add `ShipmentTransportPayload` and `ShipmentDeclarePayload`.
10. `api.ts`: add `setShipmentTransport` and `declareShipment`.
11. `permissions.ts`: add `canSetTransport(role, status)` (SM/FM + BOOKED); add `canDeclareShipment(role, status)` (SM/FM + post-DRAFT).
12. `ShipmentTransportPanel.svelte`: vessel_name + voyage_number inputs (both optional). Mounts on BOOKED+.
13. `ShipmentDeclarePanel.svelte`: signatory_name (required) + signatory_title (optional) inputs. Mounts post-DRAFT when not yet declared.
14. Page wiring: mount both panels in `shipments/[id]/+page.svelte`.

### Tests + close

15. Pytest: migration column-exists; PL contains vessel+voyage; CI contains signatory+date; `/declare` endpoint happy + 403 + 409; `/transport` endpoint happy + 403 + 409.
16. Playwright: transport panel renders on BOOKED; declare panel renders post-DRAFT; both panels hidden when not applicable.

## Tests

### Existing test impact

No existing tests break. The five new columns are nullable with no defaults that change existing row shape. The `shipment_to_response` change is additive; `ShipmentResponse` gets new optional fields. The PDF generators gain new parameters with defaults, so existing test helpers continue to pass.

### New tests

- `test_transport_schema_columns_exist`: assert vessel_name + voyage_number columns exist on shipments table.
- `test_declare_schema_columns_exist`: assert signatory_name + signatory_title + declared_at columns exist on shipments table.
- `test_set_transport_happy_path`: BOOKED shipment; PATCH /transport; response carries vessel_name + voyage_number.
- `test_set_transport_requires_booked_status`: READY_TO_SHIP shipment; PATCH /transport → 409.
- `test_set_transport_role_guard`: VENDOR role; PATCH /transport → 403.
- `test_declare_happy_path`: DOCUMENTS_PENDING shipment; POST /declare; response carries signatory_name + declared_at.
- `test_declare_role_guard`: VENDOR role; POST /declare → 403.
- `test_declare_status_guard`: DRAFT shipment; POST /declare → 409.
- `test_packing_list_contains_vessel_voyage`: BOOKED shipment with vessel_name + voyage_number; PL PDF text contains both.
- `test_commercial_invoice_contains_signatory`: declared shipment; CI PDF text contains signatory_name.

## Notes

Schema design decisions:
- Per-line manufacturer: added `manufacturer_name`, `manufacturer_address`, `manufacturer_country` to `products` (not a new Manufacturers table and not a foreign key on `shipment_line_items`). Products already have `manufacturing_address`; the new columns add name and country at the product level. A distinct Manufacturer entity with its own ID is carry-forward for a later iter.
- Signatory ownership: placed on `shipments`, not `users`. A declaration is per-shipment, not per-user. The declare endpoint stamps `declared_at = now()` server-side.
- Vessel/voyage endpoint: a separate `PATCH /{id}/transport` (not folded into /book). Booking captures carrier+booking_ref+pickup_date at READY_TO_SHIP→BOOKED; vessel/voyage are typically confirmed after booking, possibly from a separate shipping instruction. Decoupling the two allows vessel updates post-booking without re-booking.
