# UI Revamp v2 (Phase 4) — Design

Supersedes `2026-04-19-ui-revamp-plan.md`. That plan's hedges (old-page fallbacks, read-only detail pages, mock-bound scope) are gone; this plan commits to the new shell as the long-term home of every existing page.

**Visual source of truth:** Lovable mock at https://turbotonic.lovable.app, for what it shows. Anything the mock doesn't show is a brainstorm stop before implementation.

---

## Context

After iter 060, work proceeds in three serial phases: (1) UI revamp; (2) feature backlog; (3) production setup. No new features during the revamp. Every existing page ports into the new shell at feature parity. Old routes retire only when the new counterpart is feature-complete.

The app must work end-to-end at every iteration close — both pre-revamp flows and revamp-added flows. This is a hard rule.

## Sequencing

1. **UI revamp (this spec, Phase 4).** Port every pre-revamp page into the new shell. Old routes retire as each aggregate's new counterpart goes feature-complete.
2. **Feature backlog phase.** Outstanding items from `docs/backlog.md` and "What does not exist yet" in `work-log/iterations-summary.md`. Includes Certificate UI, Shipments list + redesign, RFQ aggregate, user management, PROCUREMENT_MANAGER permissions wiring.
3. **Production setup phase.** HTTPS, migrations, secrets, deploy. Plus hardening items deferred from the revamp: Sentry/error reporting, session cookie attributes, XSS audit, file-endpoint role guards, session revocation, CSP, browser-compat matrix.

## Phasing

Per aggregate, not bundled. Iteration count per phase is not committed — each phase closes when feature parity lands and old routes can retire.

| Phase | Scope |
|---|---|
| 4.0 | Foundation: design tokens, primitive components, app shell with role-conditional sidebar, mobile variant, redirect infrastructure, seed-data overhaul |
| 4.1 | Dashboard. Replaces `/dashboard`. |
| 4.2 | Production. Replaces all of `/po/*`. |
| 4.3 | Invoice. Replaces `/invoices`, `/invoice/:id`. |
| 4.4 | Product. Replaces `/products/*`. No Certificate UI (deferred). |
| 4.5 | Vendor. Replaces `/vendors/*`. |
| 4.6 | Auth. Replaces `/login`, `/register`, `/setup`. |

**Deferred to feature-backlog phase:** Certificate UI, Shipments redesign + list, RFQ aggregate, user management page, FN / PROCUREMENT_MANAGER permissions wiring.

## Ship gates (every iteration)

1. **Mock-clarity gate.** If the Lovable mock is silent on the page/component being built, stop and brainstorm. No extrapolating the mock's pattern onto flows it doesn't show.
2. **Past-flow gate.** Every pre-revamp flow the iteration touches still works. Run relevant Playwright specs on old and new routes. No regression ships.
3. **Future-flow gate.** Every flow built in prior revamp iterations still works. At every iteration close, the app works end-to-end based on what's been built so far.

## Riders

**Per iteration (acceptance criteria before close):**
- 390px viewport screenshot attached
- Loading / error / empty states present on every async surface the iteration touches
- Keyboard tab-order check on any new interactive surface
- Past-flow and future-flow Playwright spec sets run green

**Per phase close (before old routes retire):**
- axe or pa11y scan on the phase's pages — zero AA violations
- URL redirects wired when old routes retire
- Existing Playwright specs updated or rewritten to target new routes

## Role model

Use the actual six `UserRole` enum values: `ADMIN`, `SM`, `VENDOR`, `FREIGHT_MANAGER`, `QUALITY_LAB`, `PROCUREMENT_MANAGER`. Ignore the Lovable mock's four-role framing (FN / SM / FM / VN).

Sidebar items for each role derive from `frontend/src/lib/permissions.ts`, not from a hardcoded mock matrix. `ADMIN` inherits all permissions; `QUALITY_LAB` gets a minimal sidebar (Dashboard, Products). PROCUREMENT_MANAGER permissions remain unwired; its sidebar falls back to Dashboard only until the feature-backlog phase wires it.

Fix `isExact` asymmetry in `permissions.ts` (open backlog item) during Phase 4.0 so `ADMIN` inherits all role-scoped actions before primitives lock in the broken rule.

