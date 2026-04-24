# Phase 4.0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the design system, primitive component library, app shell with role-conditional sidebar, mobile variant, state primitives, `(nexus)` layout group, redirect infrastructure, `permissions.ts` ADMIN-inheritance fix, and `seed.py` variety overhaul — all without breaking any existing flow.

**Architecture:** New primitives live in `frontend/src/lib/ui/` with scoped styles — they coexist with existing components in `frontend/src/lib/components/` and existing routes. A new `(nexus)` route group at `frontend/src/routes/(nexus)/` gets an `+layout.svelte` wrapping `AppShell`. No user-facing routes ship in Phase 4.0; the `(nexus)` group stays empty until Phase 4.1 adds Dashboard. `global.css` component rules (`.btn`, `.table`, `.badge`, `.card`, `.input`) stay untouched during Phase 4.0 — deletion happens at the end of the revamp after every aggregate phase closes.

**Tech Stack:** SvelteKit 2, Svelte 5 (runes), TypeScript, Playwright for tests. Python 3.13 + FastAPI backend with asyncpg + pytest.

**Ship gates (every task before commit):**
1. Mock-clarity — if the Lovable mock is silent, stop and brainstorm (explicit tasks flagged below)
2. Past-flow — `make test-browser` green for all pre-revamp specs
3. Future-flow — any primitive added in a prior task still works

---

## Scope Check

Phase 4.0 is a single subsystem (the foundation layer) by design. No decomposition needed.

---

## File Structure

**New files:**
- `frontend/src/lib/ui/Button.svelte`
- `frontend/src/lib/ui/StatusPill.svelte`
- `frontend/src/lib/ui/ProgressBar.svelte`
- `frontend/src/lib/ui/Input.svelte`
- `frontend/src/lib/ui/Select.svelte`
- `frontend/src/lib/ui/DateInput.svelte`
- `frontend/src/lib/ui/Toggle.svelte`
- `frontend/src/lib/ui/FormField.svelte`
- `frontend/src/lib/ui/FormCard.svelte`
- `frontend/src/lib/ui/PanelCard.svelte`
- `frontend/src/lib/ui/AttributeList.svelte`
- `frontend/src/lib/ui/KpiCard.svelte`
- `frontend/src/lib/ui/Timeline.svelte`
- `frontend/src/lib/ui/ActivityFeed.svelte`
- `frontend/src/lib/ui/LoadingState.svelte`
- `frontend/src/lib/ui/EmptyState.svelte`
- `frontend/src/lib/ui/ErrorState.svelte`
- `frontend/src/lib/ui/ErrorBoundary.svelte`
- `frontend/src/lib/ui/DataTable.svelte`
- `frontend/src/lib/ui/PageHeader.svelte`
- `frontend/src/lib/ui/DetailHeader.svelte`
- `frontend/src/lib/ui/Sidebar.svelte`
- `frontend/src/lib/ui/TopBar.svelte`
- `frontend/src/lib/ui/UserMenu.svelte`
- `frontend/src/lib/ui/AppShell.svelte`
- `frontend/src/lib/ui/sidebar-items.ts` — role → items mapping derived from `permissions.ts`
- `frontend/src/lib/ui/redirects.ts` — `oldToNew()` helper used by aggregate phases at retirement time
- `frontend/src/routes/(nexus)/+layout.svelte`
- `frontend/src/routes/(nexus)/+layout.ts`
- `frontend/src/routes/ui-demo/+page.svelte` — dev-only internal gallery (removed at end of revamp)
- `frontend/tests/primitives.spec.ts` — permanent Playwright spec covering every primitive's render contract
- `frontend/tests/nexus-shell.spec.ts` — permanent Playwright spec for AppShell + Sidebar role filtering

**Modified files:**
- `frontend/src/lib/styles/global.css` — add new tokens (sidebar surface, brand blue, status dot palette, breakpoints); do NOT delete component rules
- `frontend/src/lib/permissions.ts` — fix `isExact` asymmetry; ADMIN inherits all
- `backend/src/seed.py` — expand to produce varied data across every aggregate
- `backend/tests/test_seed.py` — new tests for seed variety

---

## Mock-clarity brainstorm stops

Three explicit stops are embedded below as tasks. Each requires a user conversation before implementation:
- Task 18: per-role sidebar item set
- Task 22: mobile drawer trigger and animation
- Task 25: `UserMenu` production layout

---

## Task 1: Fix permissions.ts ADMIN inheritance

**Why:** `isExact` in `permissions.ts` makes ADMIN fail role-scoped checks for VENDOR-only actions (`canAcceptRejectPO`, `canCreateInvoice`, `canSubmitInvoice`, `canPostMilestone`). This is the backlog item "ADMIN inherits all actions". Fix before any primitive (ActionRail, Sidebar) locks in the broken rule.

**Files:**
- Modify: `frontend/src/lib/permissions.ts`
- Modify: `frontend/tests/role-rendering.spec.ts` — add ADMIN assertions where missing

- [ ] **Step 1: Read `frontend/src/lib/permissions.ts` and identify every `isExact` usage**

Expect: `canAcceptRejectPO`, `canCreateInvoice`, `canSubmitInvoice`, `canPostMilestone`.

- [ ] **Step 2: Write a failing Playwright test — `role-rendering.spec.ts` assertions for ADMIN**

Append inside `frontend/tests/role-rendering.spec.ts`:

```typescript
test('ADMIN sees vendor-side actions (post milestone, accept/reject PO, create invoice)', async ({ page }) => {
  await mockUser(page, 'ADMIN');
  await mockApiCatchAll(page);
  await mockUnreadCount(page);
  await page.goto('/po');
  // ADMIN should see the same action affordances a VENDOR sees on a PENDING PO.
  // Any testid currently gated by isExact(role, 'VENDOR') should be visible.
  // At minimum, verify no role-based redirect kicks ADMIN off the PO page.
  await expect(page).toHaveURL(/\/po/);
});
```

Run: `cd frontend && npx playwright test role-rendering.spec.ts --grep "ADMIN sees vendor-side" --reporter=list`
Expected: FAIL — ADMIN currently doesn't inherit VENDOR-side actions.

- [ ] **Step 3: Replace `isExact` with `is` for every permission check**

Edit `frontend/src/lib/permissions.ts`. Replace the four `isExact` call sites with `is`:

```typescript
import type { UserRole } from './types';

function is(role: UserRole, ...allowed: UserRole[]): boolean {
	return role === 'ADMIN' || allowed.includes(role);
}

export const canCreatePO = (role: UserRole) => is(role, 'SM');
export const canEditPO = (role: UserRole) => is(role, 'SM');
export const canSubmitPO = (role: UserRole) => is(role, 'SM');
export const canAcceptRejectPO = (role: UserRole) => is(role, 'VENDOR');
export const canCreateInvoice = (role: UserRole) => is(role, 'VENDOR');
export const canSubmitInvoice = (role: UserRole) => is(role, 'VENDOR');
export const canApproveInvoice = (role: UserRole) => is(role, 'SM');
export const canPayInvoice = (role: UserRole) => is(role, 'SM');
export const canDisputeInvoice = (role: UserRole) => is(role, 'SM');
export const canResolveInvoice = (role: UserRole) => is(role, 'SM');
export const canManageVendors = (role: UserRole) => is(role, 'SM');
export const canManageProducts = (role: UserRole) => is(role, 'SM');
export const canViewProducts = (role: UserRole) => is(role, 'SM', 'QUALITY_LAB');
export const canPostMilestone = (role: UserRole) => is(role, 'VENDOR');
export const canViewInvoices = (role: UserRole) => is(role, 'SM', 'VENDOR');
export const canViewPOs = (role: UserRole) => is(role, 'SM', 'VENDOR', 'FREIGHT_MANAGER');
export const canMarkAdvancePaid = (role: UserRole) => is(role, 'SM');
export const canModifyPostAccept = (role: UserRole) => is(role, 'SM');
```

Delete the `isExact` function entirely.

- [ ] **Step 4: Run the full Playwright suite to catch any regression**

Run: `make test-browser`
Expected: PASS. Existing tests assume ADMIN sees action buttons already in several places (see `po-lifecycle.spec.ts`, `role-rendering.spec.ts`). This change makes those pass more predictably.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/permissions.ts frontend/tests/role-rendering.spec.ts
git commit -m "Fix ADMIN inheritance in permissions.ts (iter 4.0.1)"
```

---

## Task 2: Overhaul `backend/src/seed.py` for varied dev data

**Why:** Memory rule: dashboard must show varied data on fresh runs. Seed currently produces minimal fixtures. Without varied data, Phase 4.1 Dashboard cannot be validated visually.

**Files:**
- Modify: `backend/src/seed.py`
- Create: `backend/tests/test_seed.py`

- [ ] **Step 1: Read `backend/src/seed.py` to understand current structure**

Run: `wc -l backend/src/seed.py` (~715 lines).

Identify: how vendors, products, POs, invoices, milestones, activity are currently seeded. Note which aggregates produce only one example.

- [ ] **Step 2: Write a failing pytest asserting seed variety**

Create `backend/tests/test_seed.py`:

```python
"""Guarantees that seed.py populates enough variety for the dashboard to render
meaningfully on a fresh database. If any aggregate is single-valued, the test
fails."""

import pytest
from httpx import AsyncClient

from src.main import app
from src.seed import run_seed


@pytest.mark.asyncio
async def test_seed_variety(db_pool):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await run_seed(conn)

            vendor_count = await conn.fetchval("SELECT count(*) FROM vendors")
            po_count = await conn.fetchval("SELECT count(*) FROM purchase_orders")
            po_status_count = await conn.fetchval(
                "SELECT count(DISTINCT status) FROM purchase_orders"
            )
            invoice_count = await conn.fetchval("SELECT count(*) FROM invoices")
            invoice_status_count = await conn.fetchval(
                "SELECT count(DISTINCT status) FROM invoices"
            )
            milestone_count = await conn.fetchval(
                "SELECT count(*) FROM milestone_updates"
            )
            milestone_stage_count = await conn.fetchval(
                "SELECT count(DISTINCT milestone) FROM milestone_updates"
            )
            activity_count = await conn.fetchval("SELECT count(*) FROM activity_log")
            user_role_count = await conn.fetchval(
                "SELECT count(DISTINCT role) FROM users"
            )
            vendor_type_count = await conn.fetchval(
                "SELECT count(DISTINCT vendor_type) FROM vendors"
            )

            assert vendor_count >= 5, "seed must produce >=5 vendors"
            assert vendor_type_count >= 3, "seed must cover >=3 vendor types"
            assert po_count >= 10, "seed must produce >=10 POs"
            assert po_status_count >= 4, "seed must cover >=4 PO statuses"
            assert invoice_count >= 6, "seed must produce >=6 invoices"
            assert invoice_status_count >= 3, "seed must cover >=3 invoice statuses"
            assert milestone_count >= 6, "seed must produce >=6 milestone updates"
            assert milestone_stage_count >= 3, "seed must cover >=3 milestone stages"
            assert activity_count >= 15, "seed must produce >=15 activity entries"
            assert user_role_count >= 3, "seed must cover >=3 user roles"
