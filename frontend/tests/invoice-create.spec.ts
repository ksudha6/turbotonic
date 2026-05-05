import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

// Iter 088 — Phase 4.3 Tier 3. Verifies the new InvoiceCreateModal that opens
// from PoActionRail's "Create Invoice" on a VENDOR / ACCEPTED / PROCUREMENT PO.
// The modal replaces the legacy CreateInvoiceDialog from frontend/src/lib/components/.

const PO_ID = 'po-create-invoice-1';

const REFERENCE_DATA = {
	currencies: [{ code: 'USD', label: 'US Dollar' }],
	incoterms: [{ code: 'FOB', label: 'Free on Board' }],
	payment_terms: [{ code: 'NET30', label: 'Net 30', has_advance: false }],
	countries: [
		{ code: 'US', label: 'United States' },
		{ code: 'CN', label: 'China' }
	],
	ports: [
		{ code: 'CNSHA', label: 'Shanghai' },
		{ code: 'USLAX', label: 'Los Angeles' }
	],
	vendor_types: [{ code: 'PROCUREMENT', label: 'Procurement' }],
	po_types: [{ code: 'PROCUREMENT', label: 'Procurement' }]
};

const ACCEPTED_PO = {
	id: PO_ID,
	po_number: 'PO-20260401-9001',
	status: 'ACCEPTED',
	po_type: 'PROCUREMENT',
	vendor_id: 'vendor-1',
	vendor_name: 'Acme Corp',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	ship_to_address: '123 Main St',
	payment_terms: 'NET30',
	currency: 'USD',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	terms_and_conditions: '',
	incoterm: 'FOB',
	port_of_loading: 'CNSHA',
	port_of_discharge: 'USLAX',
	country_of_origin: 'CN',
	country_of_destination: 'US',
	marketplace: null,
	line_items: [
		{
			part_number: 'PN-001',
			description: 'Widget A',
			quantity: 10,
			uom: 'pcs',
			unit_price: '15.00',
			hs_code: '7318.15',
			country_of_origin: 'CN',
			product_id: null,
			status: 'ACCEPTED',
			history: []
		},
		{
			part_number: 'PN-002',
			description: 'Widget B',
			quantity: 5,
			uom: 'pcs',
			unit_price: '20.00',
			hs_code: '7318.15',
			country_of_origin: 'CN',
			product_id: null,
			status: 'ACCEPTED',
			history: []
		}
	],
	rejection_history: [],
	total_value: '250.00',
	created_at: '2026-04-01T00:00:00+00:00',
	updated_at: '2026-04-01T00:00:00+00:00',
	round_count: 0,
	last_actor_role: null,
	advance_paid_at: null,
	has_removed_line: false,
	current_milestone: null,
	brand_id: 'brand-default',
	brand_name: 'Default Brand',
	brand_legal_name: 'Default Brand LLC',
	brand_address: '1 Brand St',
	brand_country: 'US',
	brand_tax_id: ''
};

const VENDOR_USER = {
	id: 'u-vendor',
	username: 'vendor',
	display_name: 'Vendor User',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-1'
};

const REMAINING_RESPONSE = {
	po_id: PO_ID,
	lines: [
		{ part_number: 'PN-001', description: 'Widget A', ordered: 10, invoiced: 3, remaining: 7 },
		{ part_number: 'PN-002', description: 'Widget B', ordered: 5, invoiced: 5, remaining: 0 }
	]
};

const NEW_INVOICE = {
	id: 'inv-created-1',
	invoice_number: 'INV-20260429-0001',
	po_id: PO_ID,
	status: 'DRAFT',
	payment_terms: 'NET30',
	currency: 'USD',
	line_items: [{ part_number: 'PN-001', description: 'Widget A', quantity: 7, uom: 'pcs', unit_price: '15.00' }],
	subtotal: '105.00',
	dispute_reason: '',
	created_at: '2026-04-29T00:00:00+00:00',
	updated_at: '2026-04-29T00:00:00+00:00'
};

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

async function setupDetailPage(page: Page) {
	// Catch-all first (lowest LIFO priority).
	await page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: VENDOR_USER })
		});
	});
	await page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ count: 0 })
		});
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/po/*/documents', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/po/*/milestones', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/invoices/po/*/remaining', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REMAINING_RESPONSE)
		});
	});
	// PO detail must not match the milestones / remaining nested URLs above.
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		const path = new URL(route.request().url()).pathname;
		if (path === `/api/v1/po/${PO_ID}`) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(ACCEPTED_PO)
			});
		} else {
			route.continue();
		}
	});
	// Invoice detail target after creation.
	await page.route(`**/api/v1/invoices/${NEW_INVOICE.id}`, (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(NEW_INVOICE)
		});
	});
}

async function clickCreateInvoice(page: Page) {
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();
	const rail = page.getByTestId('po-action-rail').first();
	await rail.getByTestId('po-action-create-invoice').click();
}

// ---------------------------------------------------------------------------
// Specs
// ---------------------------------------------------------------------------

test('VENDOR clicking Create Invoice opens InvoiceCreateModal with role=dialog', async ({ page }) => {
	await setupDetailPage(page);
	await clickCreateInvoice(page);

	const modal = page.getByTestId('invoice-create-modal');
	await expect(modal).toBeVisible();
	await expect(modal).toHaveAttribute('role', 'dialog');
	await expect(modal).toHaveAttribute('aria-modal', 'true');
	await expect(modal.getByRole('heading', { name: 'Create Invoice' })).toBeVisible();
});