## Retirement mechanism

`+page.ts` or `hooks.server.ts` redirects (301) when an aggregate's new pages are feature-complete. `/po/123` → `/production/123`, etc. File deletion only after redirects are confirmed working via Playwright spec.

During transition: old routes stay on pre-revamp layout; new routes under `(nexus)` layout group. Shell-owned state (session, activity feed, notification bell) is shared via stores, readable from both layouts.

## CSS scoping

Phase 4.0 iter 1 deletes document-scoped component rules from `global.css` (`.btn`, `.table`, `.badge`, `.card`, `.input`). Design tokens stay in `global.css`. All component visuals live inside their Svelte files using scoped styles.

## Phase 4.0 — Foundation

This phase ships no user-facing pages. It ships the system the rest of the phases build on.

### Deliverables

**Design tokens (in `frontend/src/lib/styles/global.css`):**
- Palette: surfaces (page background, card background, sidebar background); text (primary, secondary, sidebar, muted); borders; brand accent; status colors (green, blue, orange, red, gray)
- Typography: H1, panel title, KPI number, KPI label, body, secondary meta — sizes, weights, letter-spacing for uppercase labels
- Spacing: card gap, panel padding, section gap
- Radius: 6-8px for cards, inputs, buttons, pills
- Breakpoints: 390, 768, 1024, 1440

**Shell primitives (in `frontend/src/lib/ui/`):**
- `AppShell` — sidebar + top bar + content area wrapper; desktop and mobile variants; mobile drawer at ≤768px
- `Sidebar` — reads role from session, filters items via `permissions.ts`; brand, sections, items, footer; expanded and collapsed states
- `TopBar` — sidebar toggle, breadcrumb (static text slot), search input (decorative in revamp; live in feature-backlog phase), notification bell (bound to existing activity store), user pill
- `UserMenu` — user info and Log out. No role switcher in production. In dev, a role switcher behind `import.meta.env.DEV` continues to support local testing.
- `PageHeader` — H1 + subtitle + right-side action slot
- `DetailHeader` — back link + H1 + subtitle + status pill slot

**Page primitives:**
- `PanelCard` — titled surface with optional subtitle and right-side action
- `FormCard` — "Details" card with Cancel / Submit footer
- `AttributeList` — key/value rows inside a panel
- `Timeline` — vertical list of status steps (milestones, tracking, edit history reuse)
- `ActivityFeed` — vertical list with leading colored dot + primary + secondary line

**Controls:**
- `Button` — primary (dark solid), secondary (outline), ghost; visible focus ring; keyboard-activatable
- `Input`, `Select`, `DateInput`, `Toggle` — with visible focus, proper labels, server-error surface via `FormField`
- `FormField` — label + input wrapper + inline server-error display
- `StatusPill` — leading dot + label; five variants (green/blue/orange/red/gray)
- `ProgressBar` — dark fill on light track + inline %
- `KpiCard` — label, value, delta chip, corner icon; neutral / positive / negative variants

**Data:**
- `DataTable` — header row + body rows + optional panel header + row-click handler; paginated (server-driven) from day one; supports multi-select bar slot (for PO bulk actions and invoice bulk PDF, wired in 4.2 and 4.3)

**State primitives:**
- `LoadingState`, `EmptyState`, `ErrorState` — rendered inside async sections
- `ErrorBoundary` — wraps routes in `AppShell`; refresh or support fallback on crash

**Layout group and routing infrastructure:**
- `frontend/src/routes/(nexus)/+layout.svelte` — wraps redesigned routes; pre-revamp `frontend/src/routes/+layout.svelte` stays for the rest
- Redirect infrastructure — `+page.ts` `redirect()` or `hooks.server.ts` rewrite, activated per-aggregate when an old route retires

**Backend and data:**
- `tools/seed_data.py` overhaul — varied data across aggregates on fresh local runs (per memory). Multiple vendors across types; POs across statuses; invoices across statuses; milestones across stages; activity across categories; users across roles.
- `frontend/src/lib/permissions.ts` — fix `isExact` asymmetry so `ADMIN` inherits every role-scoped action

**No Sentry, no session cookie hardening, no XSS audit. Those land in production-setup phase.**

