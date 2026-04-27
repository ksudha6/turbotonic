# Iterations Summary

> Single-file context for future conversations. Replaces reading 29 individual iteration docs.
> Last updated: iter 076 closed on 2026-04-27 — `/po` list revamp on Phase 4.2 components under `(nexus)`.

---

## Product vision

Turbo Tonic is a vendor portal for purchase order confirmation, invoicing, production tracking, and shipment booking and tracking logistics. The CRUD workflow is table stakes. The differentiator is an agent layer that reads, validates, and flags documents (shipment docs, invoices, customs declarations). Two exit paths after customs validation ships: (a) horizontal B2B SaaS for procurement/logistics/invoicing companies, or (b) vertical industry specialization.

## Tech stack

Python 3.13, FastAPI, Postgres 16 (asyncpg, connection pool), WebAuthn/passkeys + cookie sessions. Frontend: SvelteKit 2 + Svelte 5, adapter-static. Package manager: uv (backend), npm (frontend), nvm for Node. Local dev: Postgres via Homebrew (docker-compose.yml available for Docker environments).

## Current domain model (as of iteration 046)

### Aggregates
- **PurchaseOrder** — Draft > Pending > MODIFIED (ping-pong with vendor) > Accepted | Rejected (only via all-REMOVED convergence) > Revised > Pending. Contains LineItems each with LineItemStatus (PENDING/MODIFIED_BY_VENDOR/MODIFIED_BY_SM/ACCEPTED/REMOVED), line_edit_history. PO-scoped round_count (0-2), last_actor_role. Types: PROCUREMENT, OPEX.
- **Invoice** — Draft > Submitted > Approved > Paid | Disputed > Resolved. Linked to PO. Over-invoicing guard checks cumulative quantities against PO line items.
- **Vendor** — Active | Inactive. Types: PROCUREMENT, OPEX, FREIGHT, MISCELLANEOUS. Country validated against reference data.
- **Product** — Vendor-scoped catalog (vendor_id + part_number unique). Qualifications managed via QualificationType join table (replaces requires_certification boolean).
- **QualificationType** — Named qualification requirement (e.g. QUALITY_CERTIFICATE). Linked to products via join table. Target market scoped.
- **Certificate** — Links product to qualification type. Status: Pending > Valid. EXPIRED computed from expiry_date. Tracks cert_number, issuer, testing_lab, test/issue/expiry dates, target_market. Document attachment via file storage.
- **PackagingSpec** — Per-product per-marketplace packaging requirement. Status: Pending > Collected (via file upload). Document attachment via file storage. Unique on (product_id, marketplace, spec_name).
- **Shipment** — DRAFT > DOCUMENTS_PENDING > READY_TO_SHIP > BOOKED > SHIPPED. Linked to PO; multiple shipments per PO. ShipmentLineItems carry net_weight, gross_weight, package_count, dimensions, country_of_origin (all nullable, settable in DRAFT/DOCUMENTS_PENDING). Booking metadata (carrier, booking_reference, pickup_date) populated on `book_shipment` transition; `shipped_at` set on `mark_shipped`. Cumulative shipped quantity per part_number cannot exceed PO accepted quantity. Marketplace inherited from PO.
- **ShipmentDocumentRequirement** — PENDING > COLLECTED. Per-shipment document checklist. Default PACKING_LIST and COMMERCIAL_INVOICE rows (is_auto_generated=True) seeded on submit-for-documents; SM/FREIGHT_MANAGER may add custom user-defined document_type rows. Auto-generated rows always pass the documents readiness check (PDFs render on demand).

### Supporting concepts
- **Milestone** — RAW_MATERIALS > PRODUCTION_STARTED > QC_PASSED > READY_FOR_SHIPMENT > SHIPPED. Strict sequence enforcement. Attached to PO. (READY_FOR_SHIPMENT renamed from READY_TO_SHIP in iter 074 to disambiguate from the per-shipment status.)
- **ActivityLog** — Immutable event stream. Categories: LIVE, ACTION_REQUIRED, DELAYED. Target roles: SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER. Entity types: PO, INVOICE, CERTIFICATE, PACKAGING, SHIPMENT. Powers dashboard feed and notification bell.
- **CertWarning** (iter 039) — Advisory result of the PO-submit quality gate. One entry per (line item, missing/expired qualification, marketplace).
- **ReadinessResult** (iter 046) — Composite of documents_ready + certificates_ready + packaging_ready with structured missing-item lists. Drives the mark-ready gate.
- **Reference data** — 30 currencies, 11 incoterms, 17 payment terms, 31 countries, 50+ ports, USD exchange rates.

### Database tables
purchase_orders, line_items, rejection_history, vendors, products, invoices, invoice_line_items, milestone_updates, activity_log, files, qualification_types, product_qualifications, certificates, packaging_specs, line_edit_history, shipments, shipment_line_items, shipment_document_requirements.

## Frontend routes

| Route | Purpose |
|-------|---------|
| `/dashboard` | (Phase 4.1) ADMIN/SM 4-KPI grid (Pending POs, Awaiting acceptance, In production, Outstanding A/P) + recent activity + awaiting-acceptance panel under `(nexus)` AppShell. Other roles see a placeholder pending their dashboard iter. |
| `/po` | PO list with filters, search, sort, pagination, bulk actions |
| `/po/new` | Create PO form |
| `/po/[id]` | PO detail: status actions, line items, invoices, milestones, activity timeline, PDF |
| `/po/[id]/edit` | Edit rejected PO for revision |
| `/invoices` | Invoice list with filters, bulk PDF download |
| `/invoice/[id]` | Invoice detail: status actions, line items, activity timeline, PDF |
| `/vendors` | Vendor list with status/type filters |
| `/vendors/new` | Create vendor |
| `/products` | Product catalog list with vendor filter |
| `/products/new` | Create product |
| `/products/[id]/edit` | Edit product attributes |
| `/shipments/[id]` | Shipment detail: edit per-line weights/dims, download Packing List + Commercial Invoice PDFs |
| `/login` | WebAuthn passkey login, deep link redirect support |
| `/register` | Invite-only passkey registration (username from query param) |
| `/setup` | First-user bootstrap, pending-user message, already-configured detection |

## API surface

