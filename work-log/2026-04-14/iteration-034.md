# Iteration 034 -- Frontend role-conditional rendering

## Context

The frontend has auth and user context in layout (iter 033), but renders every button, nav link, and page identically for all roles. A VENDOR sees "Create PO" which 403s; a QUALITY_LAB user sees vendor links they cannot use. This iteration adds a `permissions.ts` helper and applies role-conditional rendering across all pages: hiding inaccessible controls, redirecting unauthorized page visits, and filtering the dashboard activity feed by `target_role`.

## JTBD (Jobs To Be Done)

- When I am a VENDOR, I want to see only accept/reject on POs and create/submit on invoices, so that I am not confused by controls I cannot use
- When I am an SM, I want to see create/edit/submit on POs and approve/pay/dispute on invoices, so that I can manage the full workflow
- When I am a QUALITY_LAB user, I want to see only products and activity in navigation, so that I am not presented with irrelevant sections
- When I am a FREIGHT_MANAGER, I want to see POs (read-only) and activity in navigation, so that I can track shipment-relevant orders
- When the dashboard loads, I want to see activity entries targeted at my role, so that I see notifications relevant to me

## Tasks

### Role helper utility
- [x] Create `frontend/src/lib/permissions.ts`
  - `canDoEverything(role)` -- ADMIN only (ADMIN inherits all SM permissions plus user management)
  - Each `can*` function should return true for ADMIN (ADMIN passes every permission check)
  - `canCreatePO(role)` -- SM only
  - `canEditPO(role)` -- SM only
  - `canSubmitPO(role)` -- SM only
  - `canAcceptRejectPO(role)` -- VENDOR only
  - `canCreateInvoice(role)` -- VENDOR only
  - `canSubmitInvoice(role)` -- VENDOR only
  - `canApproveInvoice(role)` -- SM only
  - `canPayInvoice(role)` -- SM only
  - `canDisputeInvoice(role)` -- SM only
  - `canResolveInvoice(role)` -- SM only
  - `canManageVendors(role)` -- SM only
  - `canManageProducts(role)` -- SM only
  - `canViewProducts(role)` -- SM, QUALITY_LAB
  - `canPostMilestone(role)` -- VENDOR only
  - `canViewInvoices(role)` -- SM, VENDOR
  - `canViewPOs(role)` -- all roles except QUALITY_LAB
  - Each function takes UserRole and returns boolean
  - Single source of truth for frontend permission checks

### Navigation: role-based menu items
- [x] Update `frontend/src/routes/+layout.svelte`
  - SM: Dashboard, POs, Invoices, Vendors, Products (all nav links)
  - VENDOR: Dashboard, POs, Invoices (no Vendors, no Products)
  - QUALITY_LAB: Dashboard, Products (no POs, no Invoices, no Vendors)
  - FREIGHT_MANAGER: Dashboard, POs (no Invoices, no Vendors, no Products)
  - ADMIN: same as SM (no Users link yet; user management page is a backlog item, show link once `/users` page exists)
  - PROCUREMENT_MANAGER: Dashboard only (permissions not yet wired; future iteration will expand access)
  - Use `canManageVendors`, `canViewProducts`, `canViewInvoices`, `canViewPOs` to control visibility
  - Display current user's display_name and role in header/nav

### PO list page (`frontend/src/routes/po/+page.svelte`)
- [x] Hide "Create PO" button unless `canCreatePO(role)`
- [x] Bulk action buttons:
  - SM sees: Submit, Resubmit
  - VENDOR sees: Accept, Reject
  - Neither role sees the other's actions
