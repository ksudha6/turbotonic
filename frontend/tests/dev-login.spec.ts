import { test, expect } from '@playwright/test';

const SEEDED_DEV_USERS = [
	{ username: 'alice', display_name: 'Alice Admin', role: 'ADMIN' },
	{ username: 'bob', display_name: 'Bob Procurement', role: 'PROCUREMENT_MANAGER' },
	{ username: 'carol', display_name: 'Carol Vendor', role: 'VENDOR' },
	{ username: 'dave', display_name: 'Dave Lab', role: 'QUALITY_LAB' },
	{ username: 'erin', display_name: 'Erin SM', role: 'SM' },
	{ username: 'frank', display_name: 'Frank FM', role: 'FREIGHT_MANAGER' }
];

const CAROL_USER = {
	id: 'carol-id',
	username: 'carol',
	display_name: 'Carol Vendor',
	role: 'VENDOR' as const,
	status: 'ACTIVE' as const,
	vendor_id: 'vendor-1'
};

const EMPTY_DASHBOARD_SUMMARY = {
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

async function mockUnauthenticated(page: import('@playwright/test').Page) {
	await page.route('**/api/v1/auth/me', (route) =>
		route.fulfill({
			status: 401,
			contentType: 'application/json',
			body: JSON.stringify({ detail: 'Not authenticated' })
		})
	);
}

async function mockDevUsers(
	page: import('@playwright/test').Page,
	users: typeof SEEDED_DEV_USERS
) {
	await page.route('**/api/v1/auth/dev-users', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(users)
		})
	);
}

async function mockDevUsersDisabled(page: import('@playwright/test').Page) {
	await page.route('**/api/v1/auth/dev-users', (route) =>
		route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not Found' }) })
	);
}

async function mockPostDashboardLoad(page: import('@playwright/test').Page) {
	// After dev-login, the redirect target loads /api/v1/auth/me again (now
	// authenticated as carol) plus the dashboard endpoints. Stub them so the
	// nav and dashboard render without hitting the real backend.
	await page.route('**/api/v1/auth/me', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: CAROL_USER })
		})
	);
	await page.route('**/api/v1/activity/**', (route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
	);
	await page.route('**/api/v1/activity/unread-count', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ count: 0 })
		})
	);
	await page.route('**/api/v1/dashboard/summary', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(EMPTY_DASHBOARD_SUMMARY)
		})
	);
	await page.route('**/api/v1/dashboard/', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				po_summary: [],
				vendor_summary: { active: 0, inactive: 0 },
				recent_pos: [],
				invoice_summary: [],
				production_summary: [],
				overdue_pos: []
			})
		})
	);
}

test('quick-login row hidden when dev-users endpoint returns 404', async ({ page }) => {
	await mockUnauthenticated(page);
	await mockDevUsersDisabled(page);

	await page.goto('/login');

	// Existing passkey form is unaffected.
	await expect(page.getByRole('heading', { name: 'Vendor Portal' })).toBeVisible();
	await expect(page.getByLabel('Username')).toBeVisible();
	// Quick-login row never renders.
	await expect(page.getByTestId('dev-login-row')).toHaveCount(0);
});

test('quick-login row renders one button per user when dev-users returns a list', async ({
	page
}) => {
	await mockUnauthenticated(page);
	await mockDevUsers(page, SEEDED_DEV_USERS);

	await page.goto('/login');

	const row = page.getByTestId('dev-login-row');
	await expect(row).toBeVisible();
	for (const user of SEEDED_DEV_USERS) {
		await expect(page.getByTestId(`dev-login-${user.username}`)).toBeVisible();
	}
});

test('clicking a quick-login button creates a session and redirects to dashboard', async ({
	page
}) => {
	await mockUnauthenticated(page);
	await mockDevUsers(page, SEEDED_DEV_USERS);

	let devLoginPayload: { username?: string } | null = null;
	await page.route('**/api/v1/auth/dev-login', async (route) => {
		const body = route.request().postDataJSON() as { username?: string } | null;
		devLoginPayload = body;
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: CAROL_USER })
		});
	});

	await page.goto('/login');
	await expect(page.getByTestId('dev-login-carol')).toBeVisible();
	await mockPostDashboardLoad(page);
	await Promise.all([
		page.waitForURL(/\/dashboard/),
		page.getByTestId('dev-login-carol').click()
	]);

	expect(devLoginPayload).toEqual({ username: 'carol' });
});

test('quick-login honors the redirect query param', async ({ page }) => {
	// Catch-all is registered first so per-path routes (dev-users, dev-login,
	// auth/me) take LIFO priority and the broader catch-all just absorbs
	// everything else the /po/123 route load fans out to.
	await page.route('**/api/v1/**', (route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
	);
	await mockUnauthenticated(page);
	await mockDevUsers(page, SEEDED_DEV_USERS);

	await page.route('**/api/v1/auth/dev-login', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: CAROL_USER })
		})
	);

	await page.goto('/login?redirect=%2Fpo%2F123');
	await expect(page.getByTestId('dev-login-carol')).toBeVisible();
	// After dev-login, /po/123 will fetch /auth/me; reroute to authenticated.
	await page.route('**/api/v1/auth/me', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: CAROL_USER })
		})
	);
	await Promise.all([
		page.waitForURL(/\/po\/123/),
		page.getByTestId('dev-login-carol').click()
	]);
});
