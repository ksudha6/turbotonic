# Iteration 090 — Phase 4.5 Tier 1: `/products` list revamp

## Context

User confirmed splitting Phase 4.5 into per-route iters: 090 = list only, 091 = `/products/new`, 092 = `/products/[id]/edit` (the largest at 436 lines), 093 = iter 040 cert UI fold-in. Each stays small per the iter discipline.

Today's `/products` (`frontend/src/routes/products/+page.svelte`, 138 lines): inline `<select class="select">` vendor filter, raw `<table class="table">`, hand-rolled `.badge-cert` / `.badge-no-cert` pills with stale `product.requires_certification` field reference. The type `ProductListItem` no longer carries `requires_certification` — it was replaced by `qualifications: QualificationTypeListItem[]` in iter 036a — so the legacy page is reading an undefined field and rendering "No" for every row regardless of actual qualification state. The new list will surface the qualification count instead.

Permission: SM/QUALITY_LAB/VENDOR/PROCUREMENT_MANAGER can view; SM/ADMIN can manage.

`product.spec.ts` has 3 tests, all targeting `/products/new` or `/products/[id]/edit` — none assert list-page markup. The existing test that POSTs from `/products/new` and `waitForURL('**/products')` is content-agnostic and continues passing under the new list page.

## JTBD

As an SM browsing the product catalog, I want the list page to mount under the same `(nexus)` AppShell I see on `/po`, `/invoices`, and `/vendors`, with the qualification state surfaced through Phase 4.0 primitives instead of a stale boolean — so I can see at a glance which products have any qualifications attached.

## Tasks

1. New components in `frontend/src/lib/product/`:
   - `ProductListFilters.svelte` — Vendor select + Clear button. Mobile-collapsing panel mirroring `VendorListFilters` from iter 089.
   - `ProductListTable.svelte` — Responsive (desktop `<table>` / mobile `<ul>` cards). Qualifications surfaced as a Phase 4.0 `StatusPill` showing the count when > 0 (tone `blue`), or `gray` "None" when 0. Edit link per row visible only when `canManageProducts`. testids: `product-table-desktop`, `product-table-mobile`, `product-row-{id}`, `product-row-quals-{id}`, `product-row-edit-{id}`.

2. New routes:
   - `(nexus)/products/+page.svelte` — AppShell + UserMenu + PageHeader (with New Product action snippet for SM/ADMIN — testid `product-page-header-action`). Mounts `ProductListFilters` + `ProductListTable`. Standard LoadingState/EmptyState/ErrorState arrangement (iter 086 + 089 precedent).
   - `(nexus)/products/+page.ts` — same redirect-on-no-permission as legacy, copied verbatim.

3. Delete legacy `frontend/src/routes/products/+page.svelte` and `+page.ts`. The legacy `products/new/` and `products/[id]/edit/` trees stay intact (revamp deferred to iter 091 / 092).

4. `isRevampRoute` extended with `pathname === '/products'` **exact match only** (not prefix). The unrevamped `/products/new` and `/products/[id]/edit` continue rendering the pre-revamp top nav until their dedicated iters.

5. New permanent specs in `product.spec.ts`:
   - AppShell mount on `/products`.
   - List loads and renders product rows.
   - Vendor filter narrows rows.
   - Empty state when filter matches nothing.
   - Error+retry path.
   - Qualification pill shows the count when product has qualifications (tone blue) and "None" when empty (tone gray).
   - Mobile (390px) renders cards via `product-table-mobile`.

## Tests

### Existing test impact

- `product.spec.ts:117` — `waitForURL('**/products')` after a POST to `/products/new`. The redirect target is now the `(nexus)` route, but the test only asserts the URL — no markup check. Continues passing.
- `role-rendering.spec.ts` — no product-list markup assertions found. Continues passing.
- The existing 3 product specs target `/products/new` and `/products/[id]/edit` (still legacy until iters 091/092). Unchanged.

### New permanent specs

7 specs as listed in Tasks step 5, mirroring the iter 089 vendor list spec pattern.

## Notes

Pure structural retrofit. The iter 089 vendor list pattern transferred cleanly: same responsive desktop-table / mobile-cards split, same `product-table-desktop` / `product-table-mobile` parent-testid scoping for strict-mode collision avoidance, same LoadingState/EmptyState/ErrorState arrangement.

The legacy page reads `product.requires_certification` which has not existed on the type since iter 036a — every row was rendering "No" regardless of actual qualification state. The new list reads `product.qualifications.length` and renders a Phase 4.0 `StatusPill` with tone `blue` + count when > 0 ("1 qualification" / "N qualifications") or tone `gray` + "None" when empty. The qualification list returned by the backend is the source of truth; the legacy boolean is now both wrong and dead.

`isRevampRoute` extended with `pathname === '/products'` exact match only — not prefix. The pre-revamp `/products/new` (iter 091) and `/products/[id]/edit` (iter 092) keep the legacy top nav until their dedicated revamp iters. The existing 3 product specs (`product create form renders manufacturing_address field`, `product create form submits manufacturing_address`, `product edit form shows existing manufacturing_address`) target those unrevamped routes and continue passing untouched.

`product.spec.ts:117` (`waitForURL('**/products')` after a POST) now lands on the `(nexus)` route. The test asserts URL only — no markup check — so it continues passing through the new list page.

No DDD vocab additions per CLAUDE.md rule 6.1. The `qualifications.length > 0` derivation is a pure UI summary on top of the existing `Product.qualifications` aggregate; no new domain term emerges.

696 backend (no change) + 322 Playwright (315 → 322, +7).
