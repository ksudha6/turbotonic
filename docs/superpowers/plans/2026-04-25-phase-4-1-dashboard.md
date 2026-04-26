# Phase 4.1 Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship redesigned `/dashboard` under the `(nexus)` layout for ADMIN and SM (full 4-KPI + activity + awaiting-acceptance layout). Other four roles get a thin placeholder branch on the same route. Retire the pre-revamp dashboard route, endpoint shape, and Playwright specs.

**Architecture:** New SvelteKit route at `frontend/src/routes/(nexus)/dashboard/+page.svelte` consumes a new backend endpoint `GET /api/v1/dashboard/summary` that returns role-scoped KPI counts, an awaiting-acceptance PO list, and the recent activity feed in one payload. Page wraps Phase 4.0 primitives (`AppShell`, `KpiCard`, `ActivityFeed`, `PanelCard`, `DataTable`, `LoadingState`, `EmptyState`, `ErrorState`) and branches on `user.role` for ADMIN/SM full vs. placeholder.

**Tech Stack:** Svelte 5 runes (`$props`, `$state`, `$derived`), SvelteKit 2 with `(nexus)` route group, FastAPI + asyncpg, Postgres, Playwright (mocked-fetch pattern), pytest with `httpx.AsyncClient`.

**Brainstorm-resolved decisions** (locked in spec at `docs/superpowers/specs/2026-04-24-ui-revamp-v2-design.md` § "Phase 4.1 — Dashboard"):
- Scope cut: ADMIN + SM dashboards only this phase. Other four roles get placeholder.
- KPIs: PENDING POs, AWAITING ACCEPTANCE, IN PRODUCTION, OUTSTANDING A/P. Same labels for both roles.
- Scoping: SM filters to `po.po_type='PROCUREMENT'` and procurement-vendor invoices. ADMIN sees global.
- RFQ aggregate is future; no RFQ-derived data.
- Sidebar + permissions matrix patch (FREIGHT_MANAGER drops PO, VENDOR adds Products, PROCUREMENT_MANAGER promoted to SM-equivalent read-only) ships as Task 1 of this plan.
- QUALITY_LAB lab-scoping deferred (needs `User.lab` schema change).

---

## Reference: existing artifacts the plan composes

**Phase 4.0 primitives (already shipped, do not modify):**
- `frontend/src/lib/ui/AppShell.svelte` — `{ role, roleLabel?, breadcrumb?, userMenu? (snippet), sidebarFooter? (snippet), children }`
- `frontend/src/lib/ui/KpiCard.svelte` — `{ label, value, delta?: { value, tone }, icon? (snippet), 'data-testid'? }`
- `frontend/src/lib/ui/ActivityFeed.svelte` — `{ entries: { id, primary, secondary?, tone: 'green'|'blue'|'orange'|'red'|'gray' }[], 'data-testid'? }`
- `frontend/src/lib/ui/PanelCard.svelte` — wraps content in a card surface with optional header.
- `frontend/src/lib/ui/DataTable.svelte` — server-driven pagination contract.
- `frontend/src/lib/ui/LoadingState.svelte`, `EmptyState.svelte`, `ErrorState.svelte`.
- `frontend/src/lib/ui/sidebar-items.ts` — `Record<UserRole, SidebarItem[]>` map; **modify in Task 1**.
- `frontend/src/routes/(nexus)/+layout.ts` — auth guard; redirects to `/login` if no session.
- `frontend/src/routes/(nexus)/+layout.svelte` — minimal pass-through; AppShell is invoked per-page (the `_smoke` page wraps itself).

**Backend types (do not change):**
- `backend/src/domain/user.py::UserRole`: ADMIN, PROCUREMENT_MANAGER, SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER.
- `backend/src/domain/purchase_order.py::POStatus`: DRAFT, PENDING, ACCEPTED, REJECTED, REVISED, MODIFIED.
- `backend/src/domain/purchase_order.py::POType`: PROCUREMENT, OPEX.
- `backend/src/domain/invoice.py::InvoiceStatus`: DRAFT, SUBMITTED, APPROVED, PAID, DISPUTED.
- `backend/src/domain/reference_data.py::RATE_TO_USD` for currency conversion.

**Pre-revamp artifacts to retire in Task 4:**
- `frontend/src/routes/dashboard/+page.svelte` (pre-revamp dashboard).
- `frontend/tests/dashboard.spec.ts` and `frontend/tests/dashboard-activity.spec.ts` (test pre-revamp shape).
- The old `GET /api/v1/dashboard/` endpoint shape stays during this phase; **do not delete it in this plan** — it is used by lingering tests/scripts and will be cleaned up at end of Phase 4 once every aggregate has migrated.

