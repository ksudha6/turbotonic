# Iteration 043 -- Shipment aggregate

## Context

POs can be accepted with per-line-item ACCEPTED/REJECTED status (iter 037), but there is no way to organize accepted items into physical shipments. This iteration adds the Shipment aggregate with a quantity guard that prevents cumulative shipped quantities from exceeding accepted quantities, following the same pattern as the invoice over-invoicing guard. Multiple partial shipments per PO are supported.

## JTBD

- When a PO is accepted, I want to create a shipment selecting which accepted line items and quantities to ship so that I can organize partial or full shipments.
- When I create multiple shipments against the same PO, I want the system to prevent me from shipping more than the accepted quantity so that I don't over-ship.
- When I view a PO's shipments, I want to see remaining shippable quantities per line item so that I know how much is left to ship.
- When I manage shipments, I want to track their status through a lifecycle so that I know which shipments need documents, which are ready, and which are complete.

## Tasks

### Backend -- Schema
- [ ] Create `shipments` table:
  - `id TEXT PRIMARY KEY`
  - `po_id TEXT NOT NULL REFERENCES purchase_orders(id)`
  - `shipment_number TEXT UNIQUE NOT NULL` (format: SHP-YYYYMMDD-XXXX, auto-generated)
  - `marketplace TEXT NOT NULL` (inherited from PO at creation time)
  - `status TEXT NOT NULL DEFAULT 'DRAFT'`
  - `created_at TEXT NOT NULL`
  - `updated_at TEXT NOT NULL`
- [ ] Create `shipment_line_items` table:
  - `id TEXT PRIMARY KEY`
  - `shipment_id TEXT NOT NULL REFERENCES shipments(id)`
  - `part_number TEXT NOT NULL`
  - `product_id TEXT` (nullable, inherited from PO line item if available)
  - `description TEXT NOT NULL DEFAULT ''`
  - `quantity INTEGER NOT NULL`
  - `uom TEXT NOT NULL`
  - `sort_order INTEGER NOT NULL`

### Backend -- Domain
- [ ] New file: `src/domain/shipment.py`
- [ ] `ShipmentStatus` enum: `DRAFT`, `DOCUMENTS_PENDING`, `READY_TO_SHIP`
- [ ] `ShipmentLineItem` dataclass:
  - Fields: `part_number: str`, `product_id: str | None`, `description: str`, `quantity: int`, `uom: str`
  - Validation: `quantity` must be > 0; `part_number` must not be empty or whitespace-only
- [ ] `Shipment` aggregate:
  - Fields: `id: str`, `po_id: str`, `shipment_number: str`, `marketplace: str`, `status: ShipmentStatus`, `line_items: list[ShipmentLineItem]`, `created_at: datetime`, `updated_at: datetime`
  - `id`, `shipment_number`, `created_at` are immutable (properties)
  - Factory method `create(po_id: str, marketplace: str, line_items: list[ShipmentLineItem]) -> Shipment`:
    - Generates `shipment_number` in format `SHP-YYYYMMDD-XXXX` (XXXX is random 4-digit hex)
    - Validates at least one line item
    - Status starts as `DRAFT`
  - `submit_for_documents()` method: transitions DRAFT -> DOCUMENTS_PENDING
  - `mark_ready()` method: transitions DOCUMENTS_PENDING -> READY_TO_SHIP
  - Both transition methods raise `ValueError` if called from wrong status
- [ ] Shipped quantity guard function: `validate_shipment_quantities(po_line_items: list[dict], existing_shipments: list[Shipment], new_line_items: list[ShipmentLineItem]) -> None`
  - `po_line_items` is a list of dicts with `part_number`, `quantity`, `status` (from PO)
  - Only ACCEPTED PO line items are eligible for shipment
  - For each new shipment line item: cumulative shipped qty (from existing shipments) + new qty must not exceed PO accepted qty
  - Raises `ValueError` with details if any line item exceeds

### Backend -- DTO
- [ ] `ShipmentLineItemCreate` (Pydantic): `part_number: str`, `product_id: str | None = None`, `description: str`, `quantity: int`, `uom: str`
- [ ] `ShipmentCreate` (Pydantic): `po_id: str`, `line_items: list[ShipmentLineItemCreate]`
  - `marketplace` is inherited from PO, not provided by client
- [ ] `ShipmentLineItemResponse` (Pydantic): all fields
- [ ] `ShipmentResponse` (Pydantic): all fields including nested `line_items`
- [ ] `RemainingShipmentQuantity` (Pydantic): `part_number: str`, `po_quantity: int`, `shipped_quantity: int`, `remaining_quantity: int`
- [ ] `RemainingShipmentQuantityResponse` (Pydantic): `po_id: str`, `items: list[RemainingShipmentQuantity]`

