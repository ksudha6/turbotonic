# Turbo Tonic: Phases 2-4 Plan

> Phase 1: Core domain (iters 001-029, done)
> Phase 2: Auth and Roles (iters 030-034)
> Phase 3: Export Readiness (iters 035-048)
> Phase 4: UX Revamp (iters 049+, scoped in parallel chat)
> Frontend stays on SvelteKit for POC. React rewrite deferred to production build.

---

## Scope boundary

Phase 2 is auth/roles -- cross-cutting, touches everything built in Phase 1.
Phase 3 is export-specific features. Internal/domestic movement is a separate phase.
Packaging label generation deferred to after Phase 3.

---

## Corrections from v1

1. **Packaging files are product-level, reusable across POs.** Not per-PO or per-shipment. Once packaging files exist for a product, they carry forward to every future PO/shipment containing that product. Only re-collected if something changes.
2. **Marketplace drives packaging requirements.** PO gets a `marketplace` field (AMAZON, DIRECT, etc.). If destination is Amazon, packaging files are required. Extensible to other marketplaces.
3. **4 roles, not 2.** SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER. Quality Labs is a new user type for certificate management.
4. **Vendor model needs extension.** Default address, account details. Manufacturing address is per-SKU (on Product, not Vendor).
5. **Certificate status EXPIRED computed on read**, not stored. Only PENDING and VALID persisted.
6. **Line item -> Product join resolved.** Add `product_id` FK to line_items. Existing part_number stays for display; product_id enables quality gate and packaging lookups.
7. **PackagingSpec types are user-defined strings**, not hardcoded enums. System provides structure; users name the specs.
8. **Track C (shipment docs) depends on Track B (packaging)** at readiness gate. Dependency acknowledged in graph.

---

## Research findings: what the domain requires

### Export qualification documents per SKU

Different markets require different certifications. No universal list -- depends on product category, destination, and regulation:

| Market | Children's products | Food contact | Electronics | General consumer |
|--------|-------------------|--------------|-------------|-----------------|
| US | CPC (CPSIA, ASTM F963) | FDA 21 CFR compliance | FCC (SDoC or certification) | GCC |
| EU | EN 71 + CE marking | EC 1935/2004 DoC | CE (EMC, LVD, RED, RoHS) | CE DoC |