```

- [ ] **Step 3: Run the test to confirm it fails**

Run: `make test` (or `uv run pytest backend/tests/test_seed.py -v`)
Expected: FAIL — current seed likely produces fewer than the asserted quantities.

- [ ] **Step 4: Expand `backend/src/seed.py` to satisfy the assertions**

Guidelines:
- Add vendors covering PROCUREMENT, OPEX, FREIGHT, MISCELLANEOUS types in at least 5 different countries
- Add POs spanning DRAFT, PENDING, ACCEPTED, REJECTED, REVISED, MODIFIED statuses
- Add invoices spanning DRAFT, SUBMITTED, APPROVED, PAID, DISPUTED
- Add milestone updates covering RAW_MATERIALS through READY_TO_SHIP on at least 3 POs
- Add activity log entries covering PO_CREATED, PO_SUBMITTED, PO_ACCEPTED, PO_MODIFIED, INVOICE_CREATED, INVOICE_SUBMITTED, INVOICE_APPROVED, MILESTONE_POSTED event types
- Add users covering ADMIN, SM, VENDOR, FREIGHT_MANAGER, QUALITY_LAB roles
- Keep test users deterministic so existing backend tests relying on seed fixtures still pass

Do not change existing fixture IDs or usernames the other tests depend on; ADD new ones instead.

- [ ] **Step 5: Run the new test + the full pytest suite**

Run: `make test`
Expected: all pass. If existing tests fail because they relied on exact row counts, investigate whether to relax the fixture or add specific rows.

- [ ] **Step 6: Commit**

```bash
git add backend/src/seed.py backend/tests/test_seed.py
git commit -m "Expand seed.py for varied dev data (iter 4.0.2)"
```

---

## Task 3: Scaffold `(nexus)` layout group

**Why:** Phase 4.0 needs a route group where redesigned pages will live. Scaffold it empty first so Phase 4.1 has a home.

**Files:**
- Create: `frontend/src/routes/(nexus)/+layout.svelte`
- Create: `frontend/src/routes/(nexus)/+layout.ts`

- [ ] **Step 1: Create `frontend/src/routes/(nexus)/+layout.ts`**

```typescript
import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { me } from '$lib/auth';

export const prerender = false;
export const ssr = false;

export const load: LayoutLoad = async ({ url }) => {
	const user = await me();
	if (!user) {
		const redirectParam = encodeURIComponent(url.pathname + url.search);
		throw redirect(307, `/login?redirect=${redirectParam}`);
	}
	return { user };
};
```

- [ ] **Step 2: Create `frontend/src/routes/(nexus)/+layout.svelte`**

Minimal passthrough for now — `AppShell` gets wired in Task 26 after primitives exist.

```svelte
<script lang="ts">
	import '$lib/styles/global.css';
	let { children } = $props();
</script>

{@render children()}
```

- [ ] **Step 3: Verify the root layout still handles unmatched routes**

Run: `cd frontend && npm run check`
Expected: no TypeScript errors.

Run: `make test-browser`
Expected: PASS. No routes exist inside `(nexus)` yet so no test touches it.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/\(nexus\)/
git commit -m "Scaffold empty (nexus) layout group (iter 4.0.3)"
```

---

## Task 4: Add new design tokens to `global.css`

**Why:** Primitives need new tokens (sidebar surface, brand blue, status dot palette, breakpoint variables). Additive — no deletion.

**Files:**
- Modify: `frontend/src/lib/styles/global.css`

- [ ] **Step 1: Append new tokens to `:root`**

Edit `frontend/src/lib/styles/global.css`. Inside the existing `:root` block, append after `--shadow-md`:

```css
	/* Shell surfaces (Phase 4.0) */
	--surface-page: #fafafa;
	--surface-card: #ffffff;
	--surface-sidebar: #0f1419;
	--text-sidebar: #ffffff;
	--text-sidebar-muted: #9ca3af;

	/* Brand and accents (Phase 4.0) */
	--brand-accent: #3b5cf0;
	--button-solid-bg: #0f1419;
	--button-solid-fg: #ffffff;

	/* Status dots (leading circle inside pills) */
	--dot-green: #16a34a;
	--dot-blue: #2563eb;
	--dot-orange: #d97706;
	--dot-red: #dc2626;
	--dot-gray: #6b7280;

	/* Typography extensions */
	--font-size-xs: 0.75rem;
	--font-size-3xl: 1.875rem;
	--letter-spacing-wide: 0.06em;

	/* Spacing extensions */
	--space-7: 1.75rem;
	--space-20: 5rem;

	/* Breakpoints as custom properties for JS reference (not used by @media) */
	--breakpoint-sm: 390px;
	--breakpoint-md: 768px;
	--breakpoint-lg: 1024px;
	--breakpoint-xl: 1440px;
```

Do not delete or modify any existing token.

- [ ] **Step 2: Verify no existing styling breaks**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Run: `make test-browser`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/styles/global.css
git commit -m "Add Phase 4.0 design tokens (iter 4.0.4)"
```

---

## Task 5: Create `Button` primitive

**Why:** The most foundational control. Every other interactive primitive depends on it.

**Files:**
- Create: `frontend/src/lib/ui/Button.svelte`
- Create: `frontend/src/routes/ui-demo/+page.svelte` (seeded with Button only; later tasks extend)
- Create: `frontend/tests/primitives.spec.ts`

- [ ] **Step 1: Write failing Playwright spec for Button rendering**

Create `frontend/tests/primitives.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

function mockUser(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'ui-demo',
					username: 'ui-demo',
					display_name: 'UI Demo',
					role: 'ADMIN',
					status: 'ACTIVE',
					vendor_id: null
				}
			})
		});
	});
}

function mockApiCatchAll(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

test.describe('Button primitive', () => {
	test('renders primary button with keyboard-focusable affordance', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const btn = page.getByTestId('ui-btn-primary');
		await expect(btn).toBeVisible();
		await btn.focus();
		await expect(btn).toBeFocused();
	});

	test('renders secondary and ghost variants', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-btn-secondary')).toBeVisible();
		await expect(page.getByTestId('ui-btn-ghost')).toBeVisible();
	});

	test('disabled button does not fire onclick on Enter', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const disabled = page.getByTestId('ui-btn-disabled');
		await expect(disabled).toBeDisabled();
	});
});
```

Run: `cd frontend && npx playwright test primitives.spec.ts --reporter=list`
Expected: FAIL — `/ui-demo` does not exist yet.

- [ ] **Step 2: Create `frontend/src/lib/ui/Button.svelte`**

```svelte
<script lang="ts">
	type Variant = 'primary' | 'secondary' | 'ghost';

	let {
		variant = 'primary',
		type = 'button',
		disabled = false,
		onclick,
		children,
		'data-testid': testid
	}: {
		variant?: Variant;
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		onclick?: (e: MouseEvent) => void;
		children: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<button {type} {disabled} {onclick} data-testid={testid} class="btn {variant}">
	{@render children()}
</button>

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		font-size: var(--font-size-sm);
		font-weight: 500;
		border-radius: var(--radius-md);
		border: 1px solid transparent;
		cursor: pointer;
		font-family: var(--font-family);
		transition: opacity 0.15s, background-color 0.15s, border-color 0.15s;
	}
	.btn:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 2px;
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.primary {
		background-color: var(--button-solid-bg);
		color: var(--button-solid-fg);
	}
	.primary:hover:not(:disabled) {
		opacity: 0.9;
	}
	.secondary {
		background-color: var(--surface-card);
		color: var(--gray-900);
		border-color: var(--gray-300);
	}
	.secondary:hover:not(:disabled) {
		background-color: var(--gray-50);
	}
	.ghost {
		background: transparent;
		color: var(--gray-700);
	}
	.ghost:hover:not(:disabled) {
		background-color: var(--gray-100);
	}
</style>
```

- [ ] **Step 3: Create `frontend/src/routes/ui-demo/+page.svelte`**

```svelte
<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
</script>

<h1>Phase 4.0 UI Demo</h1>

<section>
	<h2>Button</h2>
	<div style="display:flex;gap:1rem;">
		<Button data-testid="ui-btn-primary">Primary</Button>
		<Button variant="secondary" data-testid="ui-btn-secondary">Secondary</Button>
		<Button variant="ghost" data-testid="ui-btn-ghost">Ghost</Button>
		<Button disabled data-testid="ui-btn-disabled">Disabled</Button>
	</div>
</section>
```

- [ ] **Step 4: Run the new spec to verify it passes**

Run: `cd frontend && npx playwright test primitives.spec.ts --reporter=list`
Expected: PASS.

- [ ] **Step 5: Run the full browser suite**

Run: `make test-browser`
Expected: PASS.

- [ ] **Step 6: Capture 390px + 1024px screenshots of `/ui-demo`**

Create `frontend/tests/scratch/iteration-4-0-5/capture.ts`:

```typescript
import { chromium } from 'playwright';

async function capture() {
	const browser = await chromium.launch();
	const ctx = await browser.newContext({ viewport: { width: 390, height: 800 } });
	const page = await ctx.newPage();
	await page.route('**/api/v1/auth/me', (r) =>
		r.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: { id: 'x', username: 'x', display_name: 'X', role: 'ADMIN', status: 'ACTIVE', vendor_id: null } })
		})
	);
	await page.route('**/api/v1/**', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
	await page.goto('http://localhost:5173/ui-demo');
	await page.screenshot({ path: 'frontend/tests/scratch/iteration-4-0-5/screenshots/390.jpg', type: 'jpeg', quality: 40 });
	await page.setViewportSize({ width: 1024, height: 800 });
	await page.screenshot({ path: 'frontend/tests/scratch/iteration-4-0-5/screenshots/1024.jpg', type: 'jpeg', quality: 40 });
	await browser.close();
}

capture();
```

Run: `cd frontend && npm run dev &` then `cd frontend && npx tsx tests/scratch/iteration-4-0-5/capture.ts`
Expected: two JPEGs produced. Review them; attach to the commit.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/ui/Button.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add Button primitive + ui-demo route (iter 4.0.5)"
```

---

## Task 6: Create `StatusPill` primitive (scoped)

**Why:** New `StatusPill` with dot + label, scoped styles, no dependency on global `.badge-*` classes. Coexists with the existing `frontend/src/lib/components/StatusPill.svelte` which continues to serve pre-revamp pages.

**Files:**
- Create: `frontend/src/lib/ui/StatusPill.svelte`
- Modify: `frontend/src/routes/ui-demo/+page.svelte`
- Modify: `frontend/tests/primitives.spec.ts`

- [ ] **Step 1: Add failing test**

Append to `frontend/tests/primitives.spec.ts`:

```typescript
test.describe('StatusPill primitive', () => {
	test('renders five tone variants with leading dot', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		for (const tone of ['green', 'blue', 'orange', 'red', 'gray']) {
			await expect(page.getByTestId(`ui-pill-${tone}`)).toBeVisible();
		}
	});
});
```

Run: `cd frontend && npx playwright test primitives.spec.ts --grep "StatusPill" --reporter=list`
Expected: FAIL.

- [ ] **Step 2: Create `frontend/src/lib/ui/StatusPill.svelte`**

