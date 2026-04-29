import { test, expect } from '@playwright/test';

// NotificationBell calls unread-count on every page load.
test.beforeEach(async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 'test-user-id', username: 'test-sm', display_name: 'Test User', role: 'SM', status: 'ACTIVE', vendor_id: null } }) });
	});
	// Catch-all first (lower LIFO priority), specific unread-count after (higher priority).
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
});

const VENDOR_ACTIVE = { id: 'v1', name: 'Acme Corp', country: 'CN', status: 'ACTIVE', vendor_type: 'PROCUREMENT' };
const VENDOR_INACTIVE = { id: 'v2', name: 'Beta LLC', country: 'US', status: 'INACTIVE', vendor_type: 'PROCUREMENT' };

test('vendor list loads and displays vendors', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE, VENDOR_INACTIVE])
		});
	});

	await page.goto('/vendors');
	await page.waitForSelector('table');

	await expect(page.locator('h1')).toContainText('Vendors');

	const rows = page.locator('tbody tr');
	await expect(rows).toHaveCount(2);

	await expect(page.locator('tbody')).toContainText('Acme Corp');
	await expect(page.locator('tbody')).toContainText('Beta LLC');

	await expect(page.locator('tbody')).toContainText('Active');
	await expect(page.locator('tbody')).toContainText('Inactive');
});

test('create vendor form submits and redirects', async ({ page }) => {
	const createdVendor = { id: 'v3', name: 'New Vendor', country: 'JP', status: 'ACTIVE', vendor_type: 'PROCUREMENT' };

	await page.route('**/api/v1/vendors**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(createdVendor)
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		}
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				currencies: [], incoterms: [], payment_terms: [], ports: [],
				vendor_types: [], po_types: [],
				countries: [{ code: 'JP', label: 'Japan' }, { code: 'US', label: 'United States' }],
			}),
		});
	});

	await page.goto('/vendors/new');
	await page.waitForSelector('form');

	await page.fill('#name', 'New Vendor');
	await page.selectOption('#country', 'JP');

	await page.getByRole('button', { name: 'Create Vendor' }).click();
	await page.waitForURL('**/vendors');

	expect(page.url()).toContain('/vendors');
});

test('deactivate vendor updates status badge', async ({ page }) => {
	const vendorInactive = { ...VENDOR_ACTIVE, status: 'INACTIVE' };

	// Initial GET returns an active vendor
	const activeHandler = (route: import('@playwright/test').Route) => {
		const url = route.request().url();
		// Only intercept the list GET, not action sub-routes
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
	await page.waitForSelector('table');
	await expect(page.getByRole('button', { name: 'Deactivate' })).toBeVisible();

	// Swap GET mock to return inactive before the click triggers a re-fetch
	await page.unroute('**/api/v1/vendors**', activeHandler);
	await page.route('**/api/v1/vendors**', (route) => {
		const url = route.request().url();
		const path = new URL(url).pathname;
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

	await page.getByRole('button', { name: 'Deactivate' }).click();

	await expect(page.getByRole('button', { name: 'Deactivate' })).toHaveCount(0);
	await expect(page.locator('tbody')).toContainText('Inactive');
});

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
				countries: [{ code: 'US', label: 'United States' }, { code: 'CN', label: 'China' }],
				ports: [{ code: 'CNSHA', label: 'Shanghai' }, { code: 'USLAX', label: 'Los Angeles' }],
				vendor_types: [
					{ code: 'PROCUREMENT', label: 'Procurement' },
					{ code: 'OPEX', label: 'OpEx' },
					{ code: 'FREIGHT', label: 'Freight' },
					{ code: 'MISCELLANEOUS', label: 'Miscellaneous' },
				],
				po_types: [
					{ code: 'PROCUREMENT', label: 'Procurement' },
					{ code: 'OPEX', label: 'OpEx' },
				]
			})
		});
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	await expect(page.getByTestId('po-form-buyer-name')).toHaveValue('TurboTonic Ltd');
	await expect(page.getByTestId('po-form-buyer-country')).toHaveValue('US');
});

