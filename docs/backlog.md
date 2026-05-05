# Backlog

## PO Confirmation module

- [ ] Auth and sessions (WebAuthn/passkeys + cookie sessions)
- [ ] Roles: SM vs Vendor views (same data, different controls)
- [ ] Overdue status (time-based trigger past required delivery date)
- [x] In-app notifications / activity feed (iterations 23-24: activity log, dashboard feed, notification bell, detail timelines)
- [ ] Mobile layout
- [ ] Custom value approval for reference data dropdowns
- [ ] Dedicated `/api/v1/po/ids` endpoint (cross-page selection beyond 200)
- [ ] Live/historical exchange rates for dashboard
- [ ] Field-level mutability rules tied to lifecycle status
- [x] Buyer as first-class entity (resolved iter 108: Brand aggregate; backend-only — frontend follows in iter 109)
- [ ] Partial PO acceptance (accept/reject at line-item level)
- [x] Notifications (in-app alerts for status changes, assignments, deadlines) (iterations 23-24)
- [ ] Shipping country missing on PO create form (no field for destination country distinct from buyer/vendor country)
- [ ] Part number dropdown scoped by PO type: filter line-item product/part picker on PO create by selected PO type (Procurement / OPEX / Freight / Misc)
- [ ] Currency field missing on PO create form (currency is implicit/inherited; needs an explicit field at create time)
- [ ] Trade Details country-of-origin must match line-item country-of-origin: validate at submit and reject mismatches between PO-level Trade Details country-of-origin and per-line `country_of_origin`
- [ ] Payment cannot be initiated on an invoice until parent PO is confirmed (ACCEPTED): guard pay-invoice action against parent PO status
- [ ] Milestone timeline as top-of-page ruler/slider on `/po/[id]`: render 5-stage production milestone sequence as a horizontal ruler with target dates, surfaced at the top of PO detail for vendor + SM
- [ ] PROCUREMENT_MANAGER milestone ruler: same 5-stage ruler aggregated across PM's PO portfolio — each marker shows roll-up value (count or summed PO value at that stage)
- [ ] PO PDF should not display "Modified" label/watermark: remove the "Modified" text from the generated PO PDF export
- [ ] Rename the "post milestone" verb across the codebase: "POST" is HTTP-layer vocabulary leaking into the domain. Pick a DDD-aligned verb (candidates: `Report` — vendor reports stage completion; `Record`; `Advance`; `Achieve`) and rename `canPostMilestone`, `POST_MILESTONE` event type, domain methods, route handlers, frontend copy, and ddd-vocab.md in one iteration
- [ ] `/po/[id]` density pass: page scrolls too much for the information shown. Compact the layout — tighter panel padding, denser AttributeList rows, two-column metadata on desktop, collapse low-signal panels by default — so above-the-fold carries header + status + line items + primary actions on a typical desktop viewport
- [ ] Stamp + watermark on PO and invoice PDFs: render a status-derived stamp (e.g. ACCEPTED / REJECTED / PAID / DISPUTED) and a faint background watermark (buyer name or "ORIGINAL" / "DUPLICATE") on both `PODocumentExport` and `InvoiceDocumentExport` outputs. Stamp text + colour map per status; watermark is diagonal, low-opacity, repeated across the page
- [ ] QUALITY_LAB needs a "certificate-required products" view: today Quality Lab lands on the generic `/products` list with no certificate-required scoping or status surface. Build an internal page (e.g. `/products?requires_cert=true` filter or a dedicated `/quality-lab/certificates` route) that lists products with `requires_certification=true`, surfaces qualification status (PENDING / VALID / EXPIRED), and lets QL act on PENDING → VALID approval (folds into the iter 040 cert metadata edit + approve workflow already in "Phase 4 UI revamp")
- [ ] Vendor identifier in UI should always render as vendor name, never the raw UUID `vendor_id`: audit every surface (filter dropdowns, table rows, detail panels, activity feed entries, PDF exports) for places that print the UUID. Backend list/detail endpoints should join the vendor name into the response, or the frontend should resolve via the cached vendor list before rendering

