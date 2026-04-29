import { test, expect } from '@playwright/test';
import type { Page, Route } from '@playwright/test';

// Iter 089 — Phase 4.4 Tier 1 — `/vendors` + `/vendors/new` revamp under (nexus).
// All selectors use testid / role / label per CLAUDE.md selector policy.

const SM_USER = {
	id: 'test-user-id',
	username: 'test-sm',
	display_name: 'Test User',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null
};

test.beforeEach(async ({ page }) => {
	// LIFO order: catch-all first (lowest priority), then specific overrides.
	await page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: SM_USER })
		});
	});
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ count: 0 })
		});
	});
});

const VENDOR_ACTIVE = {
	id: 'aaaaaaaa-1111-1111-1111-000000000001',
	name: 'Acme Corp',
	country: 'CN',
	status: 'ACTIVE',
	vendor_type: 'PROCUREMENT',
	address: '',
	account_details: ''
};
const VENDOR_INACTIVE = {
	id: 'bbbbbbbb-2222-2222-2222-000000000002',
	name: 'Beta LLC',
	country: 'US',
	status: 'INACTIVE',
	vendor_type: 'PROCUREMENT',
	address: '',
	account_details: ''
};

const REF_DATA_BASE = {
	currencies: [],
	incoterms: [],
	payment_terms: [],
	ports: [],
	vendor_types: [],
	po_types: [],
	countries: [
		{ code: 'JP', label: 'Japan' },
		{ code: 'US', label: 'United States' },
		{ code: 'CN', label: 'China' },
		{ code: 'DE', label: 'Germany' }
	]
};

function mockReferenceData(page: Page, refData: object = REF_DATA_BASE) {
	return page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(refData)
		});
	});
}

// ---------------------------------------------------------------------------
// `/vendors` — list page
// ---------------------------------------------------------------------------

test('vendor list page mounts under (nexus) AppShell', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE])
		});
	});

	await page.goto('/vendors');
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByTestId('ui-appshell-topbar')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Vendor Portal' })).toHaveCount(0);
});

test('vendor list loads and displays vendors', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE, VENDOR_INACTIVE])
		});
	});

	await page.goto('/vendors');
	await expect(page.getByRole('heading', { name: 'Vendors', level: 1 })).toBeVisible();

	const desktop = page.getByTestId('vendor-table-desktop');
	await expect(desktop.getByTestId(`vendor-row-${VENDOR_ACTIVE.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`vendor-row-${VENDOR_INACTIVE.id}`)).toBeVisible();

	await expect(desktop).toContainText('Acme Corp');
	await expect(desktop).toContainText('Beta LLC');

	await expect(desktop.getByTestId(`vendor-row-status-${VENDOR_ACTIVE.id}`)).toContainText('Active');
	await expect(desktop.getByTestId(`vendor-row-status-${VENDOR_INACTIVE.id}`)).toContainText(
		'Inactive'
	);
});

test('vendor list shows short ID column', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE])
		});
	});

	await page.goto('/vendors');
	const desktop = page.getByTestId('vendor-table-desktop');
	await expect(desktop.getByTestId(`vendor-row-id-${VENDOR_ACTIVE.id}`)).toContainText(
		VENDOR_ACTIVE.id.slice(0, 8)
	);
});

test('vendor list filter narrows by status', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		const url = new URL(route.request().url());
		const statusParam = url.searchParams.get('status');
		const rows =
			statusParam === 'INACTIVE'
				? [VENDOR_INACTIVE]
				: statusParam === 'ACTIVE'
					? [VENDOR_ACTIVE]
					: [VENDOR_ACTIVE, VENDOR_INACTIVE];
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(rows)
		});
	});

	await page.goto('/vendors');
	const desktop = page.getByTestId('vendor-table-desktop');
	await expect(desktop.getByTestId(`vendor-row-${VENDOR_ACTIVE.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`vendor-row-${VENDOR_INACTIVE.id}`)).toBeVisible();

	await page.getByTestId('vendor-filter-status').selectOption('INACTIVE');
	await expect(desktop.getByTestId(`vendor-row-${VENDOR_ACTIVE.id}`)).toHaveCount(0);
	await expect(desktop.getByTestId(`vendor-row-${VENDOR_INACTIVE.id}`)).toBeVisible();
});

test('vendor list shows empty state when filters return no rows', async ({ page }) => {
	let firstCall = true;
	await page.route('**/api/v1/vendors**', (route) => {
		// Return one vendor on the initial fetch and zero after filters apply.
		const body = firstCall ? [VENDOR_ACTIVE] : [];
		firstCall = false;
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(body)
		});
	});

	await page.goto('/vendors');
	await expect(page.getByTestId('vendor-table-desktop')).toBeVisible();

	await page.getByTestId('vendor-filter-status').selectOption('INACTIVE');
	await expect(page.getByTestId('vendor-table-desktop')).toHaveCount(0);
	await expect(page.getByText('No matching vendors')).toBeVisible();
});

