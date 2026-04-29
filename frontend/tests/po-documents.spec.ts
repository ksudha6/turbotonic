import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Iter 084 — PO document attachments (G-22). Covers panel/button visibility per
// (role, po_type), upload flow, delete flow, empty state, and cross-vendor.
// All selectors use getByRole / getByLabel / getByTestId per CLAUDE.md.
// ---------------------------------------------------------------------------

const PO_ID = 'uuid-doc-test';
const PO_VENDOR_ID = 'vendor-uuid-1';

// -- Test data constants ----------------------------------------------------

const PDF_FILENAME = 'signed.pdf';
const PDF_CONTENT = '%PDF-1.4 minimal';

const PROCUREMENT_SELECT_LABELS = ['Signed PO', 'Countersigned PO', 'Amendment', 'Addendum'];
const OPEX_SELECT_LABELS = ['Signed agreement', 'Amendment', 'Addendum'];

const FILE_ID = 'file-uuid-1';

const MOCK_FILE_ITEM = {
	id: FILE_ID,
	entity_type: 'PO',
	entity_id: PO_ID,
	file_type: 'SIGNED_PO',
	original_name: PDF_FILENAME,
	content_type: 'application/pdf',
	size_bytes: 1024,
	uploaded_at: '2026-04-20T10:00:00+00:00',
	uploaded_by: 'u-sm',
	uploaded_by_username: 'alice'
};

const MOCK_OPEX_FILE_ITEM = {
	...MOCK_FILE_ITEM,
	file_type: 'SIGNED_AGREEMENT',
	original_name: 'signed_agreement.pdf'
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
	vendor_id: PO_VENDOR_ID
};

const VENDOR_OTHER_USER = {
	id: 'u-vendor-other',
	username: 'vendor_other',
	display_name: 'Other Vendor',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-uuid-other'
};

const FREIGHT_USER = {
	id: 'u-fm',
	username: 'fm',
	display_name: 'Freight Manager',
	role: 'FREIGHT_MANAGER',
	status: 'ACTIVE',
	vendor_id: null
};

const PROCUREMENT_USER = {
	id: 'u-pm',
	username: 'pm',
	display_name: 'Procurement Manager',
	role: 'PROCUREMENT_MANAGER',
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
type POFixture = Record<string, unknown>;

// -- PO fixtures ------------------------------------------------------------

function makeProcurementPO(overrides: POFixture = {}): POFixture {
	return {
		id: PO_ID,
		po_number: 'PO-20260420-0001',
		status: 'ACCEPTED',
		po_type: 'PROCUREMENT',
		vendor_id: PO_VENDOR_ID,
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

function makeOpexPO(overrides: POFixture = {}): POFixture {
	return makeProcurementPO({ po_type: 'OPEX', ...overrides });
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

function mockReferenceData(page: Page) {
	return page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
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
				po_types: [
					{ code: 'PROCUREMENT', label: 'Procurement' },
					{ code: 'OPEX', label: 'Opex' }
				]
			})
		});
	});
}

