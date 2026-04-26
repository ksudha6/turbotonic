import { test, expect } from '@playwright/test';

// Use a stable past date for relative time assertions.
const THIRTY_DAYS_AGO = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

const MOCK_ENTRY: import('../src/lib/types').ActivityLogEntry = {
	id: 'act-1',
	entity_type: 'PO',
	entity_id: 'po-1',
	event: 'PO_SUBMITTED',
	category: 'LIVE',
	target_role: null,
	detail: null,
	read_at: null,
	created_at: THIRTY_DAYS_AGO
};

// All tests navigate to dashboard as a page that reliably renders the layout nav.
// The dashboard API is mocked to return minimal data so the page loads without errors.
const EMPTY_DASHBOARD = {
	po_summary: [], vendor_summary: { active: 0, inactive: 0 },
	recent_pos: [], invoice_summary: [], production_summary: [], overdue_pos: []
};

const EMPTY_DASHBOARD_SUMMARY = {
	kpis: { pending_pos: 0, awaiting_acceptance: 0, in_production: 0, outstanding_ap_usd: '0.00' },
	awaiting_acceptance: [],
	activity: []
};

// Registers activity mocks with correct LIFO ordering:
// catch-all first (lower priority) so unread-count (registered after) takes priority.
// The bell component calls /unread-count on mount and /activity/?limit=10 on click.
async function mockActivityRoutes(
	page: import('@playwright/test').Page,
	unreadCount: number,
	listEntries: object[]
) {
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(listEntries) });
	});
	await page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: unreadCount }) });
	});
}

test.beforeEach(async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 'test-user-id', username: 'test-sm', display_name: 'Test User', role: 'SM', status: 'ACTIVE', vendor_id: null } }) });
	});
	// Summary mock (registered first so dashboard/ catch-all that follows wins LIFO for the
	// pre-revamp shape, but the more-specific summary route here doesn't conflict).
	await page.route('**/api/v1/dashboard/summary', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_DASHBOARD_SUMMARY) });
	});
	await page.route('**/api/v1/dashboard/', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_DASHBOARD) });
	});
});

test('badge shows unread count when count is greater than zero', async ({ page }) => {
	await mockActivityRoutes(page, 5, []);

	await page.goto('/dashboard');
	const badge = page.locator('.badge');
	await expect(badge).toBeVisible();
	await expect(badge).toContainText('5');
});

test('badge is hidden when unread count is zero', async ({ page }) => {
	await mockActivityRoutes(page, 0, []);

	await page.goto('/dashboard');
	await expect(page.locator('.badge')).toHaveCount(0);
});

test('clicking bell opens dropdown with entries', async ({ page }) => {
	await mockActivityRoutes(page, 1, [MOCK_ENTRY]);

	await page.goto('/dashboard');
	await page.locator('.bell-btn').click();

	const dropdown = page.locator('.dropdown');
	await expect(dropdown).toBeVisible();
	await expect(dropdown.locator('.item-label')).toContainText('PO submitted');
	await expect(dropdown.locator('.item-time')).toContainText('d ago');
});

test('empty dropdown shows no recent notifications message', async ({ page }) => {
	await mockActivityRoutes(page, 0, []);

	await page.goto('/dashboard');
	await page.locator('.bell-btn').click();

	const dropdown = page.locator('.dropdown');
	await expect(dropdown).toBeVisible();
	await expect(dropdown.locator('.empty')).toContainText('No recent notifications.');
});

test('mark all read button calls mark-read API', async ({ page }) => {
	await mockActivityRoutes(page, 2, [MOCK_ENTRY]);

	let markReadCalled = false;
	// Registered after mockActivityRoutes; LIFO gives this priority over the catch-all.
	await page.route('**/api/v1/activity/mark-read', (route) => {
		markReadCalled = true;
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ marked: 1 }) });
	});

	await page.goto('/dashboard');
	await page.locator('.bell-btn').click();
	await expect(page.locator('.dropdown')).toBeVisible();

	await page.locator('.mark-read-btn').click();

	expect(markReadCalled).toBe(true);
	// Dropdown closes after marking read.
	await expect(page.locator('.dropdown')).toHaveCount(0);
	// Badge disappears since unread count is now 0.
	await expect(page.locator('.badge')).toHaveCount(0);
});
