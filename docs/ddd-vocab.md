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
| Tasks Queue | VENDOR dashboard read model. Derived action queue, not persisted: reconstructed from `target_role=VENDOR AND category=ACTION_REQUIRED` activity rows joined against current entity state (PO, invoice, shipment, certificate, milestone). A row is in the queue while the underlying entity is still in the action-required state; resolution is implicit when the entity transitions out. (iter 114 spec) | Procurement |
| Vendor-Scoped Dashboard | SM dashboard read model. Same shape as PM but parameterised by `vendor_id` from a header-level vendor selector. KPIs and panels filter to that vendor. Caps at `READY_FOR_SHIPMENT` milestone — post-handoff state is FM's surface. (iter 114 spec) | Procurement |
| Hand-Off Queue | Dashboard panel pattern for milestone-driven role transitions. `QC_PASSED` populates the QL inbox (POs awaiting cert work). `READY_FOR_SHIPMENT` populates the FM inbox (POs awaiting shipment creation or with shipments still in DRAFT/DOCUMENTS_PENDING). Resolves via the next role's action, not a flag on the milestone. (iter 114 spec) | Production |
| Stage Breakdown Panel | Dashboard panel showing count of ACCEPTED PROCUREMENT POs per `MILESTONE_ORDER` stage. Reuses the `ProductionStageSummary` aggregate. PM/ADMIN render all five stages including SHIPPED; SM renders four (no SHIPPED, post-handoff is FM); per-bar click deep-links to `/po?milestone=<stage>`. (iter 114 spec) | Production |
| Placeholder Tile | Dashboard KPI tile rendering `—` for a metric whose backend module has not landed yet. FM KPI 4 (Customs pending) and KPI 5 (Shipments delivered) ship as placeholders so the 5-tile grid layout stays stable when the `CUSTOMS_*` and `DELIVERED` shipment-state extensions arrive. No backend stub. (iter 114 spec) | Logistics |

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
| Production Milestone | Ordered enum of manufacturing stages: RAW_MATERIALS, PRODUCTION_STARTED, QC_PASSED, READY_FOR_SHIPMENT, SHIPPED. Append-only, posted in sequence against ACCEPTED PROCUREMENT POs. (READY_FOR_SHIPMENT renamed from READY_TO_SHIP in iter 074 to disambiguate from per-shipment status.) | Production |
| Milestone Update | Value object recording a milestone post (milestone, posted_at). Append-only child of Purchase Order. | Production |
| Milestone Order Enforcement | Validation that the proposed milestone is the next in the fixed sequence. Rejects out-of-order, duplicate, and beyond-terminal posts. | Production |
| Current Milestone | The latest posted milestone for a PO. Null when no milestones exist. Exposed on the PO list as a read model field via subquery join. | Production |
| Overdue Production | A PO whose latest milestone has exceeded its time threshold: 7 days for RAW_MATERIALS and PRODUCTION_STARTED, 3 days for QC_PASSED and READY_FOR_SHIPMENT. SHIPPED is never overdue. Surfaced on the dashboard and on the PO detail Production Status timeline. | Production |
| Milestone Overdue Threshold | Per-milestone day count after which the latest posted milestone is considered overdue. Single-sourced in `backend/src/domain/milestone.py` as `MILESTONE_OVERDUE_THRESHOLDS`. Imported by dashboard and milestone routers. | Production |
| Is Overdue | Boolean field on `MilestoneResponse`. True only for the latest posted milestone when `(now - posted_at).days > threshold`. Earlier milestones in the response always carry False. | Production |
| Days Overdue | Integer field on `MilestoneResponse`. None for SHIPPED (terminal); negative when within threshold; positive when overdue. Returned alongside `is_overdue` per row. | Production |