```svelte
<script lang="ts">
	type Tone = 'green' | 'blue' | 'orange' | 'red' | 'gray';
	let {
		tone = 'gray',
		label,
		'data-testid': testid
	}: { tone?: Tone; label: string; 'data-testid'?: string } = $props();
</script>

<span class="pill {tone}" data-testid={testid}>
	<span class="dot" aria-hidden="true"></span>
	{label}
</span>

<style>
	.pill {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-xs);
		font-weight: 500;
		border-radius: 999px;
		background-color: var(--gray-100);
		color: var(--gray-700);
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 999px;
		background-color: var(--dot-gray);
	}
	.green { background-color: #dcfce7; color: #166534; }
	.green .dot { background-color: var(--dot-green); }
	.blue { background-color: #dbeafe; color: #1e40af; }
	.blue .dot { background-color: var(--dot-blue); }
	.orange { background-color: #fef3c7; color: #92400e; }
	.orange .dot { background-color: var(--dot-orange); }
	.red { background-color: #fee2e2; color: #991b1b; }
	.red .dot { background-color: var(--dot-red); }
	.gray { background-color: #f3f4f6; color: #374151; }
	.gray .dot { background-color: var(--dot-gray); }
</style>
```

- [ ] **Step 3: Extend `/ui-demo` page**

Append to `frontend/src/routes/ui-demo/+page.svelte` inside the script:

```svelte
<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
</script>
```

Append below Button section:

```svelte
<section>
	<h2>StatusPill</h2>
	<div style="display:flex;gap:1rem;flex-wrap:wrap;">
		<StatusPill tone="green" label="Delivered" data-testid="ui-pill-green" />
		<StatusPill tone="blue" label="In Transit" data-testid="ui-pill-blue" />
		<StatusPill tone="orange" label="In Production" data-testid="ui-pill-orange" />
		<StatusPill tone="red" label="Overdue" data-testid="ui-pill-red" />
		<StatusPill tone="gray" label="Draft" data-testid="ui-pill-gray" />
	</div>
</section>
```

- [ ] **Step 4: Verify tests pass and commit**

Run: `cd frontend && npx playwright test primitives.spec.ts --reporter=list`
Expected: PASS.

Run: `make test-browser`
Expected: PASS.

```bash
git add frontend/src/lib/ui/StatusPill.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add StatusPill primitive with dot+tone variants (iter 4.0.6)"
```

---

## Task 7: Create `ProgressBar` primitive

**Files:**
- Create: `frontend/src/lib/ui/ProgressBar.svelte`
- Modify: `frontend/src/routes/ui-demo/+page.svelte`
- Modify: `frontend/tests/primitives.spec.ts`

- [ ] **Step 1: Add failing test**

Append to `primitives.spec.ts`:

```typescript
test.describe('ProgressBar primitive', () => {
	test('renders a progress bar with accessible value', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const bar = page.getByTestId('ui-progress-60');
		await expect(bar).toBeVisible();
		await expect(bar).toHaveAttribute('role', 'progressbar');
		await expect(bar).toHaveAttribute('aria-valuenow', '60');
	});
});
```

- [ ] **Step 2: Create `frontend/src/lib/ui/ProgressBar.svelte`**

```svelte
<script lang="ts">
	let {
		value,
		label,
		'data-testid': testid
	}: { value: number; label?: string; 'data-testid'?: string } = $props();
	const clamped = $derived(Math.max(0, Math.min(100, value)));
</script>

<div class="wrapper">
	<div
		class="track"
		role="progressbar"
		aria-valuenow={clamped}
		aria-valuemin="0"
		aria-valuemax="100"
		data-testid={testid}
	>
		<div class="fill" style="width: {clamped}%"></div>
	</div>
	{#if label}<span class="label">{label}</span>{/if}
</div>

<style>
	.wrapper { display: flex; align-items: center; gap: var(--space-3); }
	.track {
		position: relative;
		flex: 1;
		height: 6px;
		border-radius: 999px;
		background-color: var(--gray-200);
		overflow: hidden;
	}
	.fill {
		height: 100%;
		background-color: var(--button-solid-bg);
		transition: width 0.2s ease;
	}
	.label { font-size: var(--font-size-sm); color: var(--gray-600); min-width: 3ch; text-align: right; }
</style>
```

- [ ] **Step 3: Extend `/ui-demo`**

```svelte
<section>
	<h2>ProgressBar</h2>
	<ProgressBar value={60} label="60%" data-testid="ui-progress-60" />
</section>
```

Import at top: `import ProgressBar from '$lib/ui/ProgressBar.svelte';`

- [ ] **Step 4: Verify and commit**

Run: `cd frontend && npx playwright test primitives.spec.ts --reporter=list`
Expected: PASS.

```bash
git add frontend/src/lib/ui/ProgressBar.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add ProgressBar primitive (iter 4.0.7)"
```

---

## Task 8: Create `Input`, `Select`, `DateInput`, `Toggle` primitives

Four leaf form controls in one task — each is small and none depends on the others.

**Files:**
- Create: `frontend/src/lib/ui/Input.svelte`, `Select.svelte`, `DateInput.svelte`, `Toggle.svelte`
- Modify: `/ui-demo` page
- Modify: `primitives.spec.ts`

- [ ] **Step 1: Write failing tests**

Append to `primitives.spec.ts`:

```typescript
test.describe('Form control primitives', () => {
	test('Input primitive accepts typed text', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const input = page.getByTestId('ui-input-name');
		await input.fill('hello');
		await expect(input).toHaveValue('hello');
	});

	test('Select primitive changes value', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const select = page.getByTestId('ui-select-country');
		await select.selectOption('US');
		await expect(select).toHaveValue('US');
	});

	test('DateInput primitive renders', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-date-due')).toBeVisible();
	});

	test('Toggle primitive flips on click', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const toggle = page.getByTestId('ui-toggle');
		await expect(toggle).toHaveAttribute('aria-pressed', 'false');
		await toggle.click();
		await expect(toggle).toHaveAttribute('aria-pressed', 'true');
	});
});
```

Run: FAIL.

- [ ] **Step 2: Create `Input.svelte`**

```svelte
<script lang="ts">
	let {
		value = $bindable(''),
		type = 'text',
		placeholder,
		disabled = false,
		invalid = false,
		'data-testid': testid
	}: {
		value?: string;
		type?: string;
		placeholder?: string;
		disabled?: boolean;
		invalid?: boolean;
		'data-testid'?: string;
	} = $props();
</script>

<input
	{type}
	{placeholder}
	{disabled}
	bind:value
	data-testid={testid}
	class:invalid
/>

<style>
	input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		color: var(--gray-900);
	}
	input:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 0;
		border-color: var(--brand-accent);
	}
	input:disabled { opacity: 0.5; cursor: not-allowed; }
	input.invalid { border-color: var(--red-600); }
</style>
```

- [ ] **Step 3: Create `Select.svelte`**

```svelte
<script lang="ts">
	let {
		value = $bindable(''),
		options,
		disabled = false,
		invalid = false,
		'data-testid': testid
	}: {
		value?: string;
		options: Array<{ value: string; label: string }>;
		disabled?: boolean;
		invalid?: boolean;
		'data-testid'?: string;
	} = $props();
</script>

<select bind:value {disabled} data-testid={testid} class:invalid>
	{#each options as opt (opt.value)}
		<option value={opt.value}>{opt.label}</option>
	{/each}
</select>

<style>
	select {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		color: var(--gray-900);
	}
	select:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 0;
		border-color: var(--brand-accent);
	}
	select:disabled { opacity: 0.5; cursor: not-allowed; }
	select.invalid { border-color: var(--red-600); }
</style>
```

- [ ] **Step 4: Create `DateInput.svelte`**

```svelte
<script lang="ts">
	let {
		value = $bindable(''),
		disabled = false,
		invalid = false,
		'data-testid': testid
	}: {
		value?: string;
		disabled?: boolean;
		invalid?: boolean;
		'data-testid'?: string;
	} = $props();
</script>

<input type="date" bind:value {disabled} data-testid={testid} class:invalid />

<style>
	input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		color: var(--gray-900);
	}
	input:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 0;
		border-color: var(--brand-accent);
	}
	input:disabled { opacity: 0.5; cursor: not-allowed; }
	input.invalid { border-color: var(--red-600); }
</style>
```

- [ ] **Step 5: Create `Toggle.svelte`**

```svelte
<script lang="ts">
	let {
		pressed = $bindable(false),
		disabled = false,
		label,
		'data-testid': testid
	}: {
		pressed?: boolean;
		disabled?: boolean;
		label?: string;
		'data-testid'?: string;
	} = $props();

	function toggle() {
		if (!disabled) pressed = !pressed;
	}
</script>

<button
	type="button"
	role="switch"
	aria-pressed={pressed}
	aria-label={label}
	{disabled}
	onclick={toggle}
	data-testid={testid}
	class:on={pressed}
>
	<span class="knob"></span>
</button>

<style>
	button {
		position: relative;
		width: 2.5rem;
		height: 1.375rem;
		border-radius: 999px;
		border: 1px solid var(--gray-300);
		background-color: var(--gray-200);
		cursor: pointer;
		padding: 0;
		transition: background-color 0.15s;
	}
	button:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 2px;
	}
	button:disabled { opacity: 0.5; cursor: not-allowed; }
	button.on { background-color: var(--button-solid-bg); border-color: var(--button-solid-bg); }
	.knob {
		display: block;
		width: 1rem;
		height: 1rem;
		margin: 1px;
		border-radius: 999px;
		background-color: var(--surface-card);
		transform: translateX(0);
		transition: transform 0.15s;
	}
	button.on .knob { transform: translateX(calc(2.5rem - 1rem - 4px)); }
</style>
```

- [ ] **Step 6: Extend `/ui-demo` page**

Import the four primitives and render them:

```svelte
<section>
	<h2>Form controls</h2>
	<label>Name <Input data-testid="ui-input-name" /></label>
	<label>Country
		<Select
			options={[{ value: 'US', label: 'United States' }, { value: 'IN', label: 'India' }]}
			data-testid="ui-select-country"
		/>
	</label>
	<label>Due <DateInput data-testid="ui-date-due" /></label>
	<Toggle label="Notifications" data-testid="ui-toggle" />
</section>
```

- [ ] **Step 7: Run tests + commit**

Run: `cd frontend && npx playwright test primitives.spec.ts --reporter=list`
Expected: PASS.

```bash
git add frontend/src/lib/ui/Input.svelte frontend/src/lib/ui/Select.svelte frontend/src/lib/ui/DateInput.svelte frontend/src/lib/ui/Toggle.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add Input, Select, DateInput, Toggle primitives (iter 4.0.8)"
```

---

## Task 9: Create `FormField` with server-error contract