**KPI definitions (locked):**
1. **PENDING POs** = count of POs with `status IN ('DRAFT', 'PENDING', 'MODIFIED')`. SM scope adds `po_type='PROCUREMENT'`.
2. **AWAITING ACCEPTANCE** = count of POs with `status='PENDING' AND last_actor_role='SM'` (sent to vendor, awaiting vendor response). SM scope adds `po_type='PROCUREMENT'`.
3. **IN PRODUCTION** = count of POs with `status='ACCEPTED'` whose latest milestone is one of (RAW_MATERIALS, PRODUCTION_STARTED, QC_PASSED, READY_TO_SHIP) — i.e. accepted but not yet SHIPPED. Uses the same milestone-latest join already in `routers/dashboard.py` for production_summary. SM scope adds `po_type='PROCUREMENT'` (already enforced in that join).
4. **OUTSTANDING A/P** = USD-converted sum of invoice subtotals where `invoice.status IN ('SUBMITTED', 'APPROVED', 'DISPUTED')`. Subtotal computed as `SUM(quantity * unit_price)` per invoice (matches existing pattern in `routers/dashboard.py`). SM scope: invoice→PO→vendor where `vendor.vendor_type='PROCUREMENT'`.

---

## Task 1: Sidebar map + permissions matrix patch

**Files:**
- Modify: `frontend/src/lib/ui/sidebar-items.ts`
- Modify: `frontend/src/lib/permissions.ts`
- Modify: `frontend/tests/sidebar-items.spec.ts`

**Why this task ships first:** Phase 4.1 dashboard relies on Phase 4.0 sidebar/permissions plumbing; the matrix decided in the brainstorm differs from what iter 067 shipped. This is a foundation patch, not a new feature.

- [ ] **Step 1: Update `sidebar-items.spec.ts` with new role matrix expectations.**

Replace the test cases for FREIGHT_MANAGER, VENDOR, PROCUREMENT_MANAGER, ADMIN. Existing test file already covers ADMIN/SM/VENDOR/QUALITY_LAB; extend or rewrite to assert:

```ts
import { describe, it, expect } from 'vitest'; // or whatever the spec uses today; keep existing test runner
import { sidebarItemsFor } from '../src/lib/ui/sidebar-items';

// Test: FREIGHT_MANAGER sees Dashboard + Invoices only (drops Purchase Orders)
const fm = sidebarItemsFor('FREIGHT_MANAGER')[0].items.map(i => i.label);
expect(fm).toEqual(['Dashboard', 'Invoices']);

// Test: VENDOR sees Dashboard, Purchase Orders, Invoices, Products
const v = sidebarItemsFor('VENDOR')[0].items.map(i => i.label);
expect(v).toEqual(['Dashboard', 'Purchase Orders', 'Invoices', 'Products']);

// Test: PROCUREMENT_MANAGER sees Dashboard, Purchase Orders, Invoices, Products (SM-equivalent)
const pm = sidebarItemsFor('PROCUREMENT_MANAGER')[0].items.map(i => i.label);
expect(pm).toEqual(['Dashboard', 'Purchase Orders', 'Invoices', 'Products']);

// Test: ADMIN unchanged
const a = sidebarItemsFor('ADMIN')[0].items.map(i => i.label);
expect(a).toEqual(['Dashboard', 'Purchase Orders', 'Invoices', 'Vendors', 'Products', 'Users']);
```

If the existing spec uses Playwright (per iter 067), keep that runner. Match its existing style. Do not rewrite the spec runner.

- [ ] **Step 2: Run the spec — expect FAIL.**

Run: `cd frontend && npx playwright test sidebar-items.spec.ts`
Expected: FAIL on FREIGHT_MANAGER (currently has POs), VENDOR (currently lacks Products), PROCUREMENT_MANAGER (currently Dashboard-only).

- [ ] **Step 3: Update `frontend/src/lib/ui/sidebar-items.ts`.**

```ts
const ROLE_ITEMS: Record<UserRole, SidebarItem[]> = {
    ADMIN: [DASHBOARD, PURCHASE_ORDERS, INVOICES, VENDORS, PRODUCTS, USERS],
    SM: [DASHBOARD, PURCHASE_ORDERS, INVOICES, VENDORS, PRODUCTS],
    VENDOR: [DASHBOARD, PURCHASE_ORDERS, INVOICES, PRODUCTS],
    FREIGHT_MANAGER: [DASHBOARD, INVOICES],
    QUALITY_LAB: [DASHBOARD, PRODUCTS],
    PROCUREMENT_MANAGER: [DASHBOARD, PURCHASE_ORDERS, INVOICES, PRODUCTS]
};
```

- [ ] **Step 4: Run the spec — expect PASS.**

Run: `cd frontend && npx playwright test sidebar-items.spec.ts`
Expected: PASS.

- [ ] **Step 5: Update `frontend/src/lib/permissions.ts`.**

The existing `is(role, ...allowed)` helper short-circuits on ADMIN. Add PROCUREMENT_MANAGER to read-helpers (matching SM); leave write-helpers untouched (PROCUREMENT_MANAGER stays read-only). Add VENDOR + PROCUREMENT_MANAGER to `canViewProducts`. Add PROCUREMENT_MANAGER + FREIGHT_MANAGER to `canViewInvoices`. Add PROCUREMENT_MANAGER to `canViewPOs`.

