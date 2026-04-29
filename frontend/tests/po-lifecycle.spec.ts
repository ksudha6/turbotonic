import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Activity mocks — NotificationBell calls unread-count on every page load;
// detail pages with PoActivityPanel/InvoiceActivityPanel call the entity activity endpoint.
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

// ---------------------------------------------------------------------------
// Shared fixture data
// ---------------------------------------------------------------------------

const PO_ID = 'uuid-1';

const REFERENCE_DATA = {
	currencies: [{ code: 'USD', label: 'US Dollar' }, { code: 'EUR', label: 'Euro' }, { code: 'GBP', label: 'British Pound' }],
	incoterms: [{ code: 'FOB', label: 'Free on Board' }, { code: 'CIF', label: 'Cost, Insurance and Freight' }],
	payment_terms: [{ code: 'TT', label: 'Telegraphic Transfer' }, { code: 'LC', label: 'Letter of Credit' }],
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
};

const LINE_ITEM = {
	part_number: 'PART-001',
	description: 'Steel bolt',
	quantity: 100,
	uom: 'pcs',
	unit_price: '15',
	hs_code: '7318.15',
	country_of_origin: 'CN',
	status: 'PENDING'
};

function makePO(status: string, extra: object = {}) {
	return {
		id: PO_ID,
		po_number: 'PO-20260316-0001',
		status,
		po_type: 'PROCUREMENT',
		vendor_id: 'vendor-uuid-1',
		vendor_name: 'Acme Corp',
		vendor_country: 'CN',
		buyer_name: 'TurboTonic Ltd',
		buyer_country: 'US',
		ship_to_address: '123 Main St',
		payment_terms: 'TT',
		currency: 'USD',
		issued_date: '2026-03-16T00:00:00+00:00',
		required_delivery_date: '2026-04-16T00:00:00+00:00',
		terms_and_conditions: 'Standard terms',
		incoterm: 'FOB',
		port_of_loading: 'CNSHA',
		port_of_discharge: 'USLAX',
		country_of_origin: 'CN',
		country_of_destination: 'US',
		line_items: [LINE_ITEM],
		rejection_history: [],
		total_value: '1500',
		created_at: '2026-03-16T00:00:00+00:00',
		updated_at: '2026-03-16T00:00:00+00:00',
		...extra
	};
}

function mockDetail(page: import('@playwright/test').Page, po: object) {
	return page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		// Only respond to exact detail URL, not action sub-routes
		const url = route.request().url();
		const path = new URL(url).pathname;
		if (path === `/api/v1/po/${PO_ID}`) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(po)
			});
		} else {
			route.continue();
		}
	});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test('detail view shows header, trade, line items, status pill', async ({ page }) => {
	const po = makePO('DRAFT');

	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	await expect(page.locator('h1')).toContainText('PO-20260316-0001');
	// StatusPill renders capitalized text
	await expect(page.locator('body')).toContainText('Draft');
	// Vendor
	await expect(page.locator('body')).toContainText('Acme Corp');
	// Trade details — labels are resolved via reference data
	await expect(page.locator('body')).toContainText('Free on Board');
	await expect(page.locator('body')).toContainText('Shanghai, China');
	// Line item
	await expect(page.locator('body')).toContainText('PART-001');
	await expect(page.locator('body')).toContainText('100');
	await expect(page.locator('body')).toContainText('15.00');
});

test('detail view shows rejection history when present', async ({ page }) => {
	const po = makePO('REJECTED', {
		rejection_history: [
			{ comment: 'Price too high', rejected_at: '2026-03-10T00:00:00+00:00' },
			{ comment: 'Wrong vendor', rejected_at: '2026-03-12T00:00:00+00:00' }
		]
	});

	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	await expect(page.locator('body')).toContainText('Price too high');
	await expect(page.locator('body')).toContainText('Wrong vendor');
});

test('draft PO shows Edit and Submit buttons', async ({ page }) => {
	const po = makePO('DRAFT');

	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-detail-header').waitFor();

	// Iter 077: Edit and Submit live inside the action rail testids; the rail
	// renders both inline (>=768px) and sticky-bottom (<768px) so .first() picks
	// the one that's visible at the current viewport.
	const rail = page.getByTestId('po-action-rail').first();
	await expect(rail.getByTestId('po-action-edit')).toBeVisible();
	await expect(rail.getByTestId('po-action-submit')).toBeVisible();
});

