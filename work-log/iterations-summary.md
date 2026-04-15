# Iterations Summary

> Single-file context for future conversations. Replaces reading 29 individual iteration docs.
> Last updated: 2026-04-15 (iterations 029a, 030, 031 closed).

---

## Product vision

Turbo Tonic is a vendor portal for purchase order confirmation, invoicing, production tracking, and shipment booking and tracking logistics. The CRUD workflow is table stakes. The differentiator is an agent layer that reads, validates, and flags documents (shipment docs, invoices, customs declarations). Two exit paths after customs validation ships: (a) horizontal B2B SaaS for procurement/logistics/invoicing companies, or (b) vertical industry specialization.

## Tech stack

Python 3.13, FastAPI, Postgres 16 (asyncpg, connection pool), WebAuthn/passkeys + cookie sessions. Frontend: SvelteKit 2 + Svelte 5, adapter-static. Package manager: uv (backend), npm (frontend), nvm for Node. Local dev: Postgres via Homebrew (docker-compose.yml available for Docker environments).

## Current domain model (as of iteration 029)

### Aggregates
- **PurchaseOrder** — Draft > Pending > Accepted | Rejected > Revised > Pending. Contains LineItems, RejectionHistory. Types: PROCUREMENT, OPEX.
- **Invoice** — Draft > Submitted > Approved > Paid | Disputed > Resolved. Linked to PO. Over-invoicing guard checks cumulative quantities against PO line items.
- **Vendor** — Active | Inactive. Types: PROCUREMENT, OPEX, FREIGHT, MISCELLANEOUS. Country validated against reference data.
- **Product** — Vendor-scoped catalog (vendor_id + part_number unique). First attribute: requires_certification.

### Supporting concepts
- **Milestone** — RAW_MATERIALS > PRODUCTION_STARTED > QC_PASSED > READY_TO_SHIP > SHIPPED. Strict sequence enforcement. Attached to PO.
- **ActivityLog** — Immutable event stream. Categories: LIVE, ACTION_REQUIRED, DELAYED. Target roles: SM, VENDOR. Powers dashboard feed and notification bell.
- **Reference data** — 30 currencies, 11 incoterms, 17 payment terms, 31 countries, 50+ ports, USD exchange rates.

### Database tables
purchase_orders, line_items, rejection_history, vendors, products, invoices, invoice_line_items, milestone_updates, activity_log.

## Frontend routes

| Route | Purpose |
|-------|---------|
| `/dashboard` | PO/invoice/vendor summary cards, activity feed, production pipeline, overdue table |
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

## API surface

- **PO**: CRUD, submit, accept, reject, resubmit, bulk transition, PDF export
- **Invoice**: CRUD, submit, approve, pay, dispute, resolve, remaining quantities, PDF export, bulk PDF
- **Vendor**: CRUD, deactivate, reactivate
- **Product**: CRUD (POST, GET list, GET by id, PATCH)
- **Milestone**: list by PO, post milestone
- **Activity**: list, unread count, mark read
- **Reference data**: all lookups in one GET

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

## What does not exist yet

### From the backlog (PO confirmation module)
- Roles: SM vs Vendor views (same data, different controls) — in progress (iter 032-034)
- Overdue PO status (time-based trigger past required delivery date)
- Mobile layout
- Custom value approval for reference data dropdowns
- Dedicated `/api/v1/po/ids` endpoint for cross-page selection beyond 200
- Live/historical exchange rates
- Buyer as first-class entity (currently hardcoded)
- Partial PO acceptance at line-item level (iter 28 scoped, not built)

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
- PROCUREMENT_MANAGER role permissions: enum value exists from iter 030, no endpoint guards wired. Future iteration to define and wire access (read-only PO/vendor/invoice visibility, pay/dispute invoices)
- Invite token security: replace `/register?username=<name>` with `/register?token=<uuid>`. Add invite_token column to users table, set on invite, cleared after registration. Prevents guessable registration URLs.
- Welcome email on invite: send registration link via email when admin invites a user. Currently manual link sharing.

### From the backlog (UX)
- Error handling across all users and workflows: define and surface user-facing error states for every endpoint (validation errors, conflict errors, not-found, auth failures). Currently errors are ad hoc per endpoint with no consistent frontend treatment.
- Recent activity redesign: club PO and invoice activity into a unified feed (currently separate activity streams). Needs discussion on grouping, filtering, and presentation.

### From the backlog (infrastructure)
- HTTPS for non-localhost deployment (WebAuthn requires HTTPS or localhost; needed before first external demo)
- Database migration tool (alembic or similar; needed once real data exists that can't be dropped and recreated)
- Session revocation ("log out all devices"; currently relies on cookie expiry + user status check)
- Self-service vendor onboarding (currently invite-only; needed if vendors should sign up without admin)
- Remove dev-login endpoint before production deployment

### From the roadmap (post-confirmation)
1. **Quality labs** — certificate management, lab results, product-level cert requirements
2. **Batch creation of partial PO shipments** — Shipment as new aggregate, split PO into shipments
3. **Shipment document generation** — packing list, commercial invoice, bill of lading
4. **Shipment document validation (agents/OCR)** — AI reads uploaded docs, flags discrepancies
5. **Invoice upload** — accept vendor-uploaded invoice files (PDF/image)
6. **Invoice validation (agents)** — AI cross-checks uploaded invoice against PO/shipment data
7. **Consolidation algorithm** — combine multiple shipments (explicitly deferrable)
8. **Packaging file collections for AMZ shipments** — Amazon-specific packaging requirements
9. **Shipment booking** — carrier selection, booking creation
10. **Shipment tracking** — carrier integration, status updates, ETA
11. **Customs validation** — HS code verification, origin/destination rules, compliance checks

### Dependencies in the roadmap
- Quality labs can run in parallel with shipment work (product.requires_certification is the hook)
- Shipment creation (2) before shipment docs (3) before doc validation (4)
- Invoice upload (5) before invoice validation (6)
- Shipment booking (9) before tracking (10)
- HS codes + country of origin (already on line items) feed customs validation (11)
- Auth/roles is a cross-cutting concern that can slot in at any point but gets harder to retrofit the more UI exists

### The agent layer (items 4, 6, 11)
These are the product differentiators. The CRUD workflow (items 1-3, 5, 7-10) is infrastructure. The agent items read uploaded documents, cross-reference them against structured data, and flag discrepancies. This is what makes the system more than a form-filling app.

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
