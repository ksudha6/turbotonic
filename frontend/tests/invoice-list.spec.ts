import { test, expect, type Page } from '@playwright/test';
import type { User } from '../src/lib/types';

const SM_USER: User = {
	id: 'test-user-id',
	username: 'test-sm',
	display_name: 'Test SM',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null,
	email: null
};

const VENDOR_USER: User = {
	id: 'test-vendor-user-id',
	username: 'test-vendor',
	display_name: 'Test Vendor',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-1',
	email: null
};

const INVOICE_DRAFT = {
	id: 'inv-uuid-draft',
	invoice_number: 'INV-20260401-0001',
	status: 'DRAFT',
	subtotal: '325.00',
	created_at: '2026-04-01T10:00:00+00:00',
	po_id: 'po-uuid-alpha',
	po_number: 'PO-20260401-0001',
	vendor_name: 'Acme Supplies'
};

const INVOICE_SUBMITTED = {
	id: 'inv-uuid-submitted',
	invoice_number: 'INV-20260401-0002',
	status: 'SUBMITTED',
	subtotal: '1200.00',
	created_at: '2026-04-01T12:00:00+00:00',
	po_id: 'po-uuid-beta',
	po_number: 'PO-20260401-0002',
	vendor_name: 'Widget Corp'
};

function mockUser(page: Page, user: User) {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user })
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

function mockActivity(page: Page) {
	return page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

function mockVendors(page: Page) {
	return page.route('**/api/v1/vendors/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

function mockReferenceData(page: Page) {
	return page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				currencies: [],
				incoterms: [],
				payment_terms: [],
				countries: [],
				ports: [],
				exchange_rates: []
			})
		});
	});
}

async function mockInvoiceListRoute(
	page: Page,
	handler: (status: string | null) => object[]
) {
	await page.route('**/api/v1/invoices**', (route) => {
		const url = new URL(route.request().url());
		if (url.pathname === '/api/v1/invoices/' || url.pathname === '/api/v1/invoices') {
			const status = url.searchParams.get('status');
			const items = handler(status);
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items,
					total: items.length,
					page: 1,
					page_size: 20
				})
			});
		} else {
			route.continue();
		}
	});
}

test.beforeEach(async ({ page }) => {
	await mockUnreadCount(page);
	await mockActivity(page);
	await mockUser(page, SM_USER);
	await mockVendors(page);
	await mockReferenceData(page);
});

test('invoice list mounts the AppShell at /invoices', async ({ page }) => {
	await mockInvoiceListRoute(page, () => []);
	await page.goto('/invoices');
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
});