test('pending PO shows Accept button and per-line negotiation controls', async ({ page }) => {
	// Iter 057: the top-level Reject button is gone. Vendors now work through
	// per-line Modify / Accept / Remove on each line item and then Submit Response.
	const po = makePO('PENDING');

	// Override beforeEach SM mock — LIFO priority means this handler runs first.
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 'test-user-id', username: 'test-vendor', display_name: 'Test Vendor', role: 'VENDOR', status: 'ACTIVE', vendor_id: 'vendor-1' } }) });
	});

	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-detail-header').waitFor();

	// Iter 077: Accept is the primary action on the rail for VENDOR + PENDING.
	const rail = page.getByTestId('po-action-rail').first();
	await expect(rail.getByTestId('po-action-accept')).toBeVisible();
	// Reject is removed in iter 056/057. Per-line Modify and Remove take its place.
	await expect(page.locator('[data-testid="po-line-action-modify-PART-001"]')).toBeVisible();
});

test('accepted PO shows read-only view', async ({ page }) => {
	const po = makePO('ACCEPTED');

	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route('**/api/v1/invoices/po/*/remaining', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ po_id: PO_ID, lines: [] }) });
	});
	await page.route('**/api/v1/po/*/milestones', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	await expect(page.locator('body')).toContainText('Accepted');
	await expect(page.getByRole('button', { name: 'Submit' })).toHaveCount(0);
	await expect(page.getByRole('button', { name: 'Accept' })).toHaveCount(0);
	await expect(page.getByRole('button', { name: 'Reject' })).toHaveCount(0);
	await expect(page.locator('a[href*="/edit"]')).toHaveCount(0);
});

test('create PO form validates empty part number', async ({ page }) => {
	// Mock active vendors for the vendor dropdown
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'v1', name: 'Test Vendor', country: 'US', status: 'ACTIVE', vendor_type: 'PROCUREMENT' }])
		});
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	// Fill required header fields (form already has novalidate)
	await page.getByTestId('po-form-vendor').selectOption('v1');
	await page.getByTestId('po-form-currency').selectOption('USD');
	await page.getByTestId('po-form-issued-date').fill('2026-03-16');
	await page.getByTestId('po-form-required-delivery-date').fill('2026-04-16');

	// Whitespace-only part_number fails JS trim() check
	await page.getByTestId('po-form-line-0-part-number').fill('   ');

	await page.getByTestId('po-form-submit').click();

	await expect(page.getByTestId('po-form-error-banner')).toContainText('Part Number is required');
});

test('create PO form rejects quantity <= 0', async ({ page }) => {
	// Mock active vendors for the vendor dropdown
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'v1', name: 'Test Vendor', country: 'US', status: 'ACTIVE', vendor_type: 'PROCUREMENT' }])
		});
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	// Fill required header fields (form already has novalidate)
	await page.getByTestId('po-form-vendor').selectOption('v1');
	await page.getByTestId('po-form-currency').selectOption('USD');
	await page.getByTestId('po-form-issued-date').fill('2026-03-16');
	await page.getByTestId('po-form-required-delivery-date').fill('2026-04-16');

	// Fill part_number so it passes that check
	await page.getByTestId('po-form-line-0-part-number').fill('PART-001');

	// Set quantity to 0 (form parses with parseInt + non-positive guard)
	await page.getByTestId('po-form-line-0-quantity').fill('0');

	await page.getByTestId('po-form-submit').click();

	await expect(page.getByTestId('po-form-error-banner')).toContainText('Quantity must be greater than 0');
});

// Iter 056 removed the PO-level reject endpoint and the single-shot accept-lines flow.
// The reject-modal test and the full-cycle reject/revise/resubmit test were tied to
// those endpoints and are removed here. Iter 057 rebuilds the negotiation flow end-to-end
// with line-level modify / accept / remove / submit-response and brings back lifecycle coverage.


test('download PDF button is reachable for every PO status', async ({ page }) => {
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REFERENCE_DATA) });
	});
	await page.route('**/api/v1/invoices/po/*/remaining', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ po_id: PO_ID, lines: [] }) });
	});
	await page.route('**/api/v1/po/*/milestones', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	// Iter 077: Download PDF lives on the action rail. When primary actions are
	// present it sits in the overflow menu; for read-only roles it renders solo.
	// SM is the beforeEach default -- DRAFT/REJECTED/REVISED expose primary
	// actions, so we open the overflow first; ACCEPTED/PENDING render no SM
	// primary so PDF is solo (or in PENDING's case the rail is empty for SM).
	for (const status of ['DRAFT', 'PENDING', 'ACCEPTED', 'REJECTED', 'REVISED']) {
		const po = makePO(status);
		await mockDetail(page, po);
		await page.goto(`/po/${PO_ID}`);
		await page.getByTestId('po-detail-header').waitFor();
		const rail = page.getByTestId('po-action-rail').first();
		const overflow = rail.getByTestId('po-action-overflow');
		if ((await overflow.count()) > 0) {
			await overflow.click();
		}
		await expect(rail.getByTestId('po-action-download-pdf')).toBeVisible();
	}
});

