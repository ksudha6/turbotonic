# UI Revamp Plan (Phase 4, iters 049-055)

**Source of truth for visuals:** Lovable mock at https://turbotonic.lovable.app
**Scope rule:** Only what is visible in the mock ships in Phase 4. Everything else goes to the backlog and ships later.

> Revision 2 (2026-04-19): Mock expanded to include create forms, detail pages, Settings, Help, and a role switcher. Scope grew from 5 pages to 16 pages plus a role-conditional sidebar.

---

## Context

Phase 1 (iters 001-029) built the core domain. Phase 2 (030-034) added auth and roles. Phase 3 (035-048, partially closed) builds export readiness. Phase 4 redesigns the presentation layer without changing business logic or API contracts. The mock is the visual brief for Phase 4.

Today the frontend is SvelteKit 2 + Svelte 5 with ad-hoc styling in `frontend/src/routes/*/+page.svelte`. Global tokens live in `$lib/styles/global.css`. There is no shared component library; each page rolls its own buttons, tables, and cards. The mock introduces a consistent shell (sidebar + top bar), consistent KPI cards, a consistent table pattern across five list pages, consistent create-form pages, and consistent detail-page layouts.

## JTBD (Jobs To Be Done)

- **As any role signing in**, I want a sidebar that only shows the aggregates I work with, so my daily navigation does not include links I never use.
- **As a Supply Manager on the Overview**, I want the five most important metrics and the four most important live feeds on one screen, so I can triage without opening each list.
- **As anyone scanning a list**, I want every list page to use the same header, KPI row, and table structure, so I do not re-learn each page.
- **As anyone clicking into a row**, I want a two-column detail page (attributes + related entities/timeline) with a status badge in the header, so the same pattern applies across aggregates.
- **As anyone creating a new entity**, I want a single "Details" card with the minimum necessary fields and explicit Cancel / Create buttons, so creation is the same shape everywhere.
- **As a mobile user**, I want the shell to collapse and list pages to remain usable at 390px width.

Non-goals for Phase 4: changing any API contract, adding new domain aggregates (RFQ is a stub only), building real notification preferences or workspace metadata (Settings is decorative), building full-featured forms (the mock's forms are minimal; rich editing stays on today's pages).

---

## Scope

### In scope (pages present in the mock)