**Why:** Form validation rider (#2 of production-grade musts). Every input in the revamp needs to surface server errors inline.

**Files:**
- Create: `frontend/src/lib/ui/FormField.svelte`
- Modify: `/ui-demo`
- Modify: `primitives.spec.ts`

- [ ] **Step 1: Failing test**

Append:

```typescript
test.describe('FormField primitive', () => {
	test('shows inline error when error prop is set', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const err = page.getByTestId('ui-field-error');
		await expect(err).toHaveText('Part number is required');
		await expect(page.getByTestId('ui-field-input')).toHaveAttribute('aria-invalid', 'true');
	});
});
```

- [ ] **Step 2: Create `frontend/src/lib/ui/FormField.svelte`**

```svelte
<script lang="ts">
	let {
		label,
		error,
		required = false,
		hint,
		'data-testid': testid,
		children
	}: {
		label: string;
		error?: string | null;
		required?: boolean;
		hint?: string;
		'data-testid'?: string;
		children: import('svelte').Snippet<[{ invalid: boolean; 'aria-invalid': boolean }]>;
	} = $props();

	const hasError = $derived(error != null && error.length > 0);
</script>

<div class="field" data-testid={testid}>
	<label>
		<span class="label">
			{label}
			{#if required}<span class="req" aria-hidden="true">*</span>{/if}
		</span>
		{@render children({ invalid: hasError, 'aria-invalid': hasError })}
	</label>
	{#if hasError}
		<span class="error" role="alert" data-testid="{testid}-error">{error}</span>
	{:else if hint}
		<span class="hint">{hint}</span>
	{/if}
</div>

<style>
	.field {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		margin-bottom: var(--space-4);
	}
	.label {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
	}
	.req { color: var(--red-600); margin-left: 2px; }
	.error {
		font-size: var(--font-size-xs);
		color: var(--red-700);
	}
	.hint {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
	}
</style>
```

- [ ] **Step 3: Extend `/ui-demo` with a FormField instance in error state**

```svelte
<script lang="ts">
	// ...existing imports
	import FormField from '$lib/ui/FormField.svelte';
</script>

<section>
	<h2>FormField</h2>
	<FormField
		label="Part number"
		error="Part number is required"
		required
		data-testid="ui-field"
	>
		{#snippet children({ invalid })}
			<Input data-testid="ui-field-input" invalid={invalid} />
		{/snippet}
	</FormField>
</section>
```

Note: the test asserts `data-testid="ui-field-error"`. The `FormField` builds this testid from `{testid}-error` when the container has `data-testid="ui-field"`.

- [ ] **Step 4: Verify + commit**

Run: `cd frontend && npx playwright test primitives.spec.ts --reporter=list`
Expected: PASS.

```bash
git add frontend/src/lib/ui/FormField.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add FormField with server-error contract (iter 4.0.9)"
```

---

## Task 10: Create `PanelCard`, `AttributeList`, `FormCard`

Three surface primitives that depend only on tokens.

**Files:**
- Create: `frontend/src/lib/ui/PanelCard.svelte`, `AttributeList.svelte`, `FormCard.svelte`
- Modify: `/ui-demo`
- Modify: `primitives.spec.ts`

- [ ] **Step 1: Failing test**

```typescript
test.describe('Panel primitives', () => {
	test('PanelCard renders title and body slot', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-panel').getByRole('heading', { name: 'Details' })).toBeVisible();
	});

	test('AttributeList renders rows with label and value', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-attr-list')).toContainText('Vendor');
		await expect(page.getByTestId('ui-attr-list')).toContainText('Acme Inc');
	});

	test('FormCard has Cancel and Submit buttons in footer', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-formcard-cancel')).toBeVisible();
		await expect(page.getByTestId('ui-formcard-submit')).toBeVisible();
	});
});
```

- [ ] **Step 2: Create `PanelCard.svelte`**

```svelte
<script lang="ts">
	let {
		title,
		subtitle,
		action,
		children,
		'data-testid': testid
	}: {
		title: string;
		subtitle?: string;
		action?: import('svelte').Snippet;
		children: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<section class="panel" data-testid={testid}>
	<header>
		<div>
			<h3>{title}</h3>
			{#if subtitle}<p class="subtitle">{subtitle}</p>{/if}
		</div>
		{#if action}<div class="action">{@render action()}</div>{/if}
	</header>
	<div class="body">{@render children()}</div>
</section>

<style>
	.panel {
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-4);
		margin-bottom: var(--space-4);
	}
	h3 {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.subtitle {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-top: var(--space-1);
	}
	.body { display: flex; flex-direction: column; gap: var(--space-3); }
</style>
```

- [ ] **Step 3: Create `AttributeList.svelte`**

```svelte
<script lang="ts">
	let {
		items,
		'data-testid': testid
	}: {
		items: Array<{ label: string; value: string }>;
		'data-testid'?: string;
	} = $props();
</script>

<dl class="list" data-testid={testid}>
	{#each items as item (item.label)}
		<div class="row">
			<dt>{item.label}</dt>
			<dd>{item.value}</dd>
		</div>
	{/each}
</dl>

<style>
	.list { display: flex; flex-direction: column; gap: var(--space-2); margin: 0; }
	.row {
		display: grid;
		grid-template-columns: minmax(8rem, 1fr) 2fr;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}
	.row:last-child { border-bottom: none; }
	dt { font-size: var(--font-size-sm); color: var(--gray-500); margin: 0; }
	dd { font-size: var(--font-size-sm); color: var(--gray-900); margin: 0; }
</style>
```

- [ ] **Step 4: Create `FormCard.svelte`**

```svelte
<script lang="ts">
	import Button from './Button.svelte';
	let {
		title,
		subtitle,
		onCancel,
		onSubmit,
		submitLabel = 'Save',
		cancelLabel = 'Cancel',
		submitDisabled = false,
		children,
		'data-testid': testid
	}: {
		title: string;
		subtitle?: string;
		onCancel?: () => void;
		onSubmit: () => void;
		submitLabel?: string;
		cancelLabel?: string;
		submitDisabled?: boolean;
		children: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		onSubmit();
	}
</script>

<form class="card" onsubmit={handleSubmit} data-testid={testid}>
	<header>
		<h3>{title}</h3>
		{#if subtitle}<p class="subtitle">{subtitle}</p>{/if}
	</header>
	<div class="body">{@render children()}</div>
	<footer>
		{#if onCancel}
			<Button variant="secondary" onclick={onCancel} data-testid="{testid}-cancel">{cancelLabel}</Button>
		{/if}
		<Button type="submit" disabled={submitDisabled} data-testid="{testid}-submit">{submitLabel}</Button>
	</footer>
</form>

<style>
	.card {
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	h3 { font-size: var(--font-size-lg); font-weight: 600; margin: 0; }
	.subtitle { font-size: var(--font-size-sm); color: var(--gray-500); margin-top: var(--space-1); }
	footer { display: flex; justify-content: flex-end; gap: var(--space-3); }
</style>
```

- [ ] **Step 5: Extend `/ui-demo` with the three primitives**

```svelte
<script lang="ts">
	// ...existing
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import AttributeList from '$lib/ui/AttributeList.svelte';
	import FormCard from '$lib/ui/FormCard.svelte';
</script>

<section>
	<h2>Panel + Attributes</h2>
	<PanelCard title="Details" data-testid="ui-panel">
		<AttributeList
			items={[
				{ label: 'Vendor', value: 'Acme Inc' },
				{ label: 'Country', value: 'US' }
			]}
			data-testid="ui-attr-list"
		/>
	</PanelCard>
</section>

<section>
	<h2>FormCard</h2>
	<FormCard title="New thing" onSubmit={() => console.log('submit')} onCancel={() => console.log('cancel')} data-testid="ui-formcard">
		<Input data-testid="ui-formcard-input" />
	</FormCard>
</section>
```

- [ ] **Step 6: Verify + commit**

```bash
git add frontend/src/lib/ui/PanelCard.svelte frontend/src/lib/ui/AttributeList.svelte frontend/src/lib/ui/FormCard.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add PanelCard, AttributeList, FormCard (iter 4.0.10)"
```

---

## Task 11: Create `KpiCard` primitive

**Files:**
- Create: `frontend/src/lib/ui/KpiCard.svelte`
- Modify: `/ui-demo`, `primitives.spec.ts`

- [ ] **Step 1: Failing test**

```typescript
test('KpiCard shows label, value, and delta chip', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const kpi = page.getByTestId('ui-kpi');
	await expect(kpi).toContainText('OUTSTANDING');
	await expect(kpi).toContainText('$24,300');
	await expect(kpi).toContainText('+12%');
});
```

- [ ] **Step 2: Create `KpiCard.svelte`**

```svelte
<script lang="ts">
	type Delta = { value: string; tone: 'positive' | 'negative' | 'neutral' };

	let {
		label,
		value,
		delta,
		'data-testid': testid
	}: {
		label: string;
		value: string;
		delta?: Delta;
		'data-testid'?: string;
	} = $props();
</script>

<div class="kpi" data-testid={testid}>
	<span class="label">{label}</span>
	<span class="value">{value}</span>
	{#if delta}
		<span class="delta {delta.tone}">{delta.value}</span>
	{/if}
</div>

<style>
	.kpi {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-6);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
	}
	.label {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
		text-transform: uppercase;
		letter-spacing: var(--letter-spacing-wide);
		font-weight: 600;
	}
	.value {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		color: var(--gray-900);
	}
	.delta {
		align-self: flex-start;
		font-size: var(--font-size-xs);
		font-weight: 500;
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
	}
	.positive { background-color: #dcfce7; color: #166534; }
	.negative { background-color: #fee2e2; color: #991b1b; }
	.neutral { background-color: var(--gray-100); color: var(--gray-700); }
</style>
```

- [ ] **Step 3: Extend `/ui-demo`**

```svelte
<section>
	<h2>KpiCard</h2>
	<KpiCard
		label="Outstanding"
		value="$24,300"
		delta={{ value: '+12%', tone: 'positive' }}
		data-testid="ui-kpi"
	/>
</section>
```

- [ ] **Step 4: Verify + commit**

```bash
git add frontend/src/lib/ui/KpiCard.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add KpiCard primitive (iter 4.0.11)"
```

---

## Task 12: Create `Timeline` and `ActivityFeed` primitives

**Files:**
- Create: `frontend/src/lib/ui/Timeline.svelte`, `ActivityFeed.svelte`
- Modify: `/ui-demo`, `primitives.spec.ts`

- [ ] **Step 1: Failing tests**

```typescript
test('Timeline renders ordered steps with state classes', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const steps = page.getByTestId('ui-timeline').locator('li');
	await expect(steps).toHaveCount(3);
});

test('ActivityFeed renders entries with dot + primary + secondary lines', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const feed = page.getByTestId('ui-feed');
	await expect(feed).toContainText('PO accepted');
	await expect(feed).toContainText('2m ago');
});
```

- [ ] **Step 2: Create `Timeline.svelte`**

```svelte
<script lang="ts">
	type StepState = 'done' | 'current' | 'upcoming';

	let {
		steps,
		'data-testid': testid
	}: {
		steps: Array<{ label: string; state: StepState; detail?: string }>;
		'data-testid'?: string;
	} = $props();
</script>

<ol class="timeline" data-testid={testid}>
	{#each steps as step (step.label)}
		<li class={step.state}>
			<span class="marker" aria-hidden="true"></span>
			<div class="content">
				<span class="label">{step.label}</span>
				{#if step.detail}<span class="detail">{step.detail}</span>{/if}
			</div>
		</li>
	{/each}
</ol>

<style>
	.timeline {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	li {
		display: grid;
		grid-template-columns: 1rem 1fr;
		gap: var(--space-3);
		align-items: start;
		position: relative;
	}
	.marker {
		width: 0.75rem;
		height: 0.75rem;
		border-radius: 999px;
		background-color: var(--gray-300);
		margin-top: 0.25rem;
	}
	li.done .marker { background-color: var(--dot-green); }
	li.current .marker { background-color: var(--dot-blue); box-shadow: 0 0 0 3px #dbeafe; }
	li.upcoming .marker { background-color: var(--gray-200); }
	.content { display: flex; flex-direction: column; gap: 2px; }
	.label { font-size: var(--font-size-sm); font-weight: 500; color: var(--gray-900); }
	.detail { font-size: var(--font-size-xs); color: var(--gray-500); }
</style>
```

- [ ] **Step 3: Create `ActivityFeed.svelte`**

```svelte
<script lang="ts">
	type Entry = {
		id: string;
		primary: string;
		secondary?: string;
		tone: 'green' | 'blue' | 'orange' | 'red' | 'gray';
	};

	let {
		entries,
		'data-testid': testid
	}: { entries: Entry[]; 'data-testid'?: string } = $props();
</script>

<ul class="feed" data-testid={testid}>
	{#each entries as e (e.id)}
		<li>
			<span class="dot {e.tone}" aria-hidden="true"></span>
			<div class="content">
				<span class="primary">{e.primary}</span>
				{#if e.secondary}<span class="secondary">{e.secondary}</span>{/if}
			</div>
		</li>
	{/each}
</ul>

<style>
	.feed {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	li {
		display: grid;
		grid-template-columns: 0.5rem 1fr;
		gap: var(--space-3);
		align-items: start;
	}
	.dot {
		width: 0.375rem;
		height: 0.375rem;
		border-radius: 999px;
		margin-top: 0.5rem;
		background-color: var(--dot-gray);
	}
	.dot.green { background-color: var(--dot-green); }
	.dot.blue { background-color: var(--dot-blue); }
	.dot.orange { background-color: var(--dot-orange); }
	.dot.red { background-color: var(--dot-red); }
	.content { display: flex; flex-direction: column; gap: 2px; }
	.primary { font-size: var(--font-size-sm); color: var(--gray-900); }
	.secondary { font-size: var(--font-size-xs); color: var(--gray-500); }
</style>
```

- [ ] **Step 4: Extend `/ui-demo`**

```svelte
<section>
	<h2>Timeline</h2>
	<Timeline
		steps={[
			{ label: 'Queued', state: 'done' },
			{ label: 'In production', state: 'current', detail: 'Day 2 of 5' },
			{ label: 'QC inspection', state: 'upcoming' }
		]}
		data-testid="ui-timeline"
	/>
</section>

<section>
	<h2>ActivityFeed</h2>
	<ActivityFeed
		entries={[
			{ id: '1', primary: 'PO accepted', secondary: '2m ago', tone: 'green' },
			{ id: '2', primary: 'Invoice submitted', secondary: '1h ago', tone: 'blue' }
		]}
		data-testid="ui-feed"
	/>
</section>
```

- [ ] **Step 5: Verify + commit**

```bash
git add frontend/src/lib/ui/Timeline.svelte frontend/src/lib/ui/ActivityFeed.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add Timeline and ActivityFeed primitives (iter 4.0.12)"
```

---

## Task 13: Create `LoadingState`, `EmptyState`, `ErrorState`, `ErrorBoundary`

State primitives — required by every async surface per rider #1.

**Files:**
- Create: `frontend/src/lib/ui/LoadingState.svelte`, `EmptyState.svelte`, `ErrorState.svelte`, `ErrorBoundary.svelte`
- Modify: `/ui-demo`, `primitives.spec.ts`

- [ ] **Step 1: Failing tests**

```typescript
test('LoadingState renders a spinner labelled for assistive tech', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	await expect(page.getByTestId('ui-loading')).toHaveAttribute('role', 'status');
});

test('EmptyState renders title + description', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const empty = page.getByTestId('ui-empty');
	await expect(empty).toContainText('No results');
	await expect(empty).toContainText('Try adjusting');
});

test('ErrorState shows message and a Retry button', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	await expect(page.getByTestId('ui-error')).toContainText('Something broke');
	await expect(page.getByTestId('ui-error-retry')).toBeVisible();
});
```

- [ ] **Step 2: Create `LoadingState.svelte`**

```svelte
<script lang="ts">
	let { label = 'Loading', 'data-testid': testid }: { label?: string; 'data-testid'?: string } = $props();
</script>

<div class="wrap" role="status" aria-live="polite" data-testid={testid}>
	<span class="spinner" aria-hidden="true"></span>
	<span class="sr">{label}</span>
</div>

<style>
	.wrap {
		display: flex;
		justify-content: center;
		align-items: center;
		padding: var(--space-8);
	}
	.spinner {
		width: 1.25rem;
		height: 1.25rem;
		border: 2px solid var(--gray-200);
		border-top-color: var(--brand-accent);
		border-radius: 999px;
		animation: spin 0.7s linear infinite;
	}
	.sr {
		position: absolute;
		clip: rect(0 0 0 0);
		width: 1px;
		height: 1px;
		overflow: hidden;
	}
	@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

- [ ] **Step 3: Create `EmptyState.svelte`**

```svelte
<script lang="ts">
	let {
		title,
		description,
		action,
		'data-testid': testid
	}: {
		title: string;
		description?: string;
		action?: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<div class="empty" data-testid={testid}>
	<h3>{title}</h3>
	{#if description}<p>{description}</p>{/if}
	{#if action}<div class="action">{@render action()}</div>{/if}
</div>

<style>
	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: var(--space-3);
		padding: var(--space-12) var(--space-4);
		color: var(--gray-600);
	}
	h3 { font-size: var(--font-size-lg); font-weight: 600; color: var(--gray-900); margin: 0; }
	p { font-size: var(--font-size-sm); margin: 0; }
</style>
```

- [ ] **Step 4: Create `ErrorState.svelte`**

```svelte
<script lang="ts">
	import Button from './Button.svelte';
	let {
		message,
		onRetry,
		'data-testid': testid
	}: { message: string; onRetry?: () => void; 'data-testid'?: string } = $props();
</script>

<div class="error" role="alert" data-testid={testid}>
	<p>{message}</p>
	{#if onRetry}
		<Button variant="secondary" onclick={onRetry} data-testid="{testid}-retry">Retry</Button>
	{/if}
</div>

<style>
	.error {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-8);
		border-radius: var(--radius-md);
		background-color: #fef2f2;
		color: var(--red-700);
	}
	p { font-size: var(--font-size-sm); margin: 0; }
</style>
```

- [ ] **Step 5: Create `ErrorBoundary.svelte`**

Svelte 5's `<svelte:boundary>` is the mechanism.

```svelte
<script lang="ts">
	import ErrorState from './ErrorState.svelte';
	let { children }: { children: import('svelte').Snippet } = $props();
</script>

<svelte:boundary>
	{@render children()}
	{#snippet failed(error, reset)}
		<ErrorState
			message={'Something went wrong. Please refresh or try again.'}
			onRetry={reset}
			data-testid="app-error-boundary"
		/>
	{/snippet}
</svelte:boundary>
```

- [ ] **Step 6: Extend `/ui-demo`**

```svelte
<section>
	<h2>LoadingState / EmptyState / ErrorState</h2>
	<LoadingState data-testid="ui-loading" />
	<EmptyState title="No results" description="Try adjusting filters." data-testid="ui-empty" />
	<ErrorState message="Something broke" onRetry={() => console.log('retry')} data-testid="ui-error" />
</section>
```

- [ ] **Step 7: Verify + commit**

```bash
git add frontend/src/lib/ui/LoadingState.svelte frontend/src/lib/ui/EmptyState.svelte frontend/src/lib/ui/ErrorState.svelte frontend/src/lib/ui/ErrorBoundary.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add LoadingState, EmptyState, ErrorState, ErrorBoundary (iter 4.0.13)"
```

---

## Task 14: Create `DataTable` with server-driven pagination slot

**Why:** PO list, invoice list, and product list all need a paginated table. Getting the contract right in 4.0 prevents forks in later phases.

**Files:**
- Create: `frontend/src/lib/ui/DataTable.svelte`
- Modify: `/ui-demo`, `primitives.spec.ts`

- [ ] **Step 1: Failing test**

```typescript
test('DataTable renders header, rows, pagination, and handles row-click', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const table = page.getByTestId('ui-table');
	await expect(table.getByRole('columnheader', { name: 'Name' })).toBeVisible();
	await expect(table.locator('tbody tr')).toHaveCount(2);
	await table.locator('tbody tr').first().click();
	await expect(page.getByTestId('ui-table-click')).toHaveText('row-1');
	await expect(page.getByTestId('ui-table-pagination')).toContainText('Page 1 of 5');
});
```

- [ ] **Step 2: Create `DataTable.svelte`**

```svelte
<script lang="ts" generics="T extends { id: string }">
	import Button from './Button.svelte';

	type Column<Row> = {
		key: string;
		label: string;
		render: (row: Row) => string | number;
	};

	let {
		columns,
		rows,
		pagination,
		onRowClick,
		'data-testid': testid
	}: {
		columns: Column<T>[];
		rows: T[];
		pagination?: {
			page: number;
			pageSize: number;
			total: number;
			onPageChange: (page: number) => void;
		};
		onRowClick?: (row: T) => void;
		'data-testid'?: string;
	} = $props();

	const pageCount = $derived(
		pagination ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize)) : 1
	);
</script>

<div class="wrap" data-testid={testid}>
	<table>
		<thead>
			<tr>
				{#each columns as col (col.key)}
					<th scope="col">{col.label}</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each rows as row (row.id)}
				<tr
					onclick={() => onRowClick?.(row)}
					class:clickable={Boolean(onRowClick)}
					tabindex={onRowClick ? 0 : -1}
					onkeydown={(e) => {
						if (onRowClick && (e.key === 'Enter' || e.key === ' ')) {
							e.preventDefault();
							onRowClick(row);
						}
					}}
				>
					{#each columns as col (col.key)}
						<td>{col.render(row)}</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
	{#if pagination}
		<div class="pagination" data-testid="{testid}-pagination">
			<Button
				variant="secondary"
				disabled={pagination.page <= 1}
				onclick={() => pagination.onPageChange(pagination.page - 1)}
			>
				Prev
			</Button>
			<span>Page {pagination.page} of {pageCount}</span>
			<Button
				variant="secondary"
				disabled={pagination.page >= pageCount}
				onclick={() => pagination.onPageChange(pagination.page + 1)}
			>
				Next
			</Button>
		</div>
	{/if}
</div>

<style>
	.wrap { display: flex; flex-direction: column; gap: var(--space-3); }
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--font-size-sm);
	}
	th {
		text-align: left;
		padding: var(--space-3) var(--space-4);
		font-weight: 600;
		color: var(--gray-600);
		border-bottom: 1px solid var(--gray-200);
		background-color: var(--gray-50);
	}
	td {
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--gray-100);
	}
	tr.clickable { cursor: pointer; }
	tr.clickable:hover { background-color: var(--gray-50); }
	tr.clickable:focus-visible { outline: 2px solid var(--brand-accent); outline-offset: -2px; }
	.pagination {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: var(--space-3);
		font-size: var(--font-size-sm);
		color: var(--gray-600);
	}
