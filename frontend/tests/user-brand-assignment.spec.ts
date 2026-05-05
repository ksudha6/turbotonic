import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

// Iter 111 — Brand assignment in UserInviteModal and UserEditModal.
// Covers: brand checklist visibility by role, brand selection in invite,
// edit modal pre-population, and brand_ids in PATCH body.

type UserFixture = {
	id: string;
	username: string;
	display_name: string;
	role: string;
	status: string;
	vendor_id: string | null;
	email: string | null;
	brand_ids?: string[];
};

const ADMIN_USER: UserFixture = {
	id: 'admin-id',
	username: 'alice',
	display_name: 'Alice Admin',
	role: 'ADMIN',
	status: 'ACTIVE',
	vendor_id: null,
	email: null,
	brand_ids: []
};

const SM_USER: UserFixture = {
	id: 'sm-1',
	username: 'erin',
	display_name: 'Erin SM',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null,
	email: null,
	brand_ids: ['brand-a']
};

const SM_UNSCOPED: UserFixture = {
	id: 'sm-2',
	username: 'gary',
	display_name: 'Gary SM',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null,
	email: null,
	brand_ids: []
};

const VENDOR_USER: UserFixture = {
	id: 'vendor-1',
	username: 'vic',
	display_name: 'Vic Vendor',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'v-1',
	email: null,
	brand_ids: []
};

const BRAND_A = { id: 'brand-a', name: 'Brand Alpha', status: 'ACTIVE' };
const BRAND_B = { id: 'brand-b', name: 'Brand Beta', status: 'ACTIVE' };
const ALL_BRANDS = [BRAND_A, BRAND_B];

const ACTIVE_VENDOR_ROW = {
	id: 'v-1',
	name: 'Acme Corp',
	country: 'CN',
	status: 'ACTIVE',
	vendor_type: 'PROCUREMENT',
	address: '',
	account_details: ''
};

async function setupUsersPage(page: Page, users: UserFixture[]) {
	// Catch-all first; specific routes (registered later) win via LIFO priority.
	await page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: ADMIN_USER })
		});
	});

	await page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});

	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	// Brands list for the multi-select in the modals.
	await page.route(/\/api\/v1\/brands\/\?/, (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(ALL_BRANDS)
		});
	});

	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([ACTIVE_VENDOR_ROW])
		});
	});

	// PATCH by-id (registered before more-specific /invite path).
	await page.route(/\/api\/v1\/users\/[^/]+$/, (route) => {
		if (route.request().method() === 'PATCH') {
			const id = new URL(route.request().url()).pathname.split('/').slice(-1)[0];
			const target = users.find((u) => u.id === id);
			if (!target) {
				route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
				return;
			}
			const body = route.request().postDataJSON() as {
				display_name?: string;
				brand_ids?: string[];
			};
			const updated = {
				...target,
				display_name: body.display_name ?? target.display_name,
				brand_ids: 'brand_ids' in body ? (body.brand_ids ?? []) : (target.brand_ids ?? [])
			};
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ user: updated })
			});
			return;
		}
		// GET by-id
		const id = new URL(route.request().url()).pathname.split('/').slice(-1)[0];
		const target = users.find((u) => u.id === id);
		if (!target) {
			route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
			return;
		}
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: target }) });
	});

	// List.
	await page.route(/\/api\/v1\/users\/?(\?.*)?$/, (route) => {
		if (route.request().method() !== 'GET') {
			route.fallback();
			return;
		}
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ users })
		});
	});

	// Invite — LIFO: must be last to beat the byId regex.
	await page.route('**/api/v1/users/invite', (route) => {
		const body = route.request().postDataJSON() as {
			username: string;
			role: string;
			brand_ids?: string[] | null;
		};
		const newUser: UserFixture = {
			id: 'invited-new',
			username: body.username,
			display_name: body.username,
			role: body.role,
			status: 'PENDING',
			vendor_id: null,
			email: null,
			brand_ids: body.brand_ids ?? []
		};
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: newUser, invite_token: 'tok-123' })
		});
	});
}

// ---------------------------------------------------------------------------
// Invite modal: brand checklist visibility
// ---------------------------------------------------------------------------

test('invite modal shows brand checklist for SM role', async ({ page }) => {
	await setupUsersPage(page, [SM_USER]);
	await page.goto('/users');

	await page.getByTestId('user-page-header-action').click();
	await expect(page.getByTestId('user-invite-modal')).toBeVisible();

	// Select SM role — brands section should appear.
	await page.getByLabel('Role').selectOption('SM');
	await expect(page.getByTestId('user-invite-brands')).toBeVisible();
	await expect(page.getByText('Brand Alpha')).toBeVisible();
	await expect(page.getByText('Brand Beta')).toBeVisible();
});

test('invite modal shows brand checklist for FREIGHT_MANAGER role', async ({ page }) => {
	await setupUsersPage(page, [SM_USER]);
	await page.goto('/users');

	await page.getByTestId('user-page-header-action').click();
	await page.getByLabel('Role').selectOption('FREIGHT_MANAGER');
	await expect(page.getByTestId('user-invite-brands')).toBeVisible();
});