test('invoice list loads and displays rows with PO and vendor context', async ({ page }) => {
	await mockInvoiceListRoute(page, () => [INVOICE_DRAFT, INVOICE_SUBMITTED]);
	await page.goto('/invoices');

	const desktop = page.getByTestId('invoice-table-desktop');
	await expect(desktop).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Invoices', level: 1 })).toBeVisible();

	await expect(desktop.getByTestId(`invoice-row-${INVOICE_DRAFT.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`invoice-row-${INVOICE_SUBMITTED.id}`)).toBeVisible();

	await expect(desktop.getByTestId(`invoice-row-link-${INVOICE_DRAFT.id}`)).toContainText(
		'INV-20260401-0001'
	);
	await expect(desktop.getByTestId(`invoice-row-po-link-${INVOICE_DRAFT.id}`)).toContainText(
		'PO-20260401-0001'
	);
	await expect(desktop.getByTestId(`invoice-row-status-${INVOICE_DRAFT.id}`)).toContainText('Draft');
	await expect(desktop.getByTestId(`invoice-row-status-${INVOICE_SUBMITTED.id}`)).toContainText(
		'Submitted'
	);
});

test('status filter narrows displayed invoices', async ({ page }) => {
	await mockInvoiceListRoute(page, (status) => {
		if (status === 'DRAFT') return [INVOICE_DRAFT];
		return [INVOICE_DRAFT, INVOICE_SUBMITTED];
	});

	await page.goto('/invoices');
	const desktop = page.getByTestId('invoice-table-desktop');
	await expect(desktop.getByTestId(`invoice-row-${INVOICE_SUBMITTED.id}`)).toBeVisible();

	await page.getByTestId('invoice-filter-status').selectOption('DRAFT');

	await expect(desktop.getByTestId(`invoice-row-${INVOICE_SUBMITTED.id}`)).toHaveCount(0);
	await expect(desktop.getByTestId(`invoice-row-${INVOICE_DRAFT.id}`)).toBeVisible();
});

test('invoice and PO links route to detail pages', async ({ page }) => {
	await mockInvoiceListRoute(page, () => [INVOICE_DRAFT]);
	await page.goto('/invoices');

	const desktop = page.getByTestId('invoice-table-desktop');
	const invoiceLink = desktop.getByTestId(`invoice-row-link-${INVOICE_DRAFT.id}`);
	await expect(invoiceLink).toHaveAttribute('href', `/invoice/${INVOICE_DRAFT.id}`);

	const poLink = desktop.getByTestId(`invoice-row-po-link-${INVOICE_DRAFT.id}`);
	await expect(poLink).toHaveAttribute('href', `/po/${INVOICE_DRAFT.po_id}`);
});

test('invoice list shows checkboxes in header and rows', async ({ page }) => {
	await mockInvoiceListRoute(page, () => [INVOICE_DRAFT, INVOICE_SUBMITTED]);
	await page.goto('/invoices');

	const desktop = page.getByTestId('invoice-table-desktop');
	await expect(desktop.getByTestId('invoice-table-checkbox-all')).toBeVisible();
	await expect(desktop.getByTestId(`invoice-row-checkbox-${INVOICE_DRAFT.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`invoice-row-checkbox-${INVOICE_SUBMITTED.id}`)).toBeVisible();
});

test('selecting an invoice row shows bulk toolbar with Download PDFs button', async ({ page }) => {
	await mockInvoiceListRoute(page, () => [INVOICE_DRAFT, INVOICE_SUBMITTED]);
	await page.goto('/invoices');

	await expect(page.getByTestId('invoice-bulk-bar')).toHaveCount(0);

	const desktop = page.getByTestId('invoice-table-desktop');
	await desktop.getByTestId(`invoice-row-checkbox-${INVOICE_DRAFT.id}`).click();

	const bar = page.getByTestId('invoice-bulk-bar');
	await expect(bar).toBeVisible();
	await expect(bar).toContainText('1 selected');
	await expect(bar.getByTestId('invoice-bulk-action-download')).toBeVisible();
});

test('bulk Clear empties selection and hides the bar', async ({ page }) => {
	await mockInvoiceListRoute(page, () => [INVOICE_DRAFT, INVOICE_SUBMITTED]);
	await page.goto('/invoices');

	const desktop = page.getByTestId('invoice-table-desktop');
	await desktop.getByTestId(`invoice-row-checkbox-${INVOICE_DRAFT.id}`).click();
	await expect(page.getByTestId('invoice-bulk-bar')).toBeVisible();

	await page.getByTestId('invoice-bulk-clear').click();
	await expect(page.getByTestId('invoice-bulk-bar')).toHaveCount(0);
});

test('vendor filter is hidden for VENDOR users (vendor-scoped data)', async ({ page }) => {
	await mockUser(page, VENDOR_USER);
	await mockInvoiceListRoute(page, () => []);
	await page.goto('/invoices');

	await expect(page.getByTestId('invoice-filters')).toBeVisible();
	await expect(page.getByTestId('invoice-filter-vendor')).toHaveCount(0);
});

test('empty list with no filter shows the no-invoices-yet copy', async ({ page }) => {
	await mockInvoiceListRoute(page, () => []);
	await page.goto('/invoices');

	await expect(page.getByText('No invoices yet')).toBeVisible();
	await expect(
		page.getByText(/Invoices appear here once a vendor creates them from a PO/)
	).toBeVisible();
});

test('empty list with filter active shows the no-matches copy', async ({ page }) => {
	await mockInvoiceListRoute(page, () => []);
	await page.goto('/invoices');

	await page.getByTestId('invoice-filter-status').selectOption('DRAFT');

	await expect(page.getByText('No matching invoices')).toBeVisible();
	await expect(page.getByText('Try adjusting filters.')).toBeVisible();
});

test('error state renders when invoice list fetch fails and Retry refetches', async ({ page }) => {
	let calls = 0;
	await page.route('**/api/v1/invoices**', (route) => {
		const url = new URL(route.request().url());
		if (url.pathname === '/api/v1/invoices/' || url.pathname === '/api/v1/invoices') {
			calls++;
			// Call 1 is the onMount prefill (page_size=9999) — succeed quietly so we
			// hit the real fetch's error path. Call 2 is the real fetch — fail. Call 3
			// is the retry — succeed.
			if (calls === 2) {
				route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' });
			} else {
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ items: [INVOICE_DRAFT], total: 1, page: 1, page_size: 20 })
				});
			}
		} else {
			route.continue();
		}
	});

	await page.goto('/invoices');

	await expect(page.getByText(/failed: 500/)).toBeVisible();
	await page.getByRole('button', { name: 'Retry' }).click();

	await expect(
		page.getByTestId('invoice-table-desktop').getByTestId(`invoice-row-${INVOICE_DRAFT.id}`)
	).toBeVisible();
});

test('pagination Prev disabled at page 1 and Next disabled when no more pages', async ({ page }) => {
	await mockInvoiceListRoute(page, () => [INVOICE_DRAFT]);
	await page.goto('/invoices');

	await expect(page.getByTestId('invoice-pagination-prev')).toBeDisabled();
	await expect(page.getByTestId('invoice-pagination-next')).toBeDisabled();
});

