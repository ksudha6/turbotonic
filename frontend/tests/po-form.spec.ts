import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Iter 085 — POForm retrofit covering /po/new + /po/[id]/edit under (nexus).
// Selectors: getByTestId / getByRole / getByLabel only (CLAUDE.md selector
// policy). Form testids live under the `po-form-*` namespace.
// ---------------------------------------------------------------------------

const PO_ID = 'uuid-form';

const REFERENCE_DATA = {
	currencies: [{ code: 'USD', label: 'US Dollar' }, { code: 'EUR', label: 'Euro' }],
	incoterms: [{ code: 'FOB', label: 'Free on Board' }],
	payment_terms: [
		{ code: 'NET30', label: 'Net 30', has_advance: false },
		{ code: 'ADVANCE_30', label: 'Advance 30%', has_advance: true }
	],
	countries: [
		{ code: 'US', label: 'United States' },
		{ code: 'CN', label: 'China' }
	],
	ports: [
		{ code: 'CNSHA', label: 'Shanghai' },
		{ code: 'USLAX', label: 'Los Angeles' }
	],
	vendor_types: [
		{ code: 'PROCUREMENT', label: 'Procurement' },
		{ code: 'OPEX', label: 'OpEx' }
	],
	po_types: [
		{ code: 'PROCUREMENT', label: 'Procurement' },
		{ code: 'OPEX', label: 'OpEx' }
	]
};

const VENDORS = [
	{ id: 'v-proc-1', name: 'Acme Procurement', country: 'CN', status: 'ACTIVE', vendor_type: 'PROCUREMENT', address: '', account_details: '' },
	{ id: 'v-opex-1', name: 'Acme OpEx', country: 'US', status: 'ACTIVE', vendor_type: 'OPEX', address: '', account_details: '' }
];

const BRANDS = [
	{ id: 'brand-1', name: 'Acme Brands', legal_name: 'Acme Brands LLC', address: '1 Brand St', country: 'US', tax_id: 'US123', status: 'ACTIVE', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }
];

const SM_USER = {
	id: 'u-sm',
	username: 'sm',
	display_name: 'SM User',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null
};

function mockUser(page: Page) {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: SM_USER })
		});
	});
}

function mockReferenceData(page: Page) {
	return page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REFERENCE_DATA)
		});
	});
}

function mockVendors(page: Page) {
	return page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(VENDORS)
		});
	});
}

function mockBrands(page: Page) {
	// Broad pattern for the brands list endpoint. LIFO ordering means the
	// more-specific mockBrandVendors (registered after) wins for /brands/*/vendors.
	return page.route('**/api/v1/brands**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(BRANDS)
		});
	});
}

function mockBrandVendors(page: Page) {
	// More specific /brands/*/vendors — registered after mockBrands, wins via LIFO.
	return page.route('**/api/v1/brands/*/vendors', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(VENDORS)
		});
	});
}

function mockUnreadCount(page: Page) {
	return page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ count: 0 })
		});
	});
}

function mockApiCatchAll(page: Page) {
	return page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

test.beforeEach(async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page);
	await mockUnreadCount(page);
	await mockReferenceData(page);
	await mockVendors(page);
	await mockBrands(page);
	await mockBrandVendors(page);
});

// ---------------------------------------------------------------------------
// /po/new (create)
// ---------------------------------------------------------------------------

test('/po/new mounts under (nexus) shell with sidebar + topbar', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
});

test('default po_type is PROCUREMENT and marketplace is visible', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await expect(page.getByTestId('po-form-po-type')).toHaveValue('PROCUREMENT');
	await expect(page.getByTestId('po-form-marketplace')).toBeVisible();
});

test('switching po_type to OPEX hides marketplace select', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await page.getByTestId('po-form-po-type').selectOption('OPEX');
	await expect(page.getByTestId('po-form-marketplace')).toHaveCount(0);
});

