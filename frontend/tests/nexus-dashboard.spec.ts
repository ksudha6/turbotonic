import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Module-level constants
// ---------------------------------------------------------------------------

const ADMIN_USER = {
	id: 'user-admin',
	username: 'admin',
	display_name: 'Admin User',
	role: 'ADMIN',
	status: 'ACTIVE',
	vendor_id: null
};

const SM_USER = {
	id: 'user-sm',
	username: 'sm',
	display_name: 'SM User',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null
};

const VENDOR_USER = {
	id: 'user-vendor',
	username: 'vendor',
	display_name: 'Vendor User',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-1'
};

const FM_USER = {
	id: 'user-fm',
	username: 'fm',
	display_name: 'Freight Manager',
	role: 'FREIGHT_MANAGER',
	status: 'ACTIVE',
	vendor_id: null
};

const FULL_SUMMARY = {
	kpis: {
		pending_pos: 4,
		pending_pos_value_usd: '52000.00',
		awaiting_acceptance: 2,
		awaiting_acceptance_value_usd: '12500.00',
		in_production: 3,
		in_production_value_usd: '38000.00',
		outstanding_ap_usd: '12500.00'
	},
	awaiting_acceptance: [
		{
			id: 'po-1',
			po_number: 'PO-2026-001',
			vendor_name: 'Acme Corp',
			total_value_usd: '5000.00'
		},
		{
			id: 'po-2',
			po_number: 'PO-2026-002',
			vendor_name: 'Beta Supplies',
			total_value_usd: '7500.00'
		}
	],
	activity: [
		{
			id: 'act-1',
			entity_type: 'PO',
			entity_id: 'po-9',
			event: 'PO_SUBMITTED',
			detail: null,
			category: 'ACTION_REQUIRED',
			created_at: new Date(Date.now() - 3600000).toISOString()
		},
		{
			id: 'act-2',
			entity_type: 'INVOICE',
			entity_id: 'inv-3',
			event: 'INVOICE_APPROVED',
			detail: null,
			category: 'LIVE',
			created_at: new Date(Date.now() - 7200000).toISOString()
		}
	],
	fm_kpis: null,
	fm_ready_batches: [],
	fm_pending_invoices: []
};

const FM_SUMMARY = {
	kpis: {
		pending_pos: 0,
		pending_pos_value_usd: '0.00',
		awaiting_acceptance: 0,
		awaiting_acceptance_value_usd: '0.00',
		in_production: 0,
		in_production_value_usd: '0.00',
		outstanding_ap_usd: '0.00'
	},
	awaiting_acceptance: [],
	activity: [],
	fm_kpis: {
		ready_batches: 2,
		shipments_in_flight: 5,
		pending_invoices: 3,
		pending_invoices_value_usd: '8400.00',
		docs_missing: 7
	},
	fm_ready_batches: [
		{
			po_id: 'po-r1',
			po_number: 'PO-2026-300',
			vendor_name: 'Shenzhen Precision Works',
			accepted_qty: 100,
			shipped_qty: 0
		}
	],
	fm_pending_invoices: [
		{
			id: 'inv-fm-1',
			invoice_number: 'INV-2026-FM-001',
			vendor_name: 'Hamburg Freight Lines',
			vendor_type: 'FREIGHT',
			subtotal_usd: '2500.00',
			submitted_at: new Date(Date.now() - 3600000).toISOString()
		}
	]
};

const EMPTY_SUMMARY = {
	kpis: {
		pending_pos: 0,
		pending_pos_value_usd: '0.00',
		awaiting_acceptance: 0,
		awaiting_acceptance_value_usd: '0.00',
		in_production: 0,
		in_production_value_usd: '0.00',
		outstanding_ap_usd: '0.00'
	},
	awaiting_acceptance: [],
	activity: [],
	fm_kpis: null,
	fm_ready_batches: [],
	fm_pending_invoices: []
};

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

function mockUser(page: import('@playwright/test').Page, user: typeof ADMIN_USER) {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user })
		});
	});
}

function mockUnreadCount(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ count: 0 })
		});
	});
}

function mockDashboardSummary(
	page: import('@playwright/test').Page,
	summary: typeof FULL_SUMMARY | typeof EMPTY_SUMMARY | typeof FM_SUMMARY
) {
	return page.route('**/api/v1/dashboard/summary', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(summary)
		});
	});
}

// Catch-all for any remaining API calls (e.g. sidebar data, ref-data).
function mockApiCatchAll(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test('ADMIN sees the four KPI cards with correct values', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, ADMIN_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, FULL_SUMMARY);

	await page.goto('/dashboard');
	await expect(page.getByTestId('ui-dashboard-kpis')).toBeVisible();

	await expect(page.getByTestId('kpi-pending-pos')).toContainText('4');
	await expect(page.getByTestId('kpi-awaiting')).toContainText('2');
	await expect(page.getByTestId('kpi-in-production')).toContainText('3');
	await expect(page.getByTestId('kpi-outstanding-ap')).toContainText('$12,500');

	// USD value chip on each PO-derived KPI card
	await expect(page.getByTestId('kpi-pending-pos')).toContainText('$52,000');
	await expect(page.getByTestId('kpi-awaiting')).toContainText('$12,500');
	await expect(page.getByTestId('kpi-in-production')).toContainText('$38,000');
});

