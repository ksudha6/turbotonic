import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Iter 112 — invoice document attachments. Covers panel/button visibility per
// role, upload flow, delete flow, empty state, and cross-vendor.
// All selectors use getByRole / getByLabel / getByTestId per CLAUDE.md.
// ---------------------------------------------------------------------------

const INVOICE_ID = 'uuid-inv-doc-test';
const PO_ID = 'uuid-po-inv-doc-test';
const VENDOR_ID = 'vendor-uuid-inv-1';

const PDF_FILENAME = 'invoice.pdf';
const PDF_CONTENT = '%PDF-1.4 minimal';

const FILE_ID = 'inv-file-uuid-1';

const MOCK_FILE_ITEM = {
	id: FILE_ID,
	entity_type: 'INVOICE',
	entity_id: INVOICE_ID,
	file_type: 'VENDOR_INVOICE_PDF',
	original_name: PDF_FILENAME,
	content_type: 'application/pdf',
	size_bytes: 1024,
	uploaded_at: '2026-04-20T10:00:00+00:00',
	uploaded_by: 'u-vendor',
	uploaded_by_username: 'vendor_user'
};

// -- User fixtures ----------------------------------------------------------

const ADMIN_USER = {
	id: 'u-admin',
	username: 'admin',
	display_name: 'Admin User',
	role: 'ADMIN',
	status: 'ACTIVE',
	vendor_id: null
};

const SM_USER = {
	id: 'u-sm',
	username: 'sm',
	display_name: 'SM User',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null
};

const VENDOR_OWN_USER = {
	id: 'u-vendor-own',
	username: 'vendor_own',
	display_name: 'Own Vendor',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: VENDOR_ID
};

const VENDOR_OTHER_USER = {
	id: 'u-vendor-other',
	username: 'vendor_other',
	display_name: 'Other Vendor',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-uuid-other'
};

const PROCUREMENT_USER = {
	id: 'u-pm',
	username: 'pm',
	display_name: 'Procurement Manager',
	role: 'PROCUREMENT_MANAGER',
	status: 'ACTIVE',
	vendor_id: null
};

const FREIGHT_USER = {
	id: 'u-fm',
	username: 'fm',
	display_name: 'Freight Manager',
	role: 'FREIGHT_MANAGER',
	status: 'ACTIVE',
	vendor_id: null
};

const QUALITY_USER = {
	id: 'u-ql',
	username: 'ql',
	display_name: 'Quality Lab',
	role: 'QUALITY_LAB',
	status: 'ACTIVE',
	vendor_id: null
};

type UserFixture = typeof SM_USER;

// -- Invoice + PO fixtures --------------------------------------------------

function makeInvoice(overrides: Record<string, unknown> = {}): Record<string, unknown> {
	return {
		id: INVOICE_ID,
		invoice_number: 'INV-20260420-0001',
		po_id: PO_ID,
		status: 'DRAFT',
		payment_terms: 'NET30',
		currency: 'USD',
		line_items: [],
		subtotal: '50.00',
		dispute_reason: '',
		created_at: '2026-04-20T10:00:00+00:00',
		updated_at: '2026-04-20T10:00:00+00:00',
		...overrides
	};
}

function makePO(overrides: Record<string, unknown> = {}): Record<string, unknown> {
	return {
		id: PO_ID,
		po_number: 'PO-20260420-0001',
		status: 'ACCEPTED',
		po_type: 'PROCUREMENT',
		vendor_id: VENDOR_ID,
		vendor_name: 'Acme Corp',
		vendor_country: 'CN',
		buyer_name: 'TurboTonic Ltd',
		buyer_country: 'US',
		ship_to_address: '123 Main St',
		payment_terms: 'NET30',
		currency: 'USD',
		issued_date: '2026-04-01T00:00:00+00:00',
		required_delivery_date: '2026-05-01T00:00:00+00:00',
		terms_and_conditions: 'Standard terms',
		incoterm: 'FOB',
		port_of_loading: 'CNSHA',
		port_of_discharge: 'USLAX',
		country_of_origin: 'CN',
		country_of_destination: 'US',
		marketplace: null,
		line_items: [],
		rejection_history: [],
		total_value: '1000',
		created_at: '2026-04-01T00:00:00+00:00',
		updated_at: '2026-04-01T00:00:00+00:00',
		round_count: 0,
		last_actor_role: null,
		advance_paid_at: null,
		has_removed_line: false,
		current_milestone: null,
		...overrides
	};
}