| Mock route | Today's route | What Phase 4 builds |
|---|---|---|
| `/` (Overview) | `/dashboard` | Redesign dashboard to match mock layout: 4 KPI cards, Active production + Recent activity split, Pending RFQs + Shipments in motion split. |
| `/rfqs` | none | Stub list with seed data. RFQ is not a real aggregate. |
| `/rfqs/new` | none | Stub create form. `Create RFQ` button writes to local seed store for the session, then navigates to `/rfqs/:id`. Not persisted. |
| `/rfqs/:id` | none | Stub detail page. Two-column: Summary card + Quotes received panel. |
| `/production` | none (functionality lives inside `/po/[id]`) | New list view over existing `PurchaseOrder` + `MilestoneUpdate` data. URL is `/production`. |
| `/production/new` | none (there is `/po/new`) | Stub form with 5 fields: Linked RFQ, Vendor, Product, Quantity, ETA. In v1 of Phase 4 this is a decorative form that points back to today's `/po/new` on submit. |
| `/production/:id` | `/po/:id` | New detail page. Two-column: Order details card with progress bar + Milestones timeline. Shows real PO data. Replaces today's `/po/:id` inside the redesigned shell. |
| `/shipments` | none (Phase 3, not yet built) | Stub list with seed data until Phase 3 iter 043 ships the Shipment aggregate. |
| `/shipments/new` | none | Stub form. 6 fields: Order ID, Carrier, Origin, Destination, Mode (select), ETA. Not persisted. |
| `/shipments/:id` | none | Stub detail page. Two-column: Shipment details card + Tracking timeline. Seed data. |
| `/invoices` | `/invoices` | Redesign existing invoice list. |
| `/invoices/new` | none (today's flow is inside `/po/:id`) | New create form outside the PO. 6 fields: Vendor, Order ID, Amount, Currency, Issued, Due. In v1 this writes to the real backend via existing invoice endpoints, with the form adapting to existing API requirements (hidden defaults for fields the mock omits). |
| `/invoices/:id` | `/invoice/:id` | New detail page inside the redesigned shell. Two-column: Invoice card + Line items list. Replaces today's `/invoice/:id`. |
| `/settings` | none | Stub page with Profile section (Name, Workspace, Plan — display-only) and Notifications section (3 toggles with local state; not persisted). |
| `/help` | none | Static FAQ page with 4 questions. |

### The role switcher

The mock includes a role dropdown in the top-right user pill. Clicking it opens a "Switch role" menu with 4 options:

- **VN** Vendor
- **SM** Supply Manager
- **FM** Freight Manager
- **FN** Finance Manager

Selecting a role changes the sidebar. No other part of the UI changes (same Overview content, same list data). In the mock this is a UI-only demo selector stored in React state.

In production, the current user's role comes from the session (set during login by WebAuthn). Two options for the redesign:

- **A.** Keep the role switcher as a demo tool in dev only. Hidden behind `import.meta.env.DEV`. In production the pill renders the user's actual role without a dropdown.
- **B.** Replace the role switcher with a user menu (name, role, Log out). No role switching in production.

Tentative: **B**. Reasoning: role switching in a real session is a security risk and confuses audit logs. The pill becomes a user menu that shows the user's actual role label plus a Log out action. Backlog: admin impersonation as a separate, audited feature.

### Role-conditional sidebar matrix

Derived from the mock's Switch role demo. This is the visible-nav matrix. Data scoping stays backend-driven (today's `permissions.ts` rules continue to apply).

| Role | Overview | RFQs | Production | Shipments | Invoices | Settings | Help |
|---|---|---|---|---|---|---|---|
| **SM** (Supply Manager) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **VN** (Vendor) | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| **FM** (Freight Manager) | ✓ | — | ✓ | ✓ | — | ✓ | ✓ |
| **FN** (Finance Manager) | ✓ | ✓ | — | — | ✓ | ✓ | ✓ |

Sidebar brand subtitle updates to the role label (e.g. "Nexus / Supply Manager", "Nexus / Vendor").

### Backend role mapping (open question, see Open decisions)

Mock roles → backend `UserRole` enum values:

| Mock | Backend | Notes |
|---|---|---|
| VN (Vendor) | `VENDOR` | Direct match. |
| SM (Supply Manager) | `SM` | Direct match. |
| FM (Freight Manager) | `FREIGHT_MANAGER` | Direct match. |
| FN (Finance Manager) | `PROCUREMENT_MANAGER` *(tentative)* | Best fit in current backend. The PROCUREMENT_MANAGER role exists in iter 030 with no wired permissions yet. Phase 4 seizes the opportunity to bind the sidebar-scope to this role and label it "Finance Manager" in the UI. |
| — | `ADMIN` | Not in mock. Sees the SM sidebar plus admin-only tools on non-redesigned pages. |
| — | `QUALITY_LAB` | Not in mock. Falls back to today's existing layout. Backlog: redesign lab views. |

### Out of scope (explicitly backlog)

Anything not visible in the mock. In particular:

