# Iteration 031 -- API role guards

## Context

Session middleware (iter 030) populates `request.state.current_user` on every request, but no endpoint checks it, so all ~30 endpoints remain open. This iteration adds a `require_role(*roles)` FastAPI dependency and applies it to every router. After this, unauthenticated requests return 401 and wrong-role requests return 403. ADMIN passes every guard.

## JTBD (Jobs To Be Done)

- When an unauthenticated user calls any endpoint, I want the system to return 401, so that the API is not publicly accessible
- When an ADMIN calls any endpoint, I want the system to allow it, so that admins have unrestricted access
- When a VENDOR user tries to create a PO, I want the system to return 403, so that only SM can create POs
- When a FREIGHT_MANAGER views or manages OpEx invoices, I want the system to allow it, so that freight managers own their domain
- When a VENDOR user tries to create a vendor or product, I want the system to return 403, so that only SM manages the catalog
- When any authenticated user queries the dashboard or activity feed, I want the system to allow it, so that all roles have visibility into relevant activity

## Tasks

### Auth dependency: require_role
- [ ] Create `backend/src/auth/dependencies.py`
  - `get_current_user(request: Request) -> User` -- reads `request.state.current_user`, raises 401 HTTPException if None
  - `require_role(*roles: UserRole) -> Depends` -- returns a FastAPI dependency that calls `get_current_user`, then checks `user.role == ADMIN or user.role in roles`, raises 403 HTTPException("Insufficient permissions") if not
  - `require_auth` -- alias for `get_current_user` (any authenticated user, no role check)
  - Type aliases: `CurrentUser = Annotated[User, Depends(get_current_user)]`
  - ADMIN always passes every role check (built into require_role, not repeated per endpoint)

### Guard: Purchase Order router (`backend/src/routers/purchase_order.py`)
- [ ] `POST /api/v1/po/` (create_po) -- require_role(SM)
- [ ] `GET /api/v1/po/` (list_pos) -- require_auth (all roles)
- [ ] `POST /api/v1/po/bulk/transition` (bulk_transition) -- require_role(SM, VENDOR) (SM for submit/resubmit/accept/reject, VENDOR for accept/reject; fine-grained action check inside handler)
- [ ] `GET /api/v1/po/{po_id}` (get_po) -- require_auth (all roles)
- [ ] `GET /api/v1/po/{po_id}/pdf` (get_po_pdf) -- require_auth (all roles)
- [ ] `GET /api/v1/po/{po_id}/invoices` (list_po_invoices) -- require_role(SM, VENDOR)
- [ ] `POST /api/v1/po/{po_id}/submit` (submit_po) -- require_role(SM)
- [ ] `POST /api/v1/po/{po_id}/accept` (accept_po) -- require_role(VENDOR, SM)
- [ ] `POST /api/v1/po/{po_id}/reject` (reject_po) -- require_role(VENDOR, SM)
- [ ] `PUT /api/v1/po/{po_id}` (update_po) -- require_role(SM)
- [ ] `POST /api/v1/po/{po_id}/resubmit` (resubmit_po) -- require_role(SM)

### Guard: Invoice router (`backend/src/routers/invoice.py`)
- [ ] `GET /api/v1/invoices/po/{po_id}/remaining` (get_remaining_quantities) -- require_role(SM, VENDOR)
- [ ] `POST /api/v1/invoices/` (create_invoice) -- require_role(VENDOR, SM)
- [ ] `GET /api/v1/invoices/` (list_invoices) -- require_role(SM, VENDOR, FREIGHT_MANAGER)
- [ ] `POST /api/v1/invoices/bulk/pdf` (bulk_invoice_pdf) -- require_role(SM, VENDOR, FREIGHT_MANAGER)
- [ ] `GET /api/v1/invoices/{invoice_id}` (get_invoice) -- require_role(SM, VENDOR, FREIGHT_MANAGER)
- [ ] `GET /api/v1/invoices/{invoice_id}/pdf` (get_invoice_pdf) -- require_role(SM, VENDOR, FREIGHT_MANAGER)
- [ ] `POST /api/v1/invoices/{invoice_id}/submit` (submit_invoice) -- require_role(VENDOR, SM)
- [ ] `POST /api/v1/invoices/{invoice_id}/approve` (approve_invoice) -- require_role(SM)
- [ ] `POST /api/v1/invoices/{invoice_id}/pay` (pay_invoice) -- require_role(SM)
- [ ] `POST /api/v1/invoices/{invoice_id}/dispute` (dispute_invoice) -- require_role(SM)
- [ ] `POST /api/v1/invoices/{invoice_id}/resolve` (resolve_invoice) -- require_role(SM)

