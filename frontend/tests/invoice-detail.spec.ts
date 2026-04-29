import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import type { User } from '../src/lib/types';

// ---------------------------------------------------------------------------
// Iter 087 — `/invoice/[id]` revamp under (nexus) shell. Verifies the role ×
// status matrix surfaced by InvoiceActionRail, the dispute modal lifecycle,
// the dispute-reason panel visibility, the metadata + line items + activity
// panels, and the sticky-bottom rail at 390px.
// ---------------------------------------------------------------------------

const INVOICE_ID = 'inv-uuid-detail';
const PO_ID = 'po-uuid-detail';

type InvoiceFixture = Record<string, unknown>;

function makeInvoice(overrides: InvoiceFixture = {}): InvoiceFixture {
	return {
		id: INVOICE_ID,
		invoice_number: 'INV-20260401-0001',
		po_id: PO_ID,
		status: 'DRAFT',
		payment_terms: 'NET30',
		currency: 'USD',
		line_items: [
			{
				part_number: 'PN-001',
				description: 'Widget',
				quantity: 100,
				uom: 'EA',
				unit_price: '5.00'
			},
			{
				part_number: 'PN-002',
				description: 'Sprocket',
				quantity: 25,
				uom: 'EA',
				unit_price: '12.50'
			}
		],
		subtotal: '812.50',
		dispute_reason: '',
		created_at: '2026-04-01T10:00:00+00:00',
		updated_at: '2026-04-01T10:00:00+00:00',
		...overrides
	};
}

function makePO(): Record<string, unknown> {
	return {
		id: PO_ID,
		po_number: 'PO-20260316-0001',
		status: 'ACCEPTED',
		po_type: 'PROCUREMENT',
		vendor_id: 'vendor-1',
		vendor_name: 'Acme Supplies',
		vendor_country: 'CN',
		buyer_name: 'TurboTonic Ltd',
		buyer_country: 'US',
		ship_to_address: '123 Main St',
		payment_terms: 'NET30',
		currency: 'USD',
		issued_date: '2026-03-16T00:00:00+00:00',
		required_delivery_date: '2026-04-16T00:00:00+00:00',
		terms_and_conditions: 'Standard terms',
		incoterm: 'FOB',
		port_of_loading: 'CNSHA',
		port_of_discharge: 'USLAX',
		country_of_origin: 'CN',
		country_of_destination: 'US',
		marketplace: null,
		line_items: [],
		rejection_history: [],
		total_value: '1500',
		created_at: '2026-03-16T00:00:00+00:00',
		updated_at: '2026-03-16T00:00:00+00:00',
		round_count: 0,
		last_actor_role: null,
		advance_paid_at: null,
		has_removed_line: false,
		current_milestone: null
	};
}

const SM_USER: User = {
	id: 'u-sm',
	username: 'sm',
	display_name: 'SM User',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null
};

const VENDOR_USER: User = {
	id: 'u-vendor',
	username: 'vendor',
	display_name: 'Vendor User',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-1'
};

const PROCUREMENT_USER: User = {
	id: 'u-pm',
	username: 'pm',
	display_name: 'Procurement Manager',
	role: 'PROCUREMENT_MANAGER',
	status: 'ACTIVE',
	vendor_id: null
};

const FREIGHT_USER: User = {
	id: 'u-fm',
	username: 'fm',
	display_name: 'Freight Manager',
	role: 'FREIGHT_MANAGER',
	status: 'ACTIVE',
	vendor_id: null
};

const QUALITY_USER: User = {
	id: 'u-ql',
	username: 'ql',
	display_name: 'Quality Lab',
	role: 'QUALITY_LAB',
	status: 'ACTIVE',
	vendor_id: null
};

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

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

function mockActivity(page: Page, entries: unknown[] = []) {
	return page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(entries)
		});
	});
}

function mockInvoiceDetail(page: Page, invoice: InvoiceFixture) {
	return page.route(`**/api/v1/invoices/${INVOICE_ID}`, (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(invoice)
		});
	});
}

function mockPoDetail(page: Page) {
	return page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(makePO())
		});
	});
}

async function setupDetailPage(page: Page, user: User, invoice: InvoiceFixture) {
	await mockUnreadCount(page);
	await mockActivity(page);
	await mockUser(page, user);
	await mockInvoiceDetail(page, invoice);
	await mockPoDetail(page);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test('invoice detail mounts the AppShell at /invoice/{id}', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'SUBMITTED' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByTestId('ui-appshell-topbar')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Vendor Portal' })).toHaveCount(0);
});

test('invoice detail header renders title, status pill, and back link', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'SUBMITTED' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const header = page.getByTestId('invoice-detail-header');
	await expect(header).toBeVisible();
	await expect(page.getByRole('heading', { name: 'INV-20260401-0001', level: 1 })).toBeVisible();
	await expect(page.getByTestId('invoice-detail-status')).toContainText('Submitted');
	await expect(header.getByRole('link', { name: /Invoices/ })).toBeVisible();
});