- [x] All roles see the PO list table (data scoping is backend's job)

### PO detail page (`frontend/src/routes/po/[id]/+page.svelte`)
- [x] SM sees: Edit button (on REJECTED POs), Submit button (on DRAFT), Resubmit button (on REVISED)
- [x] VENDOR sees: Accept button (on PENDING), Reject button (on PENDING), Create Invoice button (on ACCEPTED POs), Milestone form (on ACCEPTED PROCUREMENT POs)
- [x] QUALITY_LAB and FREIGHT_MANAGER: no action buttons, read-only view
- [x] All roles see: PO details, line items, milestone timeline, activity timeline, PDF download

### PO create page (`frontend/src/routes/po/new/+page.svelte`)
- [x] Redirect non-SM users to /po: use `+page.ts` load function with `throw redirect(307, '/po')` (prevents page content flash)

### PO edit page (`frontend/src/routes/po/[id]/edit/+page.svelte`)
- [x] Redirect non-SM users to /po/[id]: use `+page.ts` load function with `throw redirect(307, '/po/' + id)` (prevents page content flash)

### Invoice list page (`frontend/src/routes/invoices/+page.svelte`)
- [x] Redirect QUALITY_LAB and FREIGHT_MANAGER to /dashboard: use `+page.ts` load function (prevents page content flash)
- [x] SM sees: no create button (invoices are created from PO detail), bulk PDF download
- [x] VENDOR sees: bulk PDF download
- [x] Both SM and VENDOR see the invoice list table

### Invoice detail page (`frontend/src/routes/invoice/[id]/+page.svelte`)
- [x] Redirect QUALITY_LAB and FREIGHT_MANAGER to /dashboard: use `+page.ts` load function
- [x] SM sees: Approve button (on SUBMITTED), Pay button (on APPROVED), Dispute button (on SUBMITTED/APPROVED), Resolve button (on DISPUTED)
- [x] VENDOR sees: Submit button (on DRAFT)
- [x] Both SM and VENDOR see: invoice details, line items, activity timeline, PDF download

### Vendor list page (`frontend/src/routes/vendors/+page.svelte`)
- [x] Redirect non-SM users to /dashboard: use `+page.ts` load function
- [x] SM sees: Create Vendor button, deactivate/reactivate actions, full vendor list

### Vendor create page (`frontend/src/routes/vendors/new/+page.svelte`)
- [x] Redirect non-SM users to /dashboard: use `+page.ts` load function

### Product list page (`frontend/src/routes/products/+page.svelte`)
- [x] Redirect VENDOR and FREIGHT_MANAGER to /dashboard: use `+page.ts` load function
- [x] SM sees: Create Product button
- [x] QUALITY_LAB sees: read-only list, no create button

### Product create page (`frontend/src/routes/products/new/+page.svelte`)
- [x] Redirect non-SM users: QUALITY_LAB to /products, others to /dashboard. Use `+page.ts` load function

### Product edit page (`frontend/src/routes/products/[id]/edit/+page.svelte`)
- [x] Redirect non-SM users: QUALITY_LAB to /products/[id], others to /dashboard. Use `+page.ts` load function

### Dashboard (`frontend/src/routes/dashboard/+page.svelte`)
- [x] Activity feed: filter by `target_role` matching current user's role
  - SM sees events targeted at SM
  - VENDOR sees events targeted at VENDOR
  - QUALITY_LAB and FREIGHT_MANAGER: currently no events target them (Phase 3 adds QUALITY_LAB and FREIGHT_MANAGER to TargetRole). Show empty feed or all-role events for now.
- [x] Notification bell (if in nav): filter unread count by target_role (requires backend change or client-side filter)
  - Note: if the backend unread count endpoint does not filter by role, pass target_role query parameter to the backend (may need a small backend change: add `target_role` filter to `unread_count()` and `list_recent()` in ActivityLogRepository)
- [x] Dashboard cards/widgets:
  - SM: PO summary, invoice summary, vendor summary, production pipeline, overdue POs, recent POs
  - VENDOR: PO summary (own), invoice summary (own), production pipeline (own), overdue POs (own)
  - QUALITY_LAB: products count, activity feed (no PO/invoice/vendor summaries)
  - FREIGHT_MANAGER: PO summary (read-only context), production pipeline (read-only context)
  - ADMIN: same view as SM (full visibility)

### Backend: target_role filter on activity endpoints (blocking -- frontend cannot filter by role without this)
- [x] Add required `target_role` query parameter to `GET /api/v1/activity/` and `GET /api/v1/activity/unread-count`
- [x] Update `ActivityLogRepository.list_recent()` and `unread_count()` to accept `target_role` filter
- [x] Frontend passes current user's role as `target_role` on every activity/unread-count call

### Existing test impact
- No existing tests break. This iteration only hides/shows UI elements based on role. All existing Playwright tests use the SM-authenticated fixture from iteration 033, and SM sees all controls.
- New tests mock different roles via /api/v1/auth/me to verify conditional rendering.

### Tests (permanent)
- [x] `frontend/tests/role-rendering.spec.ts` (Playwright)
  - SM user: nav shows Dashboard, POs, Invoices, Vendors, Products
  - VENDOR user: nav shows Dashboard, POs, Invoices; does not show Vendors, Products
  - QUALITY_LAB user: nav shows Dashboard, Products; does not show POs, Invoices, Vendors
  - FREIGHT_MANAGER user: nav shows Dashboard, POs; does not show Invoices, Vendors, Products
  - SM on PO list: Create PO button visible
  - VENDOR on PO list: Create PO button not visible
  - SM on PO detail (PENDING): no Accept/Reject buttons
  - VENDOR on PO detail (PENDING): Accept and Reject buttons visible
  - VENDOR visiting /po/new redirects to /po
  - VENDOR visiting /vendors redirects to /dashboard
  - QUALITY_LAB visiting /invoices redirects to /dashboard
  - ADMIN user: nav shows Dashboard, POs, Invoices, Vendors, Products (no Users link yet)
  - ADMIN on PO detail: same buttons as SM
  - ADMIN on invoice detail (SUBMITTED): same buttons as SM (Approve, Dispute)
  - PROCUREMENT_MANAGER: nav shows Dashboard only
  - VENDOR on PO detail (ACCEPTED): Create Invoice button visible
  - Note: these tests require mocking /api/v1/auth/me to return different user roles

### Tests (scratch)

Carried forward: scratch screenshot tests not done this iteration.

## Acceptance criteria
- [x] Navigation links are role-conditional: each role sees only their permitted sections
- [x] Current user display_name and role are shown in the header/nav
- [x] PO list: Create button visible only for SM; bulk actions differ by role
- [x] PO detail: action buttons match role (SM: edit/submit/resubmit, VENDOR: accept/reject/create invoice/milestone)
- [x] PO create/edit pages redirect non-SM users away
- [x] Invoice list/detail: visible only to SM and VENDOR; action buttons match role
- [x] Vendor pages: visible only to SM
- [x] Product pages: visible to SM (full CRUD) and QUALITY_LAB (read-only); hidden from VENDOR and FREIGHT_MANAGER
- [x] Dashboard activity feed filters by current user's target_role
- [x] Dashboard widgets adjust per role (VENDOR sees own data, QUALITY_LAB sees products)
- [x] Page-level redirects prevent unauthorized page access (not just hidden buttons)
- [x] All page-level role redirects use `+page.ts` load functions (no content flash before redirect)
- [x] `make test-browser` passes with new Playwright tests

## Notes

Created permissions.ts with `is()` (ADMIN-inheriting) and `isExact()` (VENDOR-only) helpers covering 16 permission functions. Layout nav links are role-conditional. All page-level redirects use +page.ts load functions to prevent content flash. PO detail buttons split between SM actions (edit/submit/resubmit) and VENDOR actions (accept/reject/create invoice/post milestone). Dashboard widgets and activity feed filter by role via a new `target_role` query parameter on the backend activity endpoints. QUALITY_LAB removed from canViewPOs since they should only see Products. Existing po-lifecycle tests updated: accept/reject tests use VENDOR mock override, full-cycle test uses dynamic role switching via closure variable. 84 Playwright tests pass (68 existing + 16 new role-rendering).