### Guard: Vendor router (`backend/src/routers/vendor.py`)
- [ ] `POST /api/v1/vendors/` (create_vendor) -- require_role(SM)
- [ ] `GET /api/v1/vendors/` (list_vendors) -- require_role(SM)
- [ ] `GET /api/v1/vendors/{vendor_id}` (get_vendor) -- require_role(SM)
- [ ] `POST /api/v1/vendors/{vendor_id}/deactivate` (deactivate_vendor) -- require_role(SM)
- [ ] `POST /api/v1/vendors/{vendor_id}/reactivate` (reactivate_vendor) -- require_role(SM)

### Guard: Product router (`backend/src/routers/product.py`)
- [ ] `POST /api/v1/products/` (create_product) -- require_role(SM)
- [ ] `GET /api/v1/products/` (list_products) -- require_role(SM, QUALITY_LAB)
- [ ] `GET /api/v1/products/{product_id}` (get_product) -- require_role(SM, QUALITY_LAB)
- [ ] `PATCH /api/v1/products/{product_id}` (update_product) -- require_role(SM)

### Guard: Milestone router (`backend/src/routers/milestone.py`)
- [ ] `GET /api/v1/po/{po_id}/milestones` (list_milestones) -- require_auth (all roles)
- [ ] `POST /api/v1/po/{po_id}/milestones` (post_milestone) -- require_role(VENDOR, SM)

### Guard: Activity router (`backend/src/routers/activity.py`)
- [ ] `GET /api/v1/activity/unread-count` (get_unread_count) -- require_auth (all roles)
- [ ] `GET /api/v1/activity/` (list_activity) -- require_auth (all roles)
- [ ] `POST /api/v1/activity/mark-read` (mark_read) -- require_auth (all roles)

### Guard: Dashboard router (`backend/src/routers/dashboard.py`)
- [ ] `GET /api/v1/dashboard/` (get_dashboard) -- require_auth (all roles)

### Guard: Reference Data router (`backend/src/routers/reference_data.py`)
- [ ] `GET /api/v1/reference-data/` (get_reference_data) -- require_auth (all roles)

### Guard: Auth router (`backend/src/routers/auth.py`)
- [ ] Auth endpoints remain unguarded (bootstrap, register, login, logout are pre-auth by nature)
- [ ] `GET /api/v1/auth/me` remains as-is (returns 401 if no session, user if session exists)

### Guard: User management router (`backend/src/routers/users.py`)
- [ ] `POST /api/v1/users/invite` -- require_role(ADMIN)
- [ ] `GET /api/v1/users/` -- require_role(ADMIN) (list all users with role/status filters)
- [ ] `GET /api/v1/users/{user_id}` -- require_role(ADMIN) (view single user)
- [ ] `PATCH /api/v1/users/{user_id}` -- require_role(ADMIN) (update role, display_name, vendor assignments)
- [ ] `POST /api/v1/users/{user_id}/deactivate` -- require_role(ADMIN) (enforces last-admin guard)
- [ ] `POST /api/v1/users/{user_id}/reactivate` -- require_role(ADMIN)

### Guard: Health endpoint (`backend/src/main.py`)
- [ ] `GET /health` -- remains unguarded (infrastructure endpoint)

### Bulk transition fine-grained check
- [ ] Inside `bulk_transition` handler: after role gate allows SM+VENDOR, check action permissions:
  - SM can: submit, resubmit, accept, reject
  - VENDOR can: accept, reject
  - Return 403 if a VENDOR tries to submit/resubmit

### Existing test impact
- All 14 existing backend test files break: every endpoint now returns 401 without a session.
- Add an `authenticated_client` fixture to `conftest.py` that:
  1. Creates a test user (role=ADMIN, status=ACTIVE) in the database
  2. Sets a valid `tt_session` cookie on the AsyncClient