test('Activity row links to PO detail with permission', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, ADMIN_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, FULL_SUMMARY);

	await page.goto('/dashboard');
	const activityPanel = page.getByTestId('panel-activity');
	await expect(activityPanel).toBeVisible();

	const poRow = page.getByTestId('activity-row-act-1');
	await expect(poRow).toHaveAttribute('href', '/po/po-9');

	const invoiceRow = page.getByTestId('activity-row-act-2');
	await expect(invoiceRow).toHaveAttribute('href', '/invoice/inv-3');
});

test('SM sees the same full layout', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, SM_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, FULL_SUMMARY);

	await page.goto('/dashboard');
	await expect(page.getByTestId('ui-dashboard-kpis')).toBeVisible();

	const awaitingPanel = page.getByTestId('panel-awaiting');
	await expect(awaitingPanel).toContainText('PO-2026-001');
});

test('Awaiting-acceptance row click navigates to PO detail', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, ADMIN_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, FULL_SUMMARY);

	await page.goto('/dashboard');
	await expect(page.getByTestId('panel-awaiting')).toBeVisible();

	// Click the first row (po-1)
	const firstRow = page.getByTestId('panel-awaiting').getByRole('button').first();
	await firstRow.click();

	await expect(page).toHaveURL(/\/po\/po-1/);
});

test('VENDOR sees the placeholder panel, not the KPI grid', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, VENDOR_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, EMPTY_SUMMARY);

	await page.goto('/dashboard');

	// KPI grid must not be present
	await expect(page.getByTestId('ui-dashboard-kpis')).toHaveCount(0);

	// Placeholder panel must be present with the correct text
	const placeholder = page.getByTestId('panel-placeholder');
	await expect(placeholder).toBeVisible();
	await expect(placeholder).toContainText('coming in a later iteration');
});

test('Empty awaiting list renders EmptyState', async ({ page }) => {
	const summaryWithEmptyAwaiting = {
		...FULL_SUMMARY,
		awaiting_acceptance: []
	};

	await mockApiCatchAll(page);
	await mockUser(page, ADMIN_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, summaryWithEmptyAwaiting);

	await page.goto('/dashboard');
	const awaitingPanel = page.getByTestId('panel-awaiting');
	await expect(awaitingPanel).toContainText('No POs awaiting acceptance');
});

test('Empty activity list renders EmptyState', async ({ page }) => {
	const summaryWithEmptyActivity = {
		...FULL_SUMMARY,
		activity: []
	};

	await mockApiCatchAll(page);
	await mockUser(page, ADMIN_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, summaryWithEmptyActivity);

	await page.goto('/dashboard');
	const activityPanel = page.getByTestId('panel-activity');
	await expect(activityPanel).toContainText('No recent activity');
});

test('FREIGHT_MANAGER sees shipment + invoice KPIs', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, FM_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, FM_SUMMARY);

	await page.goto('/dashboard');
	await expect(page.getByTestId('ui-dashboard-kpis')).toBeVisible();

	await expect(page.getByTestId('kpi-ready-batches')).toContainText('2');
	await expect(page.getByTestId('kpi-shipments-in-flight')).toContainText('5');
	await expect(page.getByTestId('kpi-pending-invoices')).toContainText('3');
	await expect(page.getByTestId('kpi-pending-invoices')).toContainText('$8,400');
	await expect(page.getByTestId('kpi-docs-missing')).toContainText('7');
});

test('FREIGHT_MANAGER ready batch click navigates to PO detail', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, FM_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, FM_SUMMARY);

	await page.goto('/dashboard');
	const readyPanel = page.getByTestId('panel-ready-batches');
	await expect(readyPanel).toContainText('PO-2026-300');

	await readyPanel.getByRole('button').first().click();
	await expect(page).toHaveURL(/\/po\/po-r1/);
});

test('FREIGHT_MANAGER pending invoice click navigates to invoice detail', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, FM_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, FM_SUMMARY);

	await page.goto('/dashboard');
	const invPanel = page.getByTestId('panel-pending-invoices');
	await expect(invPanel).toContainText('INV-2026-FM-001');
	await expect(invPanel).toContainText('FREIGHT');

	await invPanel.getByRole('button').first().click();
	await expect(page).toHaveURL(/\/invoice\/inv-fm-1/);
});

test('PROCUREMENT_MANAGER sees the full KPI grid', async ({ page }) => {
	const PM_USER = {
		id: 'user-pm',
		username: 'pm',
		display_name: 'Procurement Manager',
		role: 'PROCUREMENT_MANAGER',
		status: 'ACTIVE',
		vendor_id: null
	};

	const pmSummary = {
		...FULL_SUMMARY,
		awaiting_acceptance: FULL_SUMMARY.awaiting_acceptance.map((item) => ({
			...item,
			submitted_at: new Date(Date.now() - 3600000).toISOString()
		}))
	};

	await mockApiCatchAll(page);
	await mockUser(page, PM_USER);
	await mockUnreadCount(page);
	await mockDashboardSummary(page, pmSummary);

	await page.goto('/dashboard');

	await expect(page.getByTestId('kpi-pending-pos')).toBeVisible();
	await expect(page.getByTestId('kpi-awaiting')).toBeVisible();
	await expect(page.getByTestId('kpi-in-production')).toBeVisible();
	await expect(page.getByTestId('kpi-outstanding-ap')).toBeVisible();

	await expect(page.getByTestId('panel-placeholder')).toHaveCount(0);
});
