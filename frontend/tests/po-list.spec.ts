import { test, expect } from '@playwright/test';

const PO_DRAFT = {
	id: 'uuid-draft',
	po_number: 'PO-20260316-0001',
	status: 'DRAFT',
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

test('PO list page loads and shows table', async ({ page }) => {
	await page.route('**/api/v1/po', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PO_DRAFT, PO_PENDING, PO_ACCEPTED])
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

	await page.route('**/api/v1/po**', (route) => {
		lastUrl = route.request().url();
		const url = new URL(route.request().url());
		const status = url.searchParams.get('status');

		if (status === 'DRAFT') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([PO_DRAFT])
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([PO_DRAFT, PO_PENDING, PO_ACCEPTED])
			});
		}
	});

	await page.goto('/po');
	await page.waitForSelector('table');
	await expect(page.locator('tbody tr')).toHaveCount(3);

	await page.locator('select').selectOption('DRAFT');
	await page.waitForSelector('tbody tr');

	await expect(page.locator('tbody tr')).toHaveCount(1);
	await expect(lastUrl).toContain('status=DRAFT');
});

test('click row navigates to detail', async ({ page }) => {
	await page.route('**/api/v1/po**', (route) => {
		const url = route.request().url();
		// Detail page will also call /api/v1/po/{id}; return minimal valid response
		if (url.includes('/uuid-draft') && !url.endsWith('/po')) {
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
				body: JSON.stringify([PO_DRAFT])
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
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([])
		});
	});

	await page.goto('/po');
	await expect(page.locator('body')).toContainText('No purchase orders found');
});
