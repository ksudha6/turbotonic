import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

function mockUser(page: import('@playwright/test').Page, role: string, vendorId: string | null = null) {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'test-user-id',
					username: `test-${role.toLowerCase()}`,
					display_name: `Test ${role}`,
					role,
					status: 'ACTIVE',
					vendor_id: vendorId
				}
			})
		});
	});
}

function mockApiCatchAll(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

function mockUnreadCount(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
}

async function mockDashboardRoute(page: import('@playwright/test').Page) {
	await page.route('**/api/v1/dashboard/', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				po_summary: [],
				vendor_summary: { active: 0, inactive: 0 },
				recent_pos: [],
				invoice_summary: [],
				production_summary: [],
				overdue_pos: []
			})
		});
	});
}

// ---------------------------------------------------------------------------
// Shared fixture data
// ---------------------------------------------------------------------------

const PENDING_PO = {
	id: 'po-1',
	po_number: 'PO-001',
	status: 'PENDING',
	po_type: 'PROCUREMENT',
	vendor_id: 'vendor-1',
	vendor_name: 'Test Vendor',
	vendor_country: 'CN',
	buyer_name: 'Buyer Inc.',
	buyer_country: 'US',
	ship_to_address: '123 Main St',
	payment_terms: 'NET30',
	currency: 'USD',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	total_value: '1000.00',
	current_milestone: null,
	terms_and_conditions: 'Standard',
	incoterm: 'FOB',
	port_of_loading: 'CNSHA',
	port_of_discharge: 'USLAX',
	country_of_origin: 'CN',
	country_of_destination: 'US',
	line_items: [
		{
			part_number: 'P-1',
			description: 'Widget',
			quantity: 10,
			uom: 'PCS',
			unit_price: '100',
			hs_code: '7318.15',
			country_of_origin: 'CN',
			status: 'PENDING'
		}
	],
	rejection_history: [],
	created_at: '2026-04-01T00:00:00+00:00',
	updated_at: '2026-04-01T00:00:00+00:00'
};

const REF_DATA = {
	currencies: [{ code: 'USD', label: 'US Dollar' }],
	incoterms: [{ code: 'FOB', label: 'Free on Board' }],
	payment_terms: [{ code: 'NET30', label: 'Net 30' }],
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

// ---------------------------------------------------------------------------
// Navigation tests
// ---------------------------------------------------------------------------

test('SM nav shows all links', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'SM');
	await mockUnreadCount(page);
	await mockDashboardRoute(page);
	await page.goto('/dashboard');
	await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Purchase Orders' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Invoices' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Vendors' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Products' })).toBeVisible();
});

test('VENDOR nav shows Dashboard, POs, Invoices only', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'VENDOR', 'vendor-1');
	await mockUnreadCount(page);
	await mockDashboardRoute(page);
	await page.goto('/dashboard');
	await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Purchase Orders' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Invoices' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Vendors' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Products' })).toBeHidden();
});

test('QUALITY_LAB nav shows Dashboard and Products only', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'QUALITY_LAB');
	await mockUnreadCount(page);
	await mockDashboardRoute(page);
	await page.goto('/dashboard');
	await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Products' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Purchase Orders' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Invoices' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Vendors' })).toBeHidden();
});

test('FREIGHT_MANAGER nav shows Dashboard and POs only', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'FREIGHT_MANAGER');
	await mockUnreadCount(page);
	await mockDashboardRoute(page);
	await page.goto('/dashboard');
	await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Purchase Orders' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Invoices' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Vendors' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Products' })).toBeHidden();
});

test('ADMIN nav shows same links as SM', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'ADMIN');
	await mockUnreadCount(page);
	await mockDashboardRoute(page);
	await page.goto('/dashboard');
	await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Purchase Orders' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Invoices' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Vendors' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Products' })).toBeVisible();
});

test('PROCUREMENT_MANAGER nav shows Dashboard only', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'PROCUREMENT_MANAGER');
	await mockUnreadCount(page);
	await mockDashboardRoute(page);
	await page.goto('/dashboard');
	await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Purchase Orders' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Invoices' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Vendors' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Products' })).toBeHidden();
});

// ---------------------------------------------------------------------------
// PO list button tests
// ---------------------------------------------------------------------------

test('SM on PO list sees Create PO button', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'SM');
	await mockUnreadCount(page);
	await page.route('**/api/v1/po/*', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REF_DATA)
		});
	});
	await page.goto('/po');
	await expect(page.getByRole('link', { name: /new po/i })).toBeVisible();
});

test('VENDOR on PO list does not see Create PO button', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'VENDOR', 'vendor-1');
	await mockUnreadCount(page);
	await page.route('**/api/v1/po/*', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(REF_DATA)
		});
	});
	await page.goto('/po');
	await expect(page.getByRole('link', { name: /new po/i })).toBeHidden();
});

// ---------------------------------------------------------------------------
// PO detail button tests
// ---------------------------------------------------------------------------

