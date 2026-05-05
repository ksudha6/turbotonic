import { test, expect } from '@playwright/test';

// Iter 058: covers the two consumer-facing surfaces for the line-negotiation
// domain model: the PO list pill (Partial / Modified) and the activity timeline
// labels for the seven new event types.

test.beforeEach(async ({ page }) => {
	// Playwright page.route uses LIFO match ordering. Register the lowest-priority
	// catch-all first so any unmocked /api/v1/ call returns a harmless 200. More
	// specific routes registered after this (and in each test body) take priority.
	await page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
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
					vendor_id: null
				}
			})
		});
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
});

const EMPTY_REF_DATA = {
	currencies: [],
	incoterms: [],
	payment_terms: [],
	countries: [],
	ports: [],
	vendor_types: [{ code: 'PROCUREMENT', label: 'Procurement' }],
	po_types: [{ code: 'PROCUREMENT', label: 'Procurement' }]
};

const PO_ACCEPTED_PARTIAL = {
	id: 'uuid-partial',
	po_number: 'PO-20260401-0001',
	status: 'ACCEPTED',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-A',
	vendor_name: 'Vendor A',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	total_value: '500',
	currency: 'USD',
	current_milestone: null,
	marketplace: null,
	round_count: 1,
	// This flag drives the Partial pill: the PO status is ACCEPTED AND at least
	// one line ended REMOVED during negotiation.
	has_removed_line: true
};

const PO_ACCEPTED_FULL = {
	id: 'uuid-accepted',
	po_number: 'PO-20260401-0002',
	status: 'ACCEPTED',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-B',
	vendor_name: 'Vendor B',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	total_value: '1500',
	currency: 'USD',
	current_milestone: null,
	marketplace: null,
	round_count: 0,
	has_removed_line: false
};

const PO_MODIFIED_IN_FLIGHT = {
	id: 'uuid-modified',
	po_number: 'PO-20260401-0003',
	status: 'MODIFIED',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-C',
	vendor_name: 'Vendor C',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	total_value: '2500',
	currency: 'USD',
	current_milestone: null,
	marketplace: null,
	round_count: 1,
	has_removed_line: false
};

test('PO list renders Partial pill on ACCEPTED POs with removed lines', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_REF_DATA) });
	});
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				items: [PO_ACCEPTED_PARTIAL, PO_ACCEPTED_FULL, PO_MODIFIED_IN_FLIGHT],
				total: 3,
				page: 1,
				page_size: 20
			})
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	// Partial row: PN acceptance with at least one REMOVED line. Primary pill is
	// "Accepted"; a secondary "Partial" pill renders alongside it.
	const partialRow = page.locator('tbody tr', { hasText: 'PO-20260401-0001' });
	await expect(partialRow).toContainText('Accepted');
	await expect(partialRow.locator('[data-testid="po-status-partial"]')).toContainText('Partial');

	// Plain ACCEPTED row: no REMOVED lines, no Partial pill.
	const acceptedRow = page.locator('tbody tr', { hasText: 'PO-20260401-0002' });
	await expect(acceptedRow).toContainText('Accepted');
	await expect(acceptedRow.locator('[data-testid="po-status-partial"]')).toHaveCount(0);

	// MODIFIED row: in-flight negotiation surfaces the "Modified" pill.
	const modifiedRow = page.locator('tbody tr', { hasText: 'PO-20260401-0003' });
	await expect(modifiedRow).toContainText('Modified');
});

// ---------------------------------------------------------------------------
// Activity timeline -- copy and icon for each of the seven new event types
// ---------------------------------------------------------------------------

const PO_ID = 'uuid-events';

const PO_DETAIL = {
	id: PO_ID,
	po_number: 'PO-20260401-0009',
	status: 'MODIFIED',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-Z',
	vendor_name: 'Events Vendor',
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
	round_count: 1,
	last_actor_role: 'SM',
	brand_id: 'brand-default',
	brand_name: 'Default Brand',
	brand_legal_name: 'Default Brand LLC',
	brand_address: '1 Brand St',
	brand_country: 'US',
	brand_tax_id: ''
};

// All seven iter-058 events, each with a distinct category/target_role so the
// mocked entries exercise the full label mapping in PoActivityPanel.
const NEW_EVENT_ENTRIES = [
	{ id: 'e1', entity_type: 'PO', entity_id: PO_ID, event: 'PO_LINE_MODIFIED', category: 'LIVE', target_role: 'VENDOR', detail: 'PN-001: quantity', read_at: null, created_at: '2026-04-01T00:00:00+00:00' },
	{ id: 'e2', entity_type: 'PO', entity_id: PO_ID, event: 'PO_LINE_ACCEPTED', category: 'LIVE', target_role: 'VENDOR', detail: 'PN-001', read_at: null, created_at: '2026-04-01T00:01:00+00:00' },
	{ id: 'e3', entity_type: 'PO', entity_id: PO_ID, event: 'PO_LINE_REMOVED', category: 'LIVE', target_role: 'VENDOR', detail: 'PN-002', read_at: null, created_at: '2026-04-01T00:02:00+00:00' },
	{ id: 'e4', entity_type: 'PO', entity_id: PO_ID, event: 'PO_FORCE_ACCEPTED', category: 'LIVE', target_role: 'VENDOR', detail: 'PN-003', read_at: null, created_at: '2026-04-01T00:03:00+00:00' },
	{ id: 'e5', entity_type: 'PO', entity_id: PO_ID, event: 'PO_FORCE_REMOVED', category: 'LIVE', target_role: 'VENDOR', detail: 'PN-004', read_at: null, created_at: '2026-04-01T00:04:00+00:00' },
	{ id: 'e6', entity_type: 'PO', entity_id: PO_ID, event: 'PO_MODIFIED', category: 'ACTION_REQUIRED', target_role: 'VENDOR', detail: null, read_at: null, created_at: '2026-04-01T00:05:00+00:00' },
	{ id: 'e7', entity_type: 'PO', entity_id: PO_ID, event: 'PO_CONVERGED', category: 'LIVE', target_role: null, detail: 'ACCEPTED', read_at: null, created_at: '2026-04-01T00:06:00+00:00' }
];

test('activity timeline renders every new negotiation event with its label and icon', async ({ page }) => {
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_REF_DATA) });
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PO_DETAIL) });
	});
	// Entity-scoped activity query for this PO returns all seven events.
	await page.route('**/api/v1/activity/**', (route) => {
		const url = route.request().url();
		if (url.includes(`entity_id=${PO_ID}`)) {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(NEW_EVENT_ENTRIES) });
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto(`/po/${PO_ID}`);
	// Migrated to PoActivityPanel (iter 083): ActivityFeed renders list items;
	// icons are not carried through (PoActivityPanel omits icon glyphs).
	const feed = page.getByTestId('po-activity-feed');
	await expect(feed.locator('li')).toHaveCount(7);

	// Verify each event label appears in the feed.
	const expectedLabels = [
		'Line modified',
		'Line accepted',
		'Line removed',
		'Override: line force-accepted',
		'Override: line force-removed',
		'Round submitted',
		'Negotiation converged'
	];

	for (const label of expectedLabels) {
		await expect(feed.locator('.primary', { hasText: label })).toHaveCount(1);
	}
});