```ts
export const canViewProducts = (role: UserRole) => is(role, 'SM', 'QUALITY_LAB', 'VENDOR', 'PROCUREMENT_MANAGER');
export const canViewInvoices = (role: UserRole) => is(role, 'SM', 'VENDOR', 'PROCUREMENT_MANAGER', 'FREIGHT_MANAGER');
export const canViewPOs = (role: UserRole) => is(role, 'SM', 'VENDOR', 'FREIGHT_MANAGER', 'PROCUREMENT_MANAGER');
// All write-helpers unchanged. PROCUREMENT_MANAGER not added to canCreatePO, canEditPO, canSubmitPO, canApproveInvoice, etc.
```

Do NOT touch the `is()` helper. Do NOT add `canMutate` family — read-only enforcement is implicit via the existing write-helper exclusion list. SM-only mutation rules already guard PROCUREMENT_MANAGER out.

- [ ] **Step 6: Run all permanent Playwright tests.**

Run: `make test-browser`
Expected: 150 passed (Phase 4.0 baseline) + sidebar-items spec passes with new matrix. No regression elsewhere.

- [ ] **Step 7: Commit.**

```bash
git add frontend/src/lib/ui/sidebar-items.ts frontend/src/lib/permissions.ts frontend/tests/sidebar-items.spec.ts
git commit -m "$(cat <<'EOF'
Patch sidebar items + permissions per Phase 4.1 matrix (iter 071 task 1)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Backend `/api/v1/dashboard/summary` endpoint with role scoping

**Files:**
- Modify: `backend/src/routers/dashboard.py`
- Modify: `backend/src/repository.py` (add helper queries if needed; or do it inline in router)
- Test: `backend/tests/test_dashboard_summary.py` (new)

**Endpoint contract:**

`GET /api/v1/dashboard/summary` returns:
```json
{
  "kpis": {
    "pending_pos": 12,
    "awaiting_acceptance": 5,
    "in_production": 8,
    "outstanding_ap_usd": "145320.00"
  },
  "awaiting_acceptance": [
    { "id": "uuid", "po_number": "PO-20260425-0001", "vendor_name": "Acme", "total_value_usd": "5400.00", "submitted_at": "2026-04-20T10:00:00Z" }
  ],
  "activity": [
    { "id": "act-1", "entity_type": "PO", "entity_id": "uuid", "event": "PO_SUBMITTED", "detail": "...", "category": "ACTION_REQUIRED", "created_at": "..." }
  ]
}
```

The activity field reuses the existing `ActivityLogEntry` shape from `activity_repository.py` so the frontend can pass it straight to `ActivityFeed`. Limit `awaiting_acceptance` to 10 most recent. Limit `activity` to 20 most recent.

**Scoping:** ADMIN sees global; SM applies `po.po_type='PROCUREMENT'` filter on PO-derived KPIs and joins invoices through PO→vendor where `vendor.vendor_type='PROCUREMENT'`. For other roles (VENDOR, FREIGHT_MANAGER, QUALITY_LAB, PROCUREMENT_MANAGER), the endpoint returns `kpis` with all zeros and empty lists — the placeholder branch ignores them anyway.

- [ ] **Step 1: Write the failing pytest spec.**

Create `backend/tests/test_dashboard_summary.py`:

```python
"""Tests for GET /api/v1/dashboard/summary (Phase 4.1)."""
import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_as  # or whatever the existing helper is — check existing tests for pattern


@pytest.mark.asyncio
async def test_admin_sees_global_kpis(client: AsyncClient, seeded_data):
    """ADMIN response covers PROCUREMENT + OPEX POs and all invoice statuses."""
    async with auth_as(client, role='ADMIN'):
        resp = await client.get('/api/v1/dashboard/summary')
    assert resp.status_code == 200
    body = resp.json()
    assert 'kpis' in body
    assert set(body['kpis'].keys()) == {'pending_pos', 'awaiting_acceptance', 'in_production', 'outstanding_ap_usd'}
    assert isinstance(body['kpis']['pending_pos'], int)
    assert isinstance(body['kpis']['outstanding_ap_usd'], str)  # USD as string for decimal stability
    assert isinstance(body['awaiting_acceptance'], list)
    assert isinstance(body['activity'], list)
    # Seeded data has at least one OPEX PO; ADMIN must see it counted.
    assert body['kpis']['pending_pos'] >= 1


@pytest.mark.asyncio
async def test_sm_scopes_to_procurement(client: AsyncClient, seeded_data):
    """SM response excludes OPEX POs from all KPI counts."""
    async with auth_as(client, role='SM'):
        sm = (await client.get('/api/v1/dashboard/summary')).json()
    async with auth_as(client, role='ADMIN'):
        admin = (await client.get('/api/v1/dashboard/summary')).json()
    # SM must be ≤ ADMIN on every count (procurement subset of all).
    assert sm['kpis']['pending_pos'] <= admin['kpis']['pending_pos']
    assert sm['kpis']['in_production'] <= admin['kpis']['in_production']
    # Outstanding A/P comparison (USD strings → Decimal).
    from decimal import Decimal
    assert Decimal(sm['kpis']['outstanding_ap_usd']) <= Decimal(admin['kpis']['outstanding_ap_usd'])