test('vendor list shows error state with retry', async ({ page }) => {
	let attempt = 0;
	await page.route('**/api/v1/vendors**', (route) => {
		attempt += 1;
		if (attempt === 1) {
			route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' });
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([VENDOR_ACTIVE])
			});
		}
	});

	await page.goto('/vendors');
	await expect(page.getByRole('alert')).toBeVisible();
	await page.getByRole('button', { name: /retry/i }).click();
	await expect(page.getByTestId(`vendor-row-${VENDOR_ACTIVE.id}`).first()).toBeVisible();
});

test('deactivate vendor swaps action button to Reactivate', async ({ page }) => {
	const vendorInactive = { ...VENDOR_ACTIVE, status: 'INACTIVE' };

	const activeHandler = (route: Route) => {
		const url = route.request().url();
		const path = new URL(url).pathname;
		if (path === '/api/v1/vendors' || path === '/api/v1/vendors/') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([VENDOR_ACTIVE])
			});
		} else {
			route.continue();
		}
	};
	await page.route('**/api/v1/vendors**', activeHandler);

	await page.goto('/vendors');
	const desktop = page.getByTestId('vendor-table-desktop');
	const action = desktop.getByTestId(`vendor-row-action-${VENDOR_ACTIVE.id}`);
	await expect(action).toContainText('Deactivate');

	// Swap the GET to return inactive before the click triggers a re-fetch.
	await page.unroute('**/api/v1/vendors**', activeHandler);
	await page.route('**/api/v1/vendors**', (route) => {
		const path = new URL(route.request().url()).pathname;
		if (path.endsWith('/deactivate')) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(vendorInactive)
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([vendorInactive])
			});
		}
	});

	await action.click();
	await expect(action).toContainText('Reactivate');
	await expect(desktop.getByTestId(`vendor-row-status-${VENDOR_ACTIVE.id}`)).toContainText(
		'Inactive'
	);
});

test('reactivate vendor swaps action button to Deactivate', async ({ page }) => {
	const vendorActive = { ...VENDOR_INACTIVE, status: 'ACTIVE' };

	const inactiveHandler = (route: Route) => {
		const url = route.request().url();
		const path = new URL(url).pathname;
		if (path === '/api/v1/vendors' || path === '/api/v1/vendors/') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([VENDOR_INACTIVE])
			});
		} else {
			route.continue();
		}
	};
	await page.route('**/api/v1/vendors**', inactiveHandler);

	await page.goto('/vendors');
	const desktop = page.getByTestId('vendor-table-desktop');
	const action = desktop.getByTestId(`vendor-row-action-${VENDOR_INACTIVE.id}`);
	await expect(action).toContainText('Reactivate');

	await page.unroute('**/api/v1/vendors**', inactiveHandler);
	await page.route('**/api/v1/vendors**', (route) => {
		const path = new URL(route.request().url()).pathname;
		if (path.endsWith('/reactivate')) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(vendorActive)
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([vendorActive])
			});
		}
	});

	await action.click();
	await expect(action).toContainText('Deactivate');
});

test('mobile (390px) renders vendor cards instead of desktop table', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE])
		});
	});

	await page.goto('/vendors');
	await expect(page.getByTestId('vendor-table-mobile')).toBeVisible();

	const mobile = page.getByTestId('vendor-table-mobile');
	await expect(mobile.getByTestId(`vendor-row-${VENDOR_ACTIVE.id}`)).toBeVisible();
	await expect(mobile).toContainText('Acme Corp');
});

// ---------------------------------------------------------------------------
// `/vendors/new` — create form
// ---------------------------------------------------------------------------

test('vendor create page mounts under (nexus) AppShell', async ({ page }) => {
	await mockReferenceData(page);
	await page.goto('/vendors/new');
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Create Vendor', level: 1 })).toBeVisible();
	await expect(page.getByTestId('vendor-form')).toBeVisible();
});

