import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Shared fixture data
// ---------------------------------------------------------------------------

const PO_ID = 'uuid-1';

const REFERENCE_DATA = {
	currencies: [{ code: 'USD', label: 'US Dollar' }, { code: 'EUR', label: 'Euro' }, { code: 'GBP', label: 'British Pound' }],
	incoterms: [{ code: 'FOB', label: 'Free on Board' }, { code: 'CIF', label: 'Cost, Insurance and Freight' }],
	payment_terms: [{ code: 'TT', label: 'Telegraphic Transfer' }, { code: 'LC', label: 'Letter of Credit' }],
	countries: [{ code: 'US', label: 'United States' }, { code: 'CN', label: 'China' }],
	ports: [{ code: 'CNSHA', label: 'Shanghai' }, { code: 'USLAX', label: 'Los Angeles' }]
};

const LINE_ITEM = {
	part_number: 'PART-001',
	description: 'Steel bolt',
	quantity: 100,
	uom: 'pcs',
	unit_price: '15',
	hs_code: '7318.15',
	country_of_origin: 'CN'
};

function makePO(status: string, extra: object = {}) {
	return {
		id: PO_ID,
		po_number: 'PO-20260316-0001',
		status,
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
	// Trade details
	await expect(page.locator('body')).toContainText('FOB');
	await expect(page.locator('body')).toContainText('CNSHA');
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

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	await expect(page.locator('a[href*="/edit"]')).toBeVisible();
	await expect(page.getByRole('button', { name: 'Submit' })).toBeVisible();
});

test('pending PO shows Accept and Reject buttons', async ({ page }) => {
	const po = makePO('PENDING');

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	await expect(page.getByRole('button', { name: 'Accept' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible();
});

test('accepted PO shows read-only view', async ({ page }) => {
	const po = makePO('ACCEPTED');

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	await expect(page.locator('body')).toContainText('accepted');
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
			body: JSON.stringify([{ id: 'v1', name: 'Test Vendor', country: 'US', status: 'ACTIVE' }])
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
	await page.waitForSelector('form');

	// Fill required header fields
	await page.selectOption('#vendor_id', 'v1');
	await page.selectOption('#currency', 'USD');
	await page.fill('#issued_date', '2026-03-16');
	await page.fill('#required_delivery_date', '2026-04-16');

	// Fill part_number with whitespace to bypass HTML required but fail JS trim() check
	await page.locator('input[placeholder="Part No."]').fill('   ');

	// Remove HTML validation so JS validation runs
	await page.evaluate(() => {
		document.querySelector('form')?.setAttribute('novalidate', '');
	});

	await page.getByRole('button', { name: 'Create PO' }).click();

	await expect(page.locator('.error-message')).toContainText('Part Number is required');
});

test('create PO form rejects quantity <= 0', async ({ page }) => {
	// Mock active vendors for the vendor dropdown
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'v1', name: 'Test Vendor', country: 'US', status: 'ACTIVE' }])
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
	await page.waitForSelector('form');

	// Fill required header fields
	await page.selectOption('#vendor_id', 'v1');
	await page.selectOption('#currency', 'USD');
	await page.fill('#issued_date', '2026-03-16');
	await page.fill('#required_delivery_date', '2026-04-16');

	// Fill part_number so it passes that check
	await page.locator('input[placeholder="Part No."]').fill('PART-001');

	// Set quantity to 0 via JS to bypass HTML min=1 constraint
	const qtyInput = page.locator('input[placeholder="Qty"]');
	await qtyInput.fill('0');
	await qtyInput.evaluate((el: HTMLInputElement) => {
		el.value = '0';
		el.dispatchEvent(new Event('input', { bubbles: true }));
	});

	// Remove HTML validation so the form submits and JS validation runs
	await page.evaluate(() => {
		document.querySelector('form')?.setAttribute('novalidate', '');
	});

	await page.getByRole('button', { name: 'Create PO' }).click();

	await expect(page.locator('.error-message')).toContainText('Quantity must be greater than 0');
});

test('reject modal requires non-empty comment', async ({ page }) => {
	const po = makePO('PENDING');

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('h1');

	await page.getByRole('button', { name: 'Reject' }).click();
	await page.waitForSelector('.dialog');

	// Confirm button is disabled when comment is empty
	const confirmBtn = page.locator('.dialog .btn-danger');
	await expect(confirmBtn).toBeDisabled();

	// Type a comment
	await page.locator('.dialog textarea').fill('Price is too high');

	// Confirm button becomes enabled
	await expect(confirmBtn).toBeEnabled();
});