test('action rail composition for VENDOR on DRAFT', async ({ page }) => {
	await setupDetailPage(page, VENDOR_USER, makeInvoice({ status: 'DRAFT' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const rail = page.getByTestId('invoice-action-rail').first();
	await expect(rail.getByTestId('invoice-action-submit')).toBeVisible();
	await expect(rail.getByTestId('invoice-action-approve')).toHaveCount(0);
	await expect(rail.getByTestId('invoice-action-overflow')).toBeVisible();

	await rail.getByTestId('invoice-action-overflow').click();
	await expect(rail.getByTestId('invoice-action-download-pdf')).toBeVisible();
});

test('action rail composition for SM on SUBMITTED shows Approve + Dispute', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'SUBMITTED' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const rail = page.getByTestId('invoice-action-rail').first();
	await expect(rail.getByTestId('invoice-action-approve')).toBeVisible();
	await expect(rail.getByTestId('invoice-action-dispute')).toBeVisible();
	await expect(rail.getByTestId('invoice-action-submit')).toHaveCount(0);
});

test('action rail composition for SM on APPROVED shows Pay only', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'APPROVED' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const rail = page.getByTestId('invoice-action-rail').first();
	await expect(rail.getByTestId('invoice-action-pay')).toBeVisible();
	await expect(rail.getByTestId('invoice-action-approve')).toHaveCount(0);
	await expect(rail.getByTestId('invoice-action-dispute')).toHaveCount(0);
});

test('action rail composition for SM on DISPUTED shows Resolve', async ({ page }) => {
	await setupDetailPage(
		page,
		SM_USER,
		makeInvoice({ status: 'DISPUTED', dispute_reason: 'Quantity short' })
	);
	await page.goto(`/invoice/${INVOICE_ID}`);

	const rail = page.getByTestId('invoice-action-rail').first();
	await expect(rail.getByTestId('invoice-action-resolve')).toBeVisible();
});

test('PAID invoice shows Download PDF as solo action', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'PAID' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const rail = page.getByTestId('invoice-action-rail').first();
	await expect(rail.getByTestId('invoice-action-download-pdf')).toBeVisible();
	await expect(rail.getByTestId('invoice-action-overflow')).toHaveCount(0);
	await expect(rail.getByTestId('invoice-action-pay')).toHaveCount(0);
});

// QUALITY_LAB is excluded from canViewInvoices, so /invoice/[id] redirects them
// to /dashboard. PROCUREMENT_MANAGER and FREIGHT_MANAGER are the read-only viewers.
for (const readOnly of [PROCUREMENT_USER, FREIGHT_USER]) {
	test(`${readOnly.role} sees Download PDF only on SUBMITTED`, async ({ page }) => {
		await setupDetailPage(page, readOnly, makeInvoice({ status: 'SUBMITTED' }));
		await page.goto(`/invoice/${INVOICE_ID}`);

		const rail = page.getByTestId('invoice-action-rail').first();
		await expect(rail.getByTestId('invoice-action-download-pdf')).toBeVisible();
		await expect(rail.getByTestId('invoice-action-overflow')).toHaveCount(0);
		await expect(rail.getByTestId('invoice-action-approve')).toHaveCount(0);
		await expect(rail.getByTestId('invoice-action-dispute')).toHaveCount(0);
		await expect(rail.getByTestId('invoice-action-submit')).toHaveCount(0);
	});
}

test('dispute modal opens, validates non-empty reason, and posts dispute', async ({ page }) => {
	let disputeBody: { reason?: string } | null = null;
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'SUBMITTED' }));
	await page.route(`**/api/v1/invoices/${INVOICE_ID}/dispute`, async (route) => {
		const body = route.request().postDataJSON() as { reason?: string };
		disputeBody = body;
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(
				makeInvoice({ status: 'DISPUTED', dispute_reason: body.reason ?? '' })
			)
		});
	});

	await page.goto(`/invoice/${INVOICE_ID}`);

	const rail = page.getByTestId('invoice-action-rail').first();
	await rail.getByTestId('invoice-action-dispute').click();

	await expect(page.getByTestId('invoice-dispute-modal')).toBeVisible();
	await expect(page.getByTestId('invoice-dispute-confirm')).toBeDisabled();

	await page.getByTestId('invoice-dispute-reason-input').fill('Quantity short by 100');
	await expect(page.getByTestId('invoice-dispute-confirm')).toBeEnabled();
	await page.getByTestId('invoice-dispute-confirm').click();

	await expect(page.getByTestId('invoice-dispute-modal')).toHaveCount(0);
	expect(disputeBody).toEqual({ reason: 'Quantity short by 100' });
});

test('dispute modal Cancel closes without posting', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'SUBMITTED' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const rail = page.getByTestId('invoice-action-rail').first();
	await rail.getByTestId('invoice-action-dispute').click();
	await expect(page.getByTestId('invoice-dispute-modal')).toBeVisible();

	await page.getByTestId('invoice-dispute-cancel').click();
	await expect(page.getByTestId('invoice-dispute-modal')).toHaveCount(0);
});