test('modal renders one row per remaining line with qty pre-filled to remaining', async ({ page }) => {
	await setupDetailPage(page);
	await clickCreateInvoice(page);

	// Scope to the desktop table to dodge the duplicate testid that the mobile
	// card layout renders for the same data (display:none at desktop).
	const table = page.getByTestId('invoice-create-table');
	const row1 = table.getByTestId('invoice-create-row-PN-001');
	const row2 = table.getByTestId('invoice-create-row-PN-002');
	await expect(row1).toBeVisible();
	await expect(row2).toBeVisible();

	const qty1 = table.getByTestId('invoice-create-qty-input-PN-001');
	const qty2 = table.getByTestId('invoice-create-qty-input-PN-002');
	await expect(qty1).toHaveValue('7');
	await expect(qty2).toHaveValue('0');
});

test('rows with remaining=0 render the qty input as disabled', async ({ page }) => {
	await setupDetailPage(page);
	await clickCreateInvoice(page);

	const table = page.getByTestId('invoice-create-table');
	const qty2 = table.getByTestId('invoice-create-qty-input-PN-002');
	await expect(qty2).toBeDisabled();
});

test('Create button disabled when every quantity parses to zero', async ({ page }) => {
	await setupDetailPage(page);
	await clickCreateInvoice(page);

	const modal = page.getByTestId('invoice-create-modal');
	const table = page.getByTestId('invoice-create-table');
	const qty1 = table.getByTestId('invoice-create-qty-input-PN-001');

	// PN-002 starts at "0" already; emptying PN-001 makes parseQty return 0 too.
	await qty1.fill('0');
	await expect(modal.getByTestId('invoice-create-confirm')).toBeDisabled();
});

test('Cancel closes the modal without firing createInvoice', async ({ page }) => {
	await setupDetailPage(page);

	let createCalled = false;
	await page.route('**/api/v1/invoices/', (route) => {
		if (route.request().method() === 'POST') {
			createCalled = true;
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(NEW_INVOICE)
			});
		} else {
			route.continue();
		}
	});

	await clickCreateInvoice(page);
	await expect(page.getByTestId('invoice-create-modal')).toBeVisible();
	await page.getByTestId('invoice-create-cancel').click();
	await expect(page.getByTestId('invoice-create-modal')).toHaveCount(0);
	expect(createCalled).toBe(false);
});

test('Create posts only non-zero rows and navigates to /invoice/{id}', async ({ page }) => {
	await setupDetailPage(page);

	let postedBody: { po_id?: string; line_items?: Array<{ part_number: string; quantity: number }> } | null = null;
	await page.route('**/api/v1/invoices/', (route) => {
		if (route.request().method() === 'POST') {
			const raw = route.request().postData();
			postedBody = raw ? JSON.parse(raw) : null;
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(NEW_INVOICE)
			});
		} else {
			route.continue();
		}
	});

	await clickCreateInvoice(page);
	const table = page.getByTestId('invoice-create-table');
	const qty1 = table.getByTestId('invoice-create-qty-input-PN-001');
	await qty1.fill('4');

	await page.getByTestId('invoice-create-confirm').click();

	await page.waitForURL(`**/invoice/${NEW_INVOICE.id}`);

	expect(postedBody).not.toBeNull();
	expect(postedBody!.po_id).toBe(PO_ID);
	expect(postedBody!.line_items).toEqual([{ part_number: 'PN-001', quantity: 4 }]);
});

test('Create clamps a quantity above remaining at submit time', async ({ page }) => {
	await setupDetailPage(page);

	let postedBody: { po_id?: string; line_items?: Array<{ part_number: string; quantity: number }> } | null = null;
	await page.route('**/api/v1/invoices/', (route) => {
		if (route.request().method() === 'POST') {
			const raw = route.request().postData();
			postedBody = raw ? JSON.parse(raw) : null;
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(NEW_INVOICE)
			});
		} else {
			route.continue();
		}
	});

	await clickCreateInvoice(page);
	const table = page.getByTestId('invoice-create-table');
	const qty1 = table.getByTestId('invoice-create-qty-input-PN-001');
	// Type a value greater than remaining (7) — submit should clamp to 7.
	await qty1.fill('99');

	await page.getByTestId('invoice-create-confirm').click();
	await page.waitForURL(`**/invoice/${NEW_INVOICE.id}`);

	expect(postedBody!.line_items).toEqual([{ part_number: 'PN-001', quantity: 7 }]);
});

test('mobile (390px) renders rows as cards with the same qty input testid', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await setupDetailPage(page);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	// At 390px, the action rail switches to sticky-bottom wrapper. The inline
	// rail in the header is display:none, so click via the mobile wrapper.
	const stickyWrap = page.getByTestId('po-detail-page-rail-mobile');
	await expect(stickyWrap).toBeVisible();
	// "Create Invoice" is a secondary primary on ACCEPTED PROCUREMENT — the
	// first primary (Post Milestone) is inline; Create Invoice lives in the
	// overflow menu at sticky-bottom.
	await stickyWrap.getByTestId('po-action-overflow').click();
	await stickyWrap.getByTestId('po-action-create-invoice').click();

	// The card list is the visible rendering at <768px; the table is display:none.
	const cards = page.getByTestId('invoice-create-cards');
	await expect(cards).toBeVisible();

	const cardQty1 = cards.getByTestId('invoice-create-qty-input-PN-001');
	await expect(cardQty1).toBeVisible();
	await expect(cardQty1).toHaveValue('7');
});
