import { test, expect } from '@playwright/test';

const PO_DRAFT = {
	id: 'uuid-draft',
	po_number: 'PO-20260316-0001',
	status: 'DRAFT',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-A',
	vendor_name: 'Vendor A',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-03-16T00:00:00+00:00',
	required_delivery_date: '2026-04-16T00:00:00+00:00',
	total_value: '1500',
	currency: 'USD'
};

const PO_PENDING = {
	id: 'uuid-pending',
	po_number: 'PO-20260316-0002',
	status: 'PENDING',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-B',
	vendor_name: 'Vendor B',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-03-16T00:00:00+00:00',
	required_delivery_date: '2026-04-16T00:00:00+00:00',
	total_value: '2500',
	currency: 'USD'
};

const PO_ACCEPTED = {
	id: 'uuid-accepted',
	po_number: 'PO-20260316-0003',
	status: 'ACCEPTED',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-C',
	vendor_name: 'Vendor C',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-03-16T00:00:00+00:00',
	required_delivery_date: '2026-04-16T00:00:00+00:00',
	total_value: '3500',
	currency: 'USD'
};

const EMPTY_REF_DATA = {
	currencies: [],
	incoterms: [],
	payment_terms: [],
	countries: [],
	ports: [],
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
};

async function mockCommonRoutes(page: import('@playwright/test').Page) {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(EMPTY_REF_DATA)
		});
	});
}

test('PO list page loads and shows table', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [PO_DRAFT, PO_PENDING, PO_ACCEPTED], total: 3, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('table');

	await expect(page.locator('h1')).toContainText('Purchase Orders');

	const rows = page.locator('tbody tr');
	await expect(rows).toHaveCount(3);

	await expect(page.locator('tbody')).toContainText('PO-20260316-0001');
	await expect(page.locator('tbody')).toContainText('PO-20260316-0002');
	await expect(page.locator('tbody')).toContainText('PO-20260316-0003');

	await expect(page.locator('tbody')).toContainText('Vendor A');
	await expect(page.locator('tbody')).toContainText('Vendor B');
	await expect(page.locator('tbody')).toContainText('Vendor C');

	// StatusPill renders capitalized status text
	await expect(page.locator('tbody')).toContainText('Draft');
	await expect(page.locator('tbody')).toContainText('Pending');
	await expect(page.locator('tbody')).toContainText('Accepted');
});

test('status filter narrows displayed POs', async ({ page }) => {
	let lastUrl = '';

	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		lastUrl = route.request().url();
		const url = new URL(route.request().url());
		const status = url.searchParams.get('status');

		if (status === 'DRAFT') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ items: [PO_DRAFT], total: 1, page: 1, page_size: 20 })
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ items: [PO_DRAFT, PO_PENDING, PO_ACCEPTED], total: 3, page: 1, page_size: 20 })
			});
		}
	});

	await page.goto('/po');
	await page.waitForSelector('table');
	await expect(page.locator('tbody tr')).toHaveCount(3);

	await page.locator('.filter-bar select').first().selectOption('DRAFT');
	await page.waitForSelector('tbody tr');

	await expect(page.locator('tbody tr')).toHaveCount(1);
	await expect(lastUrl).toContain('status=DRAFT');
});

test('click row navigates to detail', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		const url = route.request().url();
		// Detail page will also call /api/v1/po/{id}; return minimal valid response
		if (url.includes('/uuid-draft') && !url.match(/\/po\??/)) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					...PO_DRAFT,
					ship_to_address: '',
					payment_terms: 'NET30',
					terms_and_conditions: '',
					incoterm: 'FOB',
					port_of_loading: 'Shanghai',
					port_of_discharge: 'Los Angeles',
					country_of_origin: 'CN',
					country_of_destination: 'US',
					line_items: [],
					rejection_history: [],
					created_at: '2026-03-16T00:00:00+00:00',
					updated_at: '2026-03-16T00:00:00+00:00'
				})
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ items: [PO_DRAFT], total: 1, page: 1, page_size: 20 })
			});
		}
	});

	await page.goto('/po');
	await page.waitForSelector('tbody tr');

	await page.locator('tbody tr').first().click();
	await page.waitForURL('**/po/uuid-draft');

	expect(page.url()).toContain('/po/uuid-draft');
});

test('empty list shows message', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await expect(page.locator('body')).toContainText('No purchase orders found');
});

test('filter bar renders search input and dropdowns', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('.filter-bar');

	await expect(page.locator('.filter-bar input[type="text"]')).toBeVisible();
	await expect(page.locator('.filter-bar select')).toHaveCount(4);
});

test('pagination controls appear when total exceeds page size', async ({ page }) => {
	await mockCommonRoutes(page);
	const items = Array.from({ length: 20 }, (_, i) => ({
		...PO_DRAFT,
		id: `uuid-${i}`,
		po_number: `PO-2026-${String(i).padStart(4, '0')}`
	}));
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items, total: 45, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('.pagination');

	await expect(page.locator('.pagination-info')).toContainText('Showing 1–20 of 45');
	await expect(page.locator('.pagination-controls button').last()).not.toBeDisabled();
});

test('URL state preserved on navigation', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		const url = new URL(route.request().url());
		const status = url.searchParams.get('status');
		const items = status === 'DRAFT' ? [PO_DRAFT] : [PO_DRAFT, PO_PENDING, PO_ACCEPTED];
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items, total: items.length, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po?status=DRAFT&search=foo');
	await page.waitForSelector('.filter-bar');

	await expect(page.locator('.filter-bar input[type="text"]')).toHaveValue('foo');
	await expect(page.locator('.filter-bar select').first()).toHaveValue('DRAFT');
});

// ---------------------------------------------------------------------------
// Iteration 22 — Production column and milestone filter
// ---------------------------------------------------------------------------

const PO_ACCEPTED_PROCUREMENT = {
	id: 'uuid-accepted-proc',
	po_number: 'PO-20260401-0010',
	status: 'ACCEPTED',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-D',
	vendor_name: 'Vendor D',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	total_value: '8000',
	currency: 'USD',
	current_milestone: 'RAW_MATERIALS',
};

const PO_DRAFT_NO_MILESTONE = {
	id: 'uuid-draft-no-ms',
	po_number: 'PO-20260401-0011',
	status: 'DRAFT',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-E',
	vendor_name: 'Vendor E',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	total_value: '1000',
	currency: 'USD',
	current_milestone: null,
};

test('PO list shows production column for accepted procurement PO', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [PO_ACCEPTED_PROCUREMENT], total: 1, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('table');

	// The Production column header must be present
	await expect(page.locator('thead')).toContainText('Production');
	// The milestone label for RAW_MATERIALS must appear in the row
	await expect(page.locator('tbody')).toContainText('Raw Materials');
});

test('PO list shows blank production cell for non-accepted PO', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [PO_DRAFT_NO_MILESTONE], total: 1, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('table');

	// No milestone label text should appear for a DRAFT PO with no milestone
	await expect(page.locator('tbody .milestone-cell').first()).toContainText('');
	await expect(page.locator('tbody')).not.toContainText('Raw Materials');
});

test('milestone filter dropdown exists with milestone options', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('.filter-bar');

	// The filter bar contains a milestone select with known option labels
	const milestoneSelect = page.locator('.filter-bar select').last();
	await expect(milestoneSelect).toBeVisible();
	await expect(milestoneSelect).toContainText('Raw Materials');
	await expect(milestoneSelect).toContainText('Production Started');
	await expect(milestoneSelect).toContainText('QC Passed');
});