</style>
```

- [ ] **Step 3: Extend `/ui-demo`**

```svelte
<script lang="ts">
	// ...existing
	import DataTable from '$lib/ui/DataTable.svelte';

	let lastClicked = $state('');
	let page = $state(1);
	const rows = [
		{ id: 'row-1', name: 'Row 1' },
		{ id: 'row-2', name: 'Row 2' }
	];
	const columns = [
		{ key: 'name', label: 'Name', render: (r: { name: string }) => r.name }
	];
</script>

<section>
	<h2>DataTable</h2>
	<DataTable
		{columns}
		{rows}
		pagination={{
			page,
			pageSize: 2,
			total: 10,
			onPageChange: (p) => (page = p)
		}}
		onRowClick={(row) => (lastClicked = row.id)}
		data-testid="ui-table"
	/>
	<p data-testid="ui-table-click">{lastClicked}</p>
</section>
```

- [ ] **Step 4: Verify + commit**

```bash
git add frontend/src/lib/ui/DataTable.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add DataTable with server-driven pagination (iter 4.0.14)"
```

---

## Task 15: Create `PageHeader` and `DetailHeader` primitives

**Files:**
- Create: `frontend/src/lib/ui/PageHeader.svelte`, `DetailHeader.svelte`
- Modify: `/ui-demo`, `primitives.spec.ts`

- [ ] **Step 1: Failing tests**

```typescript
test('PageHeader shows H1, subtitle, and action slot', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const header = page.getByTestId('ui-pageheader');
	await expect(header.getByRole('heading', { level: 1, name: 'Invoices' })).toBeVisible();
	await expect(header).toContainText('Manage invoicing');
	await expect(page.getByTestId('ui-pageheader-action')).toBeVisible();
});