- No empty states, loading states, error states beyond the minimum needed to render a page with seed or real data. Skeletons or spinners only.
- No pagination controls on list tables. Mock shows fixed row counts.
- No bulk-select, no row-level action menus, no inline editing.
- No search results. Top-bar search input is decorative.
- No notification flyout. Bell is decorative.
- No global "+ New" CTA (removed from mock v2). Each list page has its own page-specific create button.
- No Filters drawer. "Filters" button on `/rfqs` is present but non-functional.
- No export flow. "Export report" / "Export" buttons are dead.
- No Vendors top-level page in the new shell. Existing `/vendors` route stays on today's styling, reached via deep link only.
- No Products top-level page in the new shell. Existing `/products` route stays on today's styling, reached via deep link only.
- No Certificates, Packaging, Qualifications, Milestones-full-page, Activity-log-full-page.
- No login / register / bootstrap redesign. Existing auth flow pages keep today's styling.
- Rich/advanced forms (multi-line-item PO creation, invoice with remaining-quantity guard, etc.) keep today's pages and today's styling.

---

## Design language (inferred from mock)

### Palette

- **Surfaces**
  - Page background: near-white, warm gray (~`#fafafa`)
  - Card/panel background: pure white
  - Sidebar background: very dark navy/near-black (~`#0f1419`)
- **Text**
  - Primary: near-black (~`#0f1419`)
  - Secondary: mid-gray (~`#667085`)
  - Sidebar text: white, with muted variant for section headers
- **Borders**: 1px, light gray (~`#e5e7eb`)
- **Accent**
  - Brand logo block: blue/indigo (~`#3b5cf0`) *(revised from v1 — mock v2 uses blue, not crimson)*
  - Primary button: near-black solid, white text
- **Status colors** (soft-fill pills with leading dot)
  - Green (Delivered, Paid, Approved, Ready For Pickup, On track, Awarded)
  - Blue (In Transit, Submitted, Open, Qc)
  - Orange/amber (In Production, Customs, Quoted)
  - Red (Overdue, Delayed, overdue deltas)
  - Gray (Draft, Closed, Queued, Booked)

### Typography

- Sans-serif system stack (no custom webfont required)
- H1: 28-32px, bold
- Panel title: 16-18px, semi-bold
- KPI number: 28-32px, bold
- KPI label: 11-12px, uppercase, letter-spaced, gray
- Body / table cell: 14px, regular
- Secondary meta: 12-13px, mid-gray

### Spacing and radius

- Radius: 6-8px on cards, inputs, buttons, pills
- Panel padding: 24px
- Card gap: 16-20px
- Section gap: 24-32px
- Sidebar width: 240px (desktop), collapsed on mobile

---

## Information architecture

### Sidebar nav (desktop, per role)

See the role-conditional sidebar matrix above. Link targets are fixed per label: Overview → `/`, RFQs → `/rfqs`, Production → `/production`, Shipments → `/shipments`, Invoices → `/invoices`, Settings → `/settings`, Help → `/help`.

Existing routes that are not in the new shell (`/po`, `/po/new`, `/po/[id]/edit`, `/vendors`, `/vendors/new`, `/products`, `/products/new`, `/products/[id]/edit`, `/login`, `/register`, `/setup`) stay on today's styling and layout. They are reached by deep link, existing nav on today's layout, or from links inside redesigned pages.

### Top-bar content

- Sidebar toggle
- Breadcrumb: static text per page (e.g. "Workspace / Operations"). Not dynamic. Decorative in v1.
- Global search input: decorative, disabled, placeholder only
- Notification bell: icon only, no flyout
- User pill: avatar initials + role label. Dropdown in production shows user menu (Log out). Role switcher in dev only.

### Page-level headers inside the content area

- **List pages**: H1 (page name), subtitle, optional primary CTA on right ("+ New X") + optional secondary ("Export").
- **Detail pages**: back link ("← All X"), H1 (entity id + title), subtitle (context line), status pill in top-right.
- **Create pages**: back link ("← All X"), H1 ("New X"), subtitle. Form in a single "Details" card below. Cancel / Create buttons bottom-right of the card.

---

## Component inventory

A shared component library lives in `frontend/src/lib/ui/`. These components replace ad-hoc styles across every redesigned page.

