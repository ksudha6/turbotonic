# Parallel Slate Plan — 2026-04-30

## Goal

Run multiple small iters concurrently around iter 099, on isolated branches, merged back to main one at a time. Every merged commit must keep main green.

## Current state of iter 099 (in flight on main, uncommitted)

Phase 4.6 Tier 2: shipment documents panel + readiness panel + mark-ready UI.

Modified:
- `frontend/src/lib/api.ts`
- `frontend/src/lib/permissions.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/routes/(nexus)/shipments/[id]/+page.svelte`
- `frontend/tests/shipment-detail.spec.ts`

New:
- `frontend/src/lib/shipment/ShipmentActionRail.svelte`
- `frontend/src/lib/shipment/ShipmentDocumentsPanel.svelte`
- `frontend/src/lib/shipment/ShipmentReadinessPanel.svelte`
- `frontend/src/lib/shipment/document-type-labels.ts`

## Candidate parallel iters (drawn from backlog)

### A. `/users` page — ADMIN user management frontend
Backend already shipped (iters 095, 096, 098). Frontend adds new route + sidebar nav slot.

Touch:
- new `frontend/src/routes/(nexus)/users/+page.svelte`
- new `frontend/src/lib/user/` components (list table, invite form, deactivate/reset/reissue actions)
- `frontend/src/lib/api.ts` — append user CRUD clients
- `frontend/src/lib/permissions.ts` — `canManageUsers`
- `frontend/src/lib/types.ts` — User DTO type
- `frontend/src/lib/sidebar-items.ts` — Users nav slot

Conflict with iter 099: api.ts, permissions.ts, types.ts. All three are append-only additions in both iters; merge resolves with line-level concatenation. No semantic overlap.

Size: M.

### B. User-lifecycle activity events (backend audit)
Backend-only. `deactivate` / `reactivate` / `reset-credentials` / `reissue-invite` / `patch` currently fire no activity rows. Bundle into one audit iter.

Touch:
- `backend/src/routers/user.py` — emit `USER_LIFECYCLE_*` activity events
- `backend/src/domain/activity.py` (or wherever event types live) — new event constants
- `backend/tests/test_user_router.py` — assert events fire
- optional: SMTP templates if we want email fan-out

Conflict with iter 099: zero. Pure backend, different aggregate.

Size: S.

### C. `/login` `/register` `/setup` Phase 4 port
Last three pre-revamp routes. Each is small. Phase 4 surface closes after this.

Touch:
- `frontend/src/routes/login/+page.svelte` (or move under (nexus)? — auth routes typically stay outside the AppShell; revamp uses Phase 4.0 primitives without Sidebar)
- `frontend/src/routes/register/+page.svelte`
- `frontend/src/routes/setup/+page.svelte`
- new `frontend/src/lib/auth/` components if extraction needed

Conflict with iter 099: low. Auth routes do not import from `shipment/`. May touch `api.ts` for auth helpers but those live in `frontend/src/lib/auth.ts` (separate file).

Size: M.

### D. Cert PENDING→VALID approve + edit workflow
Iter 040 leftover. Backend adds approve endpoint, frontend adds approve action + metadata edit form on `ProductCertificatesPanel`.

Touch:
- `backend/src/routers/certificate.py` — `POST /certificates/{id}/approve`, PATCH metadata
- `frontend/src/lib/product/ProductCertificatesPanel.svelte`
- `frontend/src/lib/api.ts` — append cert approve / patch clients

Conflict with iter 099: api.ts append only. Otherwise disjoint.

Size: S-M.

### E. Iter 048 dashboard KPIs (shipment counts + cert expiry)
Adds shipment-by-status counts to FM/SM dashboards, cert-expiry KPI, packaging collection progress.

Touch:
- `backend/src/routers/dashboard.py` — extend `/dashboard/summary`
- `frontend/src/lib/dashboard/` — new KPI components
- `frontend/src/routes/(nexus)/dashboard/+page.svelte` — wire new KPIs

Conflict with iter 099: none. Different routes, different domain slice.

Size: M.

## Conflict matrix vs iter 099

| Iter | api.ts | permissions.ts | types.ts | overlap risk |
|---|---|---|---|---|
| A | append | append | append | low — additive only |
| B | none | none | none | none |
| C | none | none | none | low |
| D | append | none | none | low |
| E | none | none | none | none |

Append-only conflicts on `api.ts` resolve at merge time. The functions added by each iter are named differently (`listUsers` vs `listShipmentRequirements` vs `approveCertificate`) so no logical conflict. Standard merge protocol: rebase the second iter on top of the first before merging.

## Recommended dispatch order

Round 1 (ship now, fully disjoint from 099):
- B (user-lifecycle activity events) — zero conflict, pure backend, smallest

Round 2 (ship after iter 099 lands, append-only conflicts handled at merge):
- A (`/users` page)
- C (auth route revamps)

Defer:
- D — small but better folded into a cert UX sweep alongside dashboard expiry alerts
- E — dependency on dashboard primitives that may want refactor; do as a single dashboard iter
- F (ADMIN-inherits-all permission sweep, from earlier discussion) — cross-cutting, run serial, not in a parallel slate

## Mechanics

Each parallel iter:
1. New iteration doc `work-log/YYYY-MM-DD/iteration-NNN.md` with Context + JTBD before any code
2. Worktree at `../turbotonic-iter-NNN/` on branch `iter-NNN`
3. Sonnet sub-agent dispatch with intent-based prompt + tool-usage block from CLAUDE.md
4. Tests run inside the worktree before merge: `make test`, `make test-browser`
5. Merge order: B first (no conflicts), then iter 099, then A and C in either order with rebase

## Acceptance per iter

- All permanent tests pass
- New tests for the user-facing behaviour added (selector policy: getByRole/getByLabel/getByTestId only on revamped surfaces)
- iteration doc closed per CLAUDE.md rules: Notes paragraph, iterations-summary.md updated, ddd-vocab.md additions proposed if new terms

## What this plan deliberately excludes

- Phase 4.6 Tier 3 (booking + mark-shipped UI). Same file as iter 099 (`/shipments/[id]`); run after 099 lands.
- F (ADMIN-inherits-all sweep). Cross-cutting, run alone.