test('dispute reason panel visible only when status is DISPUTED', async ({ page }) => {
	await setupDetailPage(
		page,
		SM_USER,
		makeInvoice({ status: 'DISPUTED', dispute_reason: 'Wrong total amount' })
	);
	await page.goto(`/invoice/${INVOICE_ID}`);

	await expect(page.getByTestId('invoice-dispute-reason-panel')).toBeVisible();
	await expect(page.getByTestId('invoice-dispute-reason-panel')).toContainText(
		'Wrong total amount'
	);
});

test('dispute reason panel hidden on SUBMITTED', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'SUBMITTED' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	await expect(page.getByTestId('invoice-dispute-reason-panel')).toHaveCount(0);
});

test('metadata panel renders summary fields with PO link', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'DRAFT' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const panel = page.getByTestId('invoice-metadata-panel');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText('USD');
	await expect(panel).toContainText('NET30');
	await expect(panel).toContainText('812.50');

	const poLink = page.getByTestId('invoice-metadata-po-link');
	await expect(poLink).toHaveAttribute('href', `/po/${PO_ID}`);
});

test('line items panel renders rows', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'DRAFT' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const panel = page.getByTestId('invoice-line-items-panel');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText('PN-001');
	await expect(panel).toContainText('Widget');
	await expect(panel).toContainText('PN-002');
	await expect(panel).toContainText('Sprocket');
});

test('activity panel renders feed and Show more reveals additional entries', async ({ page }) => {
	const entries = Array.from({ length: 12 }, (_, i) => ({
		id: `act-${i}`,
		entity_type: 'INVOICE',
		entity_id: INVOICE_ID,
		event: 'INVOICE_SUBMITTED',
		category: 'LIVE',
		target_role: null,
		actor_id: null,
		actor_username: null,
		detail: `entry ${i}`,
		read: false,
		created_at: '2026-04-01T12:00:00+00:00'
	}));

	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'DRAFT' }));
	// Last-registered wins in Playwright — override the catch-all from setupDetailPage
	// for the entity-scoped activity URL.
	await page.route('**/api/v1/activity/?**', (route) => {
		const url = new URL(route.request().url());
		if (url.searchParams.get('entity_type') === 'INVOICE') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(entries)
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto(`/invoice/${INVOICE_ID}`);

	const panel = page.getByTestId('invoice-activity-panel');
	await expect(panel).toBeVisible();
	const feed = page.getByTestId('invoice-activity-feed');
	await expect(feed.getByText('Invoice submitted')).toHaveCount(10);

	await page.getByTestId('invoice-activity-show-more-btn').click();
	await expect(feed.getByText('Invoice submitted')).toHaveCount(12);
});

test('activity panel shows empty state when no entries', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'DRAFT' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	const panel = page.getByTestId('invoice-activity-panel');
	await expect(panel).toContainText('No activity yet.');
});

test('Download PDF action opens the PDF URL in a new window', async ({ page }) => {
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'PAID' }));
	// downloadInvoicePdf uses window.open(target, '_blank'). Stub window.open to
	// capture the requested URL synchronously without depending on popup load timing.
	await page.addInitScript(() => {
		(window as unknown as { __openedUrls: string[] }).__openedUrls = [];
		const original = window.open;
		window.open = (url?: string | URL, ...rest) => {
			(window as unknown as { __openedUrls: string[] }).__openedUrls.push(String(url ?? ''));
			return original?.call(window, url, ...rest) ?? null;
		};
	});

	await page.goto(`/invoice/${INVOICE_ID}`);
	const rail = page.getByTestId('invoice-action-rail').first();
	await rail.getByTestId('invoice-action-download-pdf').click();

	const opened = await page.evaluate(
		() => (window as unknown as { __openedUrls: string[] }).__openedUrls
	);
	expect(opened).toContain(`/api/v1/invoices/${INVOICE_ID}/pdf`);
});

test('sticky-bottom rail at 390px viewport is sticky and overflow opens upward', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await setupDetailPage(page, SM_USER, makeInvoice({ status: 'SUBMITTED' }));
	await page.goto(`/invoice/${INVOICE_ID}`);

	// At <768px the inline rail in the header is hidden via CSS; the sticky-bottom
	// rail is the only one rendered.
	const rails = page.getByTestId('invoice-action-rail');
	await expect(rails).toHaveCount(2);
	const stickyRail = rails.nth(1);

	await expect(stickyRail.getByTestId('invoice-action-approve')).toBeVisible();
	await expect(stickyRail.getByTestId('invoice-action-overflow')).toBeVisible();
	await stickyRail.getByTestId('invoice-action-overflow').click();
	await expect(
		stickyRail.locator('.invoice-action-rail__menu--up')
	).toBeAttached();
});