| Component | Purpose | Variants |
|---|---|---|
| `AppShell` | Full-page wrapper: sidebar + top bar + content area | Desktop, mobile (drawer) |
| `Sidebar` | Left nav with brand, sections, items, footer | Expanded, collapsed, per-role item filter |
| `TopBar` | Breadcrumb, search, user pill, bell | - |
| `UserMenu` | Role pill + dropdown (user info, Log out in prod; role switcher in dev) | - |
| `PageHeader` | H1 + subtitle + right-side action slot | - |
| `DetailHeader` | Back link + H1 + subtitle + status pill | - |
| `KpiCard` | Label, value, delta chip, corner icon | Neutral, positive, negative |
| `StatusPill` | Leading dot + label | green, blue, orange, red, gray |
| `ProgressBar` | Dark fill on light track + inline % | - |
| `DataTable` | Header row + body rows + optional panel header + row-click handler | - |
| `PanelCard` | Titled surface with optional subtitle and right-side action | - |
| `AttributeList` | Key/value rows inside a `PanelCard` (for Summary / Order details / Shipment details / Invoice cards) | - |
| `Timeline` | Vertical list of status steps with check/dot/empty state (for Milestones and Tracking panels) | - |
| `ActivityFeed` | Vertical list with leading colored dot + primary + secondary line | - |
| `Button` | Primary (dark solid), secondary (outline), ghost | - |
| `Input`, `Select`, `DateInput` | Form primitives used in create pages and Settings toggles | - |
| `Toggle` | On/off switch (Settings only) | - |
| `FormField` | Label + input wrapper with consistent spacing | - |
| `FormCard` | "Details" card for create pages, with Cancel / Submit footer | - |

Each component is self-contained in a `.svelte` file, renders nothing not shown in the mock. No variants, sizes, or states the mock does not exercise.

---

## Per-page specs

### Overview (`/`)

Replaces: today's `/dashboard`.

**Data sources**
- KPI "Open RFQs": seed data count.
- KPI "In Production": count of POs where latest milestone is between RAW_MATERIALS and QC_PASSED inclusive. Repo query over existing data.
- KPI "In Transit": seed data until Phase 3 iter 043.
- KPI "Outstanding A/P": sum of Submitted + Approved invoice amounts.
- Active production panel: PO list filtered to in-production, sorted by ETA, limit 4.
- Recent activity panel: existing activity log, limit 5, target_role matches current user's role.
- Pending RFQs panel: seed data.
- Shipments in motion panel: seed data until Phase 3 iter 043.

**Interactions**
- Row click → respective detail page (`/production/:po_id`, `/rfqs/:id`, `/shipments/:id`).
- "View all →" links go to `/production`, `/rfqs`, `/shipments`.
- "Export report" is a no-op.

### RFQs list (`/rfqs`)

Stub page. No backend work.

**Data**: hardcoded seed list of 6 RFQs in `frontend/src/lib/seed/rfqs.ts`.

**Interactions**
- Row click → `/rfqs/:id`.
- "+ New RFQ" → `/rfqs/new`.
- "Filters", filter input, "Export" are no-ops.

### RFQ create (`/rfqs/new`)

**Fields**: Title, Vendor, Buyer, Quantity, Unit (text, default "pcs"), Value (USD), Due date.

**Interactions**
- "Create RFQ" writes a new RFQ to the session-scoped seed store (Svelte store, not persisted across reloads) and navigates to `/rfqs/:id`.
- "Cancel" navigates back to `/rfqs`.
- "← All RFQs" navigates back to `/rfqs`.

### RFQ detail (`/rfqs/:id`)

Stub page.

**Layout**: DetailHeader (back link, "RFQ-XXXX · {title}", "Buyer: X — Due Y", status pill) + 2-column grid: Summary attribute list (Quantity, Pipeline value, Primary vendor, Buyer, Due date) + Quotes received panel (list of vendors with lead time and value).

**Data**: seed store. Quotes are also seeded.