test('invite modal hides brand checklist for VENDOR role', async ({ page }) => {
	await setupUsersPage(page, [VENDOR_USER]);
	await page.goto('/users');

	await page.getByTestId('user-page-header-action').click();
	await page.getByLabel('Role').selectOption('VENDOR');
	await expect(page.getByTestId('user-invite-brands')).not.toBeVisible();
});

test('invite modal hides brand checklist for ADMIN role', async ({ page }) => {
	await setupUsersPage(page, [ADMIN_USER]);
	await page.goto('/users');

	await page.getByTestId('user-page-header-action').click();
	await page.getByLabel('Role').selectOption('ADMIN');
	await expect(page.getByTestId('user-invite-brands')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// Invite modal: brand selection in POST body
// ---------------------------------------------------------------------------

test('invite with selected brands sends brand_ids in request', async ({ page }) => {
	await setupUsersPage(page, []);
	await page.goto('/users');

	let capturedBody: Record<string, unknown> | null = null;
	await page.route('**/api/v1/users/invite', async (route) => {
		capturedBody = route.request().postDataJSON() as Record<string, unknown>;
		const newUser: UserFixture = {
			id: 'inv-brand',
			username: 'branduser',
			display_name: 'branduser',
			role: 'SM',
			status: 'PENDING',
			vendor_id: null,
			email: null,
			brand_ids: ['brand-a']
		};
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: newUser, invite_token: 'tok-456' })
		});
	});

	await page.getByTestId('user-page-header-action').click();
	await page.getByLabel('Username').fill('branduser');
	await page.getByLabel('Role').selectOption('SM');

	// Check Brand Alpha only.
	const brandsRegion = page.getByTestId('user-invite-brands');
	await expect(brandsRegion).toBeVisible();
	await brandsRegion.getByRole('checkbox', { name: 'Brand Alpha' }).check();

	await page.getByTestId('user-invite-submit').click();

	expect(capturedBody).not.toBeNull();
	expect(capturedBody!['brand_ids']).toEqual(['brand-a']);
});

test('invite with no brands selected sends null brand_ids', async ({ page }) => {
	await setupUsersPage(page, []);
	await page.goto('/users');

	let capturedBody: Record<string, unknown> | null = null;
	await page.route('**/api/v1/users/invite', async (route) => {
		capturedBody = route.request().postDataJSON() as Record<string, unknown>;
		const newUser: UserFixture = {
			id: 'inv-unscoped',
			username: 'unscopeduser',
			display_name: 'unscopeduser',
			role: 'SM',
			status: 'PENDING',
			vendor_id: null,
			email: null,
			brand_ids: []
		};
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: newUser, invite_token: 'tok-789' })
		});
	});

	await page.getByTestId('user-page-header-action').click();
	await page.getByLabel('Username').fill('unscopeduser');
	await page.getByLabel('Role').selectOption('SM');
	// No brands selected.
	await page.getByTestId('user-invite-submit').click();

	expect(capturedBody).not.toBeNull();
	// Empty selection sends null (unscoped).
	expect(capturedBody!['brand_ids']).toBeNull();
});

// ---------------------------------------------------------------------------
// Edit modal: pre-population and PATCH body
// ---------------------------------------------------------------------------

test('edit modal pre-populates brand checkboxes from user.brand_ids', async ({ page }) => {
	await setupUsersPage(page, [SM_USER]);
	await page.goto('/users');

	// Open edit modal for SM_USER (has brand_ids: ['brand-a']).
	await page.getByTestId(`user-row-edit-${SM_USER.id}`).click();

	await expect(page.getByTestId('user-edit-modal')).toBeVisible();
	const brandsRegion = page.getByTestId('user-edit-brands');
	await expect(brandsRegion).toBeVisible();

	// Brand Alpha checkbox should be checked; Brand Beta unchecked.
	// The wrapping <label> gives the checkbox its accessible name.
	await expect(brandsRegion.getByRole('checkbox', { name: 'Brand Alpha' })).toBeChecked();
	await expect(brandsRegion.getByRole('checkbox', { name: 'Brand Beta' })).not.toBeChecked();
});

test('edit modal save sends brand_ids in PATCH body', async ({ page }) => {
	await setupUsersPage(page, [SM_UNSCOPED]);
	await page.goto('/users');

	let capturedBody: Record<string, unknown> | null = null;
	await page.route(/\/api\/v1\/users\/[^/]+$/, async (route) => {
		if (route.request().method() === 'PATCH') {
			capturedBody = route.request().postDataJSON() as Record<string, unknown>;
			const updated: UserFixture = { ...SM_UNSCOPED, brand_ids: ['brand-b'] };
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ user: updated })
			});
			return;
		}
		route.fallback();
	});

	await page.getByTestId(`user-row-edit-${SM_UNSCOPED.id}`).click();

	await expect(page.getByTestId('user-edit-modal')).toBeVisible();
	const brandsRegion = page.getByTestId('user-edit-brands');
	await expect(brandsRegion).toBeVisible();

	// Select Brand Beta.
	await brandsRegion.getByRole('checkbox', { name: 'Brand Beta' }).check();
	await page.getByTestId('user-edit-submit').click();

	expect(capturedBody).not.toBeNull();
	expect(capturedBody!['brand_ids']).toEqual(['brand-b']);
});