- **PO**: CRUD, submit, accept, resubmit, bulk transition, PDF export. Submit/resubmit return `POSubmitResponse` (po + cert_warnings) per iter 039.
- **PO line negotiation**: per-line modify, accept, remove, force-accept, force-remove; submit-response for round hand-off
- **Invoice**: CRUD, submit, approve, pay, dispute, resolve, remaining quantities, PDF export, bulk PDF
- **Vendor**: CRUD, deactivate, reactivate
- **Product**: CRUD (POST, GET list, GET by id, PATCH), packaging readiness per marketplace
- **Milestone**: list by PO, post milestone. QC_PASSED triggers CERT_REQUESTED activity for products lacking valid certs (iter 039).
- **Shipment**: create, list (by PO or all), get, remaining-quantities, PATCH line item weights/dims, submit-for-documents, mark-ready (gated by readiness check)
- **Shipment documents**: list requirements, add custom requirement, upload file against requirement, GET readiness (documents + certificates + packaging composite)
- **Shipment PDFs**: GET packing-list, GET commercial-invoice (CI number deterministic, not persisted)
- **Dashboard**: legacy `/dashboard/` returns the pre-revamp aggregate (kept additively during the revamp); `/dashboard/summary` (iter 071) returns role-scoped KPIs + awaiting-acceptance list + activity feed for the `(nexus)` page. Pre-revamp endpoint will retire end of Phase 4.
- **Activity**: list (with optional target_role filter), unread count (with optional target_role filter), mark read
- **Reference data**: all lookups in one GET
- **Document**: upload (multipart, PDF-only, 10MB limit), download (Content-Disposition), delete, list by entity
- **QualificationType**: CRUD, product assignment/removal
- **Certificate**: CRUD, document upload, computed EXPIRED status
- **PackagingSpec**: CRUD, file upload, packaging readiness per product/marketplace

---

## Iteration log