**Interactions**: none. Buttons to accept/reject quotes are not in the mock; do not add them.

### Production list (`/production`)

New list view over existing `PurchaseOrder` + `MilestoneUpdate` data.

**Data**
- Filters: POs with `status = ACCEPTED` and latest milestone not `SHIPPED`. "Queued" = Accepted with no milestone yet. "Active" = milestone between RAW_MATERIALS and QC_PASSED. "Ready for Pickup" = milestone = READY_TO_SHIP.
- KPI "On-Time Rate": ratio of POs whose latest `READY_TO_SHIP` milestone occurred on or before `required_delivery_date` over last 30 days. New endpoint: `GET /api/v1/po/production-stats`.
- Product column: derived from line items. If one line item, show its product name; if multiple, show "N products".

**Interactions**
- Row click → `/production/:po_id`.
- "+ New order" → `/production/new`.
- "Schedule pickup" is a no-op.

### Production create (`/production/new`)

Stub in Phase 4 v1. 5 fields: Linked RFQ, Vendor, Product, Quantity, ETA.

**Interactions**
- "Create order" writes nothing to the backend in v1; navigates to today's `/po/new` with the entered values as query params. v2 (backlog): bind to real POCreate payload with full line-item construction.
- "Cancel" → `/production`.

Reasoning: today's `/po/new` handles multi-line-item creation, vendor catalog selection, incoterm/payment-term fields, and several other requirements this simple form can't express. Phase 4 introduces the redesigned entry point without rebuilding today's creation flow. Backlog: full redesign of PO creation with multi-line-item support inside the new shell.

### Production detail (`/production/:id`)

Replaces `/po/:id` inside the redesigned shell.

**Layout**: DetailHeader + 2-column grid: Order details (Linked RFQ, Quantity, ETA, Progress bar) + Milestones timeline (5 steps: Queued, In production, QC inspection, Ready for pickup, Shipped) with Completed / In progress / Upcoming labels per step.

**Data**: real PO data. Progress % derives from current milestone position (Queued=0%, RAW_MATERIALS=20%, PRODUCTION_STARTED=40%, QC_PASSED=60%, READY_TO_SHIP=80%, SHIPPED=100%). Exact mapping TBD in implementation.

**Interactions**: today's `/po/:id` has many more controls (accept/reject, per-line-item toggles, post milestone, upload documents, link invoices). The mock's detail page shows **none** of these. Decision: the redesigned `/production/:id` is a **read-only view** in Phase 4. To take mutating actions, the user clicks a "Open full view" link (or similar) that deep-links to today's `/po/:id` with its existing UI. Backlog: redesign mutations inside the new shell.

### Shipments list (`/shipments`)

Stub until Phase 3 iter 043 ships the Shipment aggregate.

**Data**: hardcoded seed list of 5 shipments in `frontend/src/lib/seed/shipments.ts`.

**Interactions**
- Row click → `/shipments/:id`.
- "+ Book shipment" → `/shipments/new`.

### Shipment create (`/shipments/new`)

Stub form. 6 fields: Order ID, Carrier, Origin, Destination, Mode (select: Sea/Air/Road), ETA.

**Interactions**
- "Book shipment" writes to the session seed store and navigates to the new shipment's detail page. Not persisted.
- "Cancel" → `/shipments`.

### Shipment detail (`/shipments/:id`)

Stub page.

**Layout**: DetailHeader + 2-column grid: Shipment details (Order, Carrier, Mode, Origin, Destination, ETA, Progress bar) + Tracking timeline (4 steps: Booked, In transit, Customs clearance, Delivered).

**Data**: seed store.

**Interactions**: none.

### Invoices list (`/invoices`)

Replaces today's `/invoices` layout. Existing data and API unchanged.

