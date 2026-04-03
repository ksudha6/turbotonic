# Domain Vocabulary

## Entities & Aggregates

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Purchase Order | A buyer's formal request to a vendor for goods. Contains header, trade details, and one or more line items. Aggregate root. | Procurement |
| Line Item | A single product/material entry on a PO: part number, description, quantity, UoM, unit price, HS code, country of origin. Child entity of Purchase Order. | Procurement |
| Vendor | The supplier fulfilling a purchase order. Separate entity with id (UUID), name, country (validated reference data code), and active/inactive status. PO references vendor by id; name and country resolved on read. | Procurement |
| Buyer | The purchasing party on a PO. Stored inline as buyer_name and buyer_country. Prefilled with a default value on creation. | Procurement |
| Vendor Status | Active or Inactive. Only Active vendors can be assigned to new POs. Deactivation does not affect existing POs. | Procurement |
| Vendor Reactivation | Restoring an Inactive vendor to Active status. Symmetric guard to deactivation: must be INACTIVE. | Procurement |
| Reference Data | System-managed, immutable value lists (currencies, incoterms, payment terms, countries, ports) that constrain PO fields. Served via API; frontend renders as dropdowns. | Procurement |
| USD Exchange Rate | Static indicative rate converting a currency to USD, stored in reference data as `(currency_code, rate)` pairs. Used for approximate dashboard totals, not financial calculations. | Procurement |
| Rejection Record | A timestamped comment captured when a vendor rejects a PO. Append-only; accumulated across reject/revise cycles. Value object owned by Purchase Order. | Procurement |

## PO Header Fields

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| PO Number | Unique system-generated identifier for a purchase order. Format: `PO-YYYYMMDD-XXXX`, sequential per day. | Procurement |
| Ship-to Address | The physical delivery address for the goods. | Procurement |
| Payment Terms | How and when payment is made. Covers advance (ADV, CIA, COD), net terms (NET15 through NET120), early-payment discount (2NET30), documentary trade (DA, DP, LC, SBLC, TT), and open account (OA, CONSIGN). Validated against reference data. | Procurement |
| Currency | The currency in which the PO is denominated. | Procurement |
| Issued Date | Date the PO was formally issued. | Procurement |
| Required Delivery Date | Date by which goods must be delivered. | Procurement |
| Total Value | Sum of all line item values on the PO. | Procurement |
| Terms and Conditions | Full text of the legal terms governing the PO. | Procurement |

## Trade Fields

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Incoterm | International commercial term defining delivery obligations (FOB, CIF, EXW, etc.). | Trade |
| Port of Loading | The port where goods are loaded onto the export carrier. | Trade |
| Port of Discharge | The port where goods are unloaded at destination. | Trade |
| Country of Origin | The country where goods were manufactured or produced. Applies at PO header and per line item. | Trade |
| Country of Destination | The country where goods are ultimately delivered. | Trade |

## Line Item Fields

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Part Number | Identifier for the product or material. | Procurement |
| Unit of Measure | The measurement unit for a line item quantity (e.g., pcs, kg, m). | Procurement |
| HS Code | Harmonized System tariff classification code for a product. Used for customs declarations. Format: digits and dots only, minimum 4 characters. Validated on backend (field_validator) and frontend (inline error with submit-disable). | Trade |

## Document Export

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Reference Label | The human-readable form of a reference data code, resolved via lookup. Port labels combine city and country (e.g. "CNSHA" resolves to "Shanghai, China"). Resolved server-side for PDF export (`reference_labels.py`) and client-side for detail views (`labels.ts`). | Procurement |
| PO Document Export | A PDF rendering of a PO as a clean commercial document: header, parties, trade details, line items, terms and conditions. Currency stated once in the header; line item amounts are plain numbers. Excludes operational data (rejection history). | Procurement |
| Invoice Document Export | A PDF rendering of an invoice: header (invoice number, status, PO number, currency, payment terms, created date), parties (buyer/vendor), line items table with subtotal. Includes dispute reason section when status is DISPUTED. Same ReportLab layout as PO PDF. | Invoicing |
| Bulk Document Export | Multiple invoices combined into a single PDF with one invoice per page. Requested via POST with a list of invoice IDs; missing IDs are skipped. | Invoicing |

## Read Models

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Dashboard | Read model aggregating PO counts, USD-equivalent totals by status, invoice counts and totals by status, vendor health metrics (active/inactive counts), and recent PO activity. Not a domain aggregate. | Procurement |
| Invoice List | Paginated read model listing all invoices with PO and vendor context (po_number, vendor_name). Filterable by status, PO number, vendor name, invoice number, and date range (from/to). Text filters use case-insensitive substring matching. Frontend uses dropdowns for PO#, vendor, and invoice# (populated from available data). Sorted by created_at descending. | Invoicing |
| Paginated List | A windowed query result containing items, total count, page number, and page size. Backend-enforced to avoid full dataset transfer. Used by both PO list and invoice list. | Procurement |
| PO Search | Text-based lookup matching against po_number, vendor_name, and buyer_name. Case-insensitive substring match, server-side. | Procurement |

## Bulk Operations

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Bulk Action | A single command (submit, accept, reject) applied to multiple selected POs. Only transitions common to all selected statuses are offered. | Procurement |
| Cross-Page Selection | Selecting all POs matching current filters across all pages, not just the visible page. Fetched via the list endpoint with a large page size. Capped at 200 IDs until a dedicated IDs-only endpoint exists. | Procurement |
| Valid Actions | The intersection of allowed transitions for all currently selected POs. When empty, no bulk action buttons appear and an explanatory hint is shown. | Procurement |