## Activity and Notifications

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Activity Log Entry | A recorded domain event: PO or invoice status change, milestone post, or overdue detection. Stores entity reference, event type, notification category, target role, optional detail text, and read/unread state. Append-only. | Notifications |
| Notification Category | Classification of an activity log entry: LIVE (something happened), ACTION_REQUIRED (someone needs to act), DELAYED (entity is overdue). Drives UI presentation and future role-based routing. | Notifications |
| Target Role | The intended audience for a notification: SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER, PROCUREMENT_MANAGER, or ADMIN. Nullable (None = broadcast to all roles). Stored per activity_log row; used by list_recent and unread_count to filter each role's feed. | Notifications |
| TargetRole.ADMIN | TargetRole enum value added in iter 107. Activity rows with this value appear only in ADMIN notification feeds. All six USER_* lifecycle events carry this target. Non-ADMIN roles filter by their own role value and do not see ADMIN-targeted rows. | Notifications |
| ADMIN Fan-out | Dispatcher pattern that resolves all ACTIVE ADMIN users' emails via a single SQL query (list_active_emails_by_roles(("ADMIN",))) when a TargetRole.ADMIN event is dispatched. No per-user iteration. | Notifications |
| System-Level Event | An ActivityEvent that targets ADMIN rather than an operational role. These events concern the user roster (invites, credential resets, deactivations) rather than business documents (POs, invoices, shipments). In EVENT_METADATA: target_role=TargetRole.ADMIN, category=LIVE. | Notifications |
| Milestone Overdue | A DELAYED activity entry generated when a production milestone exceeds its time threshold. One entry per PO per milestone, idempotent. Generated on dashboard load using existing overdue thresholds. | Notifications |
| Event Metadata | Static mapping from each ActivityEvent to its NotificationCategory and TargetRole. Determines how events are categorized and routed. | Notifications |
| PO_DOCUMENT_UPLOADED | LIVE-category activity event recorded on every PO document attachment. EVENT_METADATA target_role is `None`; the router supplies a per-call override (SM for PROCUREMENT, FREIGHT_MANAGER for OPEX) per the iter 056 `_counterpart_target` pattern. No corresponding DELETED event. | Activity |

## Access Control

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Vendor-Scoped Access | Query-level filtering that restricts VENDOR users to data belonging to their vendor. Applied to PO lists/details, invoices, milestones, activity, and dashboard. Non-VENDOR roles pass through unfiltered. Uses 404 (not 403) on ownership mismatch to avoid leaking entity existence. | Auth |
| InviteToken | Per-PENDING-user UUID v4 secret stored on `users.invite_token`. Generated by `User.invite()` (and bootstrap), returned only in the invite/bootstrap response, consumed by the registration handshake (`register/options` and `register/verify`), and cleared by `User.activate()`. Consume-once. Never appears in `_user_to_dict`. Replaces username as the registration-link key. (iter 096) | Auth |
| ResetCredentials | User-aggregate operation flipping ACTIVE or INACTIVE status to PENDING and allocating a fresh `invite_token`. Webauthn credential rows are deleted by the repository (separate aggregate) — the User aggregate only owns the status and token mutation. Rejects PENDING (use ReissueInvite instead). Carries the same last-active-admin guard as Deactivate at the router. (iter 098) | Auth |
| ReissueInvite | User-aggregate operation that rotates `invite_token` on a PENDING user without touching credentials or status. Used when an invite link is lost before consumption. Rejects ACTIVE and INACTIVE (use ResetCredentials instead). (iter 098) | Auth |