## Post-confirmation modules

- [ ] Production status tracking (enabled once PO is Accepted)
- [x] Invoicing (iterations 12, 16, 21, 22)

## Cosmetic / Data Quality

- [x] Vendor country should be a dropdown from reference data (iteration 20)
- [x] HS code format validation (iteration 20)

## Auth and user management

- [ ] Multiple passkeys per user (register backup device for recovery)
- [ ] VENDOR user's vendor gets deactivated: make vendor-scoped data read-only
- [ ] Stale PENDING user cleanup (invited but never registered)
- [ ] Proxy access for internal leave coverage (delegation table, time-bounded, audit trail)
- [ ] Email/notification for invite links (manual link sharing works for small teams)
- [ ] PROCUREMENT_MANAGER role permissions: enum value exists from iter 030, no endpoint guards wired. Define and wire access (read-only PO/vendor/invoice visibility, pay/dispute invoices). Frontend: define redirect behavior for PM on non-dashboard pages.
- [ ] User management for PROCUREMENT_MANAGER: extend the iter 100 `/users` page so PM can manage users (likely scoped — invite/deactivate VENDOR users they own, or full parity with ADMIN). Decide scope, wire `canManageUsers(role)` to include PM, gate the user-lifecycle endpoints, expose Users in the PM sidebar
- [ ] PROCUREMENT_MANAGER dashboard fixes: iter 075 gave PM the SM dashboard payload but activity feed is near-empty (events default-route to SM target_role; PM never receives them — fan-out fix open). Audit other PM dashboard surfaces (KPIs, panels) for correctness against PM's actual scope vs. the SM-derived data they currently see (iter 114 spec)
- [ ] Welcome email on invite: send registration link via email when admin invites a user. Currently manual link sharing.
- [ ] ADMIN inherits all actions: `canPostMilestone` is exact-match VENDOR only. ADMIN should exercise any role-scoped action (post milestones, submit vendor responses, etc.) for support and debugging. Audit every `isExact` usage in `permissions.ts` and backend role guards; convert to `is(role, ...) || role === 'ADMIN'` unless there is a concrete reason to keep a capability VENDOR-only.

## UX

- [ ] Error handling across all users and workflows: define and surface user-facing error states for every endpoint (validation errors, conflict errors, not-found, auth failures). Currently errors are ad hoc per endpoint with no consistent frontend treatment.
- [ ] Recent activity redesign: club PO and invoice activity into a unified feed (currently separate activity streams). Needs discussion on grouping, filtering, and presentation.
- [ ] Deep link preservation on register/bootstrap: `/login` is done (iter 033). If an invited user opens a deep link (e.g. `/po/123`) and lands on `/register` or `/setup`, the original path is still lost. After registration/bootstrap they go to `/dashboard`, not the deep link. Low priority since registration is a one-time event.
- [ ] Session cookie path/domain audit: verify the session cookie is set with `path=/` and appropriate domain/SameSite attributes for production deployment behind a reverse proxy. Currently works in dev via Vite proxy.
- [ ] DataTable primitive extension: promote selection column + snippet cell support out of `PoListTable` and `PoInvoicesPanel` into the shared `frontend/src/lib/ui/DataTable.svelte` primitive, so other list pages can adopt the same selection contract without copy-paste. Phase 4.x cleanup task.
- [ ] PO document versioning: re-uploading a SIGNED_PO does not supersede the prior row — both rows persist, ordered by `uploaded_at DESC`. Cleanup is manual delete. Revisit when users complain about clutter or audit-trail confusion.
- [ ] PO_DOCUMENT_DELETED activity event: iter 084 records uploads only, matching the iter 046 shipment-document-upload precedent. Add a delete event when anyone needs deletion history.
- [ ] Email template for PO_DOCUMENT_UPLOADED: iter 084 records the activity row but does not invoke `NotificationDispatcher`. Wire SMTP fan-out (likely to SM for PROCUREMENT, FM for OPEX, mirroring the per-call target_role) when the workflow needs out-of-app notification.
- [ ] Shared mock-fetch helper for `/ui-demo/*` gallery: iter 084's `/ui-demo/po-documents` patches `globalThis.fetch` for upload/delete demo flows and restores on cleanup. Centralizing this would let future demo routes drop the boilerplate.
- [ ] Backend per-entity activity pagination: `/api/v1/activity/?entity_type=PO&entity_id={id}` returns the full list. Iter 083's `PoActivityPanel` does client-side "Show more" over a single fetch. Revisit when a single PO accumulates >100 events.
- [ ] FREIGHT_MANAGER PO detail visibility: `canViewPOs` includes FREIGHT_MANAGER for the iter 073 ready-batch click-through (FM lands on a PO detail to plan shipping). FM sees an action rail with Download PDF only. Revisit whether FM should see PO detail at all or whether the ready-batch surface should expose only shipping-relevant fields directly. Tier 0 G-28 (role coverage matrix) territory.
- [ ] Rounded corners across all pages (no sharp edges): bump `--radius-*` design tokens and audit every primitive (`PanelCard`, `KpiCard`, `FormCard`, `DataTable`, `StatusPill`, `Button`, `Input`, `Select`, modals, dialogs, sidebar items) to consume them. Goal: tile-like UI with consistent corner radius site-wide

