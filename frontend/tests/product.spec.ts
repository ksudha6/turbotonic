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
