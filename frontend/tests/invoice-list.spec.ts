import { test, expect } from '@playwright/test';

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

const MOCK_DASHBOARD_WITH_INVOICES = {
	po_summary: [
		{ status: 'DRAFT', count: 3, total_usd: '4500.00' },
		{ status: 'PENDING', count: 2, total_usd: '12000.00' }
	],
	vendor_summary: { active: 5, inactive: 1 },
	recent_pos: [],
	invoice_summary: [
		{ status: 'DRAFT', count: 2, total_usd: '1500.00' },
		{ status: 'SUBMITTED', count: 1, total_usd: '800.00' }
	]
};

async function mockInvoiceListRoute(
	page: import('@playwright/test').Page,
	handler: (status: string | null) => object[]
) {
	await page.route('**/api/v1/invoices**', (route) => {
		const url = new URL(route.request().url());
		if (
			url.pathname === '/api/v1/invoices/' ||
			url.pathname === '/api/v1/invoices'
		) {
			const status = url.searchParams.get('status');
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(handler(status))
			});
		} else {
			route.continue();
		}
	});
}

test('invoice list loads and displays rows with PO and vendor context', async ({ page }) => {
	await mockInvoiceListRoute(page, () => [INVOICE_DRAFT, INVOICE_SUBMITTED]);

	await page.goto('/invoices');
	await page.waitForSelector('table');

	await expect(page.locator('h1')).toContainText('Invoices');

	const rows = page.locator('tbody tr');
	await expect(rows).toHaveCount(2);

	await expect(page.locator('tbody')).toContainText('INV-20260401-0001');
	await expect(page.locator('tbody')).toContainText('INV-20260401-0002');

	await expect(page.locator('tbody')).toContainText('PO-20260401-0001');
	await expect(page.locator('tbody')).toContainText('PO-20260401-0002');

	await expect(page.locator('tbody')).toContainText('Acme Supplies');
	await expect(page.locator('tbody')).toContainText('Widget Corp');

	// StatusPill renders capitalized status text
	await expect(page.locator('tbody')).toContainText('Draft');
	await expect(page.locator('tbody')).toContainText('Submitted');
});

test('status filter narrows displayed invoices', async ({ page }) => {
	await mockInvoiceListRoute(page, (status) => {
		if (status === 'DRAFT') return [INVOICE_DRAFT];
		return [INVOICE_DRAFT, INVOICE_SUBMITTED];
	});

	await page.goto('/invoices');
	await page.waitForSelector('table');
	await expect(page.locator('tbody tr')).toHaveCount(2);

	await page.locator('.filter-bar select').selectOption('DRAFT');
	await page.waitForSelector('tbody tr');

	await expect(page.locator('tbody tr')).toHaveCount(1);
	await expect(page.locator('tbody')).toContainText('INV-20260401-0001');
	await expect(page.locator('tbody')).not.toContainText('INV-20260401-0002');
});

test('invoice row links navigate to detail and PO pages', async ({ page }) => {
	await mockInvoiceListRoute(page, () => [INVOICE_DRAFT]);

	await page.goto('/invoices');
	await page.waitForSelector('table');

	const invoiceLink = page.locator('tbody a[href="/invoice/inv-uuid-draft"]');
	await expect(invoiceLink).toBeVisible();
	await expect(invoiceLink).toContainText('INV-20260401-0001');

	const poLink = page.locator('tbody a[href="/po/po-uuid-alpha"]');
	await expect(poLink).toBeVisible();
	await expect(poLink).toContainText('PO-20260401-0001');
});

test('dashboard shows invoice summary section', async ({ page }) => {
	await page.route('**/api/v1/dashboard**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(MOCK_DASHBOARD_WITH_INVOICES)
		});
	});

	await page.goto('/dashboard');
	await expect(page.getByRole('heading', { name: 'Invoices' })).toBeVisible();

	// Invoice summary cards: DRAFT count=2, SUBMITTED count=1
	// The page renders all .summary-card elements for both PO and invoice sections;
	// scope assertions to the Invoices section.
	const invoiceSection = page.locator('section').filter({ hasText: /^Invoices/ });
	await expect(invoiceSection.locator('.summary-card')).toHaveCount(2);
	await expect(invoiceSection).toContainText('2'); // DRAFT count
	await expect(invoiceSection).toContainText('1'); // SUBMITTED count
	await expect(invoiceSection).toContainText('$1,500'); // DRAFT total
	await expect(invoiceSection).toContainText('$800');   // SUBMITTED total
});