### Per-role dashboard implementation (iter 114 spec)

- [ ] PM dashboard split from SM grid: cross-vendor 5-KPI grid (pending POs, in-production, quality pending, pending-for-shipment, outstanding A/P) + production stage breakdown panel + overdue milestones panel (iter 114 spec).
- [ ] SM dashboard with vendor selector: vendor-scoped subset of PM KPIs, stage breakdown capped at READY_FOR_SHIPMENT, sticky vendor choice in user prefs (iter 114 spec).
- [ ] QL dashboard: cert-request queue KPI, certs expiring within 30 days, certs expired, POs at QC_PASSED awaiting cert panel (iter 114 spec).
- [ ] FM dashboard extension: five-stage shipment lifecycle KPIs, CUSTOMS_PENDING and DELIVERED tiles as placeholders until those modules land (iter 114 spec).
- [ ] ADMIN dashboard split from SM grid: union-view KPIs (system-wide POs, shipments, A/P) + estate health KPIs (pending invites, inactive brands/vendors with active POs) + ShipmentStatusSummary panel (iter 114 spec).
- [ ] VENDOR dashboard: POs awaiting response + drafts-to-invoice + disputed invoices + tasks-open KPIs, action-queue panel (Panel A) as primary affordance, vendor-scoped activity feed (iter 114 spec).

### Backend gaps for dashboard iters (iter 114 spec, in dependency order)

- [ ] PM/SM event fan-out: decide which existing events route to PROCUREMENT_MANAGER and SM in EVENT_METADATA so their activity feeds are non-empty (iter 114 spec, gap 1).
- [ ] ShipmentStatusSummary aggregate query: mirrors po_summary_by_status shape, drives ADMIN Panel B and FM KPIs 1-3 (iter 114 spec, gap 2).
- [ ] Milestone-to-shipment join query for "READY_FOR_SHIPMENT POs with no or staged shipment", parameterised by vendor_id (None for PM/ADMIN, set for SM) (iter 114 spec, gap 3).
- [ ] Cert-pending aggregate: joins purchase_orders (latest milestone = QC_PASSED) x line items x products x qualifications x certificates to drive QL KPI 1 and Panel A (iter 114 spec, gap 4).
- [ ] Certificate expiry queries: SQL expressions for "expiring within N days" and derived EXPIRED count, needed for QL KPI 3 and KPI 4 (iter 114 spec, gap 5).
- [ ] CERT_UPLOADED event fan-out to FREIGHT_MANAGER so the FM cert-approval queue panel matches the inbox (iter 114 spec, gap 6).
- [ ] Inactive-but-referenced drift scan: post-hoc query for deactivated brands/vendors with open POs, drives ADMIN KPI 5 (iter 114 spec, gap 7).
- [ ] Vendor-scoped /dashboard/summary endpoint branch: SM iter must add vendor_id parameter to the existing role-branched endpoint (iter 114 spec, gap 8).