test('switching po_type clears stale vendor_id and shows hint', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	// Select a brand first to enable the vendor select, then select a vendor.
	await page.getByTestId('po-form-brand').selectOption('brand-1');
	await page.getByTestId('po-form-vendor').selectOption('v-proc-1');
	await page.getByTestId('po-form-po-type').selectOption('OPEX');
	await expect(page.getByTestId('po-form-vendor')).toHaveValue('');
	await expect(page.getByText('Vendor cleared because it does not match')).toBeVisible();
});

test('po_type select is enabled in create mode', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await expect(page.getByTestId('po-form-po-type')).toBeEnabled();
});

test('payment_terms options append "advance required" suffix when has_advance', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	const ptSelect = page.getByTestId('po-form-payment-terms');
	await expect(ptSelect.locator('option', { hasText: 'advance required' })).toHaveCount(1);
});

test('HS code with letters shows inline FormField error', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await page.getByTestId('po-form-line-0-hs-code').fill('XX');
	const field = page.getByTestId('po-form-line-0-hs-code-field');
	await expect(field.getByRole('alert')).toContainText('digits and dots');
});

test('submit disabled while HS code invalid', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await page.getByTestId('po-form-line-0-hs-code').fill('XX');
	await expect(page.getByTestId('po-form-submit')).toBeDisabled();
});

test('Add Line Item appends a second line card', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await expect(page.getByTestId('po-form-line-0')).toBeVisible();
	await expect(page.getByTestId('po-form-line-1')).toHaveCount(0);
	await page.getByTestId('po-form-add-line').click();
	await expect(page.getByTestId('po-form-line-1')).toBeVisible();
});

test('Remove disabled when only one line remains', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await expect(page.getByTestId('po-form-line-0-remove')).toBeDisabled();
});

test('valid create POSTs body and navigates to /po/{id}', async ({ page }) => {
	let capturedBody: Record<string, unknown> | null = null;

	await page.route('**/api/v1/po/', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			capturedBody = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify({ id: PO_ID })
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();

	await page.getByTestId('po-form-brand').selectOption('brand-1');
	await page.getByTestId('po-form-vendor').selectOption('v-proc-1');
	await page.getByTestId('po-form-currency').selectOption('USD');
	await page.getByTestId('po-form-issued-date').fill('2026-03-16');
	await page.getByTestId('po-form-required-delivery-date').fill('2026-04-16');
	await page.getByTestId('po-form-line-0-part-number').fill('PART-001');

	await page.getByTestId('po-form-submit').click();
	await page.waitForURL(`**/po/${PO_ID}`);

	expect(capturedBody).not.toBeNull();
	expect((capturedBody as unknown as Record<string, unknown>)['vendor_id']).toBe('v-proc-1');
	expect((capturedBody as unknown as Record<string, unknown>)['brand_id']).toBe('brand-1');
});

test('Cancel on pristine form navigates to /po without prompt', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await page.getByTestId('po-form-cancel').click();
	await expect(page).toHaveURL(/\/po(\?|$)/);
});

test('Cancel on dirty form opens discard modal', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await page.getByTestId('po-form-buyer-name').fill('Modified buyer');
	await page.getByTestId('po-form-cancel').click();
	await expect(page.getByTestId('po-form-discard-modal')).toBeVisible();
});

test('"Keep editing" closes the discard modal', async ({ page }) => {
	await page.goto('/po/new');
	await page.getByTestId('po-form').waitFor();
	await page.getByTestId('po-form-buyer-name').fill('Modified buyer');
	await page.getByTestId('po-form-cancel').click();
	await page.getByTestId('po-form-discard-keep').click();
	await expect(page.getByTestId('po-form-discard-modal')).toHaveCount(0);
	await expect(page.getByTestId('po-form')).toBeVisible();
});

// ---------------------------------------------------------------------------
// /po/[id]/edit (revise + draft)
// ---------------------------------------------------------------------------