## Vendor Classification

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Vendor Type | Classification of a vendor: Procurement, OpEx, Freight, Miscellaneous. Required on creation. Constrains which POs the vendor can be assigned to. | Procurement |
| PO Type | Classification of a purchase order: Procurement or OpEx. Required on creation (default Procurement), immutable after creation. Vendor type must match PO type. | Procurement |

## Invoicing

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Invoice | A payment obligation created against an Accepted PO (Procurement or OPEX). Pre-populated from PO line items, payment terms, and currency. Aggregate root. | Invoicing |
| Invoice Number | Unique system-generated identifier. Format: `INV-YYYYMMDD-XXXX`, sequential per day. | Invoicing |
| Invoice Status | Draft, Submitted, Approved, Paid, Disputed. | Invoicing |
| Invoice Line Item | A line copied from the PO: part number, description, quantity, UoM, unit price. Child of Invoice. | Invoicing |
| Dispute Reason | Mandatory text captured when an invoice is disputed. Stored on the invoice. | Invoicing |
| Invoiced Quantity | Cumulative quantity invoiced per line item across all non-disputed invoices for a PO. Keyed by part_number. | Invoicing |
| Remaining Quantity | Ordered quantity minus invoiced quantity for a line item. Ceiling for the next invoice's quantity on that line. | Invoicing |
| Over-invoicing Guard | Validation that rejects invoice creation when cumulative invoiced quantity would exceed the PO's ordered quantity for any line item. Returns 409 with per-line violation detail. | Invoicing |
| OPEX Invoice | An invoice against an OPEX PO. Copies all PO line items at full quantity with no partial splits. One invoice per OPEX PO; a second attempt returns 409. Explicit `line_items` param rejected with 422. | Invoicing |
| One-Invoice-per-PO Guard | OPEX-specific enforcement: if any part_number already has invoiced quantity > 0, a new invoice is rejected (409). Does not apply to Procurement POs, which allow multiple partial invoices. | Invoicing |

### Invoice Lifecycle

| Status | Definition |
|--------|-----------|
| Draft | Invoice created, not yet submitted for approval. |
| Submitted | Invoice sent for buyer approval. |
| Approved | Buyer approved the invoice. |
| Paid | Payment completed. Terminal. |
| Disputed | Buyer disputes the invoice with a mandatory reason. |

### Invoice Status Transitions

| From | To | Trigger |
|------|----|---------|
| Draft | Submitted | Invoice submitted for approval |
| Submitted | Approved | Buyer approves |
| Submitted | Disputed | Buyer disputes with reason |
| Approved | Paid | Payment confirmed |
| Disputed | Submitted | Dispute resolved, invoice resubmitted |

## Production Tracking

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Production Milestone | Ordered enum of manufacturing stages: RAW_MATERIALS, PRODUCTION_STARTED, QC_PASSED, READY_TO_SHIP, SHIPPED. Append-only, posted in sequence against ACCEPTED PROCUREMENT POs. | Production |
| Milestone Update | Value object recording a milestone post (milestone, posted_at). Append-only child of Purchase Order. | Production |
| Milestone Order Enforcement | Validation that the proposed milestone is the next in the fixed sequence. Rejects out-of-order, duplicate, and beyond-terminal posts. | Production |
| Current Milestone | The latest posted milestone for a PO. Null when no milestones exist. Exposed on the PO list as a read model field via subquery join. | Production |
| Overdue Production | A PO whose latest milestone has exceeded its time threshold: 7 days for RAW_MATERIALS and PRODUCTION_STARTED, 3 days for QC_PASSED and READY_TO_SHIP. SHIPPED is never overdue. Surfaced on the dashboard. | Production |

## Compliance (deferred)

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Letter of Credit Number | Reference to the LC issued by the buyer's bank to guarantee payment. | Compliance |
| Export License Number | Government-issued license permitting export of controlled goods. | Compliance |
| Packing List Reference | Pointer to the document detailing how goods are packed for shipment. | Compliance |
| Bill of Lading Reference | Pointer to the carrier-issued document acknowledging receipt of goods for shipment. | Compliance |

## PO Parties

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Buyer Name | Name of the purchasing party. Inline on PO, prefilled with default. | Procurement |
| Buyer Country | Country of the purchasing party. Inline on PO, prefilled with default. | Procurement |
| Default Buyer | The system owner's identity (name and country) prefilled on new POs. Currently hardcoded; will become configurable when Buyer is promoted to a first-class entity. | Procurement |

## PO Field Immutability

| Fields | Rule |
|--------|------|
| `id`, `po_number`, `created_at` | Immutable after creation |
| All other fields | Mutable only in Draft and Rejected status |

## PO Lifecycle

| Status | Definition |
|--------|-----------|
| Draft | PO is being composed, not yet visible to vendor. |
| Pending | PO submitted to vendor, awaiting accept or reject. |
| Accepted | Vendor formally accepted. Unlocks invoicing for Procurement and OPEX POs. Terminal. |
| Rejected | Vendor rejected with mandatory comment. |
| Revised | Previously rejected PO updated and resubmitted, awaiting vendor action. |

### Status Transitions

| From | To | Trigger |
|------|----|---------|
| Draft | Pending | PO submitted to vendor |
| Pending | Accepted | Vendor accepts |
| Pending | Rejected | Vendor rejects with comment |
| Rejected | Revised | Creator updates PO fields |
| Revised | Pending | Revised PO resubmitted to vendor |

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Pending : Submit to vendor
    Pending --> Accepted : Vendor accepts
    Pending --> Rejected : Vendor rejects (with comment)
    Rejected --> Revised : Creator updates fields
    Revised --> Pending : Resubmitted to vendor
    Accepted --> [*]
```