### Backend -- Repository
- [ ] New file: `src/repositories/shipment_repo.py`
- [ ] `ShipmentRepository` with methods:
  - `save(shipment: Shipment)` -- upsert shipment + line items
  - `get(shipment_id: str) -> Shipment | None`
  - `list_by_po(po_id: str) -> list[Shipment]`
  - `get_shipped_quantities(po_id: str) -> dict[str, int]` -- returns cumulative shipped qty per part_number across all shipments for a PO

### Backend -- Router
- [ ] New file: `src/routers/shipment.py`
- [ ] `POST /api/v1/shipments` -- create a new shipment
  - Validates PO exists and is ACCEPTED
  - Inherits `marketplace` from PO
  - Runs shipped quantity guard against existing shipments
  - Only ACCEPTED PO line items are eligible (rejects part_numbers that are REJECTED or PENDING)
  - Returns 201 with created shipment
  - Returns 404 if PO not found
  - Returns 409 if PO is not ACCEPTED
  - Returns 422 if shipped quantity would exceed accepted quantity, or if line item part_number not found in PO accepted lines
  - Role guard: SM and FREIGHT_MANAGER
- [ ] `GET /api/v1/shipments` -- list shipments
  - Query params: `po_id` (optional filter)
  - Role guard: SM, VENDOR, FREIGHT_MANAGER
- [ ] `GET /api/v1/shipments/{shipment_id}` -- get single shipment
  - Returns 404 if not found
  - Role guard: SM, VENDOR, FREIGHT_MANAGER
- [ ] `POST /api/v1/shipments/{shipment_id}/submit-for-documents` -- transition DRAFT -> DOCUMENTS_PENDING
  - Returns 409 if not in DRAFT status
  - Role guard: SM and FREIGHT_MANAGER
- [ ] `GET /api/v1/shipments/remaining-quantities/{po_id}` -- remaining shippable quantities
  - Returns per-line-item: po_quantity (ACCEPTED only), shipped_quantity (cumulative across shipments), remaining_quantity
  - Only includes ACCEPTED PO line items
  - Returns 404 if PO not found
  - Role guard: SM and FREIGHT_MANAGER

### Frontend
- [ ] Shipment list page at `/shipments`: table with shipment_number, PO number, marketplace, status, created_at
- [ ] Create shipment form: select PO (dropdown of ACCEPTED POs), then select line items with quantities
  - Show remaining shippable quantity per line item
  - Quantity input capped at remaining quantity
  - Exclude REJECTED and PENDING line items
- [ ] Shipment detail page at `/shipments/{id}`: header with shipment number, PO reference, marketplace, status pill; line items table
- [ ] Status action buttons: "Submit for Documents" (DRAFT -> DOCUMENTS_PENDING) visible for SM and FREIGHT_MANAGER
- [ ] PO detail page: "Shipments" section listing shipments created against this PO

### Tests (permanent)
- [ ] Create shipment from accepted PO: returns 201, shipment_number matches format, marketplace inherited from PO
- [ ] Create shipment with quantity exceeding remaining: returns 422 with detail
- [ ] Create shipment with REJECTED line item part_number: returns 422
- [ ] Create shipment from non-ACCEPTED PO: returns 409
- [ ] Create shipment from nonexistent PO: returns 404
- [ ] Create shipment with empty line items: returns 422
- [ ] Create two shipments, second uses remaining quantities correctly
- [ ] Create shipment that would over-ship (cumulative > PO qty): returns 422
- [ ] Remaining quantities endpoint: correct math after 0, 1, and 2 shipments
- [ ] Remaining quantities for REJECTED lines: not included in response
- [ ] Submit for documents: DRAFT -> DOCUMENTS_PENDING works
- [ ] Submit for documents on non-DRAFT shipment: returns 409
- [ ] List shipments by po_id: returns correct shipments
- [ ] Get shipment by id: returns correct shipment with line items

### Tests (scratch)
- [ ] Screenshot: create shipment form with line item selection and quantity inputs
- [ ] Screenshot: shipment detail page showing line items and status
- [ ] Screenshot: PO detail page with shipments section

## Acceptance criteria
- [ ] `Shipment` aggregate with status lifecycle DRAFT -> DOCUMENTS_PENDING -> READY_TO_SHIP
- [ ] `shipment_number` auto-generated in format SHP-YYYYMMDD-XXXX
- [ ] `marketplace` inherited from PO at creation
- [ ] Shipped quantity guard prevents cumulative shipped qty from exceeding PO accepted qty
- [ ] Only ACCEPTED PO line items are eligible for shipment
- [ ] Multiple shipments per PO allowed (partial shipments)
- [ ] Remaining quantities endpoint returns correct values
- [ ] Role guard: SM and FREIGHT_MANAGER create/manage; VENDOR can view
- [ ] All permanent tests pass