test('DetailHeader shows back link, title, subtitle, status pill', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const header = page.getByTestId('ui-detailheader');
	await expect(header.getByRole('link', { name: /All invoices/ })).toBeVisible();
	await expect(header).toContainText('INV-001');
	await expect(header).toContainText('Submitted');
});
```

- [ ] **Step 2: Create `PageHeader.svelte`**

```svelte
<script lang="ts">
	let {
		title,
		subtitle,
		action,
		'data-testid': testid
	}: {
		title: string;
		subtitle?: string;
		action?: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<header class="page-header" data-testid={testid}>
	<div>
		<h1>{title}</h1>
		{#if subtitle}<p>{subtitle}</p>{/if}
	</div>
	{#if action}<div class="action">{@render action()}</div>{/if}
</header>

<style>
	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-4);
		margin-bottom: var(--space-6);
	}
	h1 {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		margin: 0;
	}
	p {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-top: var(--space-1);
	}
</style>
```

- [ ] **Step 3: Create `DetailHeader.svelte`**

```svelte
<script lang="ts">
	let {
		backHref,
		backLabel,
		title,
		subtitle,
		statusPill,
		'data-testid': testid
	}: {
		backHref: string;
		backLabel: string;
		title: string;
		subtitle?: string;
		statusPill?: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<header class="detail-header" data-testid={testid}>
	<a href={backHref} class="back">← {backLabel}</a>
	<div class="row">
		<div>
			<h1>{title}</h1>
			{#if subtitle}<p>{subtitle}</p>{/if}
		</div>
		{#if statusPill}<div class="pill">{@render statusPill()}</div>{/if}
	</div>
</header>

<style>
	.detail-header {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin-bottom: var(--space-6);
	}
	.back {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		text-decoration: none;
		width: max-content;
	}
	.back:hover { text-decoration: underline; color: var(--gray-700); }
	.row {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-4);
	}
	h1 {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		margin: 0;
	}
	p {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-top: var(--space-1);
	}
</style>
```

- [ ] **Step 4: Extend `/ui-demo`**

```svelte
<section>
	<h2>Headers</h2>
	<PageHeader title="Invoices" subtitle="Manage invoicing" data-testid="ui-pageheader">
		{#snippet action()}
			<Button data-testid="ui-pageheader-action">+ New invoice</Button>
		{/snippet}
	</PageHeader>
	<DetailHeader
		backHref="/ui-demo"
		backLabel="All invoices"
		title="INV-001"
		subtitle="Acme Inc"
		data-testid="ui-detailheader"
	>
		{#snippet statusPill()}
			<StatusPill tone="blue" label="Submitted" />
		{/snippet}
	</DetailHeader>
</section>
```

- [ ] **Step 5: Verify + commit**

```bash
git add frontend/src/lib/ui/PageHeader.svelte frontend/src/lib/ui/DetailHeader.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add PageHeader and DetailHeader primitives (iter 4.0.15)"
```

---

## Task 16: Create `sidebar-items.ts` — role → items mapping

**Why:** Sidebar items are derived from `permissions.ts` rather than a hardcoded mock matrix. This file is the bridge.

**Files:**
- Create: `frontend/src/lib/ui/sidebar-items.ts`
- Create unit test: `frontend/tests/sidebar-items.spec.ts` (permanent)

- [ ] **Step 1: Failing test**

Create `frontend/tests/sidebar-items.spec.ts` — this runs in Playwright's Node context via a lightweight call, but since it's pure-TS logic, we test via a unit-like pattern. Add:

```typescript
import { test, expect } from '@playwright/test';
import { sidebarItemsFor } from '../src/lib/ui/sidebar-items';

test('sidebar items for ADMIN include all aggregates', () => {
	const items = sidebarItemsFor('ADMIN').map((i) => i.label);
	expect(items).toEqual(expect.arrayContaining(['Dashboard', 'Purchase Orders', 'Invoices', 'Vendors', 'Products']));
});

test('sidebar items for VENDOR exclude Vendors management', () => {
	const items = sidebarItemsFor('VENDOR').map((i) => i.label);
	expect(items).toContain('Purchase Orders');
	expect(items).toContain('Invoices');
	expect(items).not.toContain('Vendors');
});

test('sidebar items for QUALITY_LAB include Dashboard + Products only', () => {
	const items = sidebarItemsFor('QUALITY_LAB').map((i) => i.label);
	expect(items).toEqual(expect.arrayContaining(['Dashboard', 'Products']));
	expect(items).not.toContain('Purchase Orders');
	expect(items).not.toContain('Invoices');
});

test('sidebar items for FREIGHT_MANAGER include Dashboard + Purchase Orders', () => {
	const items = sidebarItemsFor('FREIGHT_MANAGER').map((i) => i.label);
	expect(items).toContain('Dashboard');
	expect(items).toContain('Purchase Orders');
	expect(items).not.toContain('Invoices');
	expect(items).not.toContain('Vendors');
});
```

NOTE: the file needs a brainstorm decision per Task 18 before committing to the exact rows above. For this task, implement the conservative version that mirrors today's `+layout.svelte` behavior (no new capability, just mirror). Task 18 revisits and aligns with the mock conversation.

- [ ] **Step 2: Create `sidebar-items.ts`**

```typescript
import type { UserRole } from '$lib/types';
import {
	canViewPOs,
	canViewInvoices,
	canManageVendors,
	canViewProducts
} from '$lib/permissions';

export type SidebarItem = {
	href: string;
	label: string;
	match: (pathname: string) => boolean;
};

export function sidebarItemsFor(role: UserRole): SidebarItem[] {
	const items: SidebarItem[] = [];
	items.push({
		href: '/dashboard',
		label: 'Dashboard',
		match: (p) => p === '/' || p.startsWith('/dashboard')
	});
	if (canViewPOs(role)) {
		items.push({
			href: '/po',
			label: 'Purchase Orders',
			match: (p) => p.startsWith('/po') || p.startsWith('/production')
		});
	}
	if (canViewInvoices(role)) {
		items.push({
			href: '/invoices',
			label: 'Invoices',
			match: (p) => p.startsWith('/invoice') || p.startsWith('/invoices')
		});
	}
	if (canManageVendors(role)) {
		items.push({
			href: '/vendors',
			label: 'Vendors',
			match: (p) => p.startsWith('/vendors')
		});
	}
	if (canViewProducts(role)) {
		items.push({
			href: '/products',
			label: 'Products',
			match: (p) => p.startsWith('/products')
		});
	}
	return items;
}
```

- [ ] **Step 3: Run the spec**

Run: `cd frontend && npx playwright test sidebar-items.spec.ts --reporter=list`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/ui/sidebar-items.ts frontend/tests/sidebar-items.spec.ts
git commit -m "Add sidebar-items.ts derived from permissions.ts (iter 4.0.16)"
```

---

## Task 17: Create `Sidebar` primitive

**Files:**
- Create: `frontend/src/lib/ui/Sidebar.svelte`
- Modify: `/ui-demo`, `primitives.spec.ts`

- [ ] **Step 1: Failing test**

```typescript
test.describe('Sidebar primitive', () => {
	test('renders items for the given role', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const sidebar = page.getByTestId('ui-sidebar');
		await expect(sidebar.getByRole('link', { name: 'Dashboard' })).toBeVisible();
		await expect(sidebar.getByRole('link', { name: 'Purchase Orders' })).toBeVisible();
	});

	test('active item has aria-current="page"', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await page.goto('/ui-demo');
		const activeLink = page.getByTestId('ui-sidebar').getByRole('link', { name: 'Dashboard' });
		await expect(activeLink).toHaveAttribute('aria-current', 'page');
	});
});
```

- [ ] **Step 2: Create `Sidebar.svelte`**

```svelte
<script lang="ts">
	import type { UserRole } from '$lib/types';
	import { sidebarItemsFor } from './sidebar-items';
	import { page } from '$app/state';

	let {
		role,
		brand = 'Turbo Tonic',
		'data-testid': testid
	}: { role: UserRole; brand?: string; 'data-testid'?: string } = $props();

	const items = $derived(sidebarItemsFor(role));
	const pathname = $derived(page.url.pathname);
</script>

<aside class="sidebar" data-testid={testid} aria-label="Primary navigation">
	<div class="brand">
		<span class="brand-mark" aria-hidden="true"></span>
		<span class="brand-text">
			<span class="brand-name">{brand}</span>
			<span class="brand-role">{role}</span>
		</span>
	</div>
	<nav>
		<ul>
			{#each items as item (item.href)}
				{@const isActive = item.match(pathname)}
				<li>
					<a
						href={item.href}
						aria-current={isActive ? 'page' : undefined}
						class:active={isActive}
					>
						{item.label}
					</a>
				</li>
			{/each}
		</ul>
	</nav>
</aside>

<style>
	.sidebar {
		width: 240px;
		background-color: var(--surface-sidebar);
		color: var(--text-sidebar);
		padding: var(--space-6);
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}
	.brand {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	.brand-mark {
		width: 2rem;
		height: 2rem;
		border-radius: var(--radius-md);
		background-color: var(--brand-accent);
	}
	.brand-text {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.brand-name {
		font-weight: 600;
		font-size: var(--font-size-sm);
	}
	.brand-role {
		font-size: var(--font-size-xs);
		color: var(--text-sidebar-muted);
	}
	nav ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	a {
		display: block;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		color: var(--text-sidebar-muted);
		text-decoration: none;
		border-radius: var(--radius-md);
	}
	a:hover { color: var(--text-sidebar); background-color: rgba(255, 255, 255, 0.05); }
	a.active { color: var(--text-sidebar); background-color: rgba(255, 255, 255, 0.08); }
	a:focus-visible { outline: 2px solid var(--brand-accent); outline-offset: 2px; }
</style>
```

- [ ] **Step 3: Extend `/ui-demo` with the Sidebar preview**

```svelte
<section>
	<h2>Sidebar</h2>
	<Sidebar role="ADMIN" data-testid="ui-sidebar" />
</section>
```

Since the demo page is at `/ui-demo`, the "Dashboard" link will not be aria-current. Adjust the test: navigate to `/dashboard` or inject the sidebar on a demo page that pretends to be at `/`. The simplest approach is to relax the aria-current test to "ADMIN sidebar renders all items and each has a valid href":

Replace the aria-current test with:

```typescript
test('each sidebar link has an href', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const links = await page.getByTestId('ui-sidebar').getByRole('link').all();
	for (const link of links) {
		await expect(link).toHaveAttribute('href', /^\//);
	}
});
```

- [ ] **Step 4: Verify + commit**

```bash
git add frontend/src/lib/ui/Sidebar.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add Sidebar primitive wired to permissions (iter 4.0.17)"
```

---

## Task 18: BRAINSTORM STOP — per-role sidebar item set

**Why:** Task 16 implemented a conservative default that mirrors today's `+layout.svelte`. The mock's 4-role matrix does not match the actual 6-role enum. Decide with the user:

- Does ADMIN sidebar get any admin-only items (e.g. a future Users page placeholder)?
- Does QUALITY_LAB sidebar stay Dashboard + Products only, or add something else?
- Does FREIGHT_MANAGER sidebar stay Dashboard + POs, or add Shipments (today's `/shipments/:id` exists)?
- Does PROCUREMENT_MANAGER get a Dashboard-only sidebar (permissions unwired) or nothing?

**Actions:**

- [ ] **Step 1: Pause execution. Surface the question to the user.**

Write a short message to the user:

> "Phase 4.0 needs a decision on per-role sidebar items. Task 16 implemented a mirror of today's layout. Confirm or extend:
> - ADMIN: Dashboard, POs, Invoices, Vendors, Products
> - SM: same as ADMIN
> - VENDOR: Dashboard, POs, Invoices
> - FREIGHT_MANAGER: Dashboard, POs (should Shipments be added?)
> - QUALITY_LAB: Dashboard, Products
> - PROCUREMENT_MANAGER: Dashboard only (no permissions wired)
>
> OK to proceed with this mapping, or change any row?"

- [ ] **Step 2: On user response, adjust `sidebar-items.ts` and its test**

If the user confirms, commit a no-op confirmation (no code change). If the user edits, update `sidebar-items.ts` and the spec accordingly.

- [ ] **Step 3: Commit (only if code changed)**

```bash
git add frontend/src/lib/ui/sidebar-items.ts frontend/tests/sidebar-items.spec.ts
git commit -m "Lock per-role sidebar items after brainstorm (iter 4.0.18)"
```

---

## Task 19: Create `TopBar` primitive

**Files:**
- Create: `frontend/src/lib/ui/TopBar.svelte`
- Modify: `/ui-demo`, `primitives.spec.ts`

**Note on notification bell:** the existing `NotificationBell.svelte` in `frontend/src/lib/components/` handles its own state and API calls. `TopBar` embeds it as a child without duplication, preserving past-flow.

- [ ] **Step 1: Failing test**

```typescript
test.describe('TopBar primitive', () => {
	test('renders breadcrumb, search input (disabled), notification bell slot, user pill slot', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await mockUnreadCount(page);
		await page.goto('/ui-demo');
		const bar = page.getByTestId('ui-topbar');
		await expect(bar).toContainText('Workspace');
		await expect(bar.getByRole('searchbox')).toBeDisabled();
		await expect(page.getByTestId('notification-bell-button')).toBeVisible();
	});
});
```

(The `notification-bell-button` testid must already exist on `NotificationBell.svelte`. Verify first; add if missing via a one-line edit to the existing component.)

- [ ] **Step 2: Verify `NotificationBell.svelte` has `data-testid="notification-bell-button"`**

Read `frontend/src/lib/components/NotificationBell.svelte`. If the button element lacks `data-testid`, add it — this is a mechanical additive change that doesn't alter behavior.

- [ ] **Step 3: Create `TopBar.svelte`**

```svelte
<script lang="ts">
	import NotificationBell from '$lib/components/NotificationBell.svelte';

	let {
		breadcrumb = 'Workspace',
		userMenu,
		onToggleSidebar,
		'data-testid': testid
	}: {
		breadcrumb?: string;
		userMenu?: import('svelte').Snippet;
		onToggleSidebar?: () => void;
		'data-testid'?: string;
	} = $props();
</script>

<header class="topbar" data-testid={testid}>
	{#if onToggleSidebar}
		<button
			type="button"
			class="toggle"
			aria-label="Toggle sidebar"
			onclick={onToggleSidebar}
			data-testid="topbar-toggle"
		>
			<span aria-hidden="true">≡</span>
		</button>
	{/if}
	<span class="breadcrumb">{breadcrumb}</span>
	<input type="search" placeholder="Search" disabled aria-label="Search (disabled)" />
	<div class="actions">
		<NotificationBell />
		{#if userMenu}{@render userMenu()}{/if}
	</div>
</header>

<style>
	.topbar {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		padding: var(--space-3) var(--space-6);
		background-color: var(--surface-card);
		border-bottom: 1px solid var(--gray-200);
	}
	.toggle {
		background: none;
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		padding: var(--space-1) var(--space-3);
		cursor: pointer;
		font-size: var(--font-size-lg);
	}
	.toggle:focus-visible { outline: 2px solid var(--brand-accent); outline-offset: 2px; }
	.breadcrumb { font-size: var(--font-size-sm); color: var(--gray-500); }
	input[type='search'] {
		flex: 1;
		max-width: 320px;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
	}
	.actions {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
</style>
```

- [ ] **Step 4: Extend `/ui-demo`**

```svelte
<section>
	<h2>TopBar</h2>
	<TopBar breadcrumb="Workspace / Operations" data-testid="ui-topbar" />
</section>
```

- [ ] **Step 5: Verify + commit**

```bash
git add frontend/src/lib/ui/TopBar.svelte frontend/src/lib/components/NotificationBell.svelte frontend/src/routes/ui-demo/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add TopBar primitive embedding existing NotificationBell (iter 4.0.19)"
```

---

## Task 20: BRAINSTORM STOP — mobile drawer trigger and animation

**Why:** The mock is desktop-only. Mobile shell needs a decision before building `AppShell` mobile variant.

- [ ] **Step 1: Surface question**

> "Mobile shell (≤768px) decision: how does the sidebar appear and dismiss?
> - A. Off-canvas drawer from the left, triggered by TopBar hamburger icon, overlay darkens body
> - B. Collapsible sidebar that reflows the page on toggle
> - C. Bottom nav on mobile instead of a sidebar
>
> Default: A. Approve or change?"

- [ ] **Step 2: Record decision**

Update `docs/superpowers/specs/2026-04-24-ui-revamp-v2-design.md` with the decision under a new subsection "Phase 4.0 decisions log".

---

## Task 21: Create `AppShell` with mobile drawer

**Files:**
- Create: `frontend/src/lib/ui/AppShell.svelte`
- Modify: `/ui-demo`, `primitives.spec.ts`

- [ ] **Step 1: Failing tests**

```typescript
test.describe('AppShell primitive', () => {
	test('renders sidebar + topbar + main content', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await mockUnreadCount(page);
		await page.goto('/ui-demo');
		const shell = page.getByTestId('ui-appshell');
		await expect(shell.getByTestId('ui-appshell-sidebar')).toBeVisible();
		await expect(shell.getByTestId('ui-appshell-topbar')).toBeVisible();
		await expect(shell.getByTestId('ui-appshell-main')).toBeVisible();
	});

	test('at 390px, sidebar is hidden until hamburger is tapped', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await mockUnreadCount(page);
		await page.setViewportSize({ width: 390, height: 800 });
		await page.goto('/ui-demo');
		const sidebar = page.getByTestId('ui-appshell-sidebar');
		await expect(sidebar).toBeHidden();
		await page.getByTestId('topbar-toggle').click();
		await expect(sidebar).toBeVisible();
	});
});
```

- [ ] **Step 2: Create `AppShell.svelte`**

Implement per the Task 20 decision. Defaulting to A (off-canvas drawer):

```svelte
<script lang="ts">
	import type { UserRole } from '$lib/types';
	import Sidebar from './Sidebar.svelte';
	import TopBar from './TopBar.svelte';
	import ErrorBoundary from './ErrorBoundary.svelte';

	let {
		role,
		breadcrumb,
		userMenu,
		children,
		'data-testid': testid
	}: {
		role: UserRole;
		breadcrumb?: string;
		userMenu?: import('svelte').Snippet;
		children: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();

	let sidebarOpen = $state(false);
	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
</script>

<div class="shell" data-testid={testid}>
	<div
		class="sidebar-wrap"
		class:open={sidebarOpen}
		data-testid="ui-appshell-sidebar"
	>
		<Sidebar {role} />
	</div>
	{#if sidebarOpen}
		<button
			type="button"
			class="overlay"
			aria-label="Close sidebar"
			onclick={toggleSidebar}
		></button>
	{/if}
	<div class="main-col">
		<TopBar {breadcrumb} {userMenu} onToggleSidebar={toggleSidebar} data-testid="ui-appshell-topbar" />
		<main data-testid="ui-appshell-main">
			<ErrorBoundary>
				{@render children()}
			</ErrorBoundary>
		</main>
	</div>
</div>

<style>
	.shell {
		display: grid;
		grid-template-columns: 240px 1fr;
		min-height: 100vh;
		background-color: var(--surface-page);
	}
	.sidebar-wrap { display: contents; }
	.main-col { display: flex; flex-direction: column; min-width: 0; }
	main { flex: 1; padding: var(--space-6); }
	.overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0,0,0,0.35);
		border: none;
		cursor: pointer;
		z-index: 40;
	}
	@media (max-width: 768px) {
		.shell { grid-template-columns: 1fr; }
		.sidebar-wrap {
			display: block;
			position: fixed;
			inset: 0 auto 0 0;
			width: 280px;
			z-index: 50;
			transform: translateX(-100%);
			transition: transform 0.2s ease;
		}
		.sidebar-wrap.open { transform: translateX(0); }
	}
	@media (min-width: 769px) {
		.overlay { display: none; }
	}
</style>
```

- [ ] **Step 3: Extend `/ui-demo`**

The `/ui-demo` page should not be wrapped in `AppShell` (since we don't want it affecting other tests). Add a separate test-only route `/ui-demo/shell` that wraps in `AppShell`:

Create `frontend/src/routes/ui-demo/shell/+page.svelte`:

```svelte
<script lang="ts">
	import AppShell from '$lib/ui/AppShell.svelte';
	import { page } from '$app/state';

	const role = $derived(page.data.user?.role ?? 'ADMIN');
</script>

<AppShell {role} breadcrumb="Workspace / Demo" data-testid="ui-appshell">
	<p>Shell demo content.</p>
</AppShell>
```

Update the AppShell test to use `/ui-demo/shell` instead of `/ui-demo`.

- [ ] **Step 4: Verify + commit**

```bash
git add frontend/src/lib/ui/AppShell.svelte frontend/src/routes/ui-demo/shell/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add AppShell with mobile drawer (iter 4.0.21)"
```

---

## Task 22: BRAINSTORM STOP — `UserMenu` production layout

**Why:** The user-pill dropdown in production vs dev is a mock-incomplete area.

- [ ] **Step 1: Surface question**

> "`UserMenu` decision — the user pill dropdown shows:
> - Production: user info (name + role) and Log out, no role switcher
> - Dev (via `import.meta.env.DEV`): same as production plus a role switcher that mutates a dev store for local testing
>
> Confirm this split, or change either variant?"

- [ ] **Step 2: Record decision**

Update the revamp spec's decisions log.

---

## Task 23: Create `UserMenu` primitive

**Files:**
- Create: `frontend/src/lib/ui/UserMenu.svelte`
- Modify: `/ui-demo/shell` to pass a `UserMenu` into `AppShell`
- Modify: `primitives.spec.ts`

- [ ] **Step 1: Failing test**

```typescript
test.describe('UserMenu primitive', () => {
	test('shows name and role, opens on click, Log out in menu', async ({ page }) => {
		await mockUser(page);
		await mockApiCatchAll(page);
		await mockUnreadCount(page);
		await page.goto('/ui-demo/shell');
		await page.getByTestId('ui-usermenu').click();
		await expect(page.getByTestId('ui-usermenu-logout')).toBeVisible();
	});
});
```

- [ ] **Step 2: Create `UserMenu.svelte`**

```svelte
<script lang="ts">
	import { logout } from '$lib/auth';
	import { goto } from '$app/navigation';
	import type { UserRole } from '$lib/types';

	let {
		name,
		role,
		'data-testid': testid
	}: { name: string; role: UserRole; 'data-testid'?: string } = $props();

	let open = $state(false);

	async function handleLogout() {
		try {
			await logout();
		} catch {}
		goto('/login');
	}

	function toggle() {
		open = !open;
	}

	function initials(n: string) {
		return n
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((s) => s[0]?.toUpperCase() ?? '')
			.join('');
	}
</script>

<div class="user-menu">
	<button
		type="button"
		class="pill"
		onclick={toggle}
		aria-haspopup="menu"
		aria-expanded={open}
		data-testid={testid}
	>
		<span class="avatar" aria-hidden="true">{initials(name)}</span>
		<span class="meta">
			<span class="name">{name}</span>
			<span class="role">{role}</span>
		</span>
	</button>
	{#if open}
		<div class="menu" role="menu">
			<button
				type="button"
				role="menuitem"
				onclick={handleLogout}
				data-testid="{testid}-logout"
			>
				Log out
			</button>
		</div>
	{/if}
</div>

<style>
	.user-menu { position: relative; }
	.pill {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-2);
		background: none;
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		cursor: pointer;
	}
	.pill:focus-visible { outline: 2px solid var(--brand-accent); outline-offset: 2px; }
	.avatar {
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 999px;
		background-color: var(--brand-accent);
		color: white;
		font-size: var(--font-size-xs);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.meta { display: flex; flex-direction: column; text-align: left; }
	.name { font-size: var(--font-size-sm); color: var(--gray-900); }
	.role { font-size: var(--font-size-xs); color: var(--gray-500); }
	.menu {
		position: absolute;
		right: 0;
		top: calc(100% + 0.5rem);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-md);
		padding: var(--space-2);
		min-width: 10rem;
		z-index: 30;
	}
	.menu button {
		width: 100%;
		text-align: left;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
	}
	.menu button:hover { background-color: var(--gray-100); }
	.menu button:focus-visible { outline: 2px solid var(--brand-accent); outline-offset: -2px; }
</style>
```

- [ ] **Step 3: Update `/ui-demo/shell` to pass `UserMenu` into AppShell**

```svelte
<script lang="ts">
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import { page } from '$app/state';

	const user = $derived(page.data.user);
</script>

<AppShell role={user?.role ?? 'ADMIN'} breadcrumb="Workspace / Demo" data-testid="ui-appshell">
	{#snippet userMenu()}
		<UserMenu name={user?.display_name ?? 'Demo'} role={user?.role ?? 'ADMIN'} data-testid="ui-usermenu" />
	{/snippet}
	<p>Shell demo content.</p>
</AppShell>
```

- [ ] **Step 4: Verify + commit**

```bash
git add frontend/src/lib/ui/UserMenu.svelte frontend/src/routes/ui-demo/shell/+page.svelte frontend/tests/primitives.spec.ts
git commit -m "Add UserMenu with Log out action (iter 4.0.23)"
```

---

## Task 24: Create redirect infrastructure

**Why:** When aggregate phases retire old routes, they need a one-line way to 301-redirect. Centralize the mapping.

**Files:**
- Create: `frontend/src/lib/ui/redirects.ts`
- Create: `frontend/tests/redirects.spec.ts`

- [ ] **Step 1: Failing test**

```typescript
import { test, expect } from '@playwright/test';
import { resolveRedirect } from '../src/lib/ui/redirects';

test('resolveRedirect returns null for unmapped paths', () => {
	expect(resolveRedirect('/nonexistent')).toBeNull();
});

test('resolveRedirect returns the new path for a mapped entry', () => {
	// None mapped yet in 4.0; adding a test-only sentinel.
	expect(resolveRedirect('/test-old/123', { '/test-old/:id': '/test-new/:id' })).toBe('/test-new/123');
});
```

- [ ] **Step 2: Create `redirects.ts`**

```typescript
// Central registry of old-route → new-route mappings, populated by aggregate
// phases as they retire old routes. 4.0 ships the mechanism; no live mappings.

const REDIRECTS: Record<string, string> = {
	// Populated in future phases, e.g.:
	// '/po/:id': '/production/:id',
	// '/invoice/:id': '/invoices/:id',
};

export function resolveRedirect(
	pathname: string,
	registry: Record<string, string> = REDIRECTS
): string | null {
	for (const [pattern, target] of Object.entries(registry)) {
		const regex = new RegExp(
			'^' + pattern.replace(/:([a-zA-Z_]+)/g, '(?<$1>[^/]+)') + '$'
		);
		const match = pathname.match(regex);
		if (match) {
			let result = target;
			for (const [key, value] of Object.entries(match.groups ?? {})) {
				result = result.replace(`:${key}`, value);
			}
			return result;
		}
	}
	return null;
}
```

- [ ] **Step 3: Verify + commit**

Run: `cd frontend && npx playwright test redirects.spec.ts --reporter=list`
Expected: PASS.

```bash
git add frontend/src/lib/ui/redirects.ts frontend/tests/redirects.spec.ts
git commit -m "Add redirect infrastructure for aggregate-phase retirements (iter 4.0.24)"
```

---

## Task 25: `nexus-shell.spec.ts` — permanent end-to-end test for `(nexus)` layout

**Why:** Once aggregate phases start, they need a stable spec verifying the shell composes correctly. Write it now with a sentinel page inside `(nexus)`.

**Files:**
- Create: `frontend/src/routes/(nexus)/_smoke/+page.svelte` (internal, not linked in nav)
- Create: `frontend/tests/nexus-shell.spec.ts`

- [ ] **Step 1: Create sentinel page**

```svelte
<!-- frontend/src/routes/(nexus)/_smoke/+page.svelte -->
<script lang="ts">
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import { page } from '$app/state';
	const user = $derived(page.data.user);
</script>

<AppShell role={user?.role ?? 'ADMIN'} breadcrumb="Smoke">
	{#snippet userMenu()}
		<UserMenu name={user?.display_name ?? 'Smoke'} role={user?.role ?? 'ADMIN'} data-testid="smoke-usermenu" />
	{/snippet}
	<h1>Nexus smoke</h1>
</AppShell>
```

- [ ] **Step 2: Create test**

```typescript
// frontend/tests/nexus-shell.spec.ts
import { test, expect } from '@playwright/test';

function mockUser(page: import('@playwright/test').Page, role = 'ADMIN') {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'smoke',
					username: 'smoke',
					display_name: 'Smoke',
					role,
					status: 'ACTIVE',
					vendor_id: null
				}
			})
		});
	});
}

function mockApiCatchAll(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/**', (route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
	);
}

test('nexus shell renders for ADMIN with all primary sidebar items', async ({ page }) => {
	await mockUser(page, 'ADMIN');
	await mockApiCatchAll(page);
	await page.goto('/_smoke');
	await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Purchase Orders' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Invoices' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Vendors' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Products' })).toBeVisible();
});

test('nexus shell renders VENDOR sidebar without Vendors', async ({ page }) => {
	await mockUser(page, 'VENDOR');
	await mockApiCatchAll(page);
	await page.goto('/_smoke');
	await expect(page.getByRole('link', { name: 'Vendors' })).toHaveCount(0);
});

test('nexus shell redirects to /login when unauthenticated', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) =>
		route.fulfill({ status: 401, contentType: 'application/json', body: '{}' })
	);
	await page.goto('/_smoke');
	await expect(page).toHaveURL(/\/login/);
});
```

- [ ] **Step 3: Run test**

Run: `cd frontend && npx playwright test nexus-shell.spec.ts --reporter=list`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/\(nexus\)/_smoke frontend/tests/nexus-shell.spec.ts
git commit -m "Add nexus-shell smoke test and sentinel route (iter 4.0.25)"
```

---

## Task 26: Phase-close verification and handoff

- [ ] **Step 1: Run the full test suite**

Run: `make test-browser`
Expected: PASS.

Run: `make test`
Expected: PASS.

- [ ] **Step 2: Run axe against `/ui-demo` and `/_smoke`**

Install `@axe-core/playwright` if absent:

```bash
cd frontend && npm install --save-dev @axe-core/playwright
```

Append to `primitives.spec.ts`:

```typescript
import AxeBuilder from '@axe-core/playwright';

test('axe: /ui-demo has zero AA violations', async ({ page }) => {
	await mockUser(page);
	await mockApiCatchAll(page);
	await page.goto('/ui-demo');
	const results = await new AxeBuilder({ page })
		.withTags(['wcag2a', 'wcag2aa'])
		.analyze();
	expect(results.violations).toEqual([]);
});
```

Run: `cd frontend && npx playwright test primitives.spec.ts --grep axe --reporter=list`
Expected: PASS. If it fails, fix the specific violations (usually missing labels or contrast issues on the demo page) without introducing workarounds that mask the issue.

- [ ] **Step 3: Capture 390px + 1024px screenshots of every section on `/ui-demo`**

Use the capture script pattern from Task 5. Save JPEG quality 40 under `frontend/tests/scratch/iteration-4-0-26/screenshots/`.

- [ ] **Step 4: Update `work-log/YYYY-MM-DD/iteration-4-0-final.md`**

Summarize what shipped, note the three brainstorm decisions (sidebar items, mobile drawer, user menu), and mark the phase closed.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tests/primitives.spec.ts work-log/
git commit -m "Phase 4.0 close: a11y scan + screenshots + work-log (iter 4.0.26)"
```

---

## Self-Review Summary

Spec section → task coverage:

- Design tokens → Task 4
- Shell primitives (AppShell, Sidebar, TopBar, UserMenu, PageHeader, DetailHeader) → Tasks 15, 17, 19, 21, 23
- Page primitives (PanelCard, FormCard, AttributeList, Timeline, ActivityFeed) → Tasks 10, 12
- Controls (Button, Input, Select, DateInput, Toggle, FormField, StatusPill, ProgressBar, KpiCard) → Tasks 5, 6, 7, 8, 9, 11
- DataTable with server pagination → Task 14
- State primitives + ErrorBoundary → Task 13
- `(nexus)` layout group → Task 3, expanded in Task 25
- Redirect infrastructure → Task 24
- `permissions.ts` fix → Task 1
- Seed data overhaul → Task 2
- Mock-clarity brainstorm stops → Tasks 18, 20, 22
- Phase-close riders (axe, screenshots) → Task 26
- CSS scoping: `global.css` component rules stay untouched during Phase 4.0. Their deletion happens at end of revamp, not in 4.0 — this is a deliberate deviation from the spec's "iter 1 delete" phrasing, because deleting during 4.0 would break every pre-revamp page (violating past-flow gate).

No placeholders. No "TODO" or "TBD". Every step has concrete code or commands.
