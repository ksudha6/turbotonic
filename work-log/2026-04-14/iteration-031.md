# Iteration 031 -- API role guards

## Context

Session middleware (iter 030) populates `request.state.current_user` on every request, but no endpoint checks it, so all ~30 endpoints remain open. This iteration adds a `require_role(*roles)` FastAPI dependency and applies it to every router. After this, unauthenticated requests return 401 and wrong-role requests return 403.

## JTBD (Jobs To Be Done)

- When an unauthenticated user calls any endpoint, I want the system to return 401, so that the API is not publicly accessible
- When a VENDOR user tries to create a PO, I want the system to return 403, so that only SM can create POs
- When an SM user tries to accept a PO, I want the system to return 403, so that only VENDOR can accept/reject POs
- When a VENDOR user tries to create a vendor or product, I want the system to return 403, so that only SM manages the catalog
- When any authenticated user queries the dashboard or activity feed, I want the system to allow it, so that all roles have visibility into relevant activity

## Tasks

### Auth dependency: require_role
- [ ] Create `backend/src/auth/dependencies.py`
  - `get_current_user(request: Request) -> User` -- reads `request.state.current_user`, raises 401 HTTPException if None
  - `require_role(*roles: UserRole) -> Depends` -- returns a FastAPI dependency that calls `get_current_user`, then checks `user.role in roles`, raises 403 HTTPException("Insufficient permissions") if not
  - `require_auth` -- alias for `get_current_user` (any authenticated user, no role check)
  - Type aliases: `CurrentUser = Annotated[User, Depends(get_current_user)]`

### Guard: Purchase Order router (`backend/src/routers/purchase_order.py`)
- [ ] `POST /api/v1/po/` (create_po) -- require_role(SM)
- [ ] `GET /api/v1/po/` (list_pos) -- require_auth (all roles)
- [ ] `POST /api/v1/po/bulk/transition` (bulk_transition) -- require_role(SM, VENDOR) (SM for submit/resubmit, VENDOR for accept/reject; fine-grained action check inside handler)
- [ ] `GET /api/v1/po/{po_id}` (get_po) -- require_auth (all roles)
- [ ] `GET /api/v1/po/{po_id}/pdf` (get_po_pdf) -- require_auth (all roles)
- [ ] `GET /api/v1/po/{po_id}/invoices` (list_po_invoices) -- require_role(SM, VENDOR)
- [ ] `POST /api/v1/po/{po_id}/submit` (submit_po) -- require_role(SM)
- [ ] `POST /api/v1/po/{po_id}/accept` (accept_po) -- require_role(VENDOR)
- [ ] `POST /api/v1/po/{po_id}/reject` (reject_po) -- require_role(VENDOR)
- [ ] `PUT /api/v1/po/{po_id}` (update_po) -- require_role(SM)
- [ ] `POST /api/v1/po/{po_id}/resubmit` (resubmit_po) -- require_role(SM)

### Guard: Invoice router (`backend/src/routers/invoice.py`)
- [ ] `GET /api/v1/invoices/po/{po_id}/remaining` (get_remaining_quantities) -- require_role(SM, VENDOR)
- [ ] `POST /api/v1/invoices/` (create_invoice) -- require_role(VENDOR)
- [ ] `GET /api/v1/invoices/` (list_invoices) -- require_role(SM, VENDOR)
- [ ] `POST /api/v1/invoices/bulk/pdf` (bulk_invoice_pdf) -- require_role(SM, VENDOR)
- [ ] `GET /api/v1/invoices/{invoice_id}` (get_invoice) -- require_role(SM, VENDOR)
- [ ] `GET /api/v1/invoices/{invoice_id}/pdf` (get_invoice_pdf) -- require_role(SM, VENDOR)
- [ ] `POST /api/v1/invoices/{invoice_id}/submit` (submit_invoice) -- require_role(VENDOR)
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
- [ ] `POST /api/v1/po/{po_id}/milestones` (post_milestone) -- require_role(VENDOR)