@pytest.mark.asyncio
async def test_vendor_returns_empty_kpis(client: AsyncClient, seeded_data):
    """VENDOR (and other non-ADMIN/SM roles) get the empty payload — placeholder branch on the frontend handles render."""
    async with auth_as(client, role='VENDOR'):
        resp = await client.get('/api/v1/dashboard/summary')
    assert resp.status_code == 200
    body = resp.json()
    assert body['kpis']['pending_pos'] == 0
    assert body['kpis']['awaiting_acceptance'] == 0
    assert body['kpis']['in_production'] == 0
    assert body['kpis']['outstanding_ap_usd'] == '0.00'
    assert body['awaiting_acceptance'] == []
    assert body['activity'] == []


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client: AsyncClient):
    resp = await client.get('/api/v1/dashboard/summary')
    assert resp.status_code == 401
```

If `auth_as` and `seeded_data` helpers don't already exist with those exact names, use whatever the existing pytest suite uses. **Read `backend/tests/conftest.py` and one existing router test (e.g. `test_dashboard.py` if it exists, or `test_purchase_order.py`) before writing this file** to mirror the auth/fixture pattern. Do not invent fixtures.

- [ ] **Step 2: Run the spec — expect FAIL (endpoint does not exist).**

Run: `make test`
Expected: 4 new tests fail with 404.

- [ ] **Step 3: Implement the endpoint in `backend/src/routers/dashboard.py`.**

Add a new route handler `@router.get("/summary")` (sibling of the existing `@router.get("/")`). Reuse the existing dependency-injected repos (`RepoDep`, `InvoiceRepoDep`, `MilestoneRepoDep`, `ActivityRepoDep`). For role-scoping use:

```python
from src.domain.user import UserRole

ADMIN_OR_SM = {UserRole.ADMIN, UserRole.SM}

@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    invoice_repo: InvoiceRepoDep,
    milestone_repo: MilestoneRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_auth,
) -> DashboardSummaryResponse:
    if user.role not in ADMIN_OR_SM:
        return DashboardSummaryResponse(
            kpis=DashboardKpis(pending_pos=0, awaiting_acceptance=0, in_production=0, outstanding_ap_usd="0.00"),
            awaiting_acceptance=[],
            activity=[],
        )

    procurement_only = user.role is UserRole.SM
    # ... apply scoping in the four count queries + invoice sum + awaiting list + activity feed
```

For the four counts, write four small SQL queries against `purchase_orders` joined where needed. Use `f"AND po_type = 'PROCUREMENT'"` (parameter-safe constant — POType values are not user input) when `procurement_only`. For OUTSTANDING A/P sum, mirror the existing invoice-subtotal CTE pattern in this same file (lines 175-202), filtered to `i.status IN ('SUBMITTED','APPROVED','DISPUTED')`. For SM, additionally `JOIN vendors v ON po.vendor_id = v.id WHERE v.vendor_type = 'PROCUREMENT'`.

For activity, call the existing `activity_repo.list(limit=20, target_role=user.role)` if it accepts a target_role kwarg — check the repo. If not, use `activity_repo.list_recent(20)` and let frontend filter. Do not invent new repo methods unless the SQL truly cannot be expressed with what's there; if you do add a method, put it in `activity_repository.py` and write its own pytest first.

Define new pydantic models alongside existing ones in `dashboard.py`:

```python
class DashboardKpis(BaseModel):
    pending_pos: int
    awaiting_acceptance: int
    in_production: int
    outstanding_ap_usd: str  # Decimal as string for stable serialization

class AwaitingAcceptanceItem(BaseModel):
    id: str
    po_number: str
    vendor_name: str
    total_value_usd: str
    submitted_at: datetime