**Data**: existing invoice repo.
- KPI "Outstanding": sum of Submitted + Approved amounts.
- KPI "Overdue": sum of Overdue amounts + count.
- KPI "Paid (30d)": sum of Paid in last 30 days.
- KPI "Avg DPO": new endpoint `GET /api/v1/invoices/stats`.
- Table: existing list query.

**Interactions**
- Row click → `/invoices/:id`.
- "+ New invoice" → `/invoices/new`.
- "Export" no-op.

### Invoice create (`/invoices/new`)

6 fields: Vendor, Order ID, Amount, Currency (default USD), Issued, Due.

**Interactions**
- "Create invoice" POSTs to the existing invoice create endpoint. Hidden defaults: for fields the form omits (line items, status=Draft, etc.), the backend accepts Draft invoices without line items or the frontend derives sensible defaults. Validation: Order ID must map to an existing PO.
- On success, navigate to `/invoices/:id`.
- "Cancel" → `/invoices`.

Reasoning: unlike Production create, Invoice create in today's app is already inside the PO detail page (create-from-PO flow). The mock promotes Invoice create to a top-level page. We ship a simplified create path that still goes through the real backend. The PO-scoped create-from-PO flow on today's `/po/:id` keeps working and continues to be the richer path.

### Invoice detail (`/invoices/:id`)

Replaces today's `/invoice/:id` inside the redesigned shell.

**Layout**: DetailHeader + 2-column grid: Invoice card (Vendor, Order, Issued, Due, Currency) + Line items list + Total row.

**Data**: existing invoice repo.

**Interactions**: like `/production/:id`, the mock shows no mutating actions. Redesigned `/invoices/:id` is read-only. Mutating actions (submit/approve/pay/dispute/resolve) are reached via a "Full view" deep link to today's `/invoice/:id`. Backlog: redesign mutations.

### Settings (`/settings`)

**Layout**: PageHeader ("Settings", "Workspace preferences and notifications.") + two PanelCards stacked: Profile (Name, Workspace, Plan — AttributeList with hardcoded values) + Notifications (three Toggle rows: Email digest, Shipment alerts, Invoice reminders; with secondary description line per row).

**Data**: all hardcoded / local state. No backend calls. Toggle state is lost on reload.

**Interactions**: clicking a toggle flips its visual state. No persistence.

### Help (`/help`)

**Layout**: PageHeader ("Help & Support", "Common questions about the Nexus vendor portal.") + single PanelCard "FAQ" containing 4 question/answer rows (heading + paragraph).

**Data**: static, copied verbatim from the mock.

**Interactions**: none.

---

## Iteration breakdown

**Revised for expanded scope.** Seven iterations. Sequential, one agent. Each builds on the previous.

### Iter 049 — Design tokens and primitive components
- Extend `$lib/styles/global.css` with the full token set (palette, typography, spacing, radius).
- Build primitives in `frontend/src/lib/ui/`: `Button`, `StatusPill`, `ProgressBar`, `KpiCard`, `PanelCard`, `Input`, `Select`, `DateInput`, `Toggle`, `FormField`, `FormCard`, `AttributeList`, `Timeline`, `ActivityFeed`.
- Internal `/ui-demo` gallery (removed in iter 055).
- ~12-14 files, ~1000 lines.

### Iter 050 — App shell and role-conditional sidebar
- Build `AppShell`, `Sidebar`, `TopBar`, `UserMenu`, `PageHeader`, `DetailHeader`.
- New layout group `frontend/src/routes/(nexus)/+layout.svelte` that wraps redesigned routes.
- Existing layout `frontend/src/routes/+layout.svelte` stays for non-redesigned routes.
- Sidebar filters items per `user.role` using the role matrix.
- In development, `UserMenu` shows the role-switcher dropdown that mutates `user.role` in a dev-only store. In production, dropdown shows user info + Log out.
- Mobile drawer for sidebar.
- ~8-10 files, ~700 lines.