## Document Storage

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| FileMetadata | Metadata record for an uploaded file: entity association (type + id), file classification (file_type), storage path, original name, content type, size, uploaded_by (since iter 084). Not the file itself. Aggregate root of the document storage module. | Documents |
| Entity Attachment | The pattern of associating a file to a domain entity via (entity_type, entity_id). Free-text entity_type avoids schema changes as new attachment targets are added. | Documents |
| POAttachmentType | Enum partitioning the `file_type` vocabulary by PO type. PROCUREMENT POs accept `SIGNED_PO`, `COUNTERSIGNED_PO`, `AMENDMENT`, `ADDENDUM`; OPEX POs accept `SIGNED_AGREEMENT`, `AMENDMENT`, `ADDENDUM`. `validate_attachment_type` is the single source of truth. | Documents |
| PO Attachment | A FileMetadata row with `entity_type='PO'`. Subject to PO-specific role + ownership + PO-type checks layered above the iter 035 generic file storage via the `/api/v1/po/{po_id}/documents/...` scoped endpoints. | Procurement |
| Attachment Vocabulary Partition | Pattern of constraining the allowed `file_type` set per parent-entity classification (here, PO type). Domain layer carries the partition (`PROCUREMENT_ATTACHMENT_TYPES` / `OPEX_ATTACHMENT_TYPES` frozensets); router rejects mismatches with 422. | Documents |
| Marketplace | Target sales channel for a PO: AMZ, 3PL_1, 3PL_2, 3PL_3. Validated against reference data. Optional (nullable). Determines packaging and certification requirements downstream. | Procurement |
| Manufacturing Address | Physical location where a product is manufactured. Stored on Product. Used by certificates of origin and compliance documents. | Procurement |
| Vendor Account Details | Bank/payment information for a vendor. Free-text. Used by shipping and export documents. | Procurement |

## Qualifications and Compliance

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| QualificationType | Named qualification requirement (e.g. QUALITY_CERTIFICATE) with target market scope. Products link to qualification types via join table. Created by SM; defines what certifications a product must have. | Quality |
| Certificate | Evidence that a product meets a qualification type's requirements. Tracks cert_number, issuer, testing_lab, test_date, issue_date, expiry_date, target_market. Status: PENDING → VALID → APPROVED. EXPIRED is computed from expiry_date on read via display_status(), not persisted. Document attached via file storage. | Quality |
| CertificateApproved | Status value and event marking FREIGHT_MANAGER explicit sign-off on a VALID certificate. Transitions VALID → APPROVED via Certificate.approve(); raises ValueError from any other source state. Emits CERT_APPROVED activity (LIVE, target_role SM). Only APPROVED certificates satisfy the shipment readiness certificates check. | Quality |
| PackagingSpec | Per-product per-marketplace packaging file requirement. Status: PENDING → COLLECTED (on file upload). Document attached via file storage. Unique on (product_id, marketplace, spec_name). Delete is blocked when status is COLLECTED. | Packaging |
| PackagingReadiness | Read model: per-product per-marketplace report of total vs collected packaging specs. is_ready requires total_specs > 0 and all specs collected. Returned by GET /api/v1/products/{id}/packaging-readiness?marketplace=X. | Packaging |
| LineItemStatus | Per-line acceptance state on a PO: PENDING, ACCEPTED, REJECTED. Set during partial PO acceptance. Stored on each LineItem; the PO-level accept/reject decision can be broken down per line via accept_lines(). | Procurement |

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
| Pending | PO submitted to vendor, awaiting first response. |
| Modified | At least one line has been modified by vendor or SM; awaiting counterparty response or further hand-off. |
| Accepted | Convergence reached with at least one line ACCEPTED. Unlocks invoicing for Procurement and OPEX POs. Terminal. |
| Rejected | Convergence reached with every line REMOVED. Reachable only via the negotiation loop, not via an explicit reject action. |
| Revised | Previously rejected PO updated and resubmitted, awaiting vendor action. |

### Status Transitions

| From | To | Trigger |
|------|----|---------|
| Draft | Pending | PO submitted to vendor |
| Pending | Modified | Either party issues modify_line or accept_line + submit_response with unresolved lines remaining |
| Pending | Accepted | All lines accepted in round 0 via submit_response |
| Modified | Modified | Counterparty submit_response with unresolved lines; round_count increments (cap 2) |
| Modified | Accepted | Every line ACCEPTED or REMOVED with at least one ACCEPTED at submit_response |
| Modified | Rejected | Every line REMOVED at submit_response (convergence without any accepted line) |
| Rejected | Revised | Creator updates PO fields |
| Revised | Pending | Revised PO resubmitted to vendor |

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Pending : Submit to vendor
    Pending --> Accepted : All lines accepted (round 0)
    Pending --> Modified : Any modify_line submitted
    Modified --> Modified : Counter-propose (round_count <= 2)
    Modified --> Accepted : Convergence with any ACCEPTED line
    Modified --> Rejected : Convergence with all REMOVED
    Rejected --> Revised : Creator updates fields
    Revised --> Pending : Resubmitted to vendor
    Accepted --> [*]