### Guard: Activity router (`backend/src/routers/activity.py`)
- [ ] `GET /api/v1/activity/unread-count` (get_unread_count) -- require_auth (all roles)
- [ ] `GET /api/v1/activity/` (list_activity) -- require_auth (all roles)
- [ ] `POST /api/v1/activity/mark-read` (mark_read) -- require_auth (all roles)

### Guard: Dashboard router (`backend/src/routers/dashboard.py`)
- [ ] `GET /api/v1/dashboard/` (get_dashboard) -- require_auth (all roles)

### Guard: Reference Data router (`backend/src/routers/reference_data.py`)
- [ ] `GET /api/v1/reference-data/` (get_reference_data) -- require_auth (all roles)

### Guard: Auth router (`backend/src/routers/auth.py`)
- [ ] Auth endpoints remain unguarded (register, login, logout are pre-auth by nature)
- [ ] `GET /api/v1/auth/me` remains as-is (returns 401 if no session, user if session exists)

### Guard: Health endpoint (`backend/src/main.py`)
- [ ] `GET /health` -- remains unguarded (infrastructure endpoint)

### Bulk transition fine-grained check
- [ ] Inside `bulk_transition` handler: after role gate allows SM+VENDOR, check that SM can only submit/resubmit and VENDOR can only accept/reject. Return 403 if a VENDOR tries to submit or an SM tries to accept.

### Tests (permanent)
- [ ] `backend/tests/test_role_guards.py`
  - Unauthenticated request to a guarded endpoint returns 401
  - SM can call POST /api/v1/po/ (create PO)
  - VENDOR cannot call POST /api/v1/po/ (returns 403)
  - VENDOR can call POST /api/v1/po/{id}/accept
  - SM cannot call POST /api/v1/po/{id}/accept (returns 403)
  - VENDOR can call POST /api/v1/invoices/ (create invoice)
  - SM cannot call POST /api/v1/invoices/ (returns 403)
  - SM can call POST /api/v1/invoices/{id}/approve
  - VENDOR cannot call POST /api/v1/invoices/{id}/approve (returns 403)
  - SM can call POST /api/v1/vendors/ (create vendor)
  - VENDOR cannot call POST /api/v1/vendors/ (returns 403)
  - QUALITY_LAB cannot call POST /api/v1/vendors/ (returns 403)
  - FREIGHT_MANAGER cannot call POST /api/v1/vendors/ (returns 403)
  - SM can call POST /api/v1/products/ (create product)
  - VENDOR cannot call POST /api/v1/products/ (returns 403)
  - QUALITY_LAB can call GET /api/v1/products/ (list products)
  - VENDOR can call POST /api/v1/po/{id}/milestones (post milestone)
  - SM cannot call POST /api/v1/po/{id}/milestones (returns 403)
  - Any authenticated role can call GET /api/v1/dashboard/
  - Any authenticated role can call GET /api/v1/reference-data/
  - Any authenticated role can call GET /api/v1/activity/
  - Bulk transition: VENDOR trying action=submit returns 403
  - Bulk transition: SM trying action=accept returns 403

### Tests (scratch)
- [ ] Use httpie or curl to verify 401/403 responses for representative endpoints

## Acceptance criteria
- [ ] `require_role()` dependency returns 401 for unauthenticated requests
- [ ] `require_role()` dependency returns 403 for wrong-role requests
- [ ] All 30+ endpoints have explicit auth guards (no endpoint is unguarded except /health and /api/v1/auth/*)
- [ ] SM can: create/edit/submit/resubmit PO, approve/pay/dispute/resolve invoice, CRUD vendors, CRUD products
- [ ] VENDOR can: accept/reject PO, create/submit invoice, post milestone
- [ ] QUALITY_LAB can: list/view products, view dashboard, view activity
- [ ] FREIGHT_MANAGER can: view PO list, view dashboard, view activity
- [ ] All roles can: list/view POs, view dashboard, view activity, view reference data, view milestones
- [ ] Bulk transition enforces action-level role checks (SM: submit/resubmit, VENDOR: accept/reject)
- [ ] `make test` passes with all new and existing tests
