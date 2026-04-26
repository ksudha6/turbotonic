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
	activity: []
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
	summary: typeof FULL_SUMMARY | typeof EMPTY_SUMMARY
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
