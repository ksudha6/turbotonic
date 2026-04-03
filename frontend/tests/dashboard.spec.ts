import { test, expect } from '@playwright/test';
import type { DashboardData } from '../src/lib/types';

const MOCK_DASHBOARD: DashboardData = {
	po_summary: [
		{ status: 'DRAFT', count: 3, total_usd: '4500.00' },
		{ status: 'PENDING', count: 2, total_usd: '12000.00' },
		{ status: 'ACCEPTED', count: 5, total_usd: '85000.00' }
	],
	vendor_summary: { active: 8, inactive: 2 },
	recent_pos: [
		{
			id: 'uuid-1',
			po_number: 'PO-20260324-0001',
			status: 'PENDING',
			vendor_name: 'Acme Corp',
			total_value: '5000.00',
			currency: 'USD',
			updated_at: '2026-03-24T12:00:00+00:00'
		},
		{
			id: 'uuid-2',
			po_number: 'PO-20260324-0002',
			status: 'DRAFT',
			vendor_name: 'Widget Inc',
			total_value: '2500.00',
			currency: 'EUR',
			updated_at: '2026-03-24T10:00:00+00:00'
		}
	],
	invoice_summary: [],
	production_summary: [],
	overdue_pos: []
};

function mockDashboardRoute(page: any, data = MOCK_DASHBOARD) {
	return page.route('**/api/v1/dashboard**', (route: any) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(data)
		});
	});
}

test('dashboard page loads and renders all sections', async ({ page }) => {
	await mockDashboardRoute(page);
	await page.goto('/dashboard');

	await expect(page.locator('h1')).toContainText('Dashboard');

	// PO summary cards
	await expect(page.locator('.summary-card')).toHaveCount(3);
	await expect(page.locator('body')).toContainText('3'); // DRAFT count
	await expect(page.locator('body')).toContainText('≈ $4,500');

	// Vendor summary
	await expect(page.locator('.vendor-card')).toHaveCount(2);
	await expect(page.locator('body')).toContainText('8'); // active
	await expect(page.locator('body')).toContainText('2'); // inactive

	// Recent POs table
	await expect(page.locator('tbody tr')).toHaveCount(2);
	await expect(page.locator('tbody')).toContainText('PO-20260324-0001');
	await expect(page.locator('tbody')).toContainText('Acme Corp');
});

test('status cards show count and USD total', async ({ page }) => {
	await mockDashboardRoute(page);
	await page.goto('/dashboard');

	const cards = page.locator('.summary-card');
	await expect(cards).toHaveCount(3);

	// Check each card has a count and USD value
	await expect(cards.nth(0)).toContainText('3');
	await expect(cards.nth(0)).toContainText('$4,500');
	await expect(cards.nth(1)).toContainText('2');
	await expect(cards.nth(1)).toContainText('$12,000');
	await expect(cards.nth(2)).toContainText('5');
	await expect(cards.nth(2)).toContainText('$85,000');
});

test('clicking status card navigates to filtered PO list', async ({ page }) => {
	await mockDashboardRoute(page);

	// Also mock the PO list page's API calls so it doesn't fail after navigation
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200, contentType: 'application/json',
			body: JSON.stringify({
					currencies: [], incoterms: [], payment_terms: [], countries: [], ports: [],
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
				})
		});
	});

	await page.goto('/dashboard');
	await page.locator('.summary-card').first().click();

	await page.waitForURL('**/po?status=DRAFT**');
	expect(page.url()).toContain('/po?status=DRAFT');
});

test('recent PO rows link to detail page', async ({ page }) => {
	await mockDashboardRoute(page);

	// Mock the detail page API
	await page.route('**/api/v1/po/uuid-1', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				...MOCK_DASHBOARD.recent_pos[0],
				vendor_id: 'v1',
				buyer_name: 'TurboTonic',
				buyer_country: 'US',
				vendor_country: 'CN',
				ship_to_address: '',
				payment_terms: 'TT',
				terms_and_conditions: '',
				incoterm: 'FOB',
				port_of_loading: 'CNSHA',
				port_of_discharge: 'USLAX',
				country_of_origin: 'CN',
				country_of_destination: 'US',
				line_items: [],
				rejection_history: [],
				created_at: '2026-03-24T00:00:00+00:00',
				po_type: 'PROCUREMENT'
			})
		});
	});

	await page.goto('/dashboard');
	await page.locator('tbody tr').first().click();

	await page.waitForURL('**/po/uuid-1');
	expect(page.url()).toContain('/po/uuid-1');
});

// ---------------------------------------------------------------------------
// Iteration 22 — Production pipeline and overdue POs
// ---------------------------------------------------------------------------

test('dashboard shows production pipeline section with milestone labels and counts', async ({ page }) => {
	const data = {
		...MOCK_DASHBOARD,
		production_summary: [
			{ milestone: 'RAW_MATERIALS', count: 3 },
			{ milestone: 'PRODUCTION_STARTED', count: 2 },
		],
		overdue_pos: [],
	};

	await mockDashboardRoute(page, data);
	await page.goto('/dashboard');

	// Section heading
	await expect(page.getByRole('heading', { name: 'Production Pipeline' })).toBeVisible();

	// Milestone labels and counts must appear in the table
	await expect(page.locator('body')).toContainText('Raw Materials');
	await expect(page.locator('body')).toContainText('Production Started');

	const productionSection = page.locator('section').filter({ hasText: 'Production Pipeline' });
	await expect(productionSection).toContainText('3');
	await expect(productionSection).toContainText('2');
});

test('dashboard shows overdue production section with PO number and days', async ({ page }) => {
	const data = {
		...MOCK_DASHBOARD,
		production_summary: [],
		overdue_pos: [
			{ id: 'po-1', po_number: 'PO-20260401-0001', vendor_name: 'Acme', milestone: 'RAW_MATERIALS', days_since_update: 10 },
		],
	};

	await mockDashboardRoute(page, data);
	await page.goto('/dashboard');

	// Section heading
	await expect(page.getByRole('heading', { name: 'Overdue Production' })).toBeVisible();

	// Overdue row: PO number and days count
	await expect(page.locator('body')).toContainText('PO-20260401-0001');
	await expect(page.locator('body')).toContainText('10');

	// Milestone label renders correctly
	await expect(page.locator('body')).toContainText('Raw Materials');
});

test('empty dashboard shows appropriate messages', async ({ page }) => {
	await page.route('**/api/v1/dashboard**', (route) => {
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

	await page.goto('/dashboard');
	await expect(page.locator('body')).toContainText('No purchase orders yet');
	await expect(page.locator('body')).toContainText('No recent activity');
	await expect(page.locator('.vendor-card').first()).toContainText('0');
});