test('reactivate vendor updates status badge', async ({ page }) => {
	const vendorActive = { ...VENDOR_INACTIVE, status: 'ACTIVE' };

	const inactiveHandler = (route: import('@playwright/test').Route) => {
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
	await page.waitForSelector('table');
	await expect(page.getByRole('button', { name: 'Reactivate' })).toBeVisible();

	await page.unroute('**/api/v1/vendors**', inactiveHandler);
	await page.route('**/api/v1/vendors**', (route) => {
		const url = route.request().url();
		const path = new URL(url).pathname;
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

	await page.getByRole('button', { name: 'Reactivate' }).click();

	await expect(page.getByRole('button', { name: 'Reactivate' })).toHaveCount(0);
	await expect(page.locator('tbody')).toContainText('Active');
});

test('vendor list shows UUID column', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE])
		});
	});

	await page.goto('/vendors');
	await page.waitForSelector('table');

	// ID column header exists
	await expect(page.locator('thead')).toContainText('ID');
	// First 8 chars of vendor ID are shown
	await expect(page.locator('tbody .vendor-id')).toContainText(VENDOR_ACTIVE.id.slice(0, 8));
});

// ---------------------------------------------------------------------------
// Iteration 19 — Vendor country dropdown (reference data)
// ---------------------------------------------------------------------------

test('vendor create form renders country as select dropdown', async ({ page }) => {
	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				currencies: [], incoterms: [], payment_terms: [], ports: [],
				vendor_types: [], po_types: [],
				countries: [
					{ code: 'US', label: 'United States' },
					{ code: 'CN', label: 'China' },
					{ code: 'DE', label: 'Germany' },
				],
			}),
		});
	});

	await page.goto('/vendors/new');
	await page.waitForSelector('form');

	// #country must be a <select>, not a plain text input
	const countryEl = page.locator('#country');
	await expect(countryEl).toBeVisible();
	const tagName = await countryEl.evaluate((el) => el.tagName.toLowerCase());
	expect(tagName).toBe('select');
});

test('vendor create form shows country options from reference data', async ({ page }) => {
	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				currencies: [], incoterms: [], payment_terms: [], ports: [],
				vendor_types: [], po_types: [],
				countries: [
					{ code: 'US', label: 'United States' },
					{ code: 'CN', label: 'China' },
					{ code: 'DE', label: 'Germany' },
				],
			}),
		});
	});

	await page.goto('/vendors/new');
	await page.waitForSelector('form');

	const countrySelect = page.locator('#country');
	const options = countrySelect.locator('option');
	// placeholder ("Select country") + 3 countries = 4 total
	await expect(options).toHaveCount(4);
	await expect(countrySelect).toContainText('United States');
	await expect(countrySelect).toContainText('China');
	await expect(countrySelect).toContainText('Germany');
});

// ---------------------------------------------------------------------------
// Iteration 36 — Vendor address and account_details fields
// ---------------------------------------------------------------------------

test('vendor create form renders address and account_details fields', async ({ page }) => {
	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				currencies: [], incoterms: [], payment_terms: [], ports: [],
				vendor_types: [], po_types: [],
				countries: [{ code: 'JP', label: 'Japan' }],
			}),
		});
	});

	await page.goto('/vendors/new');
	await page.waitForSelector('form');

	await expect(page.locator('#address')).toBeVisible();
	await expect(page.locator('#account_details')).toBeVisible();
	await expect(page.locator('#address')).toHaveValue('');
	await expect(page.locator('#account_details')).toHaveValue('');
});

test('vendor create form submits address and account_details', async ({ page }) => {
	const ADDRESS = '123 Factory Rd, Tokyo';
	const ACCOUNT_DETAILS = 'Bank: Mizuho, Acct: 12345';

	let capturedBody: Record<string, unknown> = {};

	await page.route('**/api/v1/vendors**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			capturedBody = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify({ id: 'v-new', name: 'Test Vendor', country: 'JP', status: 'ACTIVE', vendor_type: 'PROCUREMENT' }),
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
		}
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				currencies: [], incoterms: [], payment_terms: [], ports: [],
				vendor_types: [], po_types: [],
				countries: [{ code: 'JP', label: 'Japan' }],
			}),
		});
	});

	await page.goto('/vendors/new');
	await page.waitForSelector('form');

	await page.fill('#name', 'Test Vendor');
	await page.selectOption('#country', 'JP');
	await page.locator('#address').fill(ADDRESS);
	await page.locator('#account_details').fill(ACCOUNT_DETAILS);

	await page.getByRole('button', { name: 'Create Vendor' }).click();
	await page.waitForURL('**/vendors');

	expect(capturedBody['address']).toBe(ADDRESS);
	expect(capturedBody['account_details']).toBe(ACCOUNT_DETAILS);
});
