import { test, expect } from '@playwright/test';

const MANUFACTURING_ADDRESS = '456 Industrial Park, Shenzhen';
const EXISTING_MANUFACTURING_ADDRESS = '789 Plant Ave, Taipei';

const VENDOR_ACTIVE = {
	id: 'v1',
	name: 'Acme Corp',
	country: 'CN',
	status: 'ACTIVE',
	vendor_type: 'PROCUREMENT',
	address: '',
	account_details: '',
};

const PRODUCT = {
	id: 'prod-1',
	vendor_id: 'v1',
	part_number: 'PN-001',
	description: 'Test Part',
	manufacturing_address: EXISTING_MANUFACTURING_ADDRESS,
	qualifications: [],
	created_at: '2026-01-01T00:00:00Z',
	updated_at: '2026-01-01T00:00:00Z',
};

// NotificationBell calls unread-count on every page load.
test.beforeEach(async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'test-user-id',
					username: 'test-sm',
					display_name: 'Test User',
					role: 'SM',
					status: 'ACTIVE',
					vendor_id: null,
				},
			}),
		});
	});
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
	await page.route('**/api/v1/qualification-types', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/packaging-specs**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
});

// ---------------------------------------------------------------------------
// Iteration 36 — Product manufacturing_address field
// ---------------------------------------------------------------------------

test('product create form renders manufacturing_address field', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});

	await page.goto('/products/new');
	await page.waitForSelector('form');

	await expect(page.locator('#manufacturing_address')).toBeVisible();
	await expect(page.locator('#manufacturing_address')).toHaveValue('');
});

test('product create form submits manufacturing_address', async ({ page }) => {
	let capturedBody: Record<string, unknown> = {};

	await page.route('**/api/v1/vendors**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			route.continue();
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([VENDOR_ACTIVE]),
			});
		}
	});

	await page.route('**/api/v1/products**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			capturedBody = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify({ ...PRODUCT, manufacturing_address: MANUFACTURING_ADDRESS }),
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
		}
	});

	await page.goto('/products/new');
	await page.waitForSelector('form');

	await page.selectOption('#vendor_id', 'v1');
	await page.fill('#part_number', 'PN-002');
	await page.locator('#manufacturing_address').fill(MANUFACTURING_ADDRESS);

	await page.getByRole('button', { name: 'Create Product' }).click();
	await page.waitForURL('**/products');

	expect(capturedBody['manufacturing_address']).toBe(MANUFACTURING_ADDRESS);
});

test('product edit form shows existing manufacturing_address', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});

	await page.route('**/api/v1/products/prod-1**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(PRODUCT),
		});
	});

	await page.goto('/products/prod-1/edit');
	await page.waitForSelector('form');

	await expect(page.locator('#manufacturing_address')).toHaveValue(EXISTING_MANUFACTURING_ADDRESS);
});

// ---------------------------------------------------------------------------
// Iter 090 — `/products` list under (nexus) AppShell
// ---------------------------------------------------------------------------

const PRODUCT_NO_QUALS = {
	id: 'prod-list-1',
	vendor_id: 'v1',
	part_number: 'PN-LIST-001',
	description: 'Steel bolt M8',
	manufacturing_address: '',
	qualifications: []
};

const QUAL_ITEM = {
	id: 'qt-1',
	name: 'QUALITY_CERTIFICATE',
	target_market: 'AMZ',
	applies_to_category: 'GENERAL'
};

const PRODUCT_WITH_QUALS = {
	id: 'prod-list-2',
	vendor_id: 'v1',
	part_number: 'PN-LIST-002',
	description: 'Steel bolt M10',
	manufacturing_address: '',
	qualifications: [QUAL_ITEM]
};

test('product list page mounts under (nexus) AppShell', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PRODUCT_NO_QUALS]),
		});
	});

	await page.goto('/products');
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByTestId('ui-appshell-topbar')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Vendor Portal' })).toHaveCount(0);
});

test('product list loads and renders rows', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PRODUCT_NO_QUALS, PRODUCT_WITH_QUALS]),
		});
	});

	await page.goto('/products');
	await expect(page.getByRole('heading', { name: 'Products', level: 1 })).toBeVisible();

	const desktop = page.getByTestId('product-table-desktop');
	await expect(desktop.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`product-row-${PRODUCT_WITH_QUALS.id}`)).toBeVisible();
	await expect(desktop).toContainText('PN-LIST-001');
	await expect(desktop).toContainText('PN-LIST-002');
	await expect(desktop).toContainText('Acme Corp');
});

test('qualification pill shows count for products with qualifications and "None" otherwise', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PRODUCT_NO_QUALS, PRODUCT_WITH_QUALS]),
		});
	});

	await page.goto('/products');
	const desktop = page.getByTestId('product-table-desktop');
	await expect(desktop.getByTestId(`product-row-quals-${PRODUCT_NO_QUALS.id}`)).toContainText('None');
	await expect(desktop.getByTestId(`product-row-quals-${PRODUCT_WITH_QUALS.id}`)).toContainText('1 qualification');
});

test('vendor filter narrows product list', async ({ page }) => {
	const VENDOR_OTHER = { ...VENDOR_ACTIVE, id: 'v2', name: 'Beta LLC' };
	const PRODUCT_V2 = { ...PRODUCT_NO_QUALS, id: 'prod-list-3', vendor_id: 'v2', part_number: 'PN-V2' };

	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE, VENDOR_OTHER]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		const url = new URL(route.request().url());
		const vId = url.searchParams.get('vendor_id');
		const rows = vId === 'v2' ? [PRODUCT_V2] : vId === 'v1' ? [PRODUCT_NO_QUALS] : [PRODUCT_NO_QUALS, PRODUCT_V2];
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(rows),
		});
	});

	await page.goto('/products');
	const desktop = page.getByTestId('product-table-desktop');
	await expect(desktop.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`product-row-${PRODUCT_V2.id}`)).toBeVisible();

	await page.getByTestId('product-filter-vendor').selectOption('v2');
	await expect(desktop.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`)).toHaveCount(0);
	await expect(desktop.getByTestId(`product-row-${PRODUCT_V2.id}`)).toBeVisible();
});

test('product list shows empty state when filter returns no rows', async ({ page }) => {
	let firstCall = true;
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		const body = firstCall ? [PRODUCT_NO_QUALS] : [];
		firstCall = false;
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(body),
		});
	});

	await page.goto('/products');
	await expect(page.getByTestId('product-table-desktop')).toBeVisible();

	await page.getByTestId('product-filter-vendor').selectOption('v1');
	await expect(page.getByTestId('product-table-desktop')).toHaveCount(0);
	await expect(page.getByText('No matching products')).toBeVisible();
});

test('product list shows error state with retry', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});

	let attempt = 0;
	await page.route('**/api/v1/products**', (route) => {
		attempt += 1;
		if (attempt === 1) {
			route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' });
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([PRODUCT_NO_QUALS]),
			});
		}
	});

	await page.goto('/products');
	await expect(page.getByRole('alert')).toBeVisible();
	await page.getByRole('button', { name: /retry/i }).click();
	await expect(page.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`).first()).toBeVisible();
});

test('mobile (390px) renders product cards instead of desktop table', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PRODUCT_NO_QUALS]),
		});
	});

	await page.goto('/products');
	await expect(page.getByTestId('product-table-mobile')).toBeVisible();
	const mobile = page.getByTestId('product-table-mobile');
	await expect(mobile.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`)).toBeVisible();
	await expect(mobile).toContainText('PN-LIST-001');
});
