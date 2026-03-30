import { test, expect } from '@playwright/test';

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

	await page.route('**/api/v1/vendors', (route) => {
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

	await page.goto('/vendors/new');
	await page.waitForSelector('form');

	await page.fill('#name', 'New Vendor');
	await page.fill('#country', 'JP');

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
	await page.waitForSelector('form');

	await expect(page.locator('#buyer_name')).toHaveValue('TurboTonic Ltd');
	await expect(page.locator('#buyer_country')).toHaveValue('US');
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
