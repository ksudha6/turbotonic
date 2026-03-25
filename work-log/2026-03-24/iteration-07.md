# Iteration 07 — 2026-03-24

## Context

I want to add dashboard and summary metrics for the portal. It has two list pages: vendors (`/vendors`) and purchase orders (`/po`). POs have 5 lifecycle states: DRAFT, PENDING, ACCEPTED, REJECTED, REVISED. Vendors have 2 states: ACTIVE, INACTIVE. The backend has no aggregate/summary endpoints; all queries return full object lists.

Data available for aggregation: PO count and total value by status, by vendor, by currency, and by date. Vendor counts by status. Reference data covers 30 currencies, 31 countries, 57 ports.

Add a dashboard as the landing page that gives an at-a-glance view of PO activity and vendor health, so the user doesn't have to scan list pages to understand the state of their procurement.

## Jobs to Be Done

1. **When** I open the app, **I want to** see PO counts and USD-equivalent totals grouped by status, **so that** I know procurement volume without visiting the list.
2. **When** I'm managing vendors, **I want to** see active vs inactive vendor counts at a glance, **so that** I know the health of my vendor base.
3. **When** I need to act on something, **I want to** see recently updated POs, **so that** I can jump to items with status changes that need attention.

## Tasks

### Backend
- [x] Add static USD exchange rates to reference data module (same pattern as currencies/ports)
- [x] Add `GET /api/v1/dashboard` returning: PO summary by status (count + USD-equivalent total), vendor summary (active/inactive counts), recent POs (last 10 by `updated_at`)
- [x] Repository methods for aggregate queries (SQL GROUP BY with currency conversion)

### Frontend
- [x] Add `/dashboard` route
- [x] PO status summary cards (count + "≈ $X" per status), clickable to PO list with status filter (uses iteration 06 URL params)
- [x] Vendor health section (active/inactive counts)
- [x] Recent POs table (clickable rows to PO detail)
- [x] Update nav to include dashboard link; redirect `/` to `/dashboard`

### Tests

#### Permanent (backend)
1. Empty state: no POs/vendors returns zeroes and empty lists
2. PO counts by status are correct
3. USD conversion: EUR PO total * EUR rate = correct total_usd
4. Multi-currency same status: two currencies aggregated correctly
5. Vendor counts: active and inactive correct
6. Recent POs returns last 10 by updated_at desc
7. Recent POs resolves vendor_name (not UUID)

#### Permanent (frontend)
8. Dashboard page loads and renders all three sections
9. Status cards show count and approximate USD total
10. Clicking status card navigates to `/po?status=X`
11. Recent PO rows link to `/po/{id}`

#### Scratch
12. Screenshot dashboard with populated data

## Pending

- Replace static exchange rates with live/historical rate source

## Cross-iteration dependency

- Dashboard status card links must use the same URL query param contract that iteration 06 defines (`/po?status=PENDING`, etc.)

## Notes

Static USD exchange rates added to `reference_data.py` as `(currency_code, rate)` tuples with a `RATE_TO_USD` Decimal lookup dict. The dashboard endpoint aggregates PO totals by status and currency via SQL `GROUP BY`, then converts to USD in Python using the static rates. Display uses "≈ $X" to signal approximation. The dashboard is a read model with no domain aggregate. Repository methods `po_summary_by_status`, `vendor_count_by_status`, and `recent_pos` handle the three dashboard sections. The `/` route redirects to `/dashboard` via `onMount` + `goto`. Dashboard status cards link to `/po?status=X`, using iteration 06's URL param contract. The `svelte.config.js` needed `prerender: { handleUnseenRoutes: 'ignore' }` to fix a build failure from dynamic routes unreachable during static prerender crawl.