### Iter 051 — Overview + list pages (Production, Invoices)
- Overview route under `(nexus)` group. KPI row, Active production panel, Recent activity, Pending RFQs, Shipments in motion panels.
- Seed files: `frontend/src/lib/seed/rfqs.ts`, `frontend/src/lib/seed/shipments.ts`.
- Production list page (real data, new stats endpoint).
- Invoices list page moved under `(nexus)` group. New stats endpoint.
- Backend: `GET /api/v1/po/production-stats`, `GET /api/v1/invoices/stats`.
- Row click → detail routes (iter 053 builds the targets; iter 051 wires the click).
- ~8-10 files, ~900 lines.

### Iter 052 — RFQs and Shipments stubs (list + create + detail)
- `/rfqs`, `/rfqs/new`, `/rfqs/:id` against seed store.
- `/shipments`, `/shipments/new`, `/shipments/:id` against seed store.
- Seed store: Svelte writable that supports add (from create page) and get-by-id.
- `/rfqs/new` uses `FormCard` + `FormField` primitives. "Create RFQ" writes to store + navigates.
- `/shipments/new` same pattern.
- `/rfqs/:id` and `/shipments/:id` use `DetailHeader` + `AttributeList` + `PanelCard` / `Timeline`.
- ~8-10 files, ~800 lines.

### Iter 053 — Production detail + Invoice detail + Invoice create
- `/production/:id` read-only detail with real PO data + Milestones `Timeline` + "Full view" link to `/po/:id`.
- `/production/new` stub form that navigates to `/po/new` with query params.
- `/invoices/:id` read-only detail with real invoice data + "Full view" link to `/invoice/:id`.
- `/invoices/new` create form that POSTs to existing invoice endpoint with defaults for omitted fields.
- Milestone → progress-% mapping finalized.
- ~8-10 files, ~900 lines.

### Iter 054 — Settings + Help + user menu polish
- `/settings` page with Profile + Notifications sections. All hardcoded / local state.
- `/help` page with 4 static FAQs.
- `UserMenu` production variant: user info + Log out action.
- ~5-6 files, ~400 lines.

### Iter 055 — Mobile pass, accessibility pass, and cleanup
- Test every redesigned page at 390px, 768px, 1024px, 1440px.
- Sidebar drawer behavior on mobile. KPI row stacks 1-up. Tables overflow horizontally (mock behavior).
- Keyboard-nav smoke tests per page (visible focus, tab order, escape-closes-menus).
- Remove `/ui-demo` gallery.
- Fix any inconsistencies discovered across pages.
- ~6-8 files, ~500 lines.

---

## Data and backend implications

- Two new read-only endpoints: `GET /api/v1/po/production-stats`, `GET /api/v1/invoices/stats`.
- `POST /api/v1/invoices` (existing) must accept Draft invoices created without line items from `/invoices/new`. Verify the current endpoint's behavior; if it rejects empty-line-item requests, relax it for Draft status.
- Two seed-data files in the frontend: `rfqs.ts`, `shipments.ts`.
- Session-scoped seed store for create-stub persistence within a session (Svelte writable).
- No schema changes. No new aggregates.

---

## Testing

### Existing test impact

- No backend tests break from the pure list redesign. The two new stats endpoints get new pytest coverage.
- Relaxing `POST /api/v1/invoices` for empty-line-item Drafts needs a new pytest case and a check that the existing create-from-PO flow still works.
- Playwright specs that target `/dashboard`, `/invoices`, `/invoice/:id` need selector updates once those pages move under `(nexus)`. Specs identified: `activity-feed.spec.ts`, `notification-bell.spec.ts`, invoice list and detail specs.
- Specs targeting `/po`, `/vendors`, `/products`, `/register`, `/setup` are unaffected.

### New permanent tests