function mockPoDetail(page: Page, po: POFixture) {
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

function mockPoDocuments(page: Page, files: object[] = []) {
	return page.route('**/api/v1/po/*/documents', (route) => {
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

async function setupDocumentsPage(page: Page, user: UserFixture, po: POFixture, files: object[] = []) {
	// Register in LIFO order: catch-all first (lowest priority), specific mocks on top.
	await mockApiCatchAll(page);
	await page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
	await mockReferenceData(page);
	// Milestones, invoices, remaining — return safe empty responses.
	await page.route('**/api/v1/po/*/milestones', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/invoices/po/*/remaining', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ po_id: PO_ID, lines: [] })
		});
	});
	await mockPoDocuments(page, files);
	await mockUser(page, user);
	await mockPoDetail(page, po);
}

// ---------------------------------------------------------------------------
// 1. Panel visibility per (role, po_type)
// ---------------------------------------------------------------------------

test('panel visible for SM on PROCUREMENT PO', async ({ page }) => {
	const po = makeProcurementPO();
	// SM can manage, so panel shows even with empty files (empty-state path).
	await setupDocumentsPage(page, SM_USER, po, []);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-panel')).toBeVisible();
});

test('panel visible for FREIGHT_MANAGER on PROCUREMENT PO with files', async ({ page }) => {
	const po = makeProcurementPO();
	// FM can view but not manage on PROCUREMENT; panel only shows when files exist.
	await setupDocumentsPage(page, FREIGHT_USER, po, [MOCK_FILE_ITEM]);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-panel')).toBeVisible();
});

test('panel hidden for SM on OPEX PO', async ({ page }) => {
	const po = makeOpexPO();
	// SM cannot view OPEX attachments; panel does not render.
	await setupDocumentsPage(page, SM_USER, po, [MOCK_OPEX_FILE_ITEM]);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-panel')).toHaveCount(0);
});

test('panel visible for FREIGHT_MANAGER on OPEX PO', async ({ page }) => {
	const po = makeOpexPO();
	// FM can manage OPEX; panel visible even with empty files.
	await setupDocumentsPage(page, FREIGHT_USER, po, []);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-panel')).toBeVisible();
});

test('panel hidden for QUALITY_LAB on OPEX PO', async ({ page }) => {
	const po = makeOpexPO();
	// QL cannot view OPEX attachments at all.
	await setupDocumentsPage(page, QUALITY_USER, po, [MOCK_OPEX_FILE_ITEM]);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-panel')).toHaveCount(0);
});

test('panel hidden for VENDOR from a different vendor on PROCUREMENT PO', async ({ page }) => {
	const po = makeProcurementPO();
	// VENDOR(other) cannot view attachments for a PO owned by a different vendor.
	await setupDocumentsPage(page, VENDOR_OTHER_USER, po, [MOCK_FILE_ITEM]);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-panel')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 2. Upload button visibility per (role, po_type)
// ---------------------------------------------------------------------------

test('upload button visible for SM on PROCUREMENT PO (manage permission)', async ({ page }) => {
	const po = makeProcurementPO();
	await setupDocumentsPage(page, SM_USER, po, []);
	await page.goto(`/po/${PO_ID}`);
	// At least one upload button is present in the panel (header slot or empty-state action).
	await expect(page.getByTestId('po-documents-upload-btn').first()).toBeVisible();
});

test('upload button hidden for FREIGHT_MANAGER on PROCUREMENT PO (view-only)', async ({ page }) => {
	const po = makeProcurementPO();
	// FM views but cannot manage on PROCUREMENT; upload button absent.
	await setupDocumentsPage(page, FREIGHT_USER, po, [MOCK_FILE_ITEM]);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-panel')).toBeVisible();
	await expect(page.getByTestId('po-documents-upload-btn')).toHaveCount(0);
});

test('upload button visible for FREIGHT_MANAGER on OPEX PO (manage permission)', async ({ page }) => {
	const po = makeOpexPO();
	await setupDocumentsPage(page, FREIGHT_USER, po, []);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-upload-btn').first()).toBeVisible();
});

test('upload button hidden for VENDOR own on OPEX PO (view-only)', async ({ page }) => {
	const po = makeOpexPO();
	// VENDOR(own) can view but not manage OPEX attachments.
	await setupDocumentsPage(page, VENDOR_OWN_USER, po, [MOCK_OPEX_FILE_ITEM]);
	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-documents-panel')).toBeVisible();
	await expect(page.getByTestId('po-documents-upload-btn')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 3. Upload flow happy path — PROCUREMENT, SM
// ---------------------------------------------------------------------------

test('upload dialog shows PROCUREMENT file type options and row appears after submit', async ({ page }) => {
	const po = makeProcurementPO();
	const uploadedFile = { ...MOCK_FILE_ITEM, id: 'file-new-1', original_name: PDF_FILENAME };

	await setupDocumentsPage(page, SM_USER, po, []);

	// Override documents route to handle POST.
	await page.route('**/api/v1/po/*/documents', (route) => {
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

	await page.goto(`/po/${PO_ID}`);

	// Click the header upload button (first instance; empty-state also renders one).
	await page.getByTestId('po-documents-upload-btn').first().click();
	const dialog = page.getByRole('dialog', { name: 'Upload document' });
	await expect(dialog).toBeVisible();

	// Select shows all four PROCUREMENT labels and none of the OPEX-only ones.
	const select = page.getByLabel('Document type');
	const options = select.locator('option');
	await expect(options).toHaveText(PROCUREMENT_SELECT_LABELS);

	// Attach a minimal PDF file.
	await page.setInputFiles('[data-testid="po-document-file-input"]', {
		name: PDF_FILENAME,
		mimeType: 'application/pdf',
		buffer: Buffer.from(PDF_CONTENT)
	});

	// Submit — dialog closes, new row visible.
	await page.getByTestId('po-document-upload-submit').click();
	await expect(dialog).toHaveCount(0);
	await expect(page.getByTestId(`po-documents-row-${uploadedFile.id}`)).toBeVisible();
});

// ---------------------------------------------------------------------------
// 4. Upload flow happy path — OPEX, FREIGHT_MANAGER
// ---------------------------------------------------------------------------

test('upload dialog shows OPEX file type options and row appears after submit', async ({ page }) => {
	const po = makeOpexPO();
	const uploadedFile = {
		...MOCK_OPEX_FILE_ITEM,
		id: 'file-new-2',
		file_type: 'SIGNED_AGREEMENT',
		original_name: 'signed_agreement.pdf'
	};

	await setupDocumentsPage(page, FREIGHT_USER, po, []);

	await page.route('**/api/v1/po/*/documents', (route) => {
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

	await page.goto(`/po/${PO_ID}`);

	await page.getByTestId('po-documents-upload-btn').first().click();
	const dialog = page.getByRole('dialog', { name: 'Upload document' });
	await expect(dialog).toBeVisible();

	// Select shows exactly the three OPEX labels (no SIGNED_PO or COUNTERSIGNED_PO).
	const select = page.getByLabel('Document type');
	const options = select.locator('option');
	await expect(options).toHaveText(OPEX_SELECT_LABELS);

	await page.setInputFiles('[data-testid="po-document-file-input"]', {
		name: 'signed_agreement.pdf',
		mimeType: 'application/pdf',
		buffer: Buffer.from(PDF_CONTENT)
	});

	await page.getByTestId('po-document-upload-submit').click();
	await expect(dialog).toHaveCount(0);
	await expect(page.getByTestId(`po-documents-row-${uploadedFile.id}`)).toBeVisible();
});

// ---------------------------------------------------------------------------
// 5. Dialog cancel closes without POST
// ---------------------------------------------------------------------------

test('upload dialog cancel closes without firing POST request', async ({ page }) => {
	const po = makeProcurementPO();
	await setupDocumentsPage(page, SM_USER, po, []);

	let postCount = 0;
	await page.route('**/api/v1/po/*/documents', (route) => {
		if (route.request().method() === 'POST') {
			postCount++;
			route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_FILE_ITEM) });
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-documents-upload-btn').first().click();

	const dialog = page.getByRole('dialog', { name: 'Upload document' });
	await expect(dialog).toBeVisible();

	await page.getByTestId('po-document-upload-cancel').click();
	await expect(dialog).toHaveCount(0);

	// POST must not have been fired.
	expect(postCount).toBe(0);
});

// ---------------------------------------------------------------------------
// 6. Client-side validation: non-PDF rejection
// ---------------------------------------------------------------------------

test('upload dialog shows inline error and keeps dialog open for non-PDF file', async ({ page }) => {
	const po = makeProcurementPO();
	await setupDocumentsPage(page, SM_USER, po, []);

	let postCount = 0;
	await page.route('**/api/v1/po/*/documents', (route) => {
		if (route.request().method() === 'POST') {
			postCount++;
			route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_FILE_ITEM) });
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-documents-upload-btn').first().click();

	const dialog = page.getByRole('dialog', { name: 'Upload document' });
	await expect(dialog).toBeVisible();

	// Attach a PNG instead of a PDF.
	await page.setInputFiles('[data-testid="po-document-file-input"]', {
		name: 'image.png',
		mimeType: 'image/png',
		buffer: Buffer.from([0x89, 0x50, 0x4e, 0x47]) // PNG magic bytes
	});

	await page.getByTestId('po-document-upload-submit').click();

	// Dialog stays open and inline error shown; no POST fired.
	await expect(dialog).toBeVisible();
	await expect(page.getByTestId('po-document-file-field-error')).toContainText('Only PDF files are accepted.');
	expect(postCount).toBe(0);
});

// ---------------------------------------------------------------------------
// 7. Client-side validation: oversize file
// ---------------------------------------------------------------------------

test('upload dialog shows inline error and keeps dialog open for oversize file', async ({ page }) => {
	const po = makeProcurementPO();
	await setupDocumentsPage(page, SM_USER, po, []);

	let postCount = 0;
	await page.route('**/api/v1/po/*/documents', (route) => {
		if (route.request().method() === 'POST') {
			postCount++;
			route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_FILE_ITEM) });
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-documents-upload-btn').first().click();

	const dialog = page.getByRole('dialog', { name: 'Upload document' });
	await expect(dialog).toBeVisible();

	// Attach a file larger than 10MB (11MB buffer, PDF MIME so MIME check passes first — but
	// size check fires before MIME check in the component; use PDF MIME to isolate the size path).
	await page.setInputFiles('[data-testid="po-document-file-input"]', {
		name: 'large.pdf',
		mimeType: 'application/pdf',
		buffer: Buffer.alloc(11 * 1024 * 1024)
	});

	await page.getByTestId('po-document-upload-submit').click();

	await expect(dialog).toBeVisible();
	await expect(page.getByTestId('po-document-file-field-error')).toContainText('File must be 10 MB or smaller.');
	expect(postCount).toBe(0);
});

// ---------------------------------------------------------------------------
// 8. Delete flow
// ---------------------------------------------------------------------------

test('delete flow removes row after confirm and DELETE 204', async ({ page }) => {
	const po = makeProcurementPO();
	await setupDocumentsPage(page, SM_USER, po, [MOCK_FILE_ITEM]);

	// Accept the native confirm dialog.
	page.on('dialog', (dialog) => dialog.accept());

	await page.route(`**/api/v1/po/*/documents/${FILE_ID}`, (route) => {
		if (route.request().method() === 'DELETE') {
			route.fulfill({ status: 204 });
		} else {
			route.continue();
		}
	});

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId(`po-documents-row-${FILE_ID}`)).toBeVisible();

	await page.getByTestId(`po-documents-delete-${FILE_ID}-btn`).click();

	await expect(page.getByTestId(`po-documents-row-${FILE_ID}`)).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 9. Empty state with manage permission
// ---------------------------------------------------------------------------

test('empty state shown with upload button when SM has no documents on PROCUREMENT PO', async ({ page }) => {
	const po = makeProcurementPO();
	await setupDocumentsPage(page, SM_USER, po, []);

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-documents-panel');
	await expect(panel).toBeVisible();
	await expect(page.getByTestId('po-documents-empty-state')).toBeVisible();
	// Upload button present; two instances render (header action + empty-state action).
	await expect(page.getByTestId('po-documents-upload-btn').first()).toBeVisible();
});

// ---------------------------------------------------------------------------
// 10. Empty + view-only hides panel entirely
// ---------------------------------------------------------------------------

test('panel hidden entirely for QUALITY_LAB viewing PROCUREMENT PO with no documents', async ({ page }) => {
	const po = makeProcurementPO();
	// QL can view PROCUREMENT attachments but cannot manage. With empty files,
	// shouldRender = canView && (files.length > 0 || canManage) = false.
	await setupDocumentsPage(page, QUALITY_USER, po, []);

	await page.goto(`/po/${PO_ID}`);

	await expect(page.getByTestId('po-documents-panel')).toHaveCount(0);
});