function makePO(status: string, overrides: Record<string, unknown> = {}) {
	return {
		id: PO_ID,
		po_number: 'PO-20260316-0001',
		status,
		po_type: 'PROCUREMENT',
		vendor_id: 'v-proc-1',
		vendor_name: 'Acme Procurement',
		vendor_country: 'CN',
		buyer_name: 'TurboTonic Ltd',
		buyer_country: 'US',
		ship_to_address: '123 Main St',
		payment_terms: 'NET30',
		currency: 'USD',
		issued_date: '2026-03-16T00:00:00+00:00',
		required_delivery_date: '2026-04-16T00:00:00+00:00',
		terms_and_conditions: 'Standard',
		incoterm: 'FOB',
		port_of_loading: 'CNSHA',
		port_of_discharge: 'USLAX',
		country_of_origin: 'CN',
		country_of_destination: 'US',
		marketplace: null,
		line_items: [
			{
				part_number: 'PART-001',
				description: 'Steel bolt',
				quantity: 100,
				uom: 'pcs',
				unit_price: '15',
				hs_code: '7318.15',
				country_of_origin: 'CN',
				product_id: null
			}
		],
		rejection_history: status === 'REJECTED'
			? [{ comment: 'Price too high', rejected_at: '2026-03-20T00:00:00+00:00' }]
			: [],
		total_value: '1500',
		created_at: '2026-03-16T00:00:00+00:00',
		updated_at: '2026-03-16T00:00:00+00:00',
		round_count: 0,
		last_actor_role: null,
		advance_paid_at: null,
		has_removed_line: false,
		current_milestone: null,
		brand_id: 'brand-1',
		brand_name: 'Acme Brands',
		brand_legal_name: 'Acme Brands LLC',
		brand_address: '1 Brand St',
		brand_country: 'US',
		brand_tax_id: 'US123',
		...overrides
	};
}

function mockPoDetail(page: Page, po: Record<string, unknown>) {
	return page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		const url = new URL(route.request().url()).pathname;
		if (url === `/api/v1/po/${PO_ID}`) {
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

test('REJECTED edit renders form with rejection history above + Save & Revise label', async ({ page }) => {
	await mockPoDetail(page, makePO('REJECTED'));
	await page.goto(`/po/${PO_ID}/edit`);
	await page.getByTestId('po-form').waitFor();
	await expect(page.getByTestId('po-rejection-history-panel')).toBeVisible();
	await expect(page.getByTestId('po-form-submit')).toContainText('Save & Revise');
	await expect(page.getByTestId('po-form-buyer-name')).toHaveValue('TurboTonic Ltd');
});

test('DRAFT edit renders form, disables PO Type, uses "Save Draft" label', async ({ page }) => {
	await mockPoDetail(page, makePO('DRAFT'));
	await page.goto(`/po/${PO_ID}/edit`);
	await page.getByTestId('po-form').waitFor();
	await expect(page.getByTestId('po-form-submit')).toContainText('Save Draft');
	await expect(page.getByTestId('po-form-po-type')).toBeDisabled();
});

test('ACCEPTED edit renders not-editable message + Back to detail button', async ({ page }) => {
	await mockPoDetail(page, makePO('ACCEPTED'));
	await page.goto(`/po/${PO_ID}/edit`);
	await page.getByTestId('po-edit-not-editable').waitFor();
	await expect(page.getByTestId('po-form')).toHaveCount(0);
	await expect(page.getByTestId('po-edit-back-to-detail')).toBeVisible();
});

test('Cancel from /po/{id}/edit on pristine form returns to detail', async ({ page }) => {
	await mockPoDetail(page, makePO('REJECTED'));
	await page.goto(`/po/${PO_ID}/edit`);
	await page.getByTestId('po-form').waitFor();
	await page.getByTestId('po-form-cancel').click();
	await expect(page).toHaveURL(new RegExp(`/po/${PO_ID}(?:[?#]|$)`));
});
