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
- [ ] Create `frontend/src/lib/permissions.ts`
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
  - `canViewPOs(role)` -- all roles
  - Each function takes UserRole and returns boolean
  - Single source of truth for frontend permission checks

### Navigation: role-based menu items
- [ ] Update `frontend/src/routes/+layout.svelte`
  - SM: Dashboard, POs, Invoices, Vendors, Products (all nav links)
  - VENDOR: Dashboard, POs, Invoices (no Vendors, no Products)
  - QUALITY_LAB: Dashboard, Products (no POs, no Invoices, no Vendors)
  - FREIGHT_MANAGER: Dashboard, POs (no Invoices, no Vendors, no Products)
  - Use `canManageVendors`, `canViewProducts`, `canViewInvoices`, `canViewPOs` to control visibility
  - Display current user's display_name and role in header/nav

### PO list page (`frontend/src/routes/po/+page.svelte`)
- [ ] Hide "Create PO" button unless `canCreatePO(role)`
- [ ] Bulk action buttons:
  - SM sees: Submit, Resubmit
  - VENDOR sees: Accept, Reject
  - Neither role sees the other's actions
- [ ] All roles see the PO list table (data scoping is backend's job)

### PO detail page (`frontend/src/routes/po/[id]/+page.svelte`)
- [ ] SM sees: Edit button (on REJECTED POs), Submit button (on DRAFT), Resubmit button (on REVISED)
- [ ] VENDOR sees: Accept button (on PENDING), Reject button (on PENDING), Milestone form (on ACCEPTED PROCUREMENT POs)
- [ ] QUALITY_LAB and FREIGHT_MANAGER: no action buttons, read-only view
- [ ] All roles see: PO details, line items, milestone timeline, activity timeline, PDF download

### PO create page (`frontend/src/routes/po/new/+page.svelte`)
- [ ] Redirect non-SM users to /po with an error message or toast
- [ ] Check role on mount; if not SM, `goto('/po')`

### PO edit page (`frontend/src/routes/po/[id]/edit/+page.svelte`)
- [ ] Redirect non-SM users to /po/[id]
- [ ] Check role on mount; if not SM, `goto('/po/' + id)`

### Invoice list page (`frontend/src/routes/invoices/+page.svelte`)
- [ ] Redirect QUALITY_LAB and FREIGHT_MANAGER to /dashboard (they cannot view invoices)
- [ ] SM sees: no create button (invoices are created from PO detail), bulk PDF download
- [ ] VENDOR sees: bulk PDF download
- [ ] Both SM and VENDOR see the invoice list table

### Invoice detail page (`frontend/src/routes/invoice/[id]/+page.svelte`)
- [ ] Redirect QUALITY_LAB and FREIGHT_MANAGER to /dashboard
- [ ] SM sees: Approve button (on SUBMITTED), Pay button (on APPROVED), Dispute button (on SUBMITTED/APPROVED), Resolve button (on DISPUTED)
- [ ] VENDOR sees: Submit button (on DRAFT)
- [ ] Both SM and VENDOR see: invoice details, line items, activity timeline, PDF download

### Vendor list page (`frontend/src/routes/vendors/+page.svelte`)
- [ ] Redirect non-SM users to /dashboard
- [ ] SM sees: Create Vendor button, deactivate/reactivate actions, full vendor list

### Vendor create page (`frontend/src/routes/vendors/new/+page.svelte`)
- [ ] Redirect non-SM users to /dashboard

### Product list page (`frontend/src/routes/products/+page.svelte`)
- [ ] Redirect VENDOR and FREIGHT_MANAGER to /dashboard (they cannot view products)
- [ ] SM sees: Create Product button
- [ ] QUALITY_LAB sees: read-only list, no create button

### Product create page (`frontend/src/routes/products/new/+page.svelte`)
- [ ] Redirect non-SM users to /products (QUALITY_LAB can view but not create) or /dashboard (others)

### Product edit page (`frontend/src/routes/products/[id]/edit/+page.svelte`)
- [ ] Redirect non-SM users to /products/[id] or /dashboard

### Dashboard (`frontend/src/routes/dashboard/+page.svelte`)
- [ ] Activity feed: filter by `target_role` matching current user's role
  - SM sees events targeted at SM
  - VENDOR sees events targeted at VENDOR
  - QUALITY_LAB and FREIGHT_MANAGER: currently no events target them (Phase 3 adds QUALITY_LAB and FREIGHT_MANAGER to TargetRole). Show empty feed or all-role events for now.
- [ ] Notification bell (if in nav): filter unread count by target_role (requires backend change or client-side filter)
  - Note: if the backend unread count endpoint does not filter by role, pass target_role query parameter to the backend (may need a small backend change: add `target_role` filter to `unread_count()` and `list_recent()` in ActivityLogRepository)
- [ ] Dashboard cards/widgets:
  - SM: PO summary, invoice summary, vendor summary, production pipeline, overdue POs, recent POs
  - VENDOR: PO summary (own), invoice summary (own), production pipeline (own), overdue POs (own)
  - QUALITY_LAB: products count, activity feed (no PO/invoice/vendor summaries)
  - FREIGHT_MANAGER: PO summary (read-only context), production pipeline (read-only context)

### Backend: target_role filter on activity endpoints (small addition)
- [ ] Add optional `target_role` query parameter to `GET /api/v1/activity/` and `GET /api/v1/activity/unread-count`
- [ ] Update `ActivityLogRepository.list_recent()` and `unread_count()` to accept optional `target_role` filter
- [ ] This is a minor backend change needed to support role-filtered activity on the frontend

### Tests (permanent)
- [ ] `frontend/tests/role-rendering.spec.ts` (Playwright)
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
  - Note: these tests require mocking /api/v1/auth/me to return different user roles

### Tests (scratch)
- [ ] Screenshot: SM nav with all links visible
- [ ] Screenshot: VENDOR nav with limited links
- [ ] Screenshot: VENDOR PO detail with accept/reject buttons, no edit/submit
- [ ] Screenshot: SM PO detail with edit/submit buttons, no accept/reject
- [ ] Screenshot: SM invoice detail with approve/pay/dispute buttons
- [ ] Screenshot: VENDOR invoice detail with submit button only
- [ ] Screenshot: QUALITY_LAB dashboard (products-focused)

## Acceptance criteria
- [ ] Navigation links are role-conditional: each role sees only their permitted sections
- [ ] Current user display_name and role are shown in the header/nav
- [ ] PO list: Create button visible only for SM; bulk actions differ by role
- [ ] PO detail: action buttons match role (SM: edit/submit/resubmit, VENDOR: accept/reject/milestone)
- [ ] PO create/edit pages redirect non-SM users away
- [ ] Invoice list/detail: visible only to SM and VENDOR; action buttons match role
- [ ] Vendor pages: visible only to SM
- [ ] Product pages: visible to SM (full CRUD) and QUALITY_LAB (read-only); hidden from VENDOR and FREIGHT_MANAGER
- [ ] Dashboard activity feed filters by current user's target_role
- [ ] Dashboard widgets adjust per role (VENDOR sees own data, QUALITY_LAB sees products)
- [ ] Page-level redirects prevent unauthorized page access (not just hidden buttons)
- [ ] `make test-browser` passes with new Playwright tests