test('full cycle: create, submit, reject, revise, resubmit, accept', async ({ page }) => {
	// Mutable state tracking current PO status for the detail endpoint
	let currentPO = makePO('DRAFT');

	// Mock the list endpoint for navigation after create
	await page.route('**/api/v1/po', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(currentPO)
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([currentPO])
			});
		}
	});

	// Mock detail GET and PUT on the same route (Playwright checks routes in
	// reverse registration order; a second handler for the same pattern would
	// shadow the first and route.continue() sends to the network, not the next handler)
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		const method = route.request().method();
		if (method === 'GET') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(currentPO)
			});
		} else if (method === 'PUT') {
			currentPO = makePO('REVISED');
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(currentPO)
			});
		} else {
			route.fallback();
		}
	});

	// Mock submit action
	await page.route(`**/api/v1/po/${PO_ID}/submit`, (route) => {
		currentPO = makePO('PENDING');
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(currentPO)
		});
	});

	// Mock reject action
	await page.route(`**/api/v1/po/${PO_ID}/reject`, (route) => {
		currentPO = makePO('REJECTED', {
			rejection_history: [{ comment: 'Need revision', rejected_at: '2026-03-16T10:00:00+00:00' }]
		});
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(currentPO)
		});
	});

	// Mock resubmit action
	await page.route(`**/api/v1/po/${PO_ID}/resubmit`, (route) => {
		currentPO = makePO('PENDING');
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(currentPO)
		});
	});

	// Mock accept action
	await page.route(`**/api/v1/po/${PO_ID}/accept`, (route) => {
		currentPO = makePO('ACCEPTED');
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(currentPO)
		});
	});

	// Mock active vendors for the vendor dropdown (new and edit pages)
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'vendor-uuid-1', name: 'Acme Corp', country: 'CN', status: 'ACTIVE' }])
		});
	});

	// Mock reference data for PO form dropdowns
	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});

	// Step 1: Create PO
	await page.goto('/po/new');
	await page.waitForSelector('form');
	await page.selectOption('#vendor_id', 'vendor-uuid-1');
	await page.selectOption('#currency', 'USD');
	await page.fill('#issued_date', '2026-03-16');
	await page.fill('#required_delivery_date', '2026-04-16');
	await page.locator('input[placeholder="Part No."]').fill('PART-001');

	await page.getByRole('button', { name: 'Create PO' }).click();
	await page.waitForURL(`**/po/${PO_ID}`);
	await page.waitForSelector('h1');
	await expect(page.locator('body')).toContainText('Draft');

	// Step 2: Submit
	await page.getByRole('button', { name: 'Submit' }).click();
	await expect(page.locator('body')).toContainText('Pending');

	// Step 3: Reject
	await page.getByRole('button', { name: 'Reject' }).click();
	await page.waitForSelector('.dialog');
	await page.locator('.dialog textarea').fill('Need revision');
	await page.locator('.dialog .btn-danger').click();
	await expect(page.locator('body')).toContainText('Rejected');
	await expect(page.locator('body')).toContainText('Need revision');

	// Step 4: Edit (navigate to edit page)
	await page.locator('a[href*="/edit"]').click();
	await page.waitForURL(`**/po/${PO_ID}/edit`);
	await page.waitForSelector('form');

	// Step 5: Save revision
	await page.getByRole('button', { name: 'Save & Revise' }).click();
	await page.waitForURL(`**/po/${PO_ID}`);
	await expect(page.locator('body')).toContainText('Revised');

	// Step 6: Resubmit
	await page.getByRole('button', { name: 'Resubmit' }).click();
	await expect(page.locator('body')).toContainText('Pending');

	// Step 7: Accept
	await page.getByRole('button', { name: 'Accept' }).click();
	await expect(page.locator('body')).toContainText('Accepted');
	await expect(page.locator('body')).toContainText('accepted');
});

test('download PDF button is visible for every PO status', async ({ page }) => {
	for (const status of ['DRAFT', 'PENDING', 'ACCEPTED', 'REJECTED', 'REVISED']) {
		const po = makePO(status);
		await mockDetail(page, po);
		await page.goto(`/po/${PO_ID}`);
		await page.waitForSelector('h1');
		await expect(page.getByRole('button', { name: 'Download PDF' })).toBeVisible();
	}
});

test('PO form renders dropdown fields from reference data', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{ id: 'vendor-uuid-1', name: 'Acme Corp', country: 'CN', status: 'ACTIVE' }])
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
	await page.waitForSelector('form');

	// Verify currency is a select with options from reference data
	const currencySelect = page.locator('#currency');
	await expect(currencySelect).toBeVisible();
	const currencyOptions = currencySelect.locator('option');
	// "Select..." placeholder + reference data items
	await expect(currencyOptions).toHaveCount(4); // placeholder + USD + EUR + GBP

	// Verify incoterm is a select
	const incotermSelect = page.locator('#incoterm');
	await expect(incotermSelect).toBeVisible();

	// Verify port_of_loading is a select
	const polSelect = page.locator('#port_of_loading');
	await expect(polSelect).toBeVisible();

	// Verify buyer_country is a select with default value pre-selected
	const bcSelect = page.locator('#buyer_country');
	await expect(bcSelect).toHaveValue('US');
});