### Phase 4.0 acceptance

- All primitives exist in `frontend/src/lib/ui/` with scoped styles and no reliance on deleted global component rules
- `AppShell` renders at 390 / 768 / 1024 / 1440 with mobile drawer working at 390
- Sidebar reads role from session and filters items via `permissions.ts`; every role lands on a working default route
- `ErrorBoundary` triggers a fallback when a child throws
- Seed data script produces varied data covering every aggregate
- `permissions.ts` fixed for `ADMIN` inheritance, with a Playwright spec proving it
- All existing Playwright specs still pass on pre-revamp routes

### Phase 4.0 mock-clarity gaps

These are brainstorm stops inside 4.0, not implementer judgment calls:
- Per-role sidebar item set — the mock shows a 4-role matrix that doesn't match the 6-role backend; exact items per role need decision
- Notification bell state layout — mock shows the bell but no flyout
- Mobile drawer trigger and animation — mock is desktop-only
- `UserMenu` layout in production (user info + Log out); dev variant includes role switcher

### Phase 4.0 decisions log (closed 2026-04-25)

- **Per-role sidebar items** (iter 067 Task 18, user-confirmed): explicit `Record<UserRole, SidebarItem[]>` map decoupled from `canView*` helpers. ADMIN gets Dashboard + Purchase Orders + Invoices + Vendors + Products + Users. SM gets ADMIN set minus Users. VENDOR gets Dashboard + Purchase Orders + Invoices. FREIGHT_MANAGER gets Dashboard + Purchase Orders + Invoices (OpEx-only page scoping deferred to aggregate phase). QUALITY_LAB gets Dashboard + Products. PROCUREMENT_MANAGER gets Dashboard only. Shipments nav item deferred. Users route will 404 until the users management page ships.
- **Mobile drawer** (iter 068 Task 20, resolved from mock evidence): off-canvas drawer slides in from the left, `translateX(-100%)` by default, width `min(280px, 70vw)`, overlay `rgba(0, 0, 0, 0.35)` covers remaining viewport, tap-to-dismiss. `visibility: hidden` paired with the transform so Playwright `toBeHidden()` asserts cleanly. Breakpoint `≤768px` via media query on `.ui-appshell`.
- **TopBar search** (iter 068, audit-surfaced): search input visible at `≥768px` in the mock, absent on mobile. Phase 4.0 ships TopBar WITHOUT rendering a search element at all; live-search backend is backlog. Breadcrumb hidden on mobile via `@media (max-width: 767px) { .breadcrumb { display: none; } }` inside `TopBar.svelte`.
- **UserMenu split** (iter 069 Task 22, resolved from mock evidence): pill renders `[avatar][name + role stacked][chevron]` on desktop, collapses to `[avatar][chevron]` at `<768px` via `@media { .meta { display: none; } }`. Dropdown contains `Log out` always. When `import.meta.env.DEV` is true, a disabled "Switch role (dev)" placeholder item appears above Log out — structural affordance only; dev-store wiring is backlog. Logout swallows API errors and always redirects to `/login`.
- **Chrome alignment scope (Option B, iter 068 preflight)**: visual chrome follows the Lovable mock (section headers, humanized role label, footer slot, icon slot on KpiCard, responsive collapses) while nav items and data model follow our actual routes/schema. No adoption of mock's RFQs/Production/Shipments/Settings/Help nav items.

---

## Phase 4.1 — Dashboard

Replaces `/dashboard` under `(nexus)` layout.

**Scope:** KPI cards, Active production panel, Recent activity panel, Pending RFQs panel (seed-backed until RFQ aggregate lands), Shipments in motion panel (seed-backed until Shipments phase lands), Overdue table.

**Mock-clarity gaps:** specific KPI metrics and their data sources, how QUALITY_LAB dashboard differs, how VENDOR dashboard scopes to their vendor.

---

## Phase 4.2 — Production

Replaces all of `/po/*`: list, new, detail, edit.

**Scope:** list with filters + bulk actions (cross-page select up to 200) + marketplace filter + Partial/Modified pills; create form (multi-line-item, vendor+marketplace+payment-term selection, reference-data dropdowns); detail with 18+ mutation paths including line negotiation (modify/accept/remove/force-accept/force-remove/submit-response), milestones, activity, advance payment gate, post-acceptance line add/remove, document upload, PDF export, edit history; edit form for revision flow.