```

## Line Negotiation

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Negotiation Round | One complete hand-off between vendor and SM. PO-scoped, 0-indexed, capped at 2. Counter lives on `PurchaseOrder.round_count`. | Procurement |
| Line Item Modification | A single per-field edit captured in `line_edit_history`. Holds round, actor_role, field, old_value, new_value, edited_at. | Procurement |
| Line Edit History | Ordered list of Line Item Modifications attached to a PO. Persisted as a child table keyed by `(po_id, line_item_id, round)`. Append-only. | Procurement |
| Hand-Off | The state change where the negotiating side flips between SM and vendor. Fires via `submit_response`, increments `round_count`, flips `last_actor_role`. | Procurement |
| Force Override | SM-only terminal action reaching ACCEPTED or REMOVED unilaterally via `force_accept_line` or `force_remove_line`. Permitted only at `round_count == 2`. | Procurement |
| Convergence | State where every line on a PO is ACCEPTED or REMOVED. Triggers PO transition to ACCEPTED (at least one ACCEPTED) or REJECTED (all REMOVED). | Procurement |
| Editable Line Fields | Whitelisted set a party may modify via `modify_line`: quantity, unit_price, uom, description, hs_code, country_of_origin, required_delivery_date. `part_number` is immutable. | Procurement |
| Line Item Status | PENDING, MODIFIED_BY_VENDOR, MODIFIED_BY_SM, ACCEPTED, or REMOVED. REJECTED removed in iter 056; REMOVED now represents a line dropped from the PO. | Procurement |

## Advance Payment and Post-Acceptance Modification

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Advance Payment | A payment term component where a portion or all of PO value is collected before production starts. Derived from `payment_terms.has_advance`; not a separate entity. Recorded paid via `advance_paid_at` timestamp on the PO. | Procurement |
| Payment Term Metadata | Reference data per payment term code carrying behavior flags (currently `has_advance: bool`). Extensible; additional flags can be added without schema changes. | Procurement |
| Post-Acceptance Gate | Window during which an SM may add or remove lines on an ACCEPTED PO. Closes when the first milestone is posted OR when the advance is marked paid (for advance-required terms). Whichever fires first closes the window. | Procurement |
| Downstream Artifact | An invoice line or shipment line that references a PO line item. Presence blocks post-acceptance line removal via `remove_line_post_acceptance`. | Procurement |

## Shipments

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| DocumentRequirementStatus | Status of a single shipment document requirement: PENDING (file not yet received) or COLLECTED (file received and stored). | Shipment |
| ShipmentDocumentRequirement | Per-shipment document checklist entry. Carries `document_type`, `is_auto_generated` flag, and optional `document_id`. Status PENDING → COLLECTED on file upload. Auto-generated rows (PACKING_LIST, COMMERCIAL_INVOICE) are seeded on submit-for-documents and always pass the readiness gate; user-defined rows require a VENDOR upload. Child of Shipment. | Shipment |
| ReadinessResult | Composite readiness snapshot for a shipment: `documents_ready`, `certificates_ready`, `packaging_ready` booleans plus structured missing-item lists (`missing_documents: string[]`, `missing_certificates: [{product_id, qualification_type}]`, `missing_packaging: [{product_id, marketplace}]`), and a derived `is_ready` boolean. Returned by `GET /shipments/{id}/readiness`; also carried by a 409 from `mark-ready` when not ready. | Shipment |
| Auto-generated Requirement | A `ShipmentDocumentRequirement` with `is_auto_generated = true`. Seeded automatically on submit-for-documents for PACKING_LIST and COMMERCIAL_INVOICE. Always passes the documents readiness check; the PDFs are generated on demand from PO + shipment data. UI renders these rows read-only with no upload affordance for any role. | Shipment |
| MarkReadyNotReadyError | Client-side typed error (extends `Error`) thrown by `markShipmentReady` when the backend returns 409 with a `ReadinessResult` payload. Carries the parsed result so the page can re-render the readiness panel from the server's view and surface an inline action-rail message without a separate fetch. | Shipment |
| Mark Ready (as FM approval) | The `POST /shipments/{id}/mark-ready` transition (DOCUMENTS_PENDING → READY_TO_SHIP) is FREIGHT_MANAGER's implicit approval action over the uploaded document set. Gated by `ReadinessResult.is_ready`; a failing readiness check returns 409 with the structured `ReadinessResult`. FM reviews what VENDOR uploaded and clicks Mark Ready — FM does not upload documents. SM has the same capability as an ops override. | Shipment |
| Manufacturer Block | The manufacturer's name, address, and country rendered on the Packing List as "Shipper / Manufacturer" and on the Commercial Invoice as "Seller". Sourced from `products.manufacturer_name/address/country` when populated (iter 106); falls back to vendor data when not set. A distinct Manufacturer entity with its own UUID is deferred. | Shipment |
| Shipper's Declaration | Text block appended to the Commercial Invoice: "I declare that the information on this invoice is true and correct." Standard customs declaration. Rendered with signatory name, title, and declared_at date (iter 106); falls back to "[unsigned]" / "[undated]" when not yet declared. | Shipment |
| Signatory | The named individual who signs the shipper's declaration on the Commercial Invoice. Captured on the Shipment via `POST /shipments/{id}/declare`. Stored as `signatory_name` (required) and `signatory_title` (required) on the `shipments` table. | Shipment |
| Declared At | The UTC timestamp when the customs declaration was recorded (`declare()` method on Shipment). Set server-side on `POST /shipments/{id}/declare`. ISO-8601 string in the API response. | Shipment |
| Vessel | The ocean carrier vessel name (e.g. "MSC GULSUN"). Stored as `vessel_name TEXT` on `shipments`. Set via `PATCH /shipments/{id}/transport` after booking. Rendered in the Packing List header when present. | Shipment |
| Voyage | The vessel voyage number assigned by the carrier (e.g. "031W"). Stored as `voyage_number TEXT` on `shipments`. Set alongside vessel via `PATCH /shipments/{id}/transport`. Rendered in the Packing List header when present. | Shipment |
| Port of Loading | The origin port where goods are loaded, sourced from `purchase_orders.port_of_loading`. Resolved to a city, country label in PL and CI headers using `port_label()` from `reference_labels.py`. | Trade |
| Port of Discharge | The destination port where goods are unloaded, sourced from `purchase_orders.port_of_discharge`. Resolved to a city, country label in PL and CI headers. | Trade |
| Origin Country (PDF) | Country of origin resolved to a human-readable country name from `purchase_orders.country_of_origin` and surfaced in the PL header. Distinct from the per-line `country_of_origin` on `ShipmentLineItem` (the actual production origin per line, settable via PATCH). | Trade |
| HS Code per Line (PL) | The Harmonized System tariff code printed in the Packing List line items table, sourced from ACCEPTED PO line items keyed by `part_number`. Packing List previously showed no HS column; CI already had the column from iter 045. | Trade |
| Booking | The act of registering a shipment with a carrier. Captured via `POST /shipments/{id}/book` (READY_TO_SHIP → BOOKED). Requires `carrier`, `booking_reference`, and `pickup_date`. SM and FM are the acting roles. Booking metadata is persisted on the Shipment aggregate. | Shipment |
| Carrier | The logistics company responsible for moving the shipment (e.g. Maersk, MSC). Stored as a free-text string on the Shipment after booking. | Shipment |
| Booking Reference | The carrier-assigned reference number for the booked shipment slot (e.g. MAEU1234567). Non-empty, stored on Shipment after booking. | Shipment |
| Pickup Date | The scheduled date on which the carrier collects the cargo. ISO date string; stored as `pickup_date` on Shipment after booking. | Shipment |
| Mark Shipped | The `POST /shipments/{id}/ship` transition (BOOKED → SHIPPED). Records `shipped_at` timestamp on the Shipment. SM and FM are the acting roles. No request body. | Shipment |
| ShipmentBookingPayload | Client-side DTO for the book transition: `{ carrier: string, booking_reference: string, pickup_date: string }`. Mirrors the backend `ShipmentBookRequest`. carrier and booking_reference are validated non-empty/whitespace-only client-side before the POST. | Shipment |
| ShipmentTransportPayload | Client-side DTO for PATCH /transport: `{ vessel_name: string | null, voyage_number: string | null }`. Both fields nullable; passing null clears a previously set value. Non-null values must not be whitespace-only. | Shipment |
| ShipmentDeclarePayload | Client-side DTO for POST /declare: `{ signatory_name: string, signatory_title: string }`. Both fields required and validated non-empty/whitespace-only before send. | Shipment |

## Brand

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Brand | The buyer-principal aggregate on whose behalf an operator runs procurement, invoicing, and shipment. Carries `legal_name`, `address`, `country` (validated against reference data), and `tax_id`. Vendor↔Brand many-to-many via `brand_vendors`. Every PO carries `brand_id` (required at the Pydantic create body, immutable on update). | Procurement |
| Brand Status | ACTIVE or INACTIVE. ACTIVE brands accept new POs; INACTIVE brands reject new POs. Deactivate is blocked when any non-terminal PO references the brand. Symmetric guards mirror `VendorStatus`. | Procurement |
| Default Brand | A single brand seeded by `init_db` carrying `legal_name="Default Brand — please update"` so existing rows can be backfilled in the absence of a migration tool. ADMIN edits the placeholder fields on first login. | Procurement |
| Brand Vendor Assignment | The m2m relationship in `brand_vendors`. A vendor can serve multiple brands; a brand can use multiple vendors. PO create asserts the chosen `vendor_id` is assigned to the chosen `brand_id`; assignment is idempotent on conflict. Unassign is blocked when any non-terminal PO references the pair. | Procurement |
| Brand Importer-of-Record Model | The decision in iter 108 that Brand IS the importer of record on customs documents. `Brand.tax_id` is what appears on the CI Seller-side declaration. An operator-as-IOR singleton is deferred and added separately if a future workflow needs the operator to take title. | Trade |
| Brand Buyer Block | The buyer / consignee identity block rendered on the auto-generated Packing List and Commercial Invoice. Sourced from `po.brand.legal_name`, `po.brand.address`, and `po.brand.country`. The CI additionally renders a `Tax ID:` line from `po.brand.tax_id` when non-empty. Replaces the hardcoded operator constants in the PDF generators. | Trade |
| Vendor-Belongs-To-Brand Validation | The PO-create check that `brand_repo.is_vendor_assigned_to_brand(brand_id, vendor_id)` returns true. 422 with message naming the brand on mismatch. Mirrors the existing field-immutability and reference-data validation patterns. | Procurement |
| BRAND_CREATED / BRAND_UPDATED / BRAND_DEACTIVATED / BRAND_REACTIVATED / BRAND_VENDOR_ASSIGNED / BRAND_VENDOR_UNASSIGNED | Six brand-lifecycle ActivityEvents. All carry `(NotificationCategory.LIVE, TargetRole.ADMIN)` so rows surface only in ADMIN feeds. Vendor-assignment events use `entity_type=BRAND`, `entity_id=brand_id`, with `metadata={"vendor_id": <id>}`. | Notifications |
| EntityType.BRAND | New `EntityType` enum value. Tags `activity_log` rows scoped to a brand aggregate. | Notifications |