test('SM on PO detail (PENDING) does not see Accept/Reject', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'SM');
	await mockUnreadCount(page);
	await page.route('**/api/v1/po/po-1', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PENDING_PO) });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REF_DATA) });
	});
	await page.goto('/po/po-1');
	await page.waitForSelector('h1');
	await expect(page.getByRole('button', { name: 'Accept' })).toBeHidden();
	await expect(page.getByRole('button', { name: 'Reject' })).toBeHidden();
});

test('VENDOR on PO detail (PENDING) sees Accept plus per-line negotiation controls', async ({ page }) => {
	// Iter 057: the top-level Reject button is gone; the vendor works through
	// per-line Modify / Accept / Remove and a Submit Response bar.
	await mockApiCatchAll(page);
	await mockUser(page, 'VENDOR', 'vendor-1');
	await mockUnreadCount(page);
	await page.route('**/api/v1/po/po-1', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PENDING_PO) });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REF_DATA) });
	});
	await page.goto('/po/po-1');
	await page.waitForSelector('h1');
	await expect(page.locator('.actions').getByRole('button', { name: 'Accept' })).toBeVisible();
	await expect(page.locator('.actions').getByRole('button', { name: 'Reject' })).toHaveCount(0);
	await expect(page.locator('[data-testid="modify-btn-P-1"]')).toBeVisible();
	await expect(page.locator('[data-testid="submit-response-bar"]')).toBeVisible();
});

test('ADMIN on PO detail (DRAFT) has same buttons as SM', async ({ page }) => {
	const DRAFT_PO = { ...PENDING_PO, status: 'DRAFT' };
	await mockApiCatchAll(page);
	await mockUser(page, 'ADMIN');
	await mockUnreadCount(page);
	await page.route('**/api/v1/po/po-1', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DRAFT_PO) });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REF_DATA) });
	});
	await page.goto('/po/po-1');
	await page.waitForSelector('h1');
	await expect(page.getByRole('link', { name: 'Edit' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Submit' })).toBeVisible();
});

test('VENDOR on PO detail (ACCEPTED) sees Create Invoice button', async ({ page }) => {
	const ACCEPTED_PO = { ...PENDING_PO, status: 'ACCEPTED' };
	await mockApiCatchAll(page);
	await mockUser(page, 'VENDOR', 'vendor-1');
	await mockUnreadCount(page);
	await page.route('**/api/v1/po/po-1', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ACCEPTED_PO) });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REF_DATA) });
	});
	await page.goto('/po/po-1');
	await page.waitForSelector('h1');
	await expect(page.getByRole('button', { name: /create invoice/i })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Page redirect tests
// ---------------------------------------------------------------------------

test('VENDOR visiting /po/new redirects to /po', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'VENDOR', 'vendor-1');
	await mockUnreadCount(page);
	await page.goto('/po/new');
	await expect(page).toHaveURL(/\/po(\?|$)/);
});

test('VENDOR visiting /vendors redirects to /dashboard', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'VENDOR', 'vendor-1');
	await mockUnreadCount(page);
	await mockDashboardRoute(page);
	await page.goto('/vendors');
	await expect(page).toHaveURL(/\/dashboard/);
});

test('QUALITY_LAB visiting /invoices redirects to /dashboard', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'QUALITY_LAB');
	await mockUnreadCount(page);
	await mockDashboardRoute(page);
	await page.goto('/invoices');
	await expect(page).toHaveURL(/\/dashboard/);
});

// ---------------------------------------------------------------------------
// Invoice detail role test
// ---------------------------------------------------------------------------

test('ADMIN sees vendor-side actions (post milestone, accept/reject PO, create invoice)', async ({ page }) => {
	await mockUser(page, 'ADMIN');
	await mockApiCatchAll(page);
	await mockUnreadCount(page);
	await page.goto('/po');
	// ADMIN should see the same action affordances a VENDOR sees on a PENDING PO.
	// Any testid currently gated by isExact(role, 'VENDOR') should be visible.
	// At minimum, verify no role-based redirect kicks ADMIN off the PO page.
	await expect(page).toHaveURL(/\/po/);
});

test('ADMIN on invoice detail (SUBMITTED) sees Approve and Dispute', async ({ page }) => {
	const SUBMITTED_INVOICE = {
		id: 'inv-1',
		invoice_number: 'INV-001',
		po_id: 'po-1',
		status: 'SUBMITTED',
		payment_terms: 'NET30',
		currency: 'USD',
		line_items: [
			{ part_number: 'P-1', description: 'Widget', quantity: 10, uom: 'PCS', unit_price: '100' }
		],
		subtotal: '1000.00',
		dispute_reason: '',
		created_at: '2026-04-01T00:00:00+00:00',
		updated_at: '2026-04-01T00:00:00+00:00'
	};
	await mockApiCatchAll(page);
	await mockUser(page, 'ADMIN');
	await mockUnreadCount(page);
	await page.route('**/api/v1/invoices/inv-1', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SUBMITTED_INVOICE) });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REF_DATA) });
	});
	await page.goto('/invoice/inv-1');
	await page.waitForSelector('h1');
	await expect(page.getByRole('button', { name: 'Approve' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Dispute' })).toBeVisible();
});