test('create vendor form submits and redirects', async ({ page }) => {
	const createdVendor = {
		id: 'cccccccc-3333-3333-3333-000000000003',
		name: 'New Vendor',
		country: 'JP',
		status: 'ACTIVE',
		vendor_type: 'PROCUREMENT',
		address: '',
		account_details: ''
	};

	await mockReferenceData(page);
	await page.route('**/api/v1/vendors**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(createdVendor)
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto('/vendors/new');
	await expect(page.getByTestId('vendor-form')).toBeVisible();

	await page.getByTestId('vendor-form-name').fill('New Vendor');
	await page.getByTestId('vendor-form-country').selectOption('JP');

	await page.getByTestId('vendor-form-submit').click();
	await page.waitForURL('**/vendors');
	expect(page.url()).toContain('/vendors');
});

test('vendor create form country is a combobox with options from reference data', async ({
	page
}) => {
	await mockReferenceData(page);
	await page.goto('/vendors/new');

	const country = page.getByTestId('vendor-form-country');
	const tagName = await country.evaluate((el) => el.tagName.toLowerCase());
	expect(tagName).toBe('select');
	// "Select country" placeholder + 4 countries from REF_DATA_BASE = 5 options.
	const options = country.locator('option');
	await expect(options).toHaveCount(5);
	await expect(country).toContainText('United States');
	await expect(country).toContainText('Japan');
	await expect(country).toContainText('China');
	await expect(country).toContainText('Germany');
});

test('vendor create form renders address and account_details fields', async ({ page }) => {
	await mockReferenceData(page);
	await page.goto('/vendors/new');

	await expect(page.getByTestId('vendor-form-address')).toBeVisible();
	await expect(page.getByTestId('vendor-form-account-details')).toBeVisible();
	await expect(page.getByTestId('vendor-form-address')).toHaveValue('');
	await expect(page.getByTestId('vendor-form-account-details')).toHaveValue('');
});

test('vendor create form submits address and account_details', async ({ page }) => {
	const ADDRESS = '123 Factory Rd, Tokyo';
	const ACCOUNT_DETAILS = 'Bank: Mizuho, Acct: 12345';

	let capturedBody: Record<string, unknown> = {};

	await mockReferenceData(page);
	await page.route('**/api/v1/vendors**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			capturedBody = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify({
					id: 'v-new',
					name: 'Test Vendor',
					country: 'JP',
					status: 'ACTIVE',
					vendor_type: 'PROCUREMENT',
					address: '',
					account_details: ''
				})
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto('/vendors/new');

	await page.getByTestId('vendor-form-name').fill('Test Vendor');
	await page.getByTestId('vendor-form-country').selectOption('JP');
	await page.getByTestId('vendor-form-address').fill(ADDRESS);
	await page.getByTestId('vendor-form-account-details').fill(ACCOUNT_DETAILS);

	await page.getByTestId('vendor-form-submit').click();
	await page.waitForURL('**/vendors');

	expect(capturedBody['address']).toBe(ADDRESS);
	expect(capturedBody['account_details']).toBe(ACCOUNT_DETAILS);
});

test('vendor create form blocks submit when name is empty', async ({ page }) => {
	let postCalled = false;
	await mockReferenceData(page);
	await page.route('**/api/v1/vendors**', (route) => {
		if (route.request().method() === 'POST') {
			postCalled = true;
		}
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	await page.goto('/vendors/new');
	await page.getByTestId('vendor-form-country').selectOption('JP');
	await page.getByTestId('vendor-form-submit').click();

	// Form-level validation surfaces inline errors via FormField / Input invalid state.
	await expect(page.getByText('Name is required.')).toBeVisible();
	expect(postCalled).toBe(false);
});

test('vendor create form Cancel returns to /vendors', async ({ page }) => {
	await mockReferenceData(page);
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	await page.goto('/vendors/new');
	await page.getByTestId('vendor-form-cancel').click();
	await page.waitForURL('**/vendors');
	expect(page.url()).toContain('/vendors');
	expect(page.url()).not.toContain('/new');
});

// ---------------------------------------------------------------------------
// PO form (unrelated to vendors but historically lives in this file).
// Already uses testid selectors — left intact during the iter 089 migration.
// ---------------------------------------------------------------------------

test('PO form prefills buyer fields with defaults', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE])
		});
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				currencies: [{ code: 'USD', label: 'US Dollar' }],
				incoterms: [{ code: 'FOB', label: 'Free on Board' }],
				payment_terms: [{ code: 'TT', label: 'Telegraphic Transfer' }],
				countries: [
					{ code: 'US', label: 'United States' },
					{ code: 'CN', label: 'China' }
				],
				ports: [
					{ code: 'CNSHA', label: 'Shanghai' },
					{ code: 'USLAX', label: 'Los Angeles' }
				],
				vendor_types: [
					{ code: 'PROCUREMENT', label: 'Procurement' },
					{ code: 'OPEX', label: 'OpEx' },
					{ code: 'FREIGHT', label: 'Freight' },
					{ code: 'MISCELLANEOUS', label: 'Miscellaneous' }
				],
				po_types: [
					{ code: 'PROCUREMENT', label: 'Procurement' },
					{ code: 'OPEX', label: 'OpEx' }
				]
			})
		});
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	await expect(page.getByTestId('po-form-buyer-name')).toHaveValue('TurboTonic Ltd');
	await expect(page.getByTestId('po-form-buyer-country')).toHaveValue('US');
});