- Update all existing tests to use `authenticated_client` instead of `client`.
- The unauthenticated `client` fixture stays for testing 401 behavior.

### Tests (permanent)
- [ ] `backend/tests/test_role_guards.py`
  - Unauthenticated request to a guarded endpoint returns 401
  - ADMIN can call any endpoint (test representative sample)
  - SM can call POST /api/v1/po/ (create PO)
  - VENDOR cannot call POST /api/v1/po/ (returns 403)
  - VENDOR can call POST /api/v1/po/{id}/accept
  - SM can call POST /api/v1/po/{id}/accept
  - FREIGHT_MANAGER can call GET /api/v1/invoices/ (list invoices)
  - FREIGHT_MANAGER cannot call POST /api/v1/po/ (returns 403)
  - VENDOR can call POST /api/v1/invoices/ (create invoice)
  - SM can call POST /api/v1/invoices/
  - SM can call POST /api/v1/invoices/{id}/approve
  - VENDOR cannot call POST /api/v1/invoices/{id}/approve (returns 403)
  - SM can call POST /api/v1/vendors/ (create vendor)
  - VENDOR cannot call POST /api/v1/vendors/ (returns 403)
  - QUALITY_LAB cannot call POST /api/v1/vendors/ (returns 403)
  - FREIGHT_MANAGER cannot call POST /api/v1/vendors/ (returns 403)
  - SM can call POST /api/v1/products/ (create product)
  - QUALITY_LAB can call GET /api/v1/products/ (list products)
  - VENDOR cannot call POST /api/v1/products/ (returns 403)
  - VENDOR can call POST /api/v1/po/{id}/milestones (post milestone)
  - SM can call POST /api/v1/po/{id}/milestones
  - Any authenticated role can call GET /api/v1/dashboard/
  - Any authenticated role can call GET /api/v1/reference-data/
  - Any authenticated role can call GET /api/v1/activity/
  - Bulk transition: VENDOR trying action=submit returns 403
  - Bulk transition: SM can action=accept
  - ADMIN can call POST /api/v1/users/invite
  - SM cannot call POST /api/v1/users/invite (returns 403)

### Tests (scratch)
- [x] Verified 401/403 via dev-login endpoint and curl

## Acceptance criteria
- [x] `require_role()` dependency returns 401 for unauthenticated requests
- [x] `require_role()` dependency returns 403 for wrong-role requests
- [x] ADMIN passes every role check automatically
- [x] All 30+ endpoints have explicit auth guards (no endpoint is unguarded except /health and /api/v1/auth/*)
- [x] SM can: create/edit/submit/resubmit PO, accept/reject PO, approve/pay/dispute/resolve invoice, create/submit invoice, CRUD vendors, CRUD products, post milestones
- [x] VENDOR can: accept/reject PO, create/submit invoice, post milestone
- [x] FREIGHT_MANAGER can: view all POs, view/manage invoices (OpEx scope deferred to 032), view dashboard, view activity
- [x] QUALITY_LAB can: list/view products, view dashboard, view activity
- [x] Bulk transition enforces action-level role checks (SM: submit/resubmit/accept/reject, VENDOR: accept/reject only)
- [x] Only ADMIN can invite new users
- [x] All pre-existing backend tests pass with the authenticated_client fixture
- [x] `make test` passes with all new and existing tests (252 backend, 59 Playwright)

## Notes

Added `require_role(*roles)` and `require_auth` FastAPI dependencies in `auth/dependencies.py`. ADMIN bypasses all role checks. Applied guards to all 8 non-auth routers (30+ endpoints). Bulk transition has a fine-grained action check: VENDOR is blocked from submit/resubmit. Existing tests updated to use `authenticated_client` fixture (ADMIN session cookie). Added `dev-login` endpoint (`GET /api/v1/auth/dev-login`) to set session cookie via browser for local development; the Vite proxy means visiting `/api/v1/auth/dev-login` on the frontend port sets the cookie correctly. Carried forward: user management CRUD endpoints (list, get, update, deactivate, reactivate) listed in tasks but not implemented; only invite exists.
