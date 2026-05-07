# Iteration 111 — Brand-scoped user access

## Context

The system has brands (iter 108), brand frontend (iter 109), and vendor-scoped access via `check_vendor_access` (iter 032). VENDOR users see only their vendor's POs, invoices, milestones, activity, and dashboard data. Buyer-side roles (SM, FREIGHT_MANAGER, QUALITY_LAB, PROCUREMENT_MANAGER) see everything across all brands.

With multiple brands now live, an ops staff member supporting only Brand A should not see Brand B's POs, invoices, shipments, activity, or dashboard data. There is currently no join table or column linking users to brands.

ADMIN remains globally unscoped. VENDOR scoping is orthogonal (vendor axis, not brand axis) and unchanged. Brand scoping is a buyer-side concept only.

The `/users` page (iter 100) has an invite modal and an edit modal. Neither surfaces brand assignment. The backend `/api/v1/users` invite and patch endpoints carry no brand field.

## JTBD

- ADMIN inviting a new SM, FREIGHT_MANAGER, QUALITY_LAB, or PROCUREMENT_MANAGER user needs to optionally assign one or more brands to that user. An empty assignment means the user sees all brands (legacy behavior preserved for operators that haven't configured brand scoping yet).
- ADMIN editing an existing buyer-side user needs to add or remove brand assignments.
- An SM assigned to Brand A only sees Brand A's POs on the list, PO detail, invoices, shipments, activity feed, and dashboard KPIs. They cannot reach Brand B entities via direct URL.
- A FREIGHT_MANAGER assigned to Brand A only sees Brand A's shipments and related activity.
- A QUALITY_LAB user assigned to Brand A only sees Brand A's certificates, POs, and activity.
- A PROCUREMENT_MANAGER assigned to Brand A only sees Brand A's POs and invoices.
- ADMIN sees everything regardless of brand assignments.
- VENDOR users are unaffected; their scoping remains on the vendor axis.

## Tasks

### 1. Schema

Add a `user_brands` join table in `backend/src/schema.py`:

```sql
CREATE TABLE IF NOT EXISTS user_brands (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    brand_id TEXT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, brand_id)
);
```

No backfill needed. An empty `user_brands` set means "all brands" for non-VENDOR roles. Existing users continue to see everything until an ADMIN explicitly assigns brands.

### 2. User repository

In `backend/src/user_repository.py`:

- `assign_brand(user_id: str, brand_id: str) -> None` — inserts into `user_brands`, idempotent on conflict (INSERT OR IGNORE).
- `unassign_brand(user_id: str, brand_id: str) -> None` — deletes the row; no-op if absent.
- `list_brand_ids(user_id: str) -> list[str]` — returns all brand_ids for the user; empty list means unscoped.
- `set_brands(user_id: str, brand_ids: list[str]) -> None` — replace the full brand set atomically: delete all existing rows for `user_id`, then bulk-insert `brand_ids`. Empty list clears all assignments (reverts to unscoped).

### 3. Domain helper

In `backend/src/auth/dependencies.py`, add:

```python
async def get_accessible_brand_ids(user: User, brand_repo_dep) -> list[str] | None:
```

Returns:
- `None` when the user is ADMIN or VENDOR (ADMIN is unscoped; VENDOR is vendor-scoped by a different axis).
- `[]` (empty list, meaning "all brands") when the user is a buyer-side role with no explicit brand assignments.
- `[brand_id, ...]` when the user has explicit brand assignments.

Callers treat `None` as "no brand filter" and an empty or populated list as "filter to this set". The helper queries `user_brands` via the repository.

Also add:

```python
def check_brand_access(user: User, brand_id: str, accessible_brand_ids: list[str] | None) -> None:
```

Raises HTTP 404 if `accessible_brand_ids` is not `None` and `brand_id` is not in `accessible_brand_ids`. Used in PO detail, shipment detail, and invoice detail endpoints for direct-URL access.

### 4. User invite and patch endpoints

In `backend/src/routers/users.py`:

- `POST /api/v1/users/invite` body gains optional `brand_ids: list[str] | None` (default `None`, meaning unscoped). When provided, each brand_id is validated as an existing brand (404 on unknown); then `user_repository.set_brands()` is called after user creation. Applies only to non-VENDOR, non-ADMIN roles; silently ignored for VENDOR and ADMIN.
- `PATCH /api/v1/users/{id}` body gains optional `brand_ids: list[str] | None`. When provided (including empty list), replaces the user's brand set via `user_repository.set_brands()`. When absent (key not in body), brand assignments are unchanged. Applies only to non-VENDOR, non-ADMIN roles.
- `GET /api/v1/users/{id}` response gains `brand_ids: list[str]` (the user's current brand assignments, empty list if unscoped).
- `GET /api/v1/users/` list response gains `brand_ids: list[str]` per user (single JOIN query, not N+1).

Emit a new `BRAND_USERS_UPDATED` activity event after any brand-assignment change via invite or patch. Event carries `entity_type=EntityType.USER`, `entity_id=user_id`, `metadata={"brand_ids": [...]}`, `target_role=TargetRole.ADMIN`.

Add `ActivityEvent.BRAND_USERS_UPDATED` to `backend/src/domain/activity.py` with `EVENT_METADATA` entry: `(NotificationCategory.LIVE, TargetRole.ADMIN)`.

### 5. PO list and detail filtering

In `backend/src/routers/purchase_order.py`:

- `GET /api/v1/po/` list: when the requesting user is a buyer-side role with explicit brand assignments, add a brand filter to the query. `list_pos_paginated` in `backend/src/repository.py` gains an optional `brand_ids: list[str] | None` parameter. When provided, a `WHERE p.brand_id = ANY($N)` clause is added. When `None` or empty list, no brand filter applies.
- `GET /api/v1/po/{id}` detail: call `check_brand_access(user, po.brand_id, accessible_brand_ids)` after the PO fetch. VENDOR access continues to pass through `check_vendor_access` unchanged; brand check is additive on the buyer side.
- All other PO sub-resource endpoints (line items, documents, milestones, PDFs, transitions) that fetch the PO first will inherit the 404 from the detail fetch pattern. No additional brand checks needed in those handlers.

### 6. Dashboard filtering

In `backend/src/routers/dashboard.py`:

- `GET /api/v1/dashboard/summary`: for buyer-side users with explicit brand assignments, pass `brand_ids` into the KPI queries (`po_summary_by_status`, `recent_pos`, `awaiting_acceptance`, production pipeline). The existing `vendor_id` parameter pattern is the model; add a parallel `brand_ids: list[str] | None` parameter to each affected query function.
- The legacy `GET /api/v1/dashboard/` endpoint receives the same treatment for consistency; it will retire end of Phase 4.

### 7. Activity feed filtering

In `backend/src/routers/activity.py`:

- `GET /api/v1/activity/` list: for buyer-side users with explicit brand assignments, join against `purchase_orders` on `entity_id` where `entity_type = 'PO'` and filter to `brand_id IN (...)`. Activity rows not tied to a PO entity (e.g. USER events, CERTIFICATE events, BRAND events) remain visible regardless of brand scope. This is a pragmatic choice: brand-scoped activity narrowing applies only to PO-derived events.
- `GET /api/v1/activity/unread-count`: same brand filter logic.

### 8. Invoice and shipment filtering

In `backend/src/routers/invoice.py` and `backend/src/routers/shipment.py`:

- Invoice list (`GET /api/v1/invoices/`): invoices are linked to POs via `po_id`. When the user has explicit brand assignments, join to `purchase_orders` on `po_id` and filter `purchase_orders.brand_id IN (...)`.
- Invoice detail (`GET /api/v1/invoices/{id}`): call `check_brand_access` using the invoice's parent PO `brand_id`.
- Shipment list (`GET /api/v1/shipments/`): shipments are linked to POs via `po_id`. Same join-based brand filter.
- Shipment detail (`GET /api/v1/shipment/{id}`): call `check_brand_access` using the shipment's parent PO `brand_id`.

### 9. Frontend: user invite modal

In `frontend/src/lib/user/UserInviteModal.svelte`:

- When the selected role is SM, FREIGHT_MANAGER, QUALITY_LAB, or PROCUREMENT_MANAGER, show a "Brands" multi-select field below the Role field. Source: `listBrands({ status: 'ACTIVE' })` lazy-fetched on first render of the field (mirrors the `loadVendors` lazy pattern). An empty selection means unscoped (sees all brands).
- The field renders as a multi-checkboxlist or a multi-select `<select multiple>` using the existing `Select` primitive if it supports multiple; otherwise a custom `BrandMultiSelect` component. The selected brand IDs are submitted in `brand_ids: string[]` on the invite payload.
- `InviteUserInput` type in `frontend/src/lib/types.ts` gains `brand_ids?: string[] | null`.

### 10. Frontend: user edit modal

In `frontend/src/lib/user/UserEditModal.svelte`:

- Load the user's current `brand_ids` (available from the user row via the updated `GET /api/v1/users/{id}` response).
- Show the same "Brands" multi-select field when the user's role is SM, FREIGHT_MANAGER, QUALITY_LAB, or PROCUREMENT_MANAGER. Pre-populate from `user.brand_ids`.
- On save, include `brand_ids` in the PATCH body. Empty array clears all assignments.
- `PatchUserInput` type gains `brand_ids?: string[] | null`.

### 11. Frontend: API client

In `frontend/src/lib/api.ts`:

- `listBrandsForUser(userId)` is not needed; brand_ids are already embedded in the user detail response.
- Update `inviteUser` and `patchUser` call signatures to pass `brand_ids`.
- Update the `User` and `UserListItem` types in `frontend/src/lib/types.ts` to include `brand_ids: string[]`.

### 12. Frontend: permissions

No new permission helpers needed. Brand-scoped filtering is transparent to the frontend. The UI shows whatever the API returns. If a brand-scoped SM navigates to a PO outside their brands, the backend returns 404 and the frontend renders the standard not-found state.

## Tests

### Existing test impact

- `backend/tests/test_users.py`: `GET /api/v1/users/` and `GET /api/v1/users/{id}` response shape now includes `brand_ids`. Update response-shape assertions to expect `brand_ids: []` on all existing test users. `POST /invite` and `PATCH /{id}` bodies with no `brand_ids` field must continue to work (backward compatible). About 10-15 assertions to audit.
- `backend/tests/test_purchase_orders.py`: PO list and detail endpoints called by SM/FM/QL/PM fixture users gain brand-filter logic. Existing tests use unscoped users (no `user_brands` rows), so the brand filter is a no-op and assertions are unaffected. Confirm with a pass check before writing new tests.
- `backend/tests/test_dashboard_summary.py`: same reasoning as PO tests. Unscoped users have empty `user_brands` and see all data. No assertion changes expected.
- `backend/tests/test_activity.py`: same. No assertion changes expected.
- `backend/tests/test_brands.py`: brand activity events include the new `BRAND_USERS_UPDATED` event; if any test asserts an exhaustive list of `ActivityEvent` variants, update it.
- `backend/tests/conftest.py`: add a `scoped_sm_user` fixture (SM user with one brand assigned) and a `scoped_freight_manager_user` fixture used by brand-scoping tests. These fixtures insert into `user_brands` directly after user creation.
- `frontend/tests/users.spec.ts`: existing invite modal assertions do not check for a Brands field (it only appears for non-VENDOR, non-ADMIN roles). If existing tests invite VENDOR users, they are unaffected. If they invite SM users, the Brands field now appears; add a mock for `listBrands` in the test setup and assert the field is present. Estimate 3-5 spec edits.

### New tests

`backend/tests/test_user_brand_assignment.py`:

- `test_invite_sm_with_brand_ids_assigns_brands`: POST /invite with `brand_ids=[brand_a_id]` for SM role; assert `GET /users/{id}` returns `brand_ids=[brand_a_id]`.
- `test_invite_vendor_brand_ids_ignored`: POST /invite for VENDOR role with `brand_ids=[brand_a_id]`; assert `brand_ids=[]` on the response (VENDOR is vendor-scoped, not brand-scoped).
- `test_invite_admin_brand_ids_ignored`: same for ADMIN role.
- `test_patch_user_sets_brands`: PATCH /{id} with `brand_ids=[brand_a_id, brand_b_id]`; assert both present in user detail.
- `test_patch_user_clears_brands`: PATCH /{id} with `brand_ids=[]`; assert `brand_ids=[]`.
- `test_patch_user_no_brand_ids_key_unchanged`: PATCH /{id} body without `brand_ids` key; assert existing assignments unchanged.
- `test_invite_unknown_brand_id_returns_404`: POST /invite with a nonexistent brand_id; assert 404 with message naming the unknown id.
- `test_brand_users_updated_event_emitted`: after PATCH sets brand_ids, assert one `BRAND_USERS_UPDATED` activity row with correct `entity_type=USER`, `entity_id`, `target_role=ADMIN`.

`backend/tests/test_brand_scoped_po_access.py`:

- `test_scoped_sm_po_list_filters_to_assigned_brand`: SM with `brand_ids=[brand_a_id]` calls `GET /po/`; assert only brand_a POs in the response, brand_b POs absent.
- `test_scoped_sm_po_detail_own_brand_ok`: SM with brand_a returns 200 for brand_a PO.
- `test_scoped_sm_po_detail_other_brand_404`: SM with brand_a returns 404 for brand_b PO.
- `test_unscoped_sm_po_list_sees_all_brands`: SM with no `user_brands` rows sees POs from all brands.
- `test_admin_po_detail_ignores_brand_scope`: ADMIN with no assignments sees brand_b PO; assert 200.

`backend/tests/test_brand_scoped_dashboard.py`:

- `test_scoped_sm_kpis_reflect_only_assigned_brand`: SM with brand_a only; KPI counts match brand_a PO counts.
- `test_unscoped_sm_kpis_see_all_brands`: SM with no assignments; KPI counts include all brands.

`backend/tests/test_brand_scoped_invoice_shipment.py`:

- `test_scoped_sm_invoice_list_filters_to_brand`: invoice list returns only brand_a invoices for brand_a-scoped SM.
- `test_scoped_sm_invoice_detail_other_brand_404`: brand_b invoice returns 404 for brand_a SM.
- `test_scoped_freight_manager_shipment_list_filters_to_brand`: shipment list returns only brand_a shipments for brand_a-scoped FM.
- `test_scoped_freight_manager_shipment_detail_other_brand_404`: 404 on brand_b shipment.

`frontend/tests/user-brand-assignment.spec.ts`:

- invite modal shows Brands multi-select for SM role; not shown for VENDOR role.
- invite modal shows Brands multi-select for FREIGHT_MANAGER, QUALITY_LAB, PROCUREMENT_MANAGER roles.
- selecting brands in invite modal includes `brand_ids` in POST body.
- edit modal pre-populates Brands field from existing `user.brand_ids`.
- edit modal save sends `brand_ids` in PATCH body.

## Decisions

- **m2m via `user_brands` join table.** A user can support more than one brand within a single operator (e.g. a FREIGHT_MANAGER covering two brands). One-to-many (`users.brand_id`) would require splitting that user into two accounts. m2m is also symmetric with `brand_vendors` and requires no schema column on `users`.
- **Empty assignment means unscoped, not zero-access.** A user with no `user_brands` rows sees all brands. This preserves backward compatibility for all existing users on upgrade, and avoids locking out ops staff the moment brand scoping is introduced. ADMIN can progressively scope users without a mandatory migration step.
- **Brand filter applies on the buyer side only.** VENDOR scoping (`check_vendor_access`) is unchanged. Combining vendor-axis and brand-axis filters on a single role is not modeled; the two axes are orthogonal and users hold exactly one role.
- **ADMIN is always unscoped.** ADMIN inserting rows into `user_brands` is ignored; `check_brand_access` short-circuits for ADMIN. Consistent with how ADMIN bypasses `require_role`.
- **Activity feed narrows only PO-entity events.** Certificate, packaging, user, and brand activity rows are not PO-scoped and remain fully visible to brand-scoped users. Narrowing non-PO events would require entity-type-specific joins for each type and is deferred.
- **`set_brands` replaces atomically.** A single replace (delete + bulk insert) is simpler than diffing old vs new assignments and issuing discrete assign/unassign calls. The frontend sends the full desired set.
- **No brand-scope cascade on brand deactivation.** Deactivating a brand does not remove `user_brands` rows referencing it. A deactivated brand has no active POs (iter 108 guard), so scoped users simply see an empty list. If the brand is reactivated, the assignments remain intact.

## Out of scope

- Brand-scoped marketplace accounts (FBA seller IDs, FNSKU, ASIN) — separate marketplace-integration iter.
- Narrowing certificate, packaging, and user activity events by brand — requires per-entity-type join logic; deferred.
- Brand-scoped product catalog view (a QUALITY_LAB user seeing only the products sold by their brand's vendors) — deferred.
- Role or brand mutation at the same time (changing a user's role and their brand set in one PATCH) — brand field is silently ignored when the role is VENDOR or ADMIN; role change + brand reassignment requires two PATCH calls.
- Self-service brand selection by non-ADMIN users — ADMIN-only management.
- UI on the `/brands/[id]/edit` page showing which users are scoped to that brand — useful audit view, not blocking.

## Notes

(Filled at iteration close.)
