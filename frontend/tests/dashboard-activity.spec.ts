import { test, expect } from '@playwright/test';

const MOCK_DASHBOARD = {
	po_summary: [],
	vendor_summary: { active: 0, inactive: 0 },
	recent_pos: [],
	invoice_summary: [],
	production_summary: [],
	overdue_pos: []
};

// A created_at 30 days in the past produces a stable "30d ago" relative time.
const THIRTY_DAYS_AGO = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

const ACTIVITY_PO: import('../src/lib/types').ActivityLogEntry = {
	id: 'act-1',
	entity_type: 'PO',
	entity_id: 'po-abc',
	event: 'PO_CREATED',
	category: 'LIVE',
	target_role: null,
	detail: 'First widget order',
	read_at: null,
	created_at: THIRTY_DAYS_AGO
};

const ACTIVITY_INVOICE: import('../src/lib/types').ActivityLogEntry = {
	id: 'act-2',
	entity_type: 'INVOICE',
	entity_id: 'inv-xyz',
	event: 'INVOICE_CREATED',
	category: 'ACTION_REQUIRED',
	target_role: null,
	detail: null,
	read_at: null,
	created_at: THIRTY_DAYS_AGO
};

// Registers activity mocks with correct LIFO ordering:
// catch-all first (lower priority), unread-count after (higher priority).
function mockActivityRoutes(
	page: import('@playwright/test').Page,
	listEntries: object[]
) {
	return Promise.all([
		page.route('**/api/v1/activity/**', (route) => {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(listEntries) });
		}),
		page.route('**/api/v1/activity/unread-count', (route) => {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
		})
	]);
}

test.beforeEach(async ({ page }) => {
	await page.route('**/api/v1/dashboard**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_DASHBOARD) });
	});
});

test('activity feed renders event label, category dot, and relative time', async ({ page }) => {
	await mockActivityRoutes(page, [ACTIVITY_PO]);

	await page.goto('/dashboard');
	await page.waitForSelector('.feed-item');

	const item = page.locator('.feed-item').first();
	await expect(item.locator('.cat-dot')).toBeVisible();
	await expect(item.locator('.feed-event')).toContainText('PO created');
	await expect(item.locator('.feed-detail')).toContainText('First widget order');
	await expect(item.locator('.feed-time')).toContainText('d ago');
});

test('activity feed navigates to PO detail on click', async ({ page }) => {
	await mockActivityRoutes(page, [ACTIVITY_PO]);
	// Mock destination so the navigation doesn't 404
	await page.route('**/api/v1/po/po-abc', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
			id: 'po-abc', po_number: 'PO-TEST-0001', status: 'DRAFT', po_type: 'PROCUREMENT',
			vendor_id: 'v1', vendor_name: 'Test Vendor', vendor_country: 'CN',
			buyer_name: 'TurboTonic Ltd', buyer_country: 'US', ship_to_address: '',
			payment_terms: 'TT', currency: 'USD', issued_date: '2026-01-01T00:00:00+00:00',
			required_delivery_date: '2026-02-01T00:00:00+00:00', terms_and_conditions: '',
			incoterm: 'FOB', port_of_loading: 'CNSHA', port_of_discharge: 'USLAX',
			country_of_origin: 'CN', country_of_destination: 'US',
			line_items: [], rejection_history: [], total_value: '0',
			created_at: '2026-01-01T00:00:00+00:00', updated_at: '2026-01-01T00:00:00+00:00'
		}) });
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
			currencies: [], incoterms: [], payment_terms: [], countries: [], ports: [],
			vendor_types: [], po_types: []
		}) });
	});

	await page.goto('/dashboard');
	await page.waitForSelector('.feed-item');

	await page.locator('.feed-item').first().click();
	await page.waitForURL('**/po/po-abc');
	expect(page.url()).toContain('/po/po-abc');
});

test('activity feed navigates to invoice detail on click', async ({ page }) => {
	await mockActivityRoutes(page, [ACTIVITY_INVOICE]);
	await page.route('**/api/v1/invoices/inv-xyz', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
			id: 'inv-xyz', invoice_number: 'INV-TEST-0001', po_id: 'po-1',
			status: 'DRAFT', payment_terms: 'TT', currency: 'USD',
			line_items: [], subtotal: '0.00', dispute_reason: '',
			created_at: '2026-04-01T00:00:00+00:00', updated_at: '2026-04-01T00:00:00+00:00'
		}) });
	});

	await page.goto('/dashboard');
	await page.waitForSelector('.feed-item');

	await page.locator('.feed-item').first().click();
	await page.waitForURL('**/invoice/inv-xyz');
	expect(page.url()).toContain('/invoice/inv-xyz');
});

test('empty activity feed shows no recent activity message', async ({ page }) => {
	await mockActivityRoutes(page, []);

	await page.goto('/dashboard');
	await expect(page.locator('body')).toContainText('No recent activity');
	await expect(page.locator('.feed-item')).toHaveCount(0);
});