## Infrastructure

- [ ] File endpoint role guards: restrict upload/download/delete by role and entity ownership on the generic `/api/v1/files/...` surface. Currently any authenticated user can access any file there. Iter 084 tightened the PO surface only via PO-scoped endpoints at `/api/v1/po/{po_id}/documents/...`; the certificate (iter 038) / packaging (iter 042) / shipment (iter 046) consumers still hit the open generic endpoint. Either define per-entity-type guards inside the generic router or migrate each consumer to its own scoped router (the iter 084 pattern).
- [ ] File upload entity existence validation: upload endpoint accepts any entity_type/entity_id without checking the entity exists. Decide per-feature whether to validate at upload time or at the consuming feature level.
- [ ] Vendor catalog / vendor-SKU mapping: products are vendor-agnostic, but a vendor's catalog defines which SKUs they offer. Line item `product_id` should reference a SKU in the vendor's catalog. New entity needed.
- [ ] HTTPS for non-localhost deployment (WebAuthn requires HTTPS or localhost; needed before first external demo)
- [ ] Database migration tool (alembic or similar; needed once real data exists that can't be dropped and recreated)
- [ ] Session revocation ("log out all devices"; currently relies on cookie expiry + user status check)
- [ ] Self-service vendor onboarding (currently invite-only; needed if vendors should sign up without admin)
- [ ] Remove dev-login endpoint before production deployment

## Deferred

- [ ] Compliance fields (LC, export license, packing list, bill of lading)
- [ ] Roles and permissions (beyond SM/Vendor split)
- [ ] Email notifications
- [ ] SM internal notes
- [ ] Shipment DELIVERED state: confirmation source TBD (manual FM mark, carrier webhook, or POD upload); definition affects FM KPI 5 query shape (iter 114 spec).
- [ ] Shipment CUSTOMS_* state(s): interim or parallel-gate semantics TBD; definition affects FM KPI 4 and state-machine shape (iter 114 spec).
- [ ] ADMIN "view as role" impersonation toggle: lets ADMIN exercise any role-scoped dashboard view; affects auth shape (audit trail, impersonation model) (iter 114 spec).
- [ ] Per-user dashboard widget reordering and customisation (iter 114 spec).
- [ ] Real-time push for dashboard KPIs and panels (iter 114 spec).

## Phase 4.2 close-out (deferred, not blocking Phase 4.3)

- [ ] G-28 role-conditional rendering coverage matrix on `/po/*`. Today gating is scattered across page-level `{#if}`, `PoActionRail` internal action-list computation, and panel internals (`PoDocumentsPanel` calls `canViewPOAttachments(user, po)`, `PoAdvancePaymentPanel` calls `canMarkAdvancePaid`, etc.). Audit confirmed P2/P3/P4/P5 already aligned; only P1 (declarative `ROLE_MATRIX` const at the top of each `/po/*` page + a single 6-role × 4-page Playwright spec) is open. Risk if skipped: a future iter adds a new mutation surface, forgets a gate, ships a button that 403s on click. Source: [tools/phase-4-research/phase-4.2-mock-clarity-inventory.md L664](tools/phase-4-research/phase-4.2-mock-clarity-inventory.md). Pre-iter audit notes captured in iter 086 draft (deleted).
- [ ] G-29 99-spec Playwright migration plan for `/po/*`. Adds shared `frontend/tests/fixtures/po.ts` `buildPOFixture` + `buildUser` helpers, new `po-list-bulk.spec.ts` (SM × {DRAFT, REVISED} submit + VENDOR × PENDING accept/reject + empty Valid Actions), new `po-list-row-click.spec.ts`, migrates remaining ~99 specs to new DOM. The fixture refactor naturally absorbs the 13 svelte-check `vendor_id: null` literal-narrowing errors carried since iter 085. Source: [tools/phase-4-research/phase-4.2-mock-clarity-inventory.md L688](tools/phase-4-research/phase-4.2-mock-clarity-inventory.md).

## Type-hardening (deferred from iter 085)

- [ ] 29 svelte-check errors carried since iter 085 close. Splits: 13 in test fixtures (`tests/po-detail.spec.ts`, `po-documents.spec.ts`, `po-negotiation.spec.ts`, `nexus-dashboard.spec.ts`) — same root cause `typeof SM_USER` narrows literal `vendor_id: null` (folds into G-29). 2 in `(nexus)/po/[id]/+page.svelte:330,432` — same `let po: T \| null = $state(null)` narrowing pattern fixed on the edit page in iter 085 (fix: `let po = $state<PurchaseOrder \| null>(null)`). 6 in `(nexus)/dashboard/+page.svelte` — `summary` possibly null. 2 in `routes/shipments/[id]/+page.svelte:53` — same `$state(null)` narrowing. 1 in `routes/products/+page.svelte:78` — orphaned `requires_certification` from iter 036a. 4 in `tests/po-documents.spec.ts` — `Buffer` not found, missing `@types/node`. 1 in `tests/po-lifecycle.spec.ts:545` — null → Record cast (incorrectly noted as fixed in iter 085 summary).

## Multi-brand / multi-entity foundation

Surfaced 2026-05-02 during iter 108 brainstorming. Recorded so future iters do not re-derive them.

- [x] **Brand entity** (the missing buyer principal). Backend done in iter 108 (closed 2026-05-03; see `work-log/2026-05-02/iteration-108.md`). Frontend `/brands` admin pages + PO create-form `BrandSelect` cascade pending in iter 109.
- [ ] **Brand-scoped marketplace accounts**: today marketplace is a PO enum (AMZ, 3PL_1, ...). For multi-brand operators, Brand A's AMZ seller account is not Brand B's. Folds in the parked FBA-specific fields (FBA Shipment ID, FNSKU, ASIN, fulfilment-centre code). Becomes blocking when a second brand uses the same marketplace with a different account.
- [ ] **Brand-scoped user access**: parallels VENDOR-scoping. Brand A's ops manager sees only Brand A's POs / invoices / shipments. ADMIN/SM at the operator level remain unscoped. Blocks first hire of brand-specific ops staff.
- [ ] **VendorParty (multi-entity vendor)**: today `Vendor` is a single flat row. Trade reality has up to four legal/physical parties under one vendor relationship: Manufacturer (CoO + per-line manufacturer block), Seller (CI Seller + tax_id + payment recipient), Shipper (PL Shipper + BoL Consignor), Remit-to (banking destination). Polymorphic `VendorParty` row with `role` enum, plus per-product / per-shipment / per-PO override fields. Closes the customs-doc identity gap on the seller side. Becomes blocking on first vendor with split factory + billing entity.

## Invoicing depth

Surfaced 2026-05-02. Not on prior backlog.

- [ ] **Vendor-uploaded invoice file**: replicate iter 084 PO-documents pattern on `Invoice` (`/api/v1/invoices/{id}/documents`, VENDOR upload, INVOICE_DOCUMENT_UPLOADED activity). Roadmap item 4. Builds the corpus the invoice-validation agent (roadmap item 5) will consume.
- [ ] **Payment record entity**: today PAID is a status flip with no payment date / method / reference / amount. No partial payments, no advance offsets, no AP aging foundation. `payments(invoice_id, date, method, reference, amount, fx_rate)` plus repointed Invoice status logic.
- [ ] **Invoice tax / VAT line items**: today line is `qty × unit_price`, flat. Multi-jurisdiction shipments will fail invoice-vs-customs reconciliation without tax fields on the line.
- [ ] **Brand-scoped invoice numbering** + **due-date computation from payment_terms** (today: global numbering; due-date not derived). Both small once Brand exists.

## Logistics depth

Surfaced 2026-05-02. Not on prior backlog.

- [ ] **Carrier as first-class entity**: today free-text `carrier` string on Shipment. Real model: Carrier with rate cards, contract numbers, account credentials. Prerequisite for tracking integration.
- [ ] **Mode of transport** (sea / air / road): today vessel/voyage assumes sea. Becomes blocking on first air shipment.
- [ ] **Customs broker as entity**: receives CHB invoices, signs declarations on behalf. Today not modeled.
- [ ] **Container number + equipment type + seal numbers**: customs requirement for FCL / LCL shipments.
- [ ] **Cut-off date / VGM (Verified Gross Mass)**: sea-shipping concept. Customs houses require VGM declaration before vessel cut-off.
- [ ] **Multi-leg routing / transhipment**: today single port_of_loading + port_of_discharge. Real shipments often go via a hub.
- [ ] **Booking confirmation document upload**: today only metadata captured. The carrier's booking confirmation PDF should attach to the shipment.
- [ ] **Pickup confirmation / driver / truck** for the SHIPPED transition. Today shipped_at timestamp only.

## Compliance depth

Surfaced 2026-05-02. Not on prior backlog.

- [ ] **Trade preference / FTA classification** (USMCA, EUR.1, GSP, etc.): duty-impacting; absent today. Required for preference-claim shipments.
- [ ] **Restricted-party / denied-parties screening**: vendor + brand + consignee screened against OFAC / EU / UK sanctions lists. Compliance requirement in many jurisdictions.
- [ ] **License / permit per HS code per destination**: dual-use, dangerous goods, country-specific permits. Not modeled.
- [ ] **BoL / CoO / Insurance Certificate / EEI as first-class typed documents** (vs today's free-form `document_type` strings). Roadmap item 2. Per-doc-type required-field validation hangs off this.
- [ ] **Brand-specific document-requirement matrix**: Brand A always requires CoO for shipments to certain destinations; Brand B does not. Folded into typed-docs work.

## Finance / analytics

Surfaced 2026-05-02. Not on prior backlog. Read-model layer; depends on payment record and customs paper being correct.

- [ ] **Landed cost** (vendor cost + freight + duty + insurance + brokerage). Read model over PO + Shipment + carrier invoices + CHB invoices.
- [ ] **Per-brand / per-PO / per-shipment profitability**.
- [ ] **FX gain / loss** between PO date and payment date. Requires FX snapshot pinned at PO acceptance.
- [ ] **AR aging / AP aging** views.
- [ ] **Approval chains by amount**: today actions are role-gated only. Scales with team size.

## Quality + production depth

Surfaced 2026-05-02. Not on prior backlog.

- [ ] **QC inspection record**: today QC_PASSED is a single milestone with no inspector identity, no pass/fail detail, no photos, no rework loop.
- [ ] **Rework / rejection loop on QC fail**: not modeled. Today QC_PASSED is mandatory to proceed.
- [ ] **Sample-approval gate before production starts**: not modeled.

## Procurement upstream (RFQ)

Surfaced 2026-05-02. The system today starts at PO. Upstream is offline.

- [ ] **RFQ aggregate**: brand, requested_by, response_deadline, status (sent / responded / awarded / lost). Multi-vendor invitation list.
- [ ] **Quote aggregate** (vendor's response): per-line price, lead time, validity period.
- [ ] **Quote comparison view** + **award flow** (creates PO from winning quote). Activity events: RFQ_SENT, QUOTE_RECEIVED, RFQ_AWARDED.

## Tracking (post-shipment)

Surfaced 2026-05-02. SHIPPED is currently terminal.

- [ ] **Tracking events model**: in-transit, port-arrival, customs-cleared, out-for-delivery, delivered.
- [ ] **Carrier API integration / EDI / AIS feed**: at least one carrier first.
- [ ] **ETA / ETD / ATA / ATD** + **demurrage / detention tracking**.
- [ ] **POD upload** + customs clearance status at destination.
- [ ] **Brand notification on arrival** + deep-link to carrier portal.
- [ ] **Final-invoice trigger off delivery**.

## Cross-cutting

- [ ] **Data-change audit on entity edits** (vendor address etc.). ActivityLog covers domain events; data changes have no old→new trail.
- [ ] **Operator legal entity** as a real model element (today: hardcoded constants in PDF generators). Becomes a real entity only if Operator is the importer of record or charges sub-tenant fees.