**Mock-clarity gaps (extensive):** line negotiation UI for rounds 1/2, advance payment gate, post-acceptance line add/remove, bulk action bar, role-conditional action rails (SM vs VENDOR vs ADMIN), multi-line-item creation form layout, document upload surface, PDF button placement.

Each of the above is an explicit brainstorm stop inside 4.2.

`POForm.svelte` (shared by create and edit) is the biggest single retrofit. Plan for it inside 4.2 so both routes stay functional during transition.

---

## Phase 4.3 — Invoice

Replaces `/invoices` and `/invoice/:id`.

**Scope:** list with filters + bulk PDF download; create form with OPEX / PROCUREMENT branching + partial-invoicing remaining-quantity guard; detail with submit/approve/pay/dispute/resolve mutations + dispute reason flow + line items + activity timeline + PDF export.

**Mock-clarity gaps:** OPEX vs PROCUREMENT branching on create (mock shows generic form), dispute reason flow, remaining-quantity guard UI, bulk PDF download bar, action rail per status.

---

## Phase 4.4 — Product

Replaces `/products`, `/products/new`, `/products/[id]/edit`.

**Scope:** list with vendor filter; create form; edit form with qualifications (join-table) section and packaging specs (list + file upload) section. Manufacturing address, marketplace handling preserved.

**Out of scope:** Certificate UI (deferred to feature-backlog phase).

**Mock-clarity gaps:** qualifications assignment pattern, packaging spec upload and readiness surface.

---

## Phase 4.5 — Vendor

Replaces `/vendors`, `/vendors/new`.

**Scope:** list with status + type filters; create form; edit; deactivate/reactivate action rail; address and account_details fields.

**Mock-clarity gaps:** deactivate/reactivate confirmation flow, vendor-scoped data access feedback for VENDOR users.

---

## Phase 4.6 — Auth

Replaces `/login`, `/register`, `/setup`.

**Scope:** WebAuthn passkey login, invite-only registration (with username/token query param), first-user bootstrap, pending-user message, already-configured detection, deep-link preservation on register and setup (open backlog item to close here).

**Out of scope:** session cookie hardening (moves to production-setup phase).

**Mock-clarity gaps:** the mock doesn't show auth at all. Full brainstorm stop before any implementation.

---

## Testing

### Existing Playwright spec migration

99 tests across 13 files, ~3654 LOC. Hard-coded mock fixtures and DOM testids. This is rewrite-level, not selector updates. Budget spec rewrites into each phase: when a phase closes, specs that targeted its old routes move to new routes, with fixtures updated to match new DOM.

### New Playwright specs per phase

- Role-conditional sidebar spec in 4.0
- Per-page loading / error / empty state spec in every phase
- Session expiry with deep-link preservation spec in 4.0 and 4.6
- Bulk action spec in 4.2 and 4.3
- Row-click navigation spec on each list page in its phase

### Scratch tests

Per iteration, screenshot captures at 390 / 1024 (minimum) saved to `frontend/tests/scratch/iteration-NNN/screenshots/`. JPEG quality 40.

---

## Open decisions the spec commits to

- **Role model:** actual 6-role enum, ignore mock's 4-role framing
- **CSS scoping:** delete global component rules in 4.0; primitives own their styles
- **Retirement:** `+page.ts` 301 redirects, not file deletion
- **Certificate UI:** deferred, not in revamp
- **Shipments:** deferred, not in revamp
- **No production hardening in revamp:** Sentry, CSP, session cookie attributes, XSS audit all move to production-setup phase
- **Iteration count per phase:** uncommitted; phases close on feature parity, not on iteration count

## What comes after Phase 4

Feature-backlog phase picks up: Certificate UI, Shipments redesign + list, RFQ aggregate, user management page, PROCUREMENT_MANAGER permissions wiring, remaining backlog items.

Production-setup phase handles: Sentry, HTTPS, migrations, secrets, deploy, session cookie hardening, XSS audit, CSP, file-endpoint role guards, session revocation, browser-compat matrix.