| Iter | Date | What was done |
|------|------|---------------|
| 01 | 2026-03-12 | Project scaffold: FastAPI + SvelteKit, SQLite, PO create/list |
| 02 | 2026-03-16 | PO detail page, status transitions (submit/accept/reject), revision flow |
| 03 | 2026-03-17 | Vendor entity: CRUD, active/inactive lifecycle |
| 04 | 2026-03-19 | Vendor reactivation, reference data dropdowns (currencies, incoterms, payment terms) |
| 05 | 2026-03-19 | PO PDF export (backend + download) |
| 06 | 2026-03-24 | PO list: filtering by status/vendor/currency, text search, pagination |
| 07 | 2026-03-24 | Dashboard: PO summary cards, vendor counts, recent POs |
| 08 | 2026-03-26 | Bulk PO status transitions (submit, accept, reject multiple) |
| 09 | 2026-03-26 | UI polish: bulk action feedback, status pill component |
| 10 | 2026-03-26 | Cross-page selection for bulk actions (up to 200 IDs) |
| 11 | 2026-03-30 | Vendor types (Procurement, OpEx, Freight, Miscellaneous), PO type derived from vendor |
| 12 | 2026-03-30 | Invoice module: domain model, create from PO, over-invoicing guard, submit/approve/pay/dispute |
| 13 | 2026-03-30 | Label resolution: reference data codes to human labels in UI and PDFs |
| 14 | 2026-03-30 | Invoice quantity control: remaining quantities endpoint, UI for partial invoicing |
| 15 | 2026-03-30 | Invoice list page with filters (status, PO#, vendor, invoice#, date range), pagination |
| 16 | 2026-03-30 | Invoice PDF export (backend) |
| 17 | 2026-03-30 | Production milestones: domain model, strict sequence enforcement, API |
| 18 | 2026-03-30 | Milestone timeline UI on PO detail, post-milestone form |
| 19 | 2026-03-30 | Dashboard production pipeline: milestone counts, overdue detection |
| 20 | 2026-04-03 | Cosmetic: PO PDF cleanup, vendor country dropdown from reference data, HS code format validation |
| 21 | 2026-04-03 | OPEX invoicing: OpEx POs get free-form invoice lines (no PO line item linkage) |
| 22 | 2026-04-03 | Invoice PDF export (frontend): download button, bulk PDF download |
| 23 | 2026-04-06 | Activity log: event recording for PO/invoice/milestone actions, dashboard feed |
| 24 | 2026-04-06 | Notification bell: unread count, mark-read, activity timeline on detail pages |
| 25 | 2026-04-06 | Vendor country validation: domain-level reject of invalid country codes |
| 26 | 2026-04-06 | Playwright permanent test suite: activity feed, notification bell, timeline specs |
| 27 | 2026-04-06 | Field-level mutability rules: which PO fields are editable in which status |
| 28 | 2026-04-06 | Partial PO acceptance (line-item level accept/reject) — scoped but not started |
| 29 | 2026-04-09 | Product master: vendor-scoped product catalog with requires_certification flag |
| 29a | 2026-04-15 | Postgres migration: replaced aiosqlite with asyncpg connection pool, all repos use $N placeholders, test isolation via rolled-back transactions, seed script for demo data |
| 030 | 2026-04-15 | User entity (6 roles, 3 statuses), WebAuthn passkey registration/login, cookie sessions, session middleware, bootstrap/invite flows, critical-path integration test |
| 031 | 2026-04-15 | API role guards: require_role/require_auth on all 30+ endpoints, ADMIN bypass, bulk transition fine-grained action check, authenticated_client test fixture, dev-login endpoint |
| 032 | 2026-04-16 | Vendor-scoped data access: VENDOR users see only their vendor's POs, invoices, milestones, activity, and dashboard data. check_vendor_access helper, 404 on ownership mismatch, bulk ops skip non-owned entities |
| 033 | 2026-04-16 | Frontend auth flow: login page (WebAuthn passkey), invite-only register page, bootstrap/setup page, layout session check with redirect, logout, 401 handling, deep link preservation, credentials: include on all API calls, 9 new Playwright auth tests, existing tests updated with auth mock |
| 034 | 2026-04-16 | Frontend role-conditional rendering: permissions.ts helper, role-based nav links, PO/invoice/vendor/product page button guards, page-level role redirects via +page.ts, dashboard role-filtered widgets, backend target_role filter on activity endpoints, 16 new Playwright role tests |
| 035 | 2026-04-16 | Document storage infrastructure: files table, FileMetadata domain model, DocumentRepository, FileStorageService (local disk), upload/download/delete/list API endpoints, PDF-only 10MB limit, path traversal protection, require_auth on all endpoints, 19 new tests |
| 036 | 2026-04-16 | Model extensions: marketplace on PO (with reference data validation), product_id on LineItem, address + account_details on Vendor, manufacturing_address on Product. Schema migration via ALTER TABLE. Frontend forms updated. Marketplace filter on PO list. |
| 036a | 2026-04-16 | QualificationType entity replacing requires_certification boolean, product-qualification join table, CRUD + assignment API, 35 new tests |
| 037 | 2026-04-16 | Per-line-item accept/reject on POs: LineItemStatus enum, accept_lines() method, per-line toggle UI, vendor-only Submit Response, 16 new tests |
| 041 | 2026-04-16 | PackagingSpec entity for per-product per-marketplace packaging requirements, CRUD API, product edit UI section, 32 new tests |
| 038 | 2026-04-16 | Certificate entity linking products to qualification types with cert details, computed EXPIRED status, document upload, CERT_UPLOADED activity event, 27 new tests |
| 042 | 2026-04-16 | PackagingSpec file collection: COLLECTED status, document upload, packaging readiness endpoint, PACKAGING_COLLECTED activity event, 15 new tests |
| 056 | 2026-04-19 | Line-level negotiation domain + API: replaces iter 037 accept_lines with modify/accept/remove/force-accept/force-remove/submit-response per-line endpoints, 2-round cap, convergence to ACCEPTED/REJECTED, line_edit_history table, new statuses MODIFIED_BY_VENDOR/MODIFIED_BY_SM/REMOVED, new PO status MODIFIED. Drops `reject()` and `/reject` entirely. 70+ new permanent tests. |
| 057 | 2026-04-19 | Negotiation UI: LineNegotiationRow + ModifyLineModal + LineDiff + EditHistoryTimeline + SubmitResponseBar components; PO detail page replaces RejectDialog/accept-lines-table with per-line modify/accept/remove controls; Force Accept and Force Remove with confirmation dialog at round 2 for SM; 8 new Playwright specs. |
| 058 | 2026-04-19 | PDF scoping + negotiation activity events: PO PDF filters to ACCEPTED lines only with MODIFIED stamp when round_count >= 1; 7 new event types (PO_LINE_MODIFIED, PO_LINE_ACCEPTED, PO_LINE_REMOVED, PO_FORCE_ACCEPTED, PO_FORCE_REMOVED, PO_MODIFIED, PO_CONVERGED); router wires events on every per-line endpoint; Partial + Modified pills on PO list. 15 new permanent tests. |
| 059 | 2026-04-19 | Advance payment gate + post-acceptance line modification: payment_terms metadata with has_advance flag (4 terms flagged), advance_paid_at column on PO, mark_advance_paid + add_line_post_acceptance + remove_line_post_acceptance methods + endpoints (SM-only), downstream-artifact check via services layer, 3 new activity events (PO_ADVANCE_PAID, PO_LINE_ADDED_POST_ACCEPT, PO_LINE_REMOVED_POST_ACCEPT), minimal frontend UI. 37 new permanent tests. |
| 060 | 2026-04-19 | Email notifications: aiosmtplib-backed EmailService with Jinja2 templates (po_accepted, po_modified, po_line_modified, po_advance_paid), NotificationDispatcher decoupled from activity repo, recipient resolution per role and vendor scope, users.email column + seed backfill, EMAIL_SEND_FAILED activity event on delivery failure, FakeEmailService fixture default in tests. 15 new permanent tests. |
| 043 | 2026-04-24 | Shipment aggregate: shipments + shipment_line_items tables, DRAFT > DOCUMENTS_PENDING > READY_TO_SHIP, create from accepted PO with cumulative shipped-quantity guard, create/list/get/remaining-quantities endpoints, role guards (SM + FREIGHT_MANAGER for mutations). |
| 039 | 2026-04-24 | Quality gate at PO submit + CERT_REQUESTED on QC_PASSED: services/quality_gate.py service iterates accepted line items with product_id, checks valid certs against PO marketplace, returns CertWarning list. PO submit/resubmit return new POSubmitResponse wrapper (po + cert_warnings). QC_PASSED milestone fans out CERT_REQUESTED activity to QUALITY_LAB. TargetRole.QUALITY_LAB and FREIGHT_MANAGER added to enum. ~20 new tests. |
| 044 | 2026-04-24 | Shipment line item weights/dims + packing list PDF: net_weight/gross_weight/package_count/dimensions/country_of_origin (all nullable) + Shipment.update_line_items() guarded by status. PATCH /shipments/{id} (SM + FREIGHT_MANAGER), GET /shipments/{id}/packing-list returning ReportLab PDF (SM + VENDOR + FREIGHT_MANAGER). Frontend shipment detail page with inline weight/dim editing and download button. ~10 new tests. |
| 045 | 2026-04-24 | Export commercial invoice PDF on Shipment: GET /shipments/{id}/commercial-invoice. Deterministic CI number CI-{shipment_number}, not persisted. HS code + unit price from PO line items (matched by part_number); quantity + weights + country of origin from shipment line items. Same ReportLab pattern as packing list. Frontend Download Commercial Invoice button alongside Packing List. 7 new tests. |
| 046 | 2026-04-24 | Shipment document requirements + readiness gate (backend): shipment_document_requirements table, ShipmentDocumentRequirement entity (PENDING > COLLECTED), ReadinessResult composite (documents + certificates + packaging). Default PACKING_LIST and COMMERCIAL_INVOICE auto-generated rows seeded on submit-for-documents; both always pass docs check. New endpoints: POST /requirements (custom), POST /documents/{rid}/upload, GET /requirements, GET /readiness. Existing mark-ready endpoint enhanced with readiness gate (409 + ReadinessResult on failure). DOCUMENT_UPLOADED ActivityEvent + EntityType.SHIPMENT added. 12 new tests. Frontend (Documents section, readiness panel, Mark Ready, dashboard counts) deferred to Phase 4. |
| 061 | 2026-04-24 | Phase 4.0 foundations -- ADMIN inheritance + seed variety: removed `isExact` helper from `frontend/src/lib/permissions.ts` so ADMIN inherits VENDOR-side actions (`canAcceptRejectPO`, `canCreateInvoice`, `canSubmitInvoice`, `canPostMilestone`). First commit of `backend/src/seed.py` into git (previously untracked); expanded `_make_activity_log` from 8 to 19 rows covering all 8 named event types and derived `(category, target_role)` from `EVENT_METADATA` to prevent drift. New `backend/tests/test_seed.py` with 6 tests asserting 10 variety thresholds (vendors/types/countries, POs/statuses, invoices/statuses, milestones/stages, activity/events, users/roles). Pre-existing seed issues (non-deterministic UUIDs, `_PAYMENT_TERMS_CYCLE` dead branches, module-level `random.seed`/`_NOW`) logged to backlog for future cleanup. 591 backend tests + 100 Playwright specs green. |
| 062 | 2026-04-24 | Phase 4.0 design-system scaffold: new `(nexus)` SvelteKit layout group (empty passthrough; AppShell deferred to iter 068), 22 new design tokens appended to `global.css` (`--surface-*`, `--text-sidebar*`, `--brand-accent`, `--button-solid-*`, `--dot-*` status dots, `--font-size-xs`/`--font-size-3xl`, `--letter-spacing-wide`, `--space-7`/`--space-20`, `--breakpoint-*`), `/ui-demo` route skeleton (populated by later iters). Additive only -- zero existing tokens or component rules modified. Incidentally resolves two pre-existing `--font-size-xs` consumers (dashboard, shipments) that had been falling through to browser defaults. 591 backend tests + 100 Playwright specs green. |
| 063 | 2026-04-24 | Phase 4.0 leaf primitives: seven Svelte 5 primitives under `frontend/src/lib/ui/` — Button (primary/secondary/ghost + disabled), StatusPill (green/blue/orange/red/gray tones + leading dot), ProgressBar (role=progressbar, clamped `$derived` value), Input, Select, DateInput (native `<input type="date">`), Toggle (button + aria-pressed, bindable pressed). All primitives use the `ui-<name>` outermost-class convention so scoped styles cannot collide with pre-revamp `global.css` rules (`.btn` / `.badge` / `.input` / `.select` / etc.). Pre-revamp `$lib/components/StatusPill.svelte` unchanged. New `frontend/tests/primitives.spec.ts` with 9 Playwright tests, wired through the `/ui-demo` gallery. Playwright mock order fixed (LIFO — catch-all must register before specific `/auth/me` mock). Code reviews caught `.btn:hover` opacity leak from pre-revamp on Button secondary/ghost; fixed via `ui-btn` rename. 591 backend tests + 109 Playwright specs green. |
| 064 | 2026-04-24 | Phase 4.0 composite primitives: five more Svelte 5 primitives under `frontend/src/lib/ui/` — FormField (server-error contract with `role="alert"`, wraps child via snippet that exposes `{ invalid }`), PanelCard (section with title + subtitle + optional action slot + body), AttributeList (definition-list grid of label/value rows), FormCard (form surface with Cancel + Submit footer buttons, uses Button primitive), KpiCard (label + big value + tone-colored delta chip). Input primitive extended with `aria-invalid={invalid || undefined}` (omit-when-false per W3C) so FormField's invalid state surfaces through ARIA. `ui-<name>` class convention applied to all five; critical `.card` → `.ui-form-card` rename prevents double-styling from pre-revamp `global.css` `.card`. `primitives.spec.ts` grows by 5 tests (total 14). 591 backend tests + 114 Playwright specs green. |
| 065 | 2026-04-24 | Phase 4.0 display + state primitives: six more Svelte 5 primitives under `frontend/src/lib/ui/` — Timeline (ordered steps with done/current/upcoming state, colored marker), ActivityFeed (dot + primary + secondary entry rows using `--dot-*` tokens), LoadingState (role=status spinner, `prefers-reduced-motion` fallback disables rotation), EmptyState (centered title + description + optional action snippet), ErrorState (alert banner wrapping iter-063 Button as Retry, `role="alert"`), ErrorBoundary (Svelte 5 `<svelte:boundary>` wrapper falling back to ErrorState; does not expose error to user to avoid leaking stack traces). ErrorBoundary installed but not rendered on `/ui-demo` — will be wired into `(nexus)/+layout.svelte` at iter 068. All use `ui-<name>` class convention (ErrorBoundary has no class — it's a wrapper). `primitives.spec.ts` grows by 5 tests (total 19; ErrorBoundary not unit-tested). 591 backend tests + 119 Playwright specs green. |
| 066 | 2026-04-24 | Phase 4.0 table + header primitives: three more Svelte 5 primitives under `frontend/src/lib/ui/` — DataTable (generic over `T extends { id: string }`, server-driven pagination contract `{ page, pageSize, total, onPageChange }`, Prev/Next Buttons with `Page X of Y`, clickable rows with tabindex/Enter/Space keyboard), PageHeader (H1 + optional subtitle + optional action snippet), DetailHeader (back link + title + optional subtitle + optional statusPill snippet). DataTable `<table>` has no class attribute to avoid collision with pre-revamp global `.table` rule. `primitives.spec.ts` grows by 3 tests (total 22). 591 backend tests + 122 Playwright specs green. |
| 067 | 2026-04-24 | Phase 4.0 sidebar foundation: `frontend/src/lib/ui/sidebar-items.ts` (explicit `Record<UserRole, SidebarItem[]>` map decoupled from `permissions.ts`) + `Sidebar.svelte` primitive consuming it via `$derived`, using `$app/state`'s `page.url.pathname` for `aria-current="page"`. Per-role items locked after brainstorm: ADMIN gains Users nav (future `/users` page, 404 until built); FREIGHT_MANAGER gains Invoices nav (OpEx-only page scoping backlog'd for iter 071+); SM/VENDOR/QUALITY_LAB/PROCUREMENT_MANAGER unchanged; Shipments deferred. Sidebar visibility intentionally decoupled from `canView*` permission helpers — nav visibility and page capability are separate concerns. `primitives.spec.ts` grows by 2 Sidebar tests (total 24); new `sidebar-items.spec.ts` with 6 role-matrix tests. 591 backend tests + 130 Playwright specs green. |
| 068 | 2026-04-24 | Phase 4.0 shell: `TopBar.svelte` (hamburger toggle + optional breadcrumb hidden on mobile via `@media max-width: 767px` + embedded pre-revamp NotificationBell + optional userMenu snippet; search omitted in 4.0) and `AppShell.svelte` (composes Sidebar + TopBar + iter-065 ErrorBoundary; desktop 240px + 1fr grid; mobile ≤768px off-canvas drawer at `min(280px, 70vw)` with `translateX` + `visibility:hidden` transition + tap-to-dismiss overlay). Separate `/ui-demo/shell` route hosts the AppShell preview. All three Phase 4.0 brainstorms (Tasks 18, 20, 22) resolved from Lovable mock screenshots captured at 1440/768/390 viewports via Playwright MCP. Chrome scope = Option B: mock visual chrome + real routes. Retrofits to existing primitives: `sidebar-items.ts` returns `SidebarSection[]`; `Sidebar.svelte` gains section headers + `roleLabel?: string` + `footer?: Snippet`; `KpiCard.svelte` gains `icon?: Snippet` slot. `primitives.spec.ts` grows to 31 tests. 591 backend + 140 Playwright green. |
| 069 | 2026-04-24 | Phase 4.0 shell finish: `UserMenu.svelte` (pill with avatar + name + role stacked on desktop, collapses to avatar + chevron on mobile via `@media max-width: 767px`; dropdown with Log out; `import.meta.env.DEV`-gated Switch role placeholder for future dev-store wiring; logout swallows API errors and always redirects to `/login`). `redirects.ts` + spec (empty registry in Phase 4.0; `resolveRedirect` substitutes `:param` tokens via named-capture regex). `(nexus)/_smoke/+page.svelte` sentinel route mounts AppShell + UserMenu with `page.data.user`-derived role/name/roleLabel. `nexus-shell.spec.ts` permanent E2E test covers ADMIN-full-nav, VENDOR-no-Vendors, and 401-redirect invariants, scoping assertions to `ui-appshell-sidebar` testid to avoid colliding with pre-revamp nav links. `primitives.spec.ts` grows to 33 tests; new `redirects.spec.ts` (3) and `nexus-shell.spec.ts` (3). 591 backend + 148 Playwright green. |
| 070 | 2026-04-24 | **Phase 4.0 close.** Adds @axe-core/playwright and runs AA accessibility scan on `/ui-demo` and `/_smoke` (zero violations / fixed inline — see iter doc). Scratch 390px + 1024px screenshots captured locally for visual verification but not committed (per CLAUDE.md scratch-test rule). Work-log summary updated to mark Phase 4.0 complete. 591 backend + 150 Playwright green. Branch `ux-changes` ready for PR to main. |
| 071 | 2026-04-26 | **Phase 4.1 dashboard for ADMIN+SM.** New `frontend/src/routes/(nexus)/dashboard/+page.svelte` consuming new `GET /api/v1/dashboard/summary` (ADMIN global, SM PROCUREMENT-scoped, others empty payload). 4 KPIs (Pending POs, Awaiting acceptance, In production, Outstanding A/P) + Awaiting-acceptance panel + Recent activity panel via Phase 4.0 primitives (AppShell, KpiCard, ActivityFeed, PanelCard, EmptyState). Other roles get a thin placeholder. Pre-revamp `frontend/src/routes/dashboard/+page.svelte` and its specs deleted. Sidebar/permissions matrix patched: FREIGHT_MANAGER drops POs, VENDOR adds Products, PROCUREMENT_MANAGER promoted to SM-equivalent (read-only). Root layout `isRevampRoute` extended for `/dashboard*`. New `nexus-dashboard.spec.ts` (6 tests). Test fixture updates in `auth-flow.spec.ts`, `notification-bell.spec.ts`, `role-rendering.spec.ts`, `invoice-list.spec.ts` per route migration. 595 backend + 145 Playwright green. |
| 072 | 2026-04-26 | **Phase 4.1 dashboard polish.** KPI cards 1-3 now show USD value alongside count via `KpiCard.delta` chip (`pending_pos_value_usd`, `awaiting_acceptance_value_usd`, `in_production_value_usd` added to backend response). Recent activity panel curated: `_DASHBOARD_EXCLUDED_EVENTS` frozenset filters line-level negotiation events + force transitions + convergence + email-send failures; `target_role=user.role.value` passed to `list_recent` for SM (ADMIN sees all). Activity rows now render as `<a>` links to `/po/[id]` or `/invoice/[id]` when the role has `canViewPOs`/`canViewInvoices`, else as non-clickable `<span>`. `TopBar` hamburger hidden at `≥769px` viewports. Backlog: sidebar collapse mode, ACTION_REQUIRED row pinning. 595 backend + 146 Playwright green. |
| 073 | 2026-04-26 | **FREIGHT_MANAGER dashboard.** New FM branch on `(nexus)/dashboard/+page.svelte` replacing the placeholder. 4 KPIs (Ready batches, Shipments in flight, Pending invoices + USD, Docs missing) + 3 panels (Ready batches, Pending invoices, Recent activity). Backend `/dashboard/summary` extended with optional `fm_kpis: FmKpis \| None`, `fm_ready_batches`, `fm_pending_invoices` fields (additive — ADMIN/SM unchanged in shape and content). FM-specific KPI 1 (Ready batches) uses existing `READY_TO_SHIP` milestone as proxy until the new `READY_FOR_SHIPMENT` milestone ships in a future iter. KPI 4 (Docs missing) reads from `shipment_document_requirements` PENDING rows. `canViewPOs` widened to include FREIGHT_MANAGER for ready-batch click-through (sidebar visibility unchanged, decoupled per iter 067). Backlog: `READY_FOR_SHIPMENT` milestone, vendor → FM mapping, OpEx/Freight invoice approval routing (SM owns procurement only), shipment seed extension. 596 backend + 149 Playwright green. |
| 074 | 2026-04-26 | **Shipment booking + READY_FOR_SHIPMENT milestone rename.** `ProductionMilestone.READY_TO_SHIP` renamed to `READY_FOR_SHIPMENT` (5-stage sequence preserved); one-shot `init_db` UPDATE migrates existing rows. `ShipmentStatus` extended with `BOOKED` and `SHIPPED`; new sequence: DRAFT > DOCUMENTS_PENDING > READY_TO_SHIP > BOOKED > SHIPPED. New `Shipment.book_shipment(carrier, booking_reference, pickup_date)` and `Shipment.mark_shipped()` methods with status guards and non-empty validation. Schema adds carrier/booking_reference/pickup_date/shipped_at columns (all nullable). New endpoints: `POST /shipments/{id}/book` and `POST /shipments/{id}/ship` (ADMIN+SM+FREIGHT_MANAGER). New activity events `SHIPMENT_BOOKED` + `SHIPMENT_SHIPPED` (LIVE, target_role=SM). FM dashboard `_SHIPMENT_IN_FLIGHT_STATUSES` now includes BOOKED (excludes SHIPPED). Seed reserves first accepted PO at READY_FOR_SHIPMENT with no shipment (drives ready_batches KPI); remaining shipments span all 5 statuses with carrier metadata on BOOKED + SHIPPED rows. Frontend types updated (no booking UI yet — backlog). 610 backend + 149 Playwright green. |
| 075 | 2026-04-26 | **PROCUREMENT_MANAGER dashboard parity.** PM now receives the SM dashboard payload: same `procurement_only` scoping, same KPI grid, same panels, with the activity feed filtered by `target_role=PROCUREMENT_MANAGER`. Backend renames `_ADMIN_OR_SM` to `_DASHBOARD_FULL_LAYOUT_ROLES` and adds PM; `TargetRole` enum gains `PROCUREMENT_MANAGER` so activity rows targeted at PM no longer raise `ValueError` in `_row_to_entry`. Frontend `isFullLayout` extended to PM. Backlog: fan-out of activity events to PM (today the EVENT_METADATA default routes everything to SM, so PM's activity panel is near-empty on a fresh seed). 612 backend + 150 Playwright green. |
| 076 | 2026-04-27 | **`/po` list revamp (Phase 4.2 Tier 1).** Replaces inline filter bar / table / pagination / bulk toolbar with the new Phase 4.2 component set in `frontend/src/lib/po/`: `PoListFilters`, `PoListBulkBar`, `PoStatusPills`, `PoListTable`, `PoListPagination`. Adds `marketplace` filter (4-enum) + `canBulkPO` permission + responsive layout (table at desktop, stacked cards at 390px) + dashboard-grade empty/loading/error states (`LoadingState` overlay preserves prior rows on filter refetch per G-06). Old `frontend/src/routes/po/+page.svelte` removed; route now served from `(nexus)/po/+page.svelte` so it inherits AppShell + Sidebar + TopBar (matches iter 071 dashboard precedent). `isRevampRoute` extended for `/po*`. Existing `po-list.spec.ts` migrated to testid selectors (`po-filter-*`, `po-bulk-bar`, `po-bulk-action-{action}`, `po-table`, `po-row-{id}`, `po-pagination`, `po-status-partial`, `po-list-loading`, `po-page-header-action`); ~30 brittle class/tag assertions retired. `po-negotiation-events.spec.ts` and `role-rendering.spec.ts` updated for new selectors (status pill markup + New PO is now a button not a link). New CLAUDE.md selector policy bans class/tag/bare-text selectors in new tests; primitive `label`/`aria-label` plumbing queued in backlog. 612 backend + 156 Playwright green. |

---

## What exists and works

- Full PO lifecycle: create, submit, accept/reject, revise, resubmit
- Full invoice lifecycle: create from PO, submit, approve, pay, dispute, resolve
- Over-invoicing guard (cumulative quantity check)
- OPEX invoicing (free-form lines)
- PDF export for POs and invoices
- Production milestone tracking with strict sequencing
- Activity log powering dashboard feed and notification bell
- Vendor management with types and country validation
- Product catalog (vendor-scoped, certification flag)
- Reference data for all dropdowns
- Bulk actions on PO list
- Dashboard with summary cards, production pipeline, overdue alerts
- Postgres 16 with asyncpg connection pool (migrated from SQLite in 029a)
- Seed script for demo data (`tools/seed_data.py`)
- User entity with 6 roles (ADMIN, SM, VENDOR, FREIGHT_MANAGER, QUALITY_LAB, PROCUREMENT_MANAGER) and 3 statuses (ACTIVE, INACTIVE, PENDING)
- WebAuthn passkey registration/login, cookie sessions (itsdangerous), session middleware
- Bootstrap flow (first user becomes ADMIN), invite-only registration
- API role guards on all endpoints (ADMIN bypass, per-role access control)
- Dev-login endpoint for local development (`GET /api/v1/auth/dev-login`)
- Vendor-scoped data access: VENDOR users see only their vendor's POs, invoices, milestones, activity, and dashboard data (check_vendor_access helper, 404 on ownership mismatch)
- Frontend auth flow: login page (/login), invite-only register page (/register?username=), bootstrap page (/setup), layout session check with redirect to /login, logout button, deep link preservation
- All frontend API calls send credentials (cookies) and redirect to /login on 401
- Frontend role-conditional rendering: nav links, page-level redirects, action buttons all respect user role. SM/ADMIN see management controls, VENDOR sees accept/reject/invoice/milestone controls, QUALITY_LAB sees products only, FREIGHT_MANAGER sees POs read-only
- Backend activity endpoints accept optional target_role filter for role-scoped feeds
- Document storage: upload/download/delete/list API backed by local filesystem (`uploads/`), metadata in `files` table with entity_type/entity_id index, PDF-only with 10MB limit, filename sanitization, path traversal protection, require_auth on all endpoints
- PO marketplace field (AMZ, 3PL_1, 3PL_2, 3PL_3) with reference data validation and PO list filter
- LineItem product_id FK to product catalog (loose, no cross-vendor validation yet)
- Vendor address and account_details fields
- Product manufacturing_address field
- QualificationType entity with join table replacing requires_certification boolean; CRUD and product assignment/removal API
- Certificate entity with computed EXPIRED status (not persisted) and document upload; CERT_UPLOADED activity event
- Line-level PO negotiation: vendor and SM exchange modifications over up to 2 rounds via modify_line/accept_line/remove_line/submit_response; force-accept and force-remove overrides available at round 2 for SM; qty=0 on modify routes directly to REMOVED; line_edit_history audit trail per field change
- PackagingSpec with COLLECTED status, file upload, packaging readiness endpoint per product/marketplace; PACKAGING_COLLECTED and PACKAGING_MISSING activity events
- PDF export filters to ACCEPTED lines with MODIFIED stamp on negotiated POs; PO list shows Partial pill when ACCEPTED+REMOVED mix exists and Modified pill during negotiation
- Advance payment gate: payment_terms.has_advance drives whether mark-advance-paid is required; once marked paid or first milestone posted, post-acceptance line add/remove window closes
- Post-acceptance line modification: SM can add or remove lines on ACCEPTED POs while gate is open; removal blocked when any invoice or shipment references the line
- PO line negotiation UI: vendor and SM exchange modifications per line with inline diff, edit-history timeline, force-override at round 2 behind a confirmation dialog; line-level status pills reflect PENDING/MODIFIED_BY_VENDOR/MODIFIED_BY_SM/ACCEPTED/REMOVED
- Email notifications via SMTP: po_accepted, po_modified, po_line_modified, and po_advance_paid templates dispatched from activity events to role-scoped recipients; development mode logs without network access; failures recorded as EMAIL_SEND_FAILED activity rows
- PO submit/resubmit return POSubmitResponse wrapper carrying advisory cert_warnings (per line item, MISSING/EXPIRED). Lines without product_id and POs without marketplace skip the gate. (iter 039)
- QC_PASSED milestone fans out CERT_REQUESTED activity to QUALITY_LAB for products lacking valid certs. (iter 039)
- Shipment aggregate: create from accepted PO with cumulative shipped-quantity guard, multiple shipments per PO allowed, status DRAFT > DOCUMENTS_PENDING > READY_TO_SHIP, per-line weights/dims/package_count/dimensions/country_of_origin editable in DRAFT/DOCUMENTS_PENDING. Frontend shipment detail page (`/shipments/[id]`) with inline editing. (iters 043, 044)
- Packing list PDF generated from shipment + PO + vendor data; ReportLab pattern matches PO/Invoice PDFs. None-valued weights render as "-". (iter 044)
- Export commercial invoice PDF on Shipment with deterministic CI number CI-{shipment_number}; HS code + unit price come from PO line items, weights from shipment line items, line value = qty × unit_price. (iter 045)
- Shipment document requirements + readiness gate: PACKING_LIST and COMMERCIAL_INVOICE requirements auto-seeded on submit-for-documents; SM/FREIGHT_MANAGER can add custom user-defined types. Upload against a requirement transitions it to COLLECTED and records DOCUMENT_UPLOADED activity. mark-ready blocked unless documents + certificates + packaging all pass; 409 returns structured ReadinessResult with missing items. (iter 046, backend only)
- Phase 4.0 primitive library (iters 062-069): design tokens in `global.css`, `(nexus)` SvelteKit layout group with `/_smoke` sentinel route, `/ui-demo` gallery route + `/ui-demo/shell` AppShell preview (none linked from nav). Twenty-six Svelte 5 primitives under `frontend/src/lib/ui/`: 7 leaves, 5 composites (incl. KpiCard with icon slot), 6 display+state, 3 table+headers, 5 shell (Sidebar with sections+footer+roleLabel, TopBar, AppShell, UserMenu) + `sidebar-items.ts` + `redirects.ts`. All use `ui-<name>` scoped outermost class. Tests: `primitives.spec.ts` 33, `sidebar-items.spec.ts` 7, `redirects.spec.ts` 3, `nexus-shell.spec.ts` 3 (46 new primitive-layer tests, 148 Playwright total including pre-revamp flows). Input surfaces `aria-invalid`. LoadingState honors `prefers-reduced-motion`. UserMenu collapses meta on mobile and gates Switch role behind `import.meta.env.DEV`. DataTable generic + server-driven pagination. AppShell composes Sidebar + TopBar + ErrorBoundary + mobile off-canvas drawer. Redirect infrastructure ready for aggregate-phase retirements. No user-facing aggregate page consumes these yet.
- **Phase 4.0 foundation complete (iters 061-070)**: 26 primitives, design tokens, `(nexus)` shell, redirect infrastructure, axe AA clean. Ready for Phase 4.1 (Dashboard) to consume the primitives on a new branch.
- **Phase 4.1 dashboard live (iters 071-073, 075)** at `(nexus)/dashboard`: ADMIN/SM/PROCUREMENT_MANAGER see the four-KPI grid (Pending POs, Awaiting acceptance, In production, Outstanding A/P) with USD value chips on KPIs 1-3, awaiting-acceptance panel, and curated recent activity (line-level negotiation, force transitions, convergence, and email-failures filtered out via `_DASHBOARD_EXCLUDED_EVENTS`). Activity rows render as PO/invoice deep links when the role can view the target, else as plain spans. FREIGHT_MANAGER sees its own four-KPI branch (Ready batches, Shipments in flight, Pending invoices + USD, Docs missing) plus three FM panels. PM activity panel near-empty until events fan out to PROCUREMENT_MANAGER (backlog).
- **Phase 4.2 `/po` list live (iter 076)** at `(nexus)/po`: replaces the pre-revamp inline filter bar / table / pagination / bulk toolbar with `PoListFilters` + `PoListBulkBar` + `PoStatusPills` + `PoListTable` + `PoListPagination` from `frontend/src/lib/po/`. Marketplace filter (4-enum) + responsive layout (table at desktop, stacked cards at 390px) + `LoadingState` overlay preserves prior rows on filter refetch + role-aware selection column and New PO CTA (PROCUREMENT_MANAGER + FREIGHT_MANAGER are read-only). `canBulkPO` permission added. Test selectors migrated to testid surface (`po-filter-*`, `po-bulk-bar`, `po-bulk-action-{action}`, `po-table`, `po-row-{id}`, `po-pagination`, `po-status-partial`, `po-list-loading`, `po-page-header-action`).

## What does not exist yet

### Phase 4 UI revamp (iters 049-055, in planning by user)
The full design system + page redesign covering every existing page (~22 routes). User is drafting the plan based on a Lovable mock. The following backend-complete features are waiting on Phase 4 to ship their UI:
- **Iter 040 — Certificate UI**: product detail qualification list, certificate upload flow, expiry alerts on dashboard, PO creation cert-warning banner. Quality gate backend already returns warnings (iter 039).
- **Iter 046 frontend**: Documents section per shipment with status pills + Generate / Upload actions, Add Requirement button, Readiness panel (Documents / Certificates / Packaging pass-fail with details), Mark Ready to Ship button gated by readiness.
- **Iter 048 dashboard**: shipment counts by status (DRAFT / DOCUMENTS_PENDING / READY_TO_SHIP), certificate expiry alerts, packaging collection progress per marketplace, notification bell routing for new event types (CERT_REQUESTED, DOCUMENT_UPLOADED, etc.).

### From the backlog (PO confirmation module)
- Overdue PO status (time-based trigger past required delivery date)
- Mobile layout
- Custom value approval for reference data dropdowns
- Dedicated `/api/v1/po/ids` endpoint for cross-page selection beyond 200
- Live/historical exchange rates
- Buyer as first-class entity (currently hardcoded)

### From the backlog (auth and user management)
- Multiple passkeys per user (register backup device for recovery)
- Admin re-invite flow for lost device (reset to PENDING, user registers new passkey)
- Credential reset endpoint: `POST /api/v1/users/{id}/reset-credentials` (revoke all passkeys, reset to PENDING)
- User management CRUD endpoints: list, get, update, deactivate, reactivate (iter 031 only implemented invite)
- User management frontend page (`/users`) — list, invite, deactivate, reset credentials
- VENDOR user's vendor gets deactivated — make vendor-scoped data read-only
- Stale PENDING user cleanup (invited but never registered)
- Proxy access for internal leave coverage (delegation table, time-bounded, audit trail)
- Email/notification for invite links (manual link sharing works for small teams)
- PROCUREMENT_MANAGER role permissions: enum value exists from iter 030, no endpoint guards wired. Future iteration to define and wire access (read-only PO/vendor/invoice visibility, pay/dispute invoices). Frontend: define redirect behavior for PM on non-dashboard pages.
- User management page (`/users`): ADMIN can list, invite, deactivate, reactivate users, reset credentials. Nav "Users" link hidden until page exists.
- Invite token security: replace `/register?username=<name>` with `/register?token=<uuid>`. Add invite_token column to users table, set on invite, cleared after registration. Prevents guessable registration URLs.
- Welcome email on invite: send registration link via email when admin invites a user. Currently manual link sharing.
- ADMIN inherits all actions: `canPostMilestone` is currently exact-match VENDOR only. ADMIN should be able to exercise any role-scoped action (post milestones, submit vendor responses, etc.) for support and debugging. Audit every `isExact` usage in `permissions.ts` and the backend role guards; convert to `is(role, ...) || role === 'ADMIN'` unless there is a concrete reason to keep a capability VENDOR-only.

### From the backlog (UX)
- Error handling across all users and workflows: define and surface user-facing error states for every endpoint (validation errors, conflict errors, not-found, auth failures). Currently errors are ad hoc per endpoint with no consistent frontend treatment.
- Recent activity redesign: club PO and invoice activity into a unified feed (currently separate activity streams). Needs discussion on grouping, filtering, and presentation.
- Deep link preservation on register/bootstrap: deep link preservation on /login is done (iter 033). If an invited user opens a deep link (e.g. `/po/123`) and lands on `/register` or `/setup`, the original path is still lost. After registration/bootstrap they go to `/dashboard`, not the deep link. Low priority since registration is a one-time event.
- Session cookie path/domain audit: verify the session cookie is set with `path=/` and appropriate domain/SameSite attributes for production deployment behind a reverse proxy. Currently works in dev via Vite proxy.
- DataTable primitive extension: promote selection column + snippet cell support out of `PoListTable` into the shared `frontend/src/lib/ui/DataTable.svelte` primitive, so other list pages can adopt the same selection contract without copy-paste. Phase 4.x cleanup task.
- Primitive `label` / `aria-label` plumbing: every primitive in `frontend/src/lib/ui/` already accepts a `testid` prop (25 of 26 today), but role-based queries (`getByRole`, `getByLabel`) are not equally easy because most primitives don't expose a `label` prop forwarding to `aria-label` or a `<label>` element. Retrofit the primitives so role queries are first-class, per the test selector policy in [CLAUDE.md](CLAUDE.md). One Sonnet iter, mechanical change.
- FREIGHT_MANAGER PO detail visibility: today `canViewPOs` includes FREIGHT_MANAGER for the iter 073 ready-batch click-through (FM lands on a PO detail to plan shipping). FM sees an action rail with Download PDF only. Revisit whether FM should see PO detail at all or whether the ready-batch surface should expose only the shipping-relevant fields directly without exposing the full PO. Tier 0 G-28 (role coverage matrix) territory.

### From the backlog (infrastructure)
- File endpoint role guards: restrict upload/download/delete by role and entity ownership. Currently any authenticated user can access any file. Consumers now exist (certificates iter 038, packaging iter 042, shipment requirements iter 046), so the guard rules can be defined per entity_type and wired in.
- File upload entity existence validation: upload endpoint accepts any entity_type/entity_id without checking the entity exists. Decide per-feature whether to validate at upload time or at the consuming feature level.
- Vendor catalog / vendor-SKU mapping: products are vendor-agnostic, but a vendor's catalog defines which SKUs they offer. Line item product_id should reference a SKU in the vendor's catalog. New entity needed.
- HTTPS for non-localhost deployment (WebAuthn requires HTTPS or localhost; needed before first external demo)
- Database migration tool (alembic or similar; needed once real data exists that can't be dropped and recreated)
- Session revocation ("log out all devices"; currently relies on cookie expiry + user status check)
- Self-service vendor onboarding (currently invite-only; needed if vendors should sign up without admin)
- Dev-login UX: dev-login is a GET endpoint that returns JSON and sets a cookie, but doesn't redirect to the app. After hitting dev-login the user must manually navigate to /dashboard. Either redirect dev-login to /dashboard, or add a "Dev Login" button on the /login page when running in development mode.
- Remove dev-login endpoint before production deployment

### From the roadmap (post-confirmation)
1. **Quality labs frontend** — backend done (iters 036a, 038, 039); frontend cert UI is iter 040 (folded into Phase 4).
2. **Bill of Lading + Certificate of Origin + Insurance Certificate + EEI/AES** — additional shipment document types beyond packing list and commercial invoice. Iter 046 supports user-defined document_type strings, so adding these is configuration; system-generated BoL or chamber-of-commerce CoO integration would be new iters.
3. **Shipment document validation (agents/OCR)** — AI reads uploaded docs, flags discrepancies against shipment + PO data.
4. **Invoice upload** — accept vendor-uploaded invoice files (PDF/image).
5. **Invoice validation (agents)** — AI cross-checks uploaded invoice against PO/shipment data.
6. **Consolidation algorithm** — combine multiple shipments (explicitly deferrable).
7. **Packaging file collections for AMZ shipments** — Amazon-specific packaging requirement templates beyond the generic PackagingSpec.
8. **Shipment booking** — carrier selection, booking creation.
9. **Shipment tracking** — carrier integration, status updates, ETA.
10. **Customs validation** — HS code verification, origin/destination rules, compliance checks.

### Dependencies in the roadmap
- Shipment doc validation (3) needs an uploaded-doc corpus from iter 046 in production use first.
- Invoice upload (4) before invoice validation (5).
- Shipment booking (8) before tracking (9).
- HS codes + country of origin (already on PO line items + shipment line items) feed customs validation (10).

### The agent layer (items 3, 5, 10)
These are the product differentiators. Items 3, 5, and 10 read uploaded documents, cross-reference them against structured data (PO, shipment, certificates), and flag discrepancies. The CRUD workflow is the infrastructure that produces the structured data those agents read.

---

## Domain terms introduced by iteration

| Iteration | New domain terms |
|-----------|-----------------|
| 01-02 | PurchaseOrder, LineItem, POStatus (Draft/Pending/Accepted/Rejected/Revised) |
| 03-04 | Vendor, VendorStatus, ReferenceData (currencies, incoterms, payment terms) |
| 05 | PODocumentExport |
| 06 | PaginatedList, POSearch |
| 07 | Dashboard (read model) |
| 08-10 | BulkAction, CrossPageSelection, ValidActions |
| 11 | VendorType (Procurement/OpEx/Freight/Misc), POType |
| 12 | Invoice, InvoiceLineItem, InvoiceStatus, OverInvoicingGuard, DisputeReason |
| 13 | ReferenceLabel |
| 14 | RemainingQuantity |
| 16 | InvoiceDocumentExport |
| 17-19 | Milestone (5 stages), MilestoneUpdate, MilestoneOrderEnforcement, OverdueProduction |
| 20 | HSCodeFormat |
| 21 | OPEXInvoice |
| 23-24 | ActivityLogEntry, EventType, NotificationCategory, TargetRole |
| 25 | VendorCountryValidation |
| 27 | FieldImmutability (mutable-by-status rules) |
| 29 | Product, RequiresCertification |
| 030 | User, UserRole (6 values), UserStatus (3 values), WebAuthnCredential, SessionCookie, Bootstrap |
| 031 | RoleGuard, RequireRole, RequireAuth |
| 032 | VendorScopedAccess |
| 034 | RolePermission, RoleConditionalRendering |
| 035 | FileMetadata, EntityAttachment |
| 036 | Marketplace, ManufacturingAddress, VendorAccountDetails |
| 036a | QualificationType, ProductQualification (join) |
| 037 | LineItemStatus (Pending/Accepted/Rejected), AcceptLinesRequest |
| 056 | LineItemStatus (new: MODIFIED_BY_VENDOR/MODIFIED_BY_SM/REMOVED), POStatus.MODIFIED, LineEditHistory, LineEditHistoryEntry, NegotiationRound, RoundCount, LastActorRole, ForceOverride, Convergence, EDITABLE_LINE_FIELDS, HandOff |
| 057 | LineNegotiationRow, ModifyLineModal, LineDiff, EditHistoryTimeline, SubmitResponseBar (UI components); CanActOnNegotiation; ForceOverrideConfirmation |
| 041 | PackagingSpec, PackagingSpecStatus |
| 038 | Certificate, CertificateStatus (Pending/Valid/Expired-computed) |
| 042 | PackagingCollection, PackagingReadiness |
| 058 | ActivityEvent.{PO_LINE_MODIFIED, PO_LINE_ACCEPTED, PO_LINE_REMOVED, PO_FORCE_ACCEPTED, PO_FORCE_REMOVED, PO_MODIFIED, PO_CONVERGED}, PartialPill, ModifiedPill, PDFAcceptedOnly |
| 059 | PaymentTermMetadata, AdvancePayment, RequiresAdvance, PostAcceptanceGate, DownstreamArtifact, LineHasDownstreamArtifactError, FirstMilestonePostedAt, PO_ADVANCE_PAID, PO_LINE_ADDED_POST_ACCEPT, PO_LINE_REMOVED_POST_ACCEPT |
| 060 | EmailService, NotificationDispatcher, EmailTemplate, RecipientResolution, FakeEmailService, EMAIL_SEND_FAILED, SMTP_ENV_VARS |
| 043 | Shipment, ShipmentLineItem, ShipmentStatus (DRAFT/DOCUMENTS_PENDING/READY_TO_SHIP), ShipmentNumber, CumulativeShippedQuantityGuard |
| 039 | CertWarning, CertWarningReason (MISSING/EXPIRED), POSubmitResponse, QualityGate, CERT_REQUESTED, TargetRole.QUALITY_LAB, TargetRole.FREIGHT_MANAGER |
| 044 | ShipmentLineItem.{net_weight, gross_weight, package_count, dimensions, country_of_origin}, PackingListPDF, ShipmentLineItemUpdate |
| 045 | CommercialInvoicePDF, CINumber (deterministic CI-{shipment_number}, not persisted) |
| 046 | ShipmentDocumentRequirement, DocumentRequirementStatus (PENDING/COLLECTED), ReadinessResult, AutoGeneratedRequirement, DOCUMENT_UPLOADED, EntityType.SHIPMENT, MarkReadyGate |
| 074 | ShipmentStatus.BOOKED, ShipmentStatus.SHIPPED, BookingMetadata (carrier, booking_reference, pickup_date), ShippedAt, BookShipment, MarkShipped, SHIPMENT_BOOKED, SHIPMENT_SHIPPED, ProductionMilestone.READY_FOR_SHIPMENT (renamed from READY_TO_SHIP) |