class DashboardActivityItem(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    event: str
    detail: str | None
    category: str
    created_at: datetime

class DashboardSummaryResponse(BaseModel):
    kpis: DashboardKpis
    awaiting_acceptance: list[AwaitingAcceptanceItem]
    activity: list[DashboardActivityItem]
```

- [ ] **Step 4: Run the spec — expect PASS.**

Run: `make test`
Expected: 591 prior passes + 4 new = 595 passed. If a count is off, fix the implementation; never relax a test assertion.

- [ ] **Step 5: Commit.**

```bash
git add backend/src/routers/dashboard.py backend/tests/test_dashboard_summary.py
git commit -m "$(cat <<'EOF'
Add GET /api/v1/dashboard/summary with role scoping (iter 071 task 2)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Frontend `(nexus)/dashboard/+page.svelte` — ADMIN/SM full + placeholder branch

**Files:**
- Create: `frontend/src/routes/(nexus)/dashboard/+page.svelte`
- Create: `frontend/src/lib/api/dashboard.ts` (or extend `frontend/src/lib/api.ts` — match existing pattern; the file is one big api.ts today, so extend it)
- Modify: `frontend/src/lib/api.ts` (add `fetchDashboardSummary()`)
- Modify: `frontend/src/lib/types.ts` (add `DashboardSummary` type matching backend response)
- Delete: `frontend/src/routes/dashboard/+page.svelte` (pre-revamp)
- Delete: `frontend/tests/dashboard.spec.ts`, `frontend/tests/dashboard-activity.spec.ts` (pre-revamp specs)

**Why delete the pre-revamp specs in the same task:** the route is shared (`/dashboard`); SvelteKit will not allow both `routes/dashboard/+page.svelte` and `routes/(nexus)/dashboard/+page.svelte` to coexist (both resolve to `/dashboard`). Once the new page lives at the canonical URL, the old specs reference behavior that no longer exists.

- [ ] **Step 1: Add types in `frontend/src/lib/types.ts`.**

```ts
export interface DashboardKpis {
    pending_pos: number;
    awaiting_acceptance: number;
    in_production: number;
    outstanding_ap_usd: string;
}

export interface AwaitingAcceptanceItem {
    id: string;
    po_number: string;
    vendor_name: string;
    total_value_usd: string;
    submitted_at: string; // ISO 8601
}

export interface DashboardActivityItem {
    id: string;
    entity_type: string;
    entity_id: string;
    event: string;
    detail: string | null;
    category: string;
    created_at: string;
}

export interface DashboardSummary {
    kpis: DashboardKpis;
    awaiting_acceptance: AwaitingAcceptanceItem[];
    activity: DashboardActivityItem[];
}
```

- [ ] **Step 2: Add `fetchDashboardSummary()` in `frontend/src/lib/api.ts`.**

```ts
export function fetchDashboardSummary(): Promise<DashboardSummary> {
    return apiGet<DashboardSummary>('/api/v1/dashboard/summary');
}
```

Add `DashboardSummary` to the import list at the top of the file. Leave the existing `fetchDashboard()` alone (it stays in place during transition).

- [ ] **Step 3: Create `frontend/src/routes/(nexus)/dashboard/+page.svelte`.**

```svelte
<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { fetchDashboardSummary } from '$lib/api';
    import type { DashboardSummary, UserRole } from '$lib/types';
    import AppShell from '$lib/ui/AppShell.svelte';
    import KpiCard from '$lib/ui/KpiCard.svelte';
    import ActivityFeed from '$lib/ui/ActivityFeed.svelte';
    import PanelCard from '$lib/ui/PanelCard.svelte';
    import LoadingState from '$lib/ui/LoadingState.svelte';
    import EmptyState from '$lib/ui/EmptyState.svelte';
    import ErrorState from '$lib/ui/ErrorState.svelte';

    const ROLE_LABELS: Record<UserRole, string> = {
        ADMIN: 'Administrator',
        SM: 'Supply Manager',
        VENDOR: 'Vendor',
        FREIGHT_MANAGER: 'Freight Manager',
        QUALITY_LAB: 'Quality Lab',
        PROCUREMENT_MANAGER: 'Procurement Manager'
    };

    const FULL_ROLES: ReadonlySet<UserRole> = new Set(['ADMIN', 'SM']);

    const user = $derived(page.data.user);
    const role = $derived(user?.role as UserRole | undefined);
    const showsFullDashboard = $derived(role !== undefined && FULL_ROLES.has(role));

    let summary: DashboardSummary | null = $state(null);
    let loading = $state(true);
    let error: string | null = $state(null);

    onMount(async () => {
        try {
            summary = await fetchDashboardSummary();
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load dashboard';
        } finally {
            loading = false;
        }
    });

    function formatUsd(value: string): string {
        return parseFloat(value).toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    function relativeTime(iso: string): string {
        const diffMs = Date.now() - new Date(iso).getTime();
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return 'just now';
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return `${diffHr}h ago`;
        return `${Math.floor(diffHr / 24)}d ago`;
    }

    function activityToFeedEntry(a: DashboardSummary['activity'][number]) {
        const tone =
            a.category === 'ACTION_REQUIRED' ? 'orange' :
            a.category === 'DELAYED' ? 'red' : 'blue';
        return {
            id: a.id,
            primary: `${a.event}${a.detail ? ` — ${a.detail}` : ''}`,
            secondary: relativeTime(a.created_at),
            tone
        } as const;
    }
</script>

<svelte:head><title>Dashboard</title></svelte:head>

{#if !role}
    <LoadingState />
{:else}
    <AppShell {role} roleLabel={ROLE_LABELS[role]} breadcrumb="Dashboard" data-testid="ui-dashboard">
        {#if loading}
            <LoadingState />
        {:else if error}
            <ErrorState message={error} />
        {:else if !showsFullDashboard}
            <PanelCard heading="Dashboard">
                <p class="placeholder">
                    Welcome, {user?.display_name ?? user?.username ?? ''}. Your role-specific
                    dashboard is coming soon. Use the sidebar to navigate to the modules
                    available to you.
                </p>
            </PanelCard>
        {:else if summary}
            <div class="kpi-grid" data-testid="ui-dashboard-kpis">
                <KpiCard label="Pending POs" value={String(summary.kpis.pending_pos)} data-testid="kpi-pending-pos" />
                <KpiCard label="Awaiting acceptance" value={String(summary.kpis.awaiting_acceptance)} data-testid="kpi-awaiting" />
                <KpiCard label="In production" value={String(summary.kpis.in_production)} data-testid="kpi-in-production" />
                <KpiCard label="Outstanding A/P" value={formatUsd(summary.kpis.outstanding_ap_usd)} data-testid="kpi-outstanding-ap" />
            </div>

            <div class="panel-grid">
                <PanelCard heading="Awaiting acceptance" data-testid="panel-awaiting">
                    {#if summary.awaiting_acceptance.length === 0}
                        <EmptyState message="No POs awaiting vendor acceptance." />
                    {:else}
                        <ul class="awaiting-list">
                            {#each summary.awaiting_acceptance as po (po.id)}
                                <li>
                                    <button type="button" onclick={() => goto(`/po/${po.id}`)}>
                                        <span class="po-number">{po.po_number}</span>
                                        <span class="vendor">{po.vendor_name}</span>
                                        <span class="value">{formatUsd(po.total_value_usd)}</span>
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </PanelCard>

                <PanelCard heading="Recent activity" data-testid="panel-activity">
                    {#if summary.activity.length === 0}
                        <EmptyState message="No recent activity." />
                    {:else}
                        <ActivityFeed entries={summary.activity.map(activityToFeedEntry)} />
                    {/if}
                </PanelCard>
            </div>
        {/if}
    </AppShell>
{/if}

<style>
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: var(--space-4);
        margin-bottom: var(--space-6);
    }
    .panel-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: var(--space-4);
    }
    @media (max-width: 768px) {
        .panel-grid {
            grid-template-columns: 1fr;
        }
    }
    .awaiting-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
    .awaiting-list button {
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: var(--space-3);
        align-items: baseline;
        width: 100%;
        background: none;
        border: none;
        text-align: left;
        padding: var(--space-2) var(--space-3);
        border-radius: var(--radius-sm);
        cursor: pointer;
        font: inherit;
        color: inherit;
    }
    .awaiting-list button:hover { background-color: var(--gray-50); }
    .po-number { font-weight: 600; color: var(--gray-900); }
    .vendor { color: var(--gray-700); font-size: var(--font-size-sm); }
    .value { color: var(--gray-900); font-weight: 500; font-variant-numeric: tabular-nums; }
    .placeholder { color: var(--gray-700); }
</style>
```

Note: `AppShell` already wraps a `<TopBar>` with menu toggle + sidebar from Phase 4.0; do not re-render those.

- [ ] **Step 4: Delete the pre-revamp dashboard route file and its specs.**

```bash
rm frontend/src/routes/dashboard/+page.svelte
rm frontend/tests/dashboard.spec.ts
rm frontend/tests/dashboard-activity.spec.ts
```

If `frontend/src/routes/dashboard/` becomes empty, also remove the directory:

```bash
rmdir frontend/src/routes/dashboard 2>/dev/null || true
```

The pre-revamp `fetchDashboard()` and `fetchActivity()` API helpers in `frontend/src/lib/api.ts` may still be called by other pre-revamp routes (PO detail, etc). **Do not delete them in this task.** They get cleaned up at end of Phase 4.

- [ ] **Step 5: Run the build to confirm no broken imports.**

Run: `cd frontend && npm run build`
Expected: build succeeds. If a pre-revamp page still imports something we removed, surface it; the implementer must NOT silently re-add deleted artifacts.

- [ ] **Step 6: Smoke-test the page locally.**

Run: `make up`
Visit http://localhost:5173/dashboard while logged in as ADMIN, SM, and VENDOR. Confirm:
- ADMIN sees 4 KPI cards with non-zero values + activity feed + awaiting list (or empty states if seed data has none).
- SM sees same layout, scoped values.
- VENDOR sees the placeholder card with role-aware welcome text.

Do not commit screenshots — per CLAUDE.md, scratch artifacts stay outside version control. Note results in iter 071 doc Notes.

- [ ] **Step 7: Commit.**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/routes/(nexus)/dashboard/+page.svelte
git rm frontend/src/routes/dashboard/+page.svelte frontend/tests/dashboard.spec.ts frontend/tests/dashboard-activity.spec.ts
git commit -m "$(cat <<'EOF'
Replace /dashboard with (nexus)/dashboard for ADMIN+SM (iter 071 task 3)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Permanent Playwright spec for the new dashboard

**Files:**
- Create: `frontend/tests/nexus-dashboard.spec.ts`

**Why a new spec file:** Pre-revamp `dashboard.spec.ts` was deleted in Task 3. This spec covers the new contract.

- [ ] **Step 1: Write the spec.**

```ts
import { test, expect } from '@playwright/test';

const ADMIN_USER = { id: 'u-admin', username: 'admin', display_name: 'Admin', role: 'ADMIN', status: 'ACTIVE', vendor_id: null };
const SM_USER = { id: 'u-sm', username: 'sm', display_name: 'SM User', role: 'SM', status: 'ACTIVE', vendor_id: null };
const VENDOR_USER = { id: 'u-v', username: 'vendor', display_name: 'V Co', role: 'VENDOR', status: 'ACTIVE', vendor_id: 'vendor-1' };

const FULL_SUMMARY = {
    kpis: { pending_pos: 4, awaiting_acceptance: 2, in_production: 3, outstanding_ap_usd: '12500.00' },
    awaiting_acceptance: [
        { id: 'po-1', po_number: 'PO-20260425-0001', vendor_name: 'Acme', total_value_usd: '5400.00', submitted_at: '2026-04-25T10:00:00Z' },
        { id: 'po-2', po_number: 'PO-20260425-0002', vendor_name: 'Widget Co', total_value_usd: '7100.00', submitted_at: '2026-04-25T11:00:00Z' }
    ],
    activity: [
        { id: 'a-1', entity_type: 'PO', entity_id: 'po-1', event: 'PO_SUBMITTED', detail: 'Acme PO-001', category: 'ACTION_REQUIRED', created_at: '2026-04-25T10:05:00Z' }
    ]
};

const EMPTY_SUMMARY = {
    kpis: { pending_pos: 0, awaiting_acceptance: 0, in_production: 0, outstanding_ap_usd: '0.00' },
    awaiting_acceptance: [],
    activity: []
};

function setupRoutes(page, user, summary) {
    return Promise.all([
        page.route('**/api/v1/auth/me', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user }) })),
        page.route('**/api/v1/dashboard/summary', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(summary) })),
        page.route('**/api/v1/activity/unread-count', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) })),
    ]);
}

test('ADMIN sees the four KPI cards', async ({ page }) => {
    await setupRoutes(page, ADMIN_USER, FULL_SUMMARY);
    await page.goto('/dashboard');
    await expect(page.getByTestId('ui-dashboard-kpis')).toBeVisible();
    await expect(page.getByTestId('kpi-pending-pos')).toContainText('4');
    await expect(page.getByTestId('kpi-awaiting')).toContainText('2');
    await expect(page.getByTestId('kpi-in-production')).toContainText('3');
    await expect(page.getByTestId('kpi-outstanding-ap')).toContainText('$12,500');
});

test('SM sees the same layout', async ({ page }) => {
    await setupRoutes(page, SM_USER, FULL_SUMMARY);
    await page.goto('/dashboard');
    await expect(page.getByTestId('ui-dashboard-kpis')).toBeVisible();
    await expect(page.getByTestId('panel-awaiting')).toContainText('PO-20260425-0001');
});

test('Awaiting-acceptance click navigates to PO detail', async ({ page }) => {
    await setupRoutes(page, ADMIN_USER, FULL_SUMMARY);
    await page.goto('/dashboard');
    await page.getByText('PO-20260425-0001').click();
    await expect(page).toHaveURL(/\/po\/po-1/);
});

test('VENDOR sees placeholder, not KPI grid', async ({ page }) => {
    await setupRoutes(page, VENDOR_USER, EMPTY_SUMMARY);
    await page.goto('/dashboard');
    await expect(page.getByTestId('ui-dashboard-kpis')).toHaveCount(0);
    await expect(page.getByText('role-specific dashboard is coming soon')).toBeVisible();
});

test('Empty awaiting-acceptance renders EmptyState', async ({ page }) => {
    const emptyAwaiting = { ...FULL_SUMMARY, awaiting_acceptance: [] };
    await setupRoutes(page, ADMIN_USER, emptyAwaiting);
    await page.goto('/dashboard');
    await expect(page.getByTestId('panel-awaiting')).toContainText('No POs awaiting vendor acceptance');
});
```

- [ ] **Step 2: Run the spec — expect PASS.**

Run: `make test-browser`
Expected: 150 prior passes (but minus the 2-3 deleted dashboard specs from Task 3) + 5 new = roughly 152 passed. Confirm exact count from the test runner output, not from arithmetic — pre-revamp specs had multiple `test()` blocks that I have not enumerated.

- [ ] **Step 3: Commit.**

```bash
git add frontend/tests/nexus-dashboard.spec.ts
git commit -m "$(cat <<'EOF'
Add Playwright spec for (nexus)/dashboard (iter 071 task 4)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Phase 4.1.0 close — iter doc + iterations-summary

**Files:**
- Create: `work-log/2026-04-25/iteration-071.md`
- Modify: `work-log/iterations-summary.md`

- [ ] **Step 1: Open iter 071 doc with Context + JTBD.**

Per CLAUDE.md iteration flow: Context first, JTBD next, no other content before those. Cover:
- Phase 4.1 starts. Iter 070 closed Phase 4.0 with 26 primitives and 150 Playwright passes. Iter 071 ships the first redesigned aggregate page (Dashboard) under `(nexus)`.
- The five tasks above and which committed.
- Mock-clarity / past-flow / future-flow gates: how each was satisfied.
- KPI definitions locked in spec.

JTBD examples (write three):
- As an SM, when I open the dashboard, I want to see how many procurement POs are pending vendor acceptance so I can chase the slow ones.
- As an ADMIN, when I open the dashboard, I want a single view of every status count regardless of PO type so I can spot system-wide issues.
- As a VENDOR, when I open the dashboard, I want a clear note that my own dashboard is on the way so I do not assume the redesign is broken.

- [ ] **Step 2: Tasks + Notes sections.**

List all five tasks above with `- [x]` checkboxes (this iter is closing as it's written; checkboxes flip immediately after each implementer report — no bulk sweep at close). Notes must include:
- Test counts at open vs close.
- Final commit list with SHAs (filled in at close).
- Any deviations from the plan (e.g., if seed data didn't surface OUTSTANDING A/P so the iter shipped with a TODO note for follow-up).
- Carry-forward backlog (e.g., quality flags KPI, shipments-in-transit, other roles' dashboards, QUALITY_LAB lab schema).

- [ ] **Step 3: Update `work-log/iterations-summary.md`.**

- Header: "Last updated: iter 071 closed on 2026-04-25 — **Phase 4.1 dashboard for ADMIN+SM**".
- Append iter 071 row to the iteration log table.
- Update "Frontend routes" table: `/dashboard` row now reads "Dashboard (Phase 4.1) — ADMIN/SM 4-KPI + activity + awaiting; placeholder for other roles".
- Update "API surface" entry for Dashboard: add `GET /summary` line.
- Add to Phase 4 backlog: VENDOR/FREIGHT/QL/PROCUREMENT_MANAGER dashboards, quality-flags KPI, shipments-in-transit KPI, QUALITY_LAB.lab schema.

- [ ] **Step 4: Commit and push.**

```bash
git add work-log/2026-04-25/iteration-071.md work-log/iterations-summary.md
git commit -m "$(cat <<'EOF'
Close iter 071 — Phase 4.1 dashboard for ADMIN+SM (iter 071 task 5)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push origin phase-4-1-dashboard
```

---

## Existing test impact (per CLAUDE.md iteration rule)

- **Broken by Task 3:** `frontend/tests/dashboard.spec.ts` and `frontend/tests/dashboard-activity.spec.ts` — both test pre-revamp dashboard structure on the now-removed route. Deleted in same task.
- **Broken by Task 1:** `frontend/tests/sidebar-items.spec.ts` — updated in Task 1 with new role matrix.
- **Untouched:** `frontend/tests/primitives.spec.ts` (Phase 4.0 primitives), `frontend/tests/nexus-shell.spec.ts`, `frontend/tests/redirects.spec.ts`, all backend tests except for the new `test_dashboard_summary.py`.
- **Fixtures/mocks:** No shared fixtures affected. The new spec mocks its own routes.

Net Playwright count change: -2 specs (deleted) + 1 new spec (5 tests) + 4 updated tests in sidebar-items.spec.ts. Final count must be reported in iter 071 Notes from the actual test runner output, not predicted here.

Net pytest count change: +4 new tests in `test_dashboard_summary.py`. Expected 595 passed.

---

## Self-review

**Spec coverage check:**
- ADMIN dashboard: ✅ Task 3 covers full layout for ADMIN.
- SM dashboard: ✅ Task 3 covers full layout for SM, scoped via Task 2 backend.
- KPI definitions (4): ✅ locked in plan preamble + Task 2 implementation.
- Sidebar/permissions matrix patch: ✅ Task 1.
- Other-role placeholder: ✅ Task 3 placeholder branch.
- Pre-revamp retirement: ✅ Task 3 deletes route + specs.
- Permanent test coverage: ✅ Task 4.
- Iter doc + summary: ✅ Task 5.

**Placeholder scan:** No "TBD" / "TODO" / "implement later" in this plan. Concrete code blocks for every code step.

**Type consistency:** `DashboardSummary` (frontend) ↔ `DashboardSummaryResponse` (backend) — fields match. `DashboardKpis.outstanding_ap_usd` is `string` in both. `AwaitingAcceptanceItem.submitted_at` is ISO string on the wire, `datetime` on backend.

**Open implementation choices left to the subagent (intentional, per CLAUDE.md "intent over dictation"):**
- Exact existing pytest fixture/auth pattern (subagent reads `conftest.py`).
- Whether `activity_repo.list()` already supports `target_role` filter or needs an extension (subagent reads the repo).
- Exact USD conversion path on `outstanding_ap_usd` (already a pattern in the same router — reuse).