// -- Mock helpers -----------------------------------------------------------

function mockUser(page: Page, user: UserFixture) {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user })
		});
	});
}

function mockInvoiceDetail(page: Page, invoice: Record<string, unknown>) {
	return page.route(`**/api/v1/invoices/${INVOICE_ID}`, (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(invoice)
		});
	});
}

function mockPODetail(page: Page, po: Record<string, unknown>) {
	return page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		const path = new URL(route.request().url()).pathname;
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

function mockInvoiceDocuments(page: Page, files: object[] = []) {
	return page.route(`**/api/v1/invoices/${INVOICE_ID}/documents`, (route) => {
		if (route.request().method() === 'GET') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(files)
			});
		} else {
			route.continue();
		}
	});
}

function mockApiCatchAll(page: Page) {
	return page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

async function setupInvoiceDetailPage(
	page: Page,
	user: UserFixture,
	files: object[] = []
) {
	await mockApiCatchAll(page);
	await page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
	await page.route(`**/api/v1/activity/entity/INVOICE/${INVOICE_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await mockInvoiceDocuments(page, files);
	await mockInvoiceDetail(page, makeInvoice());
	await mockPODetail(page, makePO());
	await mockUser(page, user);
}

// ---------------------------------------------------------------------------
// 1. Panel visibility per role
// ---------------------------------------------------------------------------

test('invoice documents panel visible for SM with no files (manage permission)', async ({ page }) => {
	await setupInvoiceDetailPage(page, SM_USER, []);
	await page.goto(`/invoice/${INVOICE_ID}`);
	await expect(page.getByTestId('invoice-documents-panel')).toBeVisible();
});

test('invoice documents panel visible for VENDOR own with files', async ({ page }) => {
	await setupInvoiceDetailPage(page, VENDOR_OWN_USER, [MOCK_FILE_ITEM]);
	await page.goto(`/invoice/${INVOICE_ID}`);
	await expect(page.getByTestId('invoice-documents-panel')).toBeVisible();
});

test('invoice documents panel visible for PROCUREMENT_MANAGER with files (view-only)', async ({ page }) => {
	await setupInvoiceDetailPage(page, PROCUREMENT_USER, [MOCK_FILE_ITEM]);
	await page.goto(`/invoice/${INVOICE_ID}`);
	await expect(page.getByTestId('invoice-documents-panel')).toBeVisible();
});

test('invoice documents panel hidden for QUALITY_LAB', async ({ page }) => {
	await setupInvoiceDetailPage(page, QUALITY_USER, [MOCK_FILE_ITEM]);
	await page.goto(`/invoice/${INVOICE_ID}`);
	await expect(page.getByTestId('invoice-documents-panel')).toHaveCount(0);
});

test('invoice documents panel hidden for VENDOR from a different vendor', async ({ page }) => {
	await setupInvoiceDetailPage(page, VENDOR_OTHER_USER, [MOCK_FILE_ITEM]);
	await page.goto(`/invoice/${INVOICE_ID}`);
	await expect(page.getByTestId('invoice-documents-panel')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 2. Upload button visibility
// ---------------------------------------------------------------------------

test('upload button visible for SM (manage permission)', async ({ page }) => {
	await setupInvoiceDetailPage(page, SM_USER, []);
	await page.goto(`/invoice/${INVOICE_ID}`);
	await expect(page.getByTestId('invoice-documents-upload-btn').first()).toBeVisible();
});

test('upload button hidden for PROCUREMENT_MANAGER (view-only)', async ({ page }) => {
	await setupInvoiceDetailPage(page, PROCUREMENT_USER, [MOCK_FILE_ITEM]);
	await page.goto(`/invoice/${INVOICE_ID}`);
	await expect(page.getByTestId('invoice-documents-panel')).toBeVisible();
	await expect(page.getByTestId('invoice-documents-upload-btn')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 3. Upload flow: dialog shows all four attachment types, row appears after submit
// ---------------------------------------------------------------------------

test('upload dialog shows all invoice attachment types and row appears after submit', async ({ page }) => {
	await setupInvoiceDetailPage(page, SM_USER, []);

	const uploadedFile = { ...MOCK_FILE_ITEM, id: 'file-new-1' };

	await page.route(`**/api/v1/invoices/${INVOICE_ID}/documents`, (route) => {
		if (route.request().method() === 'POST') {
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(uploadedFile)
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto(`/invoice/${INVOICE_ID}`);

	await page.getByTestId('invoice-documents-upload-btn').first().click();
	const dialog = page.getByRole('dialog', { name: 'Upload document' });
	await expect(dialog).toBeVisible();

	// All four attachment type options must be present.
	const select = page.getByLabel('Document type');
	const options = select.locator('option');
	await expect(options).toHaveText([
		'Vendor invoice PDF',
		'Credit note',
		'Debit note',
		'Other'
	]);

	await page.setInputFiles('[data-testid="invoice-document-file-input"]', {
		name: PDF_FILENAME,
		mimeType: 'application/pdf',
		buffer: Buffer.from(PDF_CONTENT)
	});

	await page.getByTestId('invoice-document-upload-submit').click();
	await expect(dialog).toHaveCount(0);
	await expect(page.getByTestId(`invoice-documents-row-${uploadedFile.id}`)).toBeVisible();
});

// ---------------------------------------------------------------------------
// 4. Client-side validation: non-PDF file rejected before POST
// ---------------------------------------------------------------------------

test('upload dialog shows error and keeps open for non-PDF file', async ({ page }) => {
	await setupInvoiceDetailPage(page, SM_USER, []);

	let postCount = 0;
	await page.route(`**/api/v1/invoices/${INVOICE_ID}/documents`, (route) => {
		if (route.request().method() === 'POST') {
			postCount++;
			route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_FILE_ITEM) });
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto(`/invoice/${INVOICE_ID}`);
	await page.getByTestId('invoice-documents-upload-btn').first().click();

	const dialog = page.getByRole('dialog', { name: 'Upload document' });
	await expect(dialog).toBeVisible();

	await page.setInputFiles('[data-testid="invoice-document-file-input"]', {
		name: 'image.png',
		mimeType: 'image/png',
		buffer: Buffer.from([0x89, 0x50, 0x4e, 0x47])
	});

	await page.getByTestId('invoice-document-upload-submit').click();

	await expect(dialog).toBeVisible();
	await expect(page.getByTestId('invoice-document-file-field-error')).toContainText('Only PDF files are accepted.');
	expect(postCount).toBe(0);
});

// ---------------------------------------------------------------------------
// 5. Client-side validation: oversize file rejected before POST
// ---------------------------------------------------------------------------

test('upload dialog shows error and keeps open for oversize file', async ({ page }) => {
	await setupInvoiceDetailPage(page, SM_USER, []);

	let postCount = 0;
	await page.route(`**/api/v1/invoices/${INVOICE_ID}/documents`, (route) => {
		if (route.request().method() === 'POST') {
			postCount++;
			route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_FILE_ITEM) });
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto(`/invoice/${INVOICE_ID}`);
	await page.getByTestId('invoice-documents-upload-btn').first().click();

	const dialog = page.getByRole('dialog', { name: 'Upload document' });
	await expect(dialog).toBeVisible();

	await page.setInputFiles('[data-testid="invoice-document-file-input"]', {
		name: 'large.pdf',
		mimeType: 'application/pdf',
		buffer: Buffer.alloc(11 * 1024 * 1024)
	});

	await page.getByTestId('invoice-document-upload-submit').click();

	await expect(dialog).toBeVisible();
	await expect(page.getByTestId('invoice-document-file-field-error')).toContainText('File must be 10 MB or smaller.');
	expect(postCount).toBe(0);
});
