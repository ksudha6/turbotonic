import { test, expect } from '@playwright/test';

const PO_ID = 'po-timeline-1';
const INV_ID = 'inv-timeline-1';

const REFERENCE_DATA = {
	currencies: [{ code: 'USD', label: 'US Dollar' }],
	incoterms: [{ code: 'FOB', label: 'Free on Board' }],
	payment_terms: [{ code: 'TT', label: 'Telegraphic Transfer' }],
	countries: [{ code: 'US', label: 'United States' }, { code: 'CN', label: 'China' }],
	ports: [{ code: 'CNSHA', label: 'Shanghai' }, { code: 'USLAX', label: 'Los Angeles' }],
	vendor_types: [{ code: 'PROCUREMENT', label: 'Procurement' }],
	po_types: [{ code: 'PROCUREMENT', label: 'Procurement' }]
};

const PO_DRAFT = {
	id: PO_ID,
	po_number: 'PO-20260401-0001',
	status: 'DRAFT',
	po_type: 'PROCUREMENT',
	vendor_id: 'v1',
	vendor_name: 'Test Vendor',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	ship_to_address: '123 Main St',
	payment_terms: 'TT',
	currency: 'USD',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	terms_and_conditions: '',
	incoterm: 'FOB',
	port_of_loading: 'CNSHA',
	port_of_discharge: 'USLAX',
	country_of_origin: 'CN',
	country_of_destination: 'US',
	line_items: [],
	rejection_history: [],
	total_value: '0',
	created_at: '2026-04-01T00:00:00+00:00',
	updated_at: '2026-04-01T00:00:00+00:00',
	brand_id: 'brand-default',
	brand_name: 'Default Brand',
	brand_legal_name: 'Default Brand LLC',
	brand_address: '1 Brand St',
	brand_country: 'US',
	brand_tax_id: ''
};

const INVOICE_DETAIL = {
	id: INV_ID,
	invoice_number: 'INV-20260401-0001',
	po_id: 'po-1',
	status: 'DRAFT',
	payment_terms: 'TT',
	currency: 'USD',
	line_items: [{ part_number: 'PN-001', description: 'Widget', quantity: 10, uom: 'pcs', unit_price: '50.00' }],
	subtotal: '500.00',
	dispute_reason: '',
	created_at: '2026-04-01T00:00:00+00:00',
	updated_at: '2026-04-01T00:00:00+00:00'
};

const PO_ACTIVITY_ENTRY: import('../src/lib/types').ActivityLogEntry = {
	id: 'act-po-1',
	entity_type: 'PO',
	entity_id: PO_ID,
	event: 'PO_CREATED',
	category: 'LIVE',
	target_role: null,
	detail: 'Order placed',
	read_at: null,
	created_at: '2026-04-01T00:00:00+00:00'
};

const INVOICE_ACTIVITY_ENTRY: import('../src/lib/types').ActivityLogEntry = {
	id: 'act-inv-1',
	entity_type: 'INVOICE',
	entity_id: INV_ID,
	event: 'INVOICE_CREATED',
	category: 'ACTION_REQUIRED',
	target_role: null,
	detail: null,
	read_at: null,
	created_at: '2026-04-01T00:00:00+00:00'
};

// Registers activity mocks with correct LIFO ordering:
// catch-all first (lower priority), unread-count after (higher priority).
async function mockActivityRoutes(
	page: import('@playwright/test').Page,
	entityEntries: object[]
) {
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(entityEntries) });
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
}

// ---------------------------------------------------------------------------
// PO detail — Activity section
// ---------------------------------------------------------------------------

test.beforeEach(async ({ page }) => {
	// Catch-all for any unmocked API route (lowest LIFO priority — registered first).
	await page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 'test-user-id', username: 'test-sm', display_name: 'Test User', role: 'SM', status: 'ACTIVE', vendor_id: null } }) });
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
});

test('PO detail page shows Activity section heading and timeline entries', async ({ page }) => {
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PO_DRAFT) });
	});
	await mockActivityRoutes(page, [PO_ACTIVITY_ENTRY]);

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	// Migrated to PoActivityPanel (iter 083): panel and ActivityFeed primitive.
	const panel = page.getByTestId('po-activity-panel');
	await expect(panel.getByRole('heading', { name: 'Activity' })).toBeVisible();
	const feed = page.getByTestId('po-activity-feed');
	await expect(feed.locator('li')).toHaveCount(1);
	await expect(feed.locator('.primary').first()).toContainText('PO created');
	await expect(feed.locator('.secondary').first()).toContainText('Order placed');
});

test('PO detail activity timeline shows category-colored dot', async ({ page }) => {
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PO_DRAFT) });
	});
	await mockActivityRoutes(page, [PO_ACTIVITY_ENTRY]);

	await page.goto(`/po/${PO_ID}`);
	// Migrated to PoActivityPanel (iter 083): LIVE category maps to 'blue' tone
	// via categoryToTone; ActivityFeed renders <span class="dot blue">.
	const feed = page.getByTestId('po-activity-feed');
	await expect(feed.locator('li').first()).toBeVisible();
	const dot = feed.locator('.dot').first();
	await expect(dot).toHaveClass(/blue/);
});

test('PO detail activity timeline shows empty message when no entries', async ({ page }) => {
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PO_DRAFT) });
	});
	await mockActivityRoutes(page, []);

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	// Migrated to PoActivityPanel (iter 083): empty state uses EmptyState primitive.
	const panel = page.getByTestId('po-activity-panel');
	await expect(panel).toContainText('No activity yet.');
	await expect(page.getByTestId('po-activity-feed')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Invoice detail — Activity section
// ---------------------------------------------------------------------------

test('invoice detail page shows Activity panel and feed entries', async ({ page }) => {
	await page.route(`**/api/v1/invoices/${INV_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(INVOICE_DETAIL) });
	});
	await mockActivityRoutes(page, [INVOICE_ACTIVITY_ENTRY]);

	await page.goto(`/invoice/${INV_ID}`);
	await page.waitForSelector('h1');

	await expect(page.getByTestId('invoice-activity-panel')).toBeVisible();
	const feed = page.getByTestId('invoice-activity-feed');
	await expect(feed).toBeVisible();
	await expect(feed.getByText('Invoice created')).toHaveCount(1);
});

test('invoice detail activity feed dot uses category-mapped tone class', async ({ page }) => {
	await page.route(`**/api/v1/invoices/${INV_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(INVOICE_DETAIL) });
	});
	await mockActivityRoutes(page, [INVOICE_ACTIVITY_ENTRY]);

	await page.goto(`/invoice/${INV_ID}`);
	await page.waitForSelector('h1');

	// ACTION_REQUIRED → 'orange' tone via categoryToTone in $lib/event-labels.
	const feed = page.getByTestId('invoice-activity-feed');
	await expect(feed).toBeVisible();
	await expect(feed.locator('.dot.orange').first()).toBeVisible();
});

test('invoice detail activity panel shows empty state when no entries', async ({ page }) => {
	await page.route(`**/api/v1/invoices/${INV_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(INVOICE_DETAIL) });
	});
	await mockActivityRoutes(page, []);

	await page.goto(`/invoice/${INV_ID}`);
	await page.waitForSelector('h1');

	const panel = page.getByTestId('invoice-activity-panel');
	await expect(panel).toContainText('No activity yet.');
	await expect(page.getByTestId('invoice-activity-feed')).toHaveCount(0);
});