// ---------------------------------------------------------------------------
// Iteration 20 — HS code validation
// ---------------------------------------------------------------------------

test('HS code input shows error for invalid value', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'v1', name: 'Test Vendor', country: 'US', status: 'ACTIVE', vendor_type: 'PROCUREMENT' }])
		});
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	// Enter a value that fails the HS code pattern (letters, fewer than 4 chars)
	await page.getByTestId('po-form-line-0-hs-code').fill('AB');

	// Error message must appear via FormField on the same field
	const hsCodeField = page.getByTestId('po-form-line-0-hs-code-field');
	await expect(hsCodeField.getByRole('alert')).toBeVisible();
	await expect(hsCodeField.getByRole('alert')).toContainText('digits and dots');
});

test('submit button disabled when HS code invalid', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'v1', name: 'Test Vendor', country: 'US', status: 'ACTIVE', vendor_type: 'PROCUREMENT' }])
		});
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	// Enter an invalid HS code
	await page.getByTestId('po-form-line-0-hs-code').fill('AB');

	// Submit button must be disabled while HS code error is present
	await expect(page.getByTestId('po-form-submit')).toBeDisabled();
});

test('PO form renders dropdown fields from reference data', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'vendor-uuid-1', name: 'Acme Corp', country: 'CN', status: 'ACTIVE', vendor_type: 'PROCUREMENT' }])
		});
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	// Verify currency is a select with options from reference data
	const currencySelect = page.getByTestId('po-form-currency');
	await expect(currencySelect).toBeVisible();
	const currencyOptions = currencySelect.locator('option');
	// "Select..." placeholder + reference data items
	await expect(currencyOptions).toHaveCount(4); // placeholder + USD + EUR + GBP

	// Verify incoterm is a select
	await expect(page.getByTestId('po-form-incoterm')).toBeVisible();

	// Verify port_of_loading is a select
	await expect(page.getByTestId('po-form-port-loading')).toBeVisible();

	// Verify buyer_country is a select with default value pre-selected
	await expect(page.getByTestId('po-form-buyer-country')).toHaveValue('US');
});

// ---------------------------------------------------------------------------
// Iteration 36 — Marketplace dropdown
// ---------------------------------------------------------------------------

test('PO form renders marketplace dropdown with correct options', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'vendor-uuid-1', name: 'Acme Corp', country: 'CN', status: 'ACTIVE', vendor_type: 'PROCUREMENT' }])
		});
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	const marketplaceSelect = page.getByTestId('po-form-marketplace');
	await expect(marketplaceSelect).toBeVisible();

	// 1 empty (None) option + 4 marketplace values = 5 total
	const options = marketplaceSelect.locator('option');
	await expect(options).toHaveCount(5);

	// Assert each expected value is present
	for (const value of ['', 'AMZ', '3PL_1', '3PL_2', '3PL_3']) {
		await expect(marketplaceSelect.locator(`option[value="${value}"]`)).toHaveCount(1);
	}
});

test('PO form submits marketplace value', async ({ page }) => {
	let capturedBody: Record<string, unknown> | null = null;

	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'vendor-uuid-1', name: 'Acme Corp', country: 'CN', status: 'ACTIVE', vendor_type: 'PROCUREMENT' }])
		});
	});

	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});

	await page.route('**/api/v1/po/', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			capturedBody = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(makePO('DRAFT'))
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	// Fill required header fields
	await page.getByTestId('po-form-vendor').selectOption('vendor-uuid-1');
	await page.getByTestId('po-form-currency').selectOption('USD');
	await page.getByTestId('po-form-issued-date').fill('2026-03-16');
	await page.getByTestId('po-form-required-delivery-date').fill('2026-04-16');

	// Fill required line item field
	await page.getByTestId('po-form-line-0-part-number').fill('PART-001');

	// Select marketplace
	await page.getByTestId('po-form-marketplace').selectOption('AMZ');

	await page.getByTestId('po-form-submit').click();
	await page.waitForURL(`**/po/${PO_ID}`);

	// Assert the POST body included the selected marketplace
	expect(capturedBody).not.toBeNull();
	expect((capturedBody as Record<string, unknown>)['marketplace']).toBe('AMZ');
});