Key attributes per certificate: type, applicable standards, issuing entity, testing lab, test date, issue date, expiry date (nullable -- some don't expire), product coverage, target market, document file.

**Design decision**: Qualification types are **user-defined**. The system provides the structure (what's needed, what's collected, what's missing); users populate the specifics. Scales to any country without code changes.

### Quality certificates

These are the export compliance certificates that prove a product meets the target market's safety/regulatory standards.

Typical flow: sample pulled from production -> accredited lab (ISO/IEC 17025) tests against applicable standards -> test report issued -> certificate created citing report.

| Type | What it is | Who issues | Validity |
|------|-----------|------------|----------|
| Certificate of Conformity (CoC) | Product meets specified standards | Manufacturer, importer, or accredited body | 1-3 years typically |
| Certificate of Analysis (CoA) | Detailed test results per parameter | Testing laboratory | Per-batch/lot |
| Test Report | Raw lab output with methodology | Accredited testing lab | Until product/process changes |
| Declaration of Conformity (DoC) | Legal self-declaration (EU CE) | Manufacturer | Until product/directive changes |
| Inspection Certificate | Visual/physical inspection confirmation | Third-party (SGS, Bureau Veritas, Intertek) | Per-shipment |

System must track expiry and flag when missing or expired at PO creation and before shipment.

### Amazon FBA packaging requirements (from Seller Central research)

**Key policy change (Jan 1, 2026):** Amazon ended FBA prep and labeling services in the US. Sellers must arrive with 100% prepped and labeled inventory.

**Prep categories (product-specific):**
- Poly bagging (fabric, loose parts, items < 2", plush, footwear) -- 1.5 mil minimum, sealed
- Bubble wrapping (fragile, glass, high-value books) -- 2 layers, 3-foot drop test
- Boxing/overboxing (items failing drop test, vinyl records)
- Cap sealing (liquids > 4.2 oz without secondary seal)
- Set creation (bundles -- "Sold as set" / "Do not separate" labels)
- No prep (sealed manufacturer packaging passing drop test)

**Labels per unit:**
- FNSKU label (Code 128, 1"x2" min, 300 DPI, covers all manufacturer barcodes)
- Suffocation warning (poly bags with 5"+ opening, font size varies by bag size)
- Expiration date label (MM-YYYY or MM-DD-YYYY, 36pt+, on outside of prep material)

**Labels per carton:**
- FBA Box ID label (from Seller Central Shipping Queue, 3.33"x4")
- Carrier shipping label
- Box content info (web form, file upload, or 2D barcode: PDF417/QR/DataMatrix)

**Box requirements:** max 36"x25"x25" (length increased June 2025), max 50 lbs, 2" cushioning, no packing peanuts.

**What the system tracks per product (for Amazon marketplace):**
- Prep category assignment
- Which labels are needed
- Whether packaging files (FNSKU, box content template) exist for this product
- Packaging file reuse: once created for a product, valid for all future POs/shipments

### Shipment documents (pre-ship collection)

| Document | Generated or uploaded | Who creates |
|----------|----------------------|-------------|
| Packing List | Generated (PDF) | System, from shipment data |
| Commercial Invoice (export) | Generated (PDF) | System, from shipment + PO data |
| Certificate of Origin | Uploaded | Exporter, certified by chamber of commerce |
| Bill of Lading | Uploaded (reference tracked) | Carrier |
| Insurance Certificate | Uploaded (when CIF) | Insurer |
| EEI/AES filing confirmation | Uploaded or reference | Filed via AES for US exports > $2,500 |

### Important distinction: Commercial Invoice (export) vs Invoice (billing)

The existing `Invoice` entity is a **billing/payment document** between buyer and vendor. The **Commercial Invoice for export** is a **customs document** with different fields: HS codes, country of origin, net/gross weights, number of packages, marks and numbers. They share a name but are different domain concepts. The export CI is generated from shipment data, not from the billing invoice.

---

## Model changes required (Phase 2 foundation)

### PurchaseOrder -- add marketplace
```
marketplace: str  # AMAZON, DIRECT, etc. User-defined values.
```
Determines what packaging files are required for products in this PO.

### Vendor -- extend with address and account details
```
address: str           # Default vendor address
account_details: str   # Bank/payment account info (free-text for now)
```

### Product -- add manufacturing address
```
manufacturing_address: str  # Per-SKU, since same vendor may manufacture in different locations
```

### LineItem -- add product_id FK
```
product_id: str | None  # FK to products(id). Nullable for backward compatibility.
```
Enables quality gate and packaging lookups without composite key gymnastics.

---

# Phase 2: Auth and Roles (iters 030-034)

Auth is a phase, not a side task. It touches every existing endpoint (7 routers), every frontend page (~15 pages), and adds data scoping. Every Phase 3 feature will have role guards from day one.

## Roles and permissions

| Role | What they do |
|------|-------------|
| SM (Supply Manager) | Full access. Creates POs, manages vendors/products, approves invoices, manages shipments, views dashboard, configures qualifications and packaging specs. |
| VENDOR | Sees own POs only. Accepts/rejects POs, posts milestones, submits invoices, uploads certificates. Cannot create POs or manage other vendors. |
| QUALITY_LAB | Manages certificates. Views products and their qualification requirements. Uploads test reports and certificates. No access to invoices or shipments. |
| FREIGHT_MANAGER | Manages shipments and shipment documents. Views POs (read-only). No access to invoices or vendor management. |

### Iter 030 -- User entity and auth infrastructure
- New aggregate: `User` (id, username, display_name, role, status: ACTIVE | INACTIVE, created_at)
- Database: users table, webauthn_credentials table (credential_id, user_id, public_key, sign_count)
- WebAuthn/passkey registration and login endpoints
- Cookie sessions (itsdangerous)
- `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me`
- Session middleware: inject current user into request state
- No role enforcement yet -- just "is this user logged in?"
- ~8 new files, ~800 lines.

### Iter 031 -- Role guards on backend
- Role enum on User: SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER
- `require_role(*roles)` FastAPI dependency
- Guard every existing endpoint:
  - PO create/edit/submit: SM
  - PO accept/reject: VENDOR
  - Invoice create/submit: VENDOR; approve/pay/dispute: SM
  - Vendor CRUD: SM
  - Product CRUD: SM
  - Milestone post: VENDOR
  - Activity/dashboard: all roles (filtered by target_role)
- ~7 router files + 1 dependency file, ~400 lines changed.

### Iter 032 -- Vendor-scoped data access
- VENDOR users linked to a vendor_id (new column on users table)
- VENDOR queries filter by their vendor_id: PO list, invoice list, milestone list, activity log
- SM/QUALITY_LAB/FREIGHT_MANAGER see all data (within their role's allowed entities)
- Repository-level filtering: pass current_user context into list queries
- Tests: VENDOR cannot see another vendor's POs; SM sees all
- ~8 files touched, ~500 lines.

### Iter 033 -- Frontend auth flow
- Login page (WebAuthn passkey registration and authentication)
- Session handling: `/api/v1/auth/me` on layout load, redirect unauthenticated users to login
- Store current user in SvelteKit layout context (available to all pages)
- Logout flow
- ~5 new files + 2 files touched, ~500 lines.

### Iter 034 -- Frontend role-conditional rendering
- Hide/show action buttons per role on all existing pages:
  - PO list/detail: SM sees create/edit/submit; VENDOR sees accept/reject
  - Invoice pages: VENDOR sees create/submit; SM sees approve/pay/dispute
  - Vendor/product pages: hidden for non-SM roles
  - Milestone form: VENDOR only
- Navigation: role-based menu items (SM sees everything, VENDOR sees POs + invoices, etc.)
- Dashboard: filter activity feed by target_role matching current user
- ~15 files touched, ~600 lines.

**Parallelism:** 030 -> 031 -> 032 are sequential (each depends on previous). 033 and 034 can run after 032, and 033 -> 034 is sequential. Total: one agent, 5 iterations.

---

# Phase 3: Export Readiness (iters 035-048)

### Foundation (4 iterations)

#### Iter 035 -- Document storage infrastructure
- File upload endpoint (multipart), file metadata table (id, entity_type, entity_id, file_type, original_name, stored_path, uploaded_at)
- File download/view endpoint
- Storage: local filesystem initially (abstractable to S3 later)
- Role guard: all authenticated users can upload/download
- No UI yet -- API only
- ~6 files, ~600 lines.

#### Iter 036 -- Existing model extensions
- Add `marketplace` to PurchaseOrder (domain, DTO, schema, frontend dropdown)
- Add `product_id` FK to LineItem (nullable, backward-compatible migration)
- Extend Vendor: `address`, `account_details` fields
- Extend Product: `manufacturing_address` field
- Update affected DTOs, repositories, and forms
- ~12 files touched, ~300 lines changed.

#### Iter 036a -- Export qualification type entity
- New aggregate: `QualificationType` (name, description, target_market, applies_to_category). User-defined.
- New join: `product_qualifications` (product_id, qualification_type_id)
- Replace `requires_certification` boolean with qualification list (empty = no requirements)
- Migration: existing products with requires_certification=true get a generic "QUALITY_CERTIFICATE" qualification
- API: CRUD for qualification types, assign/remove from product
- Role guard: SM creates/manages qualification types
- ~8 new files, ~800 lines.

#### Iter 037 -- Partial PO acceptance (carried from iter 028)
- Line-item level accept/reject on PENDING POs
- All lines addressed (no omissions)
- Invoicing excludes rejected lines
- Role guard: VENDOR accepts/rejects lines
- Backend + frontend + tests
- ~10 files, ~800 lines.

**Parallelism:** 035 and 036 run together. Then 036a and 037 run together.

### Three parallel tracks

---

**Track A: Quality Certificates** (users: Quality Labs, SMs, Vendors)

#### Iter 038 -- Certificate entity and lifecycle
- New aggregate: `Certificate`
  - product_id, qualification_type_id, cert_number, issuer, testing_lab, test_date, issue_date, expiry_date (nullable), target_market, document_id (FK to file storage)
  - Persisted status: PENDING | VALID. EXPIRED computed on read when expiry_date < now.
- API: create certificate, upload document, list by product, get by id
- Role guard: QUALITY_LAB and VENDOR can create/upload; SM can view
- Activity log: CERT_UPLOADED event (target: SM), new entity type CERTIFICATE
- Depends on: 036a (qualification types), 035 (file storage)
- ~8 new files, ~800 lines.

#### Iter 039 -- Quality gate and request flow
- On PO creation/submission: check if line item products (via product_id) have required qualifications covered by valid certificates for the PO's target market
- If missing/expired: surface warning (not blocking -- user decides)
- After QC_PASSED milestone: if product needs cert and none exists, create CERT_REQUESTED activity (ACTION_REQUIRED for QUALITY_LAB)
- If cert exists and is valid: no action needed
- Notification: "Product X requires [qualification] -- certificate missing/expired"
- Product without product_id on line item: skip quality gate (graceful degradation)
- Depends on: 038 (certificate entity), 036 (product_id on line items)
- ~5-8 files, ~400 lines.

#### Iter 040 -- Certificate UI
- Product detail: qualification requirements list, certificate status per qualification
- Certificate upload flow (uses document storage from iter 035)
- Expiry alerts on dashboard
- PO creation: warning banner when products lack required certs for the selected marketplace
- Depends on: 035 (file upload), 038-039 (certificate API)
- ~5 frontend files, ~500 lines.

---

**Track B: Packaging Compliance** (users: SMs, Vendors)

#### Iter 041 -- Packaging specification entity
- New entity: `PackagingSpec` (product_id, marketplace, spec_name: string, description, requirements_text)
- User defines what packaging files are needed per product per marketplace
- Packaging specs are product-level: created once, reused across all POs/shipments containing that product
- For Amazon: prep category, FNSKU requirements, box content template, suffocation warnings, etc.
- API: CRUD, list by product, list by product + marketplace
- Role guard: SM creates specs; VENDOR views
- No file attachment yet -- this is the "what's needed" definition
- ~8 new files, ~700 lines.

#### Iter 042 -- Packaging file collection and reuse
- Extend PackagingSpec with status: PENDING | COLLECTED
- File upload against a packaging spec (links to document storage from iter 035)
- Once collected, packaging files persist and apply to all future POs/shipments for that product
- Re-collection only if user explicitly updates the spec
- Packaging readiness check per product: all specs for the relevant marketplace have files?
- Role guard: SM and VENDOR can upload packaging files
- Activity log: PACKAGING_COLLECTED, PACKAGING_MISSING events (target: SM)
- Runs parallel to production milestones -- no dependency on milestone status
- Depends on: 035 (file upload), 041 (packaging specs)
- ~5 files, ~400 lines.

---

**Track C: Shipment and Export Documents** (users: SMs, Vendors, Freight Managers)

#### Iter 043 -- Shipment aggregate
- New aggregate: `Shipment`
  - po_id, shipment_number (format SHP-YYYYMMDD-XXXX), marketplace (inherited from PO)
  - Status: DRAFT | DOCUMENTS_PENDING | READY_TO_SHIP
  - Line items: subset of PO (selected lines + quantities from accepted lines)
- Create from accepted PO: full PO (all accepted lines) or partial (selected lines + quantities)
- Multiple shipments per PO allowed (partial shipments)
- Shipped quantity tracking: cumulative shipped quantity per line item cannot exceed PO accepted quantity
- API: create, list by PO, get by id
- Role guard: SM and FREIGHT_MANAGER create/manage shipments
- Depends on: 037 (partial PO acceptance for line-item-level accepted status)
- ~10 new files, ~1000 lines.

#### Iter 044 -- Packing list generation (PDF)
- Generated from shipment data
- Fields: shipper (vendor address), consignee (buyer), shipment ref, PO ref, per-line: description, quantity, package count, net/gross weight, dimensions, country of origin
- New fields on shipment line items: net_weight, gross_weight, package_count, dimensions
- PDF download endpoint
- Depends on: 043 (shipment entity)
- ~3-4 files, ~400 lines.

#### Iter 045 -- Export commercial invoice generation (PDF)
- Generated from shipment + PO + vendor data as a PDF endpoint on Shipment (same pattern as existing PO/Invoice PDFs)
- Fields: seller, buyer, consignee, invoice number, date, PO ref, incoterm, per-line: description, HS code, quantity, unit price, net/gross weight, country of origin, total value, currency
- PDF download endpoint
- Depends on: 043 (shipment entity)
- ~3-4 files, ~400 lines.

#### Iter 046 -- Shipment document collection and readiness gate
- Define required documents per shipment (packing list, export CI, certificate of origin, others as user-configured)
- Track collection status: which docs are generated, which are uploaded, which are missing
- Readiness check (all must pass for READY_TO_SHIP):
  1. All required documents collected
  2. All products in shipment have valid certificates for qualifications required by target market
  3. All products in shipment have packaging files collected for the PO's marketplace
- Dashboard: shipments pending documents, shipments ready to ship
- Depends on: 035 (file upload), 042 (packaging readiness), 043 (shipment entity)
- ~6-8 files, ~600 lines.

### Integration (2 iterations)

#### Iter 047 -- Activity log extensions
- New target roles: QUALITY_LAB, FREIGHT_MANAGER (added to TargetRole enum)
- New entity types: CERTIFICATE, SHIPMENT, PACKAGING (added to EntityType enum)
- New activity events: SHIPMENT_CREATED, SHIPMENT_READY, CERT_REQUESTED, CERT_UPLOADED, CERT_EXPIRED, PACKAGING_COLLECTED, PACKAGING_MISSING, DOCUMENT_UPLOADED
- Wire events into existing activity log recording pattern
- ~4-6 files, ~300 lines.

#### Iter 048 -- Dashboard updates for Phase 3 features
- Shipment pipeline (by status): pending, documents pending, ready to ship
- Certificate expiry alerts: products with expiring/expired certs
- Packaging collection progress per marketplace
- Notification bell: new event types routed to appropriate roles
- ~4-6 files, ~400 lines.

---

# Phase 4: UX Revamp (iters 049+)

All domain features exist. Auth/roles are enforced. This phase redesigns the presentation layer without changing business logic or API contracts.

## Scope

The revamp covers every existing page (~15 now, ~22 after Phase 2) plus navigation, layout, and component consistency. The backend API is untouched.

## What needs design input (from parallel chat)

Before iterations can be scoped, these decisions are needed:

1. **Design language**: what does "minimalistic + high UX" mean concretely? Reference apps, color palette, typography, spacing system.
2. **Navigation model**: sidebar vs top nav, role-based menu structure, how deep the hierarchy goes.
3. **Dashboard layout**: what cards/widgets, what priority order, role-specific views.
4. **Table design**: the app is table-heavy (PO list, invoice list, vendor list, product list, shipment list). Consistent table component with sorting, filtering, pagination, bulk actions.
5. **Form design**: create/edit forms are the primary interaction. Inline validation, field grouping, mobile-friendly layout.
6. **Detail page pattern**: PO detail, invoice detail, shipment detail all follow a similar structure (header + status + tabs/sections). Standardize.
7. **Mobile layout**: responsive breakpoints, which features are mobile-accessible.
8. **Notification/alert patterns**: toast vs inline, error vs warning vs info.

## Preliminary iteration structure

Exact scope depends on design decisions from the parallel chat, but the structure will be:

#### Iter 049 -- Design system and component library
- Color tokens, typography scale, spacing grid
- Base components: Button, Input, Select, Table, Card, Badge/Pill, Modal, Toast
- Replaces ad-hoc component styling across the app
- ~10-15 files, ~1000 lines.

#### Iter 050 -- Layout and navigation
- App shell: sidebar/top nav, role-based menu, breadcrumbs
- Responsive breakpoints
- Apply to all pages (layout wrapper, not per-page)
- ~5-8 files, ~500 lines.

#### Iter 051 -- Dashboard redesign
- Role-specific dashboard views (SM sees everything, VENDOR sees their POs, etc.)
- Widget layout per the design decisions
- ~3-5 files, ~600 lines.

#### Iter 052 -- List pages redesign
- Unified table component applied to: PO list, invoice list, vendor list, product list, shipment list, certificate list
- Consistent filter/search/sort/pagination/bulk-action pattern
- ~8-10 files, ~800 lines.

#### Iter 053 -- Detail pages redesign
- Unified detail layout: PO detail, invoice detail, shipment detail, product detail
- Status header, tabbed sections, timeline, action buttons
- ~6-8 files, ~600 lines.

#### Iter 054 -- Form pages redesign
- Unified form layout: PO create/edit, invoice create, vendor create, product create/edit, shipment create
- Field grouping, inline validation, mobile layout
- ~8-10 files, ~600 lines.

#### Iter 055 -- Mobile pass
- Test and fix all pages at mobile breakpoints
- Touch targets, scroll behavior, collapsed navigation
- ~10+ files, ~400 lines.

Total Phase 4: ~7 iterations, one agent sequentially (each builds on the design system from 049).

---

## Full dependency graph

```
PHASE 2: Auth (sequential, 1 agent)
  030 (user + auth infra) -> 031 (API role guards) -> 032 (vendor-scoped data) ->
  033 (frontend auth) -> 034 (frontend role rendering)

PHASE 3: Export Readiness
  Foundation:
    Step 1 (parallel):  035 (doc storage)  |  036 (model extensions)
    Step 2 (parallel):  036a (qual types, needs 036)  |  037 (partial PO, independent)

  Three tracks (A+B parallel, C after 037):
    Track A               Track B                Track C
    038 (cert entity)     041 (packaging spec)   043 (shipment)
      \-- needs 036a,035    |                      \-- needs 037
      |                     |                      |
    039 (quality gate)    042 (packaging files)   044 (packing list PDF)
      \-- needs 036,038     \-- needs 035,041       \-- needs 043
      |                                            |
    040 (cert UI)                                045 (export CI PDF)
      \-- needs 035,039                            \-- needs 043
                                                   |
                                                 046 (readiness gate)
                                                   \-- needs 035,042,043

  Integration:
    047 (activity log) -> 048 (dashboard)

PHASE 4: UX Revamp (sequential, 1 agent, scoped in parallel chat)
  049 (design system) -> 050 (layout) -> 051 (dashboard) ->
  052 (list pages) -> 053 (detail pages) -> 054 (forms) -> 055 (mobile)
```

### Parallelism summary

| Step | Concurrent agents | Iterations |
|------|------------------|------------|
| Phase 2 | 1 | 030 -> 031 -> 032 -> 033 -> 034 |
| Phase 3, foundation step 1 | 2 | 035, 036 |
| Phase 3, foundation step 2 | 2 | 036a, 037 |
| Phase 3, tracks | 3 | A (038-040), B (041-042), C (043-046) |
| Phase 3, integration | 1 | 047 -> 048 |
| Phase 4 | 1 | 049 -> 055 |

---

## Agent strategy

| Phase | Agents | What each does |
|-------|--------|---------------|
| 2 (auth) | 1 Sonnet | User entity, WebAuthn, guards, scoping, frontend auth. Sequential -- each iteration touches what the previous built. |
| 3 foundation | 2 Sonnet | Agent-A: doc storage, then qual types. Agent-B: model extensions, then partial PO. |
| 3 tracks | 3 Sonnet | Agent-A: quality (038-040). Agent-B: packaging (041-042). Agent-C: shipment (043-046). |
| 3 integration | 1 Sonnet | 047 then 048. |
| 4 (UX) | 1 Sonnet | Design system through mobile pass (sequential, each builds on previous). |

**Export domain agent (research, not coding):** A reference agent holding export compliance findings. Consulted by coding agents when they need to validate domain decisions against real-world requirements. Does not write code.

---

## Resolved decisions

1. **Export Commercial Invoice**: PDF endpoint on Shipment. No separate entity.
2. **Frontend**: SvelteKit for POC. React rewrite deferred to production build.
3. **Auth/roles**: Phase 2, before export features. Every new feature gets guards from day one.
4. **UX revamp**: Phase 4, after all domain features exist. Scoped in parallel chat.

## Open item

1. **Export domain agent**: scope and prompt structure -- to discuss.

---

## What comes after Phase 4

1. Product compliance (regulatory tracking beyond quality certs)
2. Customs documents (customs declaration, EEI/AES filing for US, TARIC for EU)
3. Shipment booking (carrier selection, booking creation)
4. Shipment tracking (carrier integration, status updates, ETA)
5. Internal/domestic movement
6. Packaging label generation
7. React production rewrite
