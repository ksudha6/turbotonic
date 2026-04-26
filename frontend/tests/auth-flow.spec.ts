import { test, expect } from '@playwright/test';

const MOCK_USER = {
	id: 'test-user-id',
	username: 'test-sm',
	display_name: 'Test User',
	role: 'SM' as const,
	status: 'ACTIVE' as const,
	vendor_id: null
};

const EMPTY_DASHBOARD = {
	po_summary: [],
	vendor_summary: { active: 0, inactive: 0 },
	recent_pos: [],
	invoice_summary: [],
	production_summary: [],
	overdue_pos: []
};

// Registers the activity routes needed for authenticated pages that render the nav.
// Catch-all first (lower LIFO priority) so unread-count takes priority.
async function mockActivityRoutes(page: import('@playwright/test').Page) {
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
}

async function mockDashboard(page: import('@playwright/test').Page) {
	await page.route('**/api/v1/dashboard/', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_DASHBOARD) });
	});
	await page.route('**/api/v1/dashboard/summary', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
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
			})
		});
	});
}

// ---------------------------------------------------------------------------
// Unauthenticated redirect tests
// ---------------------------------------------------------------------------

test('visiting /dashboard without session redirects to /login', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) });
	});
	await page.goto('/dashboard');
	await expect(page).toHaveURL(/\/login/);
});

test('visiting /po without session redirects to /login', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) });
	});
	await page.goto('/po');
	await expect(page).toHaveURL(/\/login/);
});

// ---------------------------------------------------------------------------
// No redirect loop
// ---------------------------------------------------------------------------

test('visiting /login does not redirect when unauthenticated', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) });
	});
	await page.goto('/login');
	await expect(page).toHaveURL(/\/login/);
	await expect(page.getByRole('heading', { name: 'Vendor Portal' })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Register page without username param
// ---------------------------------------------------------------------------

test('visiting /register without username shows invalid invite link', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) });
	});
	await page.goto('/register');
	await expect(page.getByText('Invalid invite link.')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Setup page redirects when authenticated and ACTIVE
// ---------------------------------------------------------------------------

test('visiting /setup while authenticated and ACTIVE redirects to /dashboard', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: MOCK_USER }) });
	});
	await mockActivityRoutes(page);
	await mockDashboard(page);
	await page.goto('/setup');
	await expect(page).toHaveURL(/\/dashboard/);
});

// ---------------------------------------------------------------------------
// Setup page shows pending message when PENDING
// ---------------------------------------------------------------------------

test('visiting /setup while authenticated and PENDING shows pending message', async ({ page }) => {
	const pendingUser = { ...MOCK_USER, status: 'PENDING' };
	// Register catch-all first (lower LIFO priority), then specific route after (higher priority).
	await page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) });
	});
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: pendingUser }) });
	});
	await page.goto('/setup');
	await expect(page).toHaveURL(/\/setup/);
	await expect(page.locator('body')).toContainText('pending approval');
});

// ---------------------------------------------------------------------------
// Deep link preservation
// ---------------------------------------------------------------------------

test('unauthenticated access to /po/123 redirects to /login with redirect param', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) });
	});
	await page.goto('/po/123');
	await expect(page).toHaveURL(/\/login\?redirect=/);
	const url = new URL(page.url());
	const redirect = url.searchParams.get('redirect');
	expect(redirect).toBe('/po/123');
});

// ---------------------------------------------------------------------------
// Logout redirects to /login
// ---------------------------------------------------------------------------

test('logout button redirects to /login', async ({ page }) => {
	// auth/me returns authenticated until logout fires, then 401.
	let loggedOut = false;
	await page.route('**/api/v1/auth/me', (route) => {
		if (loggedOut) {
			route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) });
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: MOCK_USER }) });
		}
	});
	await mockActivityRoutes(page);
	await mockDashboard(page);
	await page.route('**/api/v1/auth/logout', (route) => {
		loggedOut = true;
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ detail: 'Logged out' }) });
	});

	await page.goto('/dashboard');
	// AppShell UserMenu hides Log out behind a click on the user pill.
	await page.getByRole('button', { expanded: false }).filter({ hasText: 'Test User' }).click();
	await page.getByRole('menuitem', { name: 'Log out' }).click();
	await expect(page).toHaveURL(/\/login/);
});

// ---------------------------------------------------------------------------
// Nav shows user display name when authenticated
// ---------------------------------------------------------------------------

test('nav shows user display name when authenticated', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: MOCK_USER }) });
	});
	await mockActivityRoutes(page);
	await mockDashboard(page);

	await page.goto('/dashboard');
	// New AppShell UserMenu: display name visible directly in the pill,
	// Log out lives in the dropdown that opens on click.
	await expect(page.getByText('Test User')).toBeVisible();
	await page.getByRole('button', { expanded: false }).filter({ hasText: 'Test User' }).click();
	await expect(page.getByRole('menuitem', { name: 'Log out' })).toBeVisible();
});