- Playwright spec per redesigned page asserting: header renders, KPI row or attribute list renders, table renders with expected data, mobile drawer opens.
- Role-conditional sidebar spec: log in as each role, verify sidebar items match the matrix.
- Row-click navigation spec: clicking a row on each list lands on the correct detail page.
- Create-stub spec: `/rfqs/new` and `/shipments/new` add to the seed store and the new entity shows up on the list (in-session).
- Real create spec: `/invoices/new` POSTs and the new invoice appears on `/invoices`.
- Accessibility smoke: keyboard nav to primary CTA on each page.

### Scratch tests

- Per iteration, capture scripts that screenshot each redesigned page at desktop and mobile. JPEG quality 40. Saved to `frontend/tests/scratch/iteration-NNN/screenshots/`.

---

## Open decisions

### Carried from v1, still open

1. **Sidebar icons.** Mock shows leading icons. Which set? Tentative: Lucide (matches Lovable / shadcn defaults).
2. **Brand name.** Mock says "Nexus". App is "Turbo Tonic". Tentative: use "Turbo Tonic / {role}" in production; keep "Nexus" only in the Lovable reference. Alternative: adopt "Nexus" as the product name.
3. **Font.** Mock uses a system sans-serif stack. Tentative: keep system stack.
4. **Dark sidebar with light body.** Tentative: keep.
5. **Retiring the old `/po` list page.** Tentative: keep for VENDOR flows that need multi-line-item PO creation; revisit after Phase 4.

### New in v2

6. **Role switcher in production: A (dev-only) or B (remove).** Tentative: B. Role is taken from session. User pill becomes a user menu with Log out.
7. **Backend mapping for FN "Finance Manager".** Tentative: map to existing `PROCUREMENT_MANAGER`. Label as "Finance Manager" in the UI. Relies on iter 031 having left PROCUREMENT_MANAGER permissions unwired; we'd wire them now to match the FN sidebar matrix.
8. **ADMIN and QUALITY_LAB views in Phase 4.** Not in the mock. Tentative: ADMIN inherits the SM sidebar; QUALITY_LAB falls back to today's existing layout for now. Backlog: redesign lab view.
9. **Detail pages are read-only in Phase 4.** Mock shows no mutating actions. Tentative: add a "Full view" link to today's detail page for actions. Alternative: port the buttons into the new detail page design.
10. **Invoice create takes a simplified payload.** Mock form has 6 fields; real invoices have line items and other constraints. Tentative: create as Draft with no line items; user continues editing in today's `/invoice/:id` for line items and submission. Alternative: route "+ New invoice" to today's create flow.
11. **Production create navigates to `/po/new` with prefilled query params.** Tentative. Alternative: drop the page entirely and link "+ New order" straight to `/po/new`.
12. **Milestone → progress-% mapping.** Tentative: Queued=0, RAW_MATERIALS=20, PRODUCTION_STARTED=40, QC_PASSED=60, READY_TO_SHIP=80, SHIPPED=100. Alternative: let the vendor post a progress % alongside each milestone (new field, backlog).
13. **Settings is decorative.** Tentative: hardcoded display-only in Phase 4. Alternative: wire notification preferences to a new backend field on User.
14. **Help is static.** Tentative: copy the FAQ verbatim. Alternative: pull from a CMS or markdown file.

---

## What comes after Phase 4

- Phase 5: RFQ aggregate (real backend, state machine, UI becomes functional). Replaces seed data on `/rfqs` and the Overview KPI.
- Phase 6 (or folded into Phase 3 iter 043+): Shipment aggregate replaces seed data on `/shipments` and the Overview KPI.
- Detail-page mutations: port accept/reject, post milestone, invoice submit/approve/pay/dispute/resolve, document upload into the redesigned detail pages.
- Form redesigns: rebuild today's rich forms (`/po/new`, `/po/:id/edit`, `/vendors/new`, `/products/new`, `/products/:id/edit`) inside the new shell.
- Settings backend: wire real notification preferences, workspace metadata.
- Role redesign: QUALITY_LAB view; admin impersonation audit trail.
- Login / register / bootstrap redesign.
