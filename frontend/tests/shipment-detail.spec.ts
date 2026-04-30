import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import type { ShipmentStatus, User, UserRole } from '../src/lib/types';

// ---------------------------------------------------------------------------
// Iter 097 — `/shipments/[id]` shell port + line items panel.
// Iter 099 — documents + readiness + mark-ready UI.
// ---------------------------------------------------------------------------

const SHIPMENT_ID = 'ship-uuid-1';
const PART_A = 'PN-A';
const PART_B = 'PN-B';

type ShipmentFixture = Record<string, unknown>;

function makeShipment(overrides: ShipmentFixture = {}): ShipmentFixture {
	return {
		id: SHIPMENT_ID,
		po_id: 'po-uuid-1',
		shipment_number: 'SHP-20260401-0001',
		marketplace: 'AMAZON',
		status: 'DRAFT' as ShipmentStatus,
		line_items: [
			{
				id: 'li-1',
				shipment_id: SHIPMENT_ID,
				part_number: PART_A,
				product_id: null,
				description: 'Widget',
				quantity: 100,
				uom: 'EA',
				sort_order: 0,
				net_weight: null,
				gross_weight: null,
				package_count: null,
				dimensions: null,
				country_of_origin: null
			},
			{
				id: 'li-2',
				shipment_id: SHIPMENT_ID,
				part_number: PART_B,
				product_id: null,
				description: 'Sprocket',
				quantity: 50,
				uom: 'EA',
				sort_order: 1,
				net_weight: '12.5',
				gross_weight: '14.0',
				package_count: 5,
				dimensions: '40x30x20 cm',
				country_of_origin: 'CN'
			}
		],
		created_at: '2026-04-01T10:00:00+00:00',
		updated_at: '2026-04-02T10:00:00+00:00',
		...overrides
	};
}

// ---------------------------------------------------------------------------
// Iter 099 builder helpers
// ---------------------------------------------------------------------------

type RequirementFixture = Record<string, unknown>;
type ReadinessFixture = Record<string, unknown>;

function makeRequirement(overrides: RequirementFixture = {}): RequirementFixture {
	return {
		id: 'req-1',
		shipment_id: SHIPMENT_ID,
		document_type: 'PACKING_LIST',
		status: 'PENDING',
		is_auto_generated: true,
		document_id: null,
		created_at: '2026-04-01T10:00:00+00:00',
		...overrides
	};
}

function makeReadiness(overrides: ReadinessFixture = {}): ReadinessFixture {
	return {
		documents_ready: true,
		certificates_ready: true,
		packaging_ready: true,
		is_ready: true,
		missing_documents: [],
		missing_certificates: [],
		missing_packaging: [],
		...overrides
	};
}

// Default all-ready readiness used by the shared mock helper.
const DEFAULT_READINESS = makeReadiness();

// ---------------------------------------------------------------------------
// User fixtures
// ---------------------------------------------------------------------------

const SM_USER: User = {
	id: 'u-sm',
	username: 'sm',
	display_name: 'SM User',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null,
	email: null
};

const VENDOR_USER: User = {
	id: 'u-v',
	username: 'vendor',
	display_name: 'Vendor User',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-1',
	email: null
};

function userForRole(role: UserRole): User {
	if (role === 'SM') return SM_USER;
	if (role === 'VENDOR') return VENDOR_USER;
	return { ...SM_USER, role };
}

// ---------------------------------------------------------------------------
// Shared route-mock helper (iter 097 + iter 102)
//
// IMPORTANT: Do not register routes for the base shipment endpoint
// (`**/api/v1/shipments/${SHIPMENT_ID}`) inside test bodies using the same
// URL pattern. Playwright glob patterns are prefix-matched, so
// `**/api/v1/shipments/ship-uuid-1` also intercepts sub-paths like
// `ship-uuid-1/requirements` and `ship-uuid-1/readiness`. All sub-path
// routes are registered here with distinct patterns; tests override them
// via `page.route` with the same pattern (LIFO wins) when needed.
// ---------------------------------------------------------------------------

async function setupShipmentDetail(
	page: Page,
	opts: {
		status?: ShipmentStatus;
		role?: UserRole;
		shipmentOverride?: ShipmentFixture;
		requirements?: RequirementFixture[];
		readiness?: ReadinessFixture | null;
	} = {}
) {
	const status = opts.status ?? 'DRAFT';
	const role = opts.role ?? 'SM';
	const fixture = makeShipment({ status, ...opts.shipmentOverride });

	// When caller passes undefined for readiness, use default all-ready; null means "skip mock".
	const readinessMock = 'readiness' in opts ? opts.readiness : DEFAULT_READINESS;
	const requirementsMock = opts.requirements ?? [];

	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: userForRole(role) })
		});
	});
	await page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ count: 0 })
		});
	});
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	// Base shipment endpoint — only EXACT URL (no sub-paths).
	// LIFO: if a test needs a different response for a specific call, re-register
	// this route inside the test body using the same pattern.
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}`, (route) => {
		if (route.request().method() === 'GET') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(fixture)
			});
		} else {
			route.fallback();
		}
	});

	// Requirements list + add (iter 102). GET returns the fixture; POST defaults to success.
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/requirements`, (route) => {
		if (route.request().method() === 'GET') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(requirementsMock)
			});
		} else if (route.request().method() === 'POST') {
			let docType = 'USER_DEFINED';
			try {
				docType = JSON.parse(route.request().postData() ?? '{}').document_type ?? 'USER_DEFINED';
			} catch {
				// ignore
			}
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(
					makeRequirement({
						id: 'req-new',
						document_type: docType,
						status: 'PENDING',
						is_auto_generated: false
					})
				)
			});
		} else {
			route.fallback();
		}
	});

	// Readiness (iter 102) — only mock when non-null.
	if (readinessMock !== null) {
		await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/readiness`, (route) => {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(readinessMock)
			});
		});
	}

	// Transition endpoints — success-by-default so accidental clicks during
	// navigation don't 404. Tests override these with specific assertions.
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/submit-for-documents`, (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(makeShipment({ status: 'DOCUMENTS_PENDING' }))
		});
	});
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/mark-ready`, (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(makeShipment({ status: 'READY_TO_SHIP' }))
		});
	});
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/documents/*/upload`, (route) => {
		const url = route.request().url();
		const reqIdMatch = url.match(/\/documents\/([^/]+)\/upload/);
		const reqId = reqIdMatch?.[1] ?? 'req-1';
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(
				makeRequirement({
					id: reqId,
					status: 'COLLECTED',
					document_id: 'file-uuid-1',
					is_auto_generated: false
				})
			)
		});
	});
}

// ---------------------------------------------------------------------------
// Iter 097 specs
// ---------------------------------------------------------------------------

test('shipment detail page mounts under (nexus) shell with header + panels', async ({ page }) => {
	await setupShipmentDetail(page);
	await page.goto(`/shipments/${SHIPMENT_ID}`);

	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByTestId('shipment-detail-header')).toBeVisible();
	await expect(page.getByTestId('shipment-meta-panel')).toBeVisible();
	await expect(page.getByTestId('shipment-line-items-panel')).toBeVisible();
});

test('status pill renders correct tone per shipment status', async ({ page }) => {
	type Row = { status: ShipmentStatus; tone: 'gray' | 'orange' | 'blue' | 'green'; text: string };
	const rows: Row[] = [
		{ status: 'DRAFT', tone: 'gray', text: 'Draft' },
		{ status: 'READY_TO_SHIP', tone: 'blue', text: 'Ready To Ship' },
		{ status: 'SHIPPED', tone: 'green', text: 'Shipped' }
	];

	for (const row of rows) {
		await setupShipmentDetail(page, { status: row.status });
		await page.goto(`/shipments/${SHIPMENT_ID}`);
		const pill = page.getByTestId('shipment-detail-status');
		await expect(pill).toBeVisible();
		await expect(pill).toContainText(row.text);
		await expect(pill).toHaveClass(new RegExp(`\\b${row.tone}\\b`));
		await page.unrouteAll({ behavior: 'ignoreErrors' });
	}
});

test('DRAFT shipment exposes editable inputs for SM', async ({ page }) => {
	await setupShipmentDetail(page, { status: 'DRAFT', role: 'SM' });
	await page.goto(`/shipments/${SHIPMENT_ID}`);

	const panel = page.getByTestId('shipment-line-items-panel');
	await expect(panel).toBeVisible();
	const netWeightInput = panel.getByTestId(`shipment-line-item-net-weight-${PART_A}`).first();
	await expect(netWeightInput).toBeVisible();
	await expect(netWeightInput).toHaveJSProperty('tagName', 'INPUT');
	await expect(panel.getByTestId('shipment-line-items-save').first()).toBeVisible();
});

test('READY_TO_SHIP shipment renders read-only cells', async ({ page }) => {
	await setupShipmentDetail(page, { status: 'READY_TO_SHIP', role: 'SM' });
	await page.goto(`/shipments/${SHIPMENT_ID}`);

	const panel = page.getByTestId('shipment-line-items-panel');
	await expect(panel).toBeVisible();
	await expect(panel.getByTestId(`shipment-line-item-net-weight-${PART_A}`)).toHaveCount(0);
	await expect(panel.getByTestId('shipment-line-items-save')).toHaveCount(0);
	const row = panel.getByTestId(`shipment-line-item-row-${PART_B}`).first();
	await expect(row).toContainText('12.5');
	await expect(row).toContainText('14.0');
});

test('save round-trip sends trimmed fields and shows Saved pill', async ({ page }) => {
	await setupShipmentDetail(page, { status: 'DRAFT', role: 'SM' });

	let captured: Record<string, unknown> = {};
	const updated = makeShipment({
		status: 'DRAFT',
		line_items: [
			{
				id: 'li-1',
				shipment_id: SHIPMENT_ID,
				part_number: PART_A,
				product_id: null,
				description: 'Widget',
				quantity: 100,
				uom: 'EA',
				sort_order: 0,
				net_weight: '8.25',
				gross_weight: null,
				package_count: 3,
				dimensions: null,
				country_of_origin: null
			},
			{
				id: 'li-2',
				shipment_id: SHIPMENT_ID,
				part_number: PART_B,
				product_id: null,
				description: 'Sprocket',
				quantity: 50,
				uom: 'EA',
				sort_order: 1,
				net_weight: '12.5',
				gross_weight: '14.0',
				package_count: 5,
				dimensions: '40x30x20 cm',
				country_of_origin: 'CN'
			}
		]
	});
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}`, (route) => {
		const method = route.request().method();
		if (method === 'PATCH') {
			captured = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(updated)
			});
		} else {
			route.fallback();
		}
	});

	await page.goto(`/shipments/${SHIPMENT_ID}`);
	const panel = page.getByTestId('shipment-line-items-panel');
	await expect(panel).toBeVisible();

	await panel.getByTestId(`shipment-line-item-net-weight-${PART_A}`).first().fill('  8.25  ');
	await panel.getByTestId(`shipment-line-item-package-count-${PART_A}`).first().fill('3');

	await panel.getByTestId('shipment-line-items-save').first().click();

	await expect(panel.getByTestId('shipment-line-items-saved-pill').first()).toBeVisible();

	const lineItems = (captured['line_items'] as Record<string, unknown>[]) ?? [];
	const partA = lineItems.find((li) => li['part_number'] === PART_A) ?? {};
	expect(partA['net_weight']).toBe('8.25');
	expect(partA['package_count']).toBe(3);
	expect(partA['gross_weight']).toBeNull();
	expect(partA['dimensions']).toBeNull();
	expect(partA['country_of_origin']).toBeNull();
});

test('save error renders inline message', async ({ page }) => {
	await setupShipmentDetail(page, { status: 'DRAFT', role: 'SM' });
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}`, (route) => {
		const method = route.request().method();
		if (method === 'PATCH') {
			route.fulfill({
				status: 500,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'boom' })
			});
		} else {
			route.fallback();
		}
	});

	await page.goto(`/shipments/${SHIPMENT_ID}`);
	const panel = page.getByTestId('shipment-line-items-panel');
	await panel.getByTestId('shipment-line-items-save').first().click();

	await expect(panel.getByTestId('shipment-line-items-error').first()).toContainText('boom');
});

test('download buttons fire GETs to packing-list and commercial-invoice', async ({ page }) => {
	await setupShipmentDetail(page, { status: 'DRAFT', role: 'SM' });

	let packingHits = 0;
	let ciHits = 0;
	const PDF_BODY = '%PDF-1.4\n';
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/packing-list`, (route) => {
		packingHits += 1;
		route.fulfill({ status: 200, contentType: 'application/pdf', body: PDF_BODY });
	});
	await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/commercial-invoice`, (route) => {
		ciHits += 1;
		route.fulfill({ status: 200, contentType: 'application/pdf', body: PDF_BODY });
	});

	await page.goto(`/shipments/${SHIPMENT_ID}`);
	await expect(page.getByTestId('shipment-detail-header')).toBeVisible();

	await page.getByTestId('shipment-download-packing-list').click();
	await expect.poll(() => packingHits).toBeGreaterThan(0);

	await page.getByTestId('shipment-download-commercial-invoice').click();
	await expect.poll(() => ciHits).toBeGreaterThan(0);
});

// ---------------------------------------------------------------------------
// Iter 099 — documents + readiness
// ---------------------------------------------------------------------------

test.describe('iter 102 — documents + readiness', () => {
	// -----------------------------------------------------------------------
	// Spec 1: DRAFT + SM — submit button visible; docs + readiness panels absent.
	// Click submit → DOCUMENTS_PENDING UI appears.
	//
	// After submit, the page sets shipment from the submit-for-documents
	// response (DOCUMENTS_PENDING) and re-fetches requirements and readiness.
	// We override the requirements route (LIFO) so it returns the two
	// auto-generated rows on the SECOND call. The readiness route is already
	// registered by setupShipmentDetail with DEFAULT_READINESS.
	// -----------------------------------------------------------------------
	test('DRAFT + SM: submit button visible; click transitions to DOCUMENTS_PENDING', async ({
		page
	}) => {
		const STATUS_DRAFT = 'DRAFT' as ShipmentStatus;
		const STATUS_DOCS_PENDING = 'DOCUMENTS_PENDING' as ShipmentStatus;

		const autoReqPl = makeRequirement({
			id: 'req-pl',
			document_type: 'PACKING_LIST',
			status: 'PENDING',
			is_auto_generated: true
		});
		const autoReqCi = makeRequirement({
			id: 'req-ci',
			document_type: 'COMMERCIAL_INVOICE',
			status: 'PENDING',
			is_auto_generated: true
		});

		// Initial state: DRAFT + SM, no requirements, no readiness (DRAFT → not fetched).
		await setupShipmentDetail(page, {
			status: STATUS_DRAFT,
			role: 'SM',
			requirements: []
		});

		// Override submit-for-documents to count calls and return DOCS_PENDING.
		let submitCalls = 0;
		await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/submit-for-documents`, (route) => {
			submitCalls++;
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(makeShipment({ status: STATUS_DOCS_PENDING }))
			});
		});

		// Override requirements route so it returns the seeded rows on the
		// second call (after submit). First call is initial mount → returns [].
		let reqCallCount = 0;
		await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/requirements`, (route) => {
			if (route.request().method() === 'GET') {
				reqCallCount++;
				const reqs = reqCallCount > 1 ? [autoReqPl, autoReqCi] : [];
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(reqs)
				});
			} else {
				route.fallback();
			}
		});

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		// DRAFT+SM: submit button visible; mark-ready and readiness panel absent.
		await expect(page.getByTestId('shipment-action-rail')).toBeVisible();
		await expect(page.getByTestId('shipment-action-submit')).toBeVisible();
		await expect(page.getByTestId('shipment-action-mark-ready')).toHaveCount(0);
		await expect(page.getByTestId('shipment-readiness-panel')).toHaveCount(0);

		// Submit.
		await page.getByTestId('shipment-action-submit').click();
		expect(submitCalls).toBe(1);

		// DOCUMENTS_PENDING: mark-ready button appears; submit gone.
		await expect(page.getByTestId('shipment-action-mark-ready')).toBeVisible();
		await expect(page.getByTestId('shipment-action-submit')).toHaveCount(0);

		// Documents panel shows the two auto-generated rows.
		await expect(page.getByTestId('shipment-documents-panel')).toBeVisible();
		await expect(page.getByTestId(`shipment-document-row-${autoReqPl.id}`)).toBeVisible();
		await expect(page.getByTestId(`shipment-document-row-${autoReqCi.id}`)).toBeVisible();
	});

	// -----------------------------------------------------------------------
	// Spec 2: DRAFT + FREIGHT_MANAGER and DRAFT + VENDOR — action rail collapses.
	// -----------------------------------------------------------------------
	test('DRAFT + FREIGHT_MANAGER: action rail absent', async ({ page }) => {
		await setupShipmentDetail(page, { status: 'DRAFT', role: 'FREIGHT_MANAGER' });
		await page.goto(`/shipments/${SHIPMENT_ID}`);

		await expect(page.getByTestId('shipment-action-rail')).toHaveCount(0);
	});

	test('DRAFT + VENDOR: action rail absent', async ({ page }) => {
		await setupShipmentDetail(page, { status: 'DRAFT', role: 'VENDOR' });
		await page.goto(`/shipments/${SHIPMENT_ID}`);

		await expect(page.getByTestId('shipment-action-rail')).toHaveCount(0);
	});

	// -----------------------------------------------------------------------
	// Spec 3: DOCUMENTS_PENDING + FM, all-ready.
	// Readiness panel green across all sections. Mark Ready enabled. Click → READY_TO_SHIP.
	// Add Requirement form visible for FM.
	//
	// After mark-ready, the page sets shipment from the mark-ready response.
	// The requirements and readiness routes retain their setup fixtures; the
	// action rail collapses because canMarkShipmentReady(FM, READY_TO_SHIP) = false.
	// -----------------------------------------------------------------------
	test('DOCUMENTS_PENDING + FM, all-ready: readiness green; Mark Ready enabled; click transitions to READY_TO_SHIP', async ({
		page
	}) => {
		const STATUS_DOCS_PENDING = 'DOCUMENTS_PENDING' as ShipmentStatus;
		const STATUS_READY = 'READY_TO_SHIP' as ShipmentStatus;

		const autoReqPl = makeRequirement({
			id: 'req-pl',
			document_type: 'PACKING_LIST',
			status: 'COLLECTED',
			is_auto_generated: true,
			document_id: null
		});
		const autoReqCi = makeRequirement({
			id: 'req-ci',
			document_type: 'COMMERCIAL_INVOICE',
			status: 'COLLECTED',
			is_auto_generated: true,
			document_id: null
		});
		const allReadiness = makeReadiness();

		await setupShipmentDetail(page, {
			status: STATUS_DOCS_PENDING,
			role: 'FREIGHT_MANAGER',
			requirements: [autoReqPl, autoReqCi],
			readiness: allReadiness
		});

		// Override mark-ready to count calls and return READY_TO_SHIP.
		let markReadyCalls = 0;
		await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/mark-ready`, (route) => {
			markReadyCalls++;
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(makeShipment({ status: STATUS_READY }))
			});
		});

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		// Readiness panel visible with all-green sections.
		await expect(page.getByTestId('shipment-readiness-panel')).toBeVisible();
		await expect(page.getByTestId('shipment-readiness-overall')).toContainText('Ready to ship');
		await expect(page.getByTestId('shipment-readiness-documents')).toBeVisible();
		await expect(page.getByTestId('shipment-readiness-certificates')).toBeVisible();
		await expect(page.getByTestId('shipment-readiness-packaging')).toBeVisible();

		// Mark Ready button enabled (readiness.is_ready = true).
		const markReadyBtn = page.getByTestId('shipment-action-mark-ready');
		await expect(markReadyBtn).toBeVisible();
		await expect(markReadyBtn).not.toBeDisabled();
		// Hint copy absent when ready.
		await expect(page.getByTestId('shipment-action-mark-ready-hint')).toHaveCount(0);

		// Auto-generated rows visible, read-only.
		await expect(page.getByTestId(`shipment-document-row-${autoReqPl.id}`)).toBeVisible();
		await expect(page.getByTestId(`shipment-document-row-${autoReqCi.id}`)).toBeVisible();

		// FM sees the Add Requirement form.
		await expect(page.getByTestId('shipment-documents-add-form')).toBeVisible();

		// Click Mark Ready.
		await markReadyBtn.click();
		expect(markReadyCalls).toBe(1);

		// READY_TO_SHIP: action rail collapses (canMarkShipmentReady(FM, READY_TO_SHIP) = false).
		await expect(page.getByTestId('shipment-action-rail')).toHaveCount(0);
	});

	// -----------------------------------------------------------------------
	// Spec 4: DOCUMENTS_PENDING + FM, missing items.
	// Mark Ready disabled when readiness has missing items.
	// Stale-readiness 409 path: click while all-ready → 409 → readiness panel
	// updates to red + inline error on the action rail.
	//
	// Two sub-scenarios:
	//  a) Missing readiness on load → button disabled.
	//  b) All-ready on load, 409 on submit → panel turns red, error appears.
	// -----------------------------------------------------------------------
	test('DOCUMENTS_PENDING + FM, missing items: Mark Ready disabled when readiness has gaps', async ({
		page
	}) => {
		const STATUS_DOCS_PENDING = 'DOCUMENTS_PENDING' as ShipmentStatus;
		const MISSING_DOC_TYPE = 'BILL_OF_LADING';

		const missingReadiness = makeReadiness({
			documents_ready: false,
			is_ready: false,
			missing_documents: [MISSING_DOC_TYPE]
		});

		await setupShipmentDetail(page, {
			status: STATUS_DOCS_PENDING,
			role: 'FREIGHT_MANAGER',
			requirements: [],
			readiness: missingReadiness
		});

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		// Mark Ready disabled because is_ready === false.
		const markReadyBtn = page.getByTestId('shipment-action-mark-ready');
		await expect(markReadyBtn).toBeVisible();
		await expect(markReadyBtn).toBeDisabled();
		// Hint copy visible.
		await expect(page.getByTestId('shipment-action-mark-ready-hint')).toBeVisible();

		// Readiness panel documents section red.
		await expect(page.getByTestId('shipment-readiness-overall')).toContainText('Not ready');
		await expect(
			page.getByTestId(`shipment-readiness-missing-document-${MISSING_DOC_TYPE}`)
		).toBeVisible();
	});

	test('DOCUMENTS_PENDING + FM: stale-readiness 409 updates panel to red and shows inline error', async ({
		page
	}) => {
		const STATUS_DOCS_PENDING = 'DOCUMENTS_PENDING' as ShipmentStatus;
		const MISSING_DOC_TYPE = 'BILL_OF_LADING';

		const missingReadiness = makeReadiness({
			documents_ready: false,
			is_ready: false,
			missing_documents: [MISSING_DOC_TYPE]
		});

		// Load with all-ready so button is enabled.
		await setupShipmentDetail(page, {
			status: STATUS_DOCS_PENDING,
			role: 'FREIGHT_MANAGER',
			requirements: [],
			readiness: makeReadiness()
		});

		// Override mark-ready to return 409 with missing readiness payload.
		await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/mark-ready`, (route) => {
			route.fulfill({
				status: 409,
				contentType: 'application/json',
				body: JSON.stringify({ detail: missingReadiness })
			});
		});

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		// Button is enabled (all-ready readiness on load).
		const markReadyBtn = page.getByTestId('shipment-action-mark-ready');
		await expect(markReadyBtn).toBeVisible();
		await expect(markReadyBtn).not.toBeDisabled();

		// Click → 409 → readiness panel updates + inline error.
		await markReadyBtn.click();

		await expect(page.getByTestId('shipment-action-error')).toBeVisible();
		await expect(page.getByTestId('shipment-action-error')).toContainText(
			'Some readiness checks failed'
		);
		// Readiness panel now reflects the 409 payload (server supersedes client state).
		await expect(page.getByTestId('shipment-readiness-overall')).toContainText('Not ready');
		await expect(
			page.getByTestId(`shipment-readiness-missing-document-${MISSING_DOC_TYPE}`)
		).toBeVisible();
	});

	// -----------------------------------------------------------------------
	// Spec 5: DOCUMENTS_PENDING + FM — no Upload affordance on user-defined PENDING rows.
	// FM's review action is Mark Ready, not Upload.
	// -----------------------------------------------------------------------
	test('DOCUMENTS_PENDING + FM: no upload button on user-defined PENDING rows', async ({
		page
	}) => {
		const STATUS_DOCS_PENDING = 'DOCUMENTS_PENDING' as ShipmentStatus;
		const USER_REQ_ID = 'req-bol';

		const userReq = makeRequirement({
			id: USER_REQ_ID,
			document_type: 'BILL_OF_LADING',
			status: 'PENDING',
			is_auto_generated: false
		});

		await setupShipmentDetail(page, {
			status: STATUS_DOCS_PENDING,
			role: 'FREIGHT_MANAGER',
			requirements: [userReq],
			readiness: makeReadiness()
		});

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		await expect(page.getByTestId(`shipment-document-row-${USER_REQ_ID}`)).toBeVisible();
		// FM must NOT see the upload button.
		await expect(page.getByTestId(`shipment-document-upload-${USER_REQ_ID}`)).toHaveCount(0);
		// FM does see the Add Requirement form.
		await expect(page.getByTestId('shipment-documents-add-form')).toBeVisible();
	});

	// -----------------------------------------------------------------------
	// Spec 6: DOCUMENTS_PENDING + VENDOR — upload flow.
	// Auto-generated rows have no upload affordance.
	// User-defined PENDING rows show Upload PDF button.
	// After file selection the row flips to COLLECTED with a download link.
	// Readiness panel, Add Requirement form, and action rail are all hidden.
	//
	// VENDOR cannot view readiness (backend forbids GET /readiness for VENDOR).
	// setupShipmentDetail skips readiness mock when role is VENDOR.
	// -----------------------------------------------------------------------
	test('DOCUMENTS_PENDING + VENDOR: upload flow; auto rows read-only; readiness + add form + action rail hidden', async ({
		page
	}) => {
		const STATUS_DOCS_PENDING = 'DOCUMENTS_PENDING' as ShipmentStatus;
		const AUTO_REQ_ID = 'req-pl';
		const USER_REQ_ID = 'req-bol';
		const FILE_ID = 'file-uuid-uploaded';

		const autoReq = makeRequirement({
			id: AUTO_REQ_ID,
			document_type: 'PACKING_LIST',
			status: 'PENDING',
			is_auto_generated: true
		});
		const userReq = makeRequirement({
			id: USER_REQ_ID,
			document_type: 'BILL_OF_LADING',
			status: 'PENDING',
			is_auto_generated: false
		});

		// VENDOR cannot see the readiness panel (canViewShipmentReadiness(VENDOR) = false).
		// The page skips the readiness GET for VENDOR. Pass readiness: null to avoid
		// setting up a route that would never be called.
		await setupShipmentDetail(page, {
			status: STATUS_DOCS_PENDING,
			role: 'VENDOR',
			requirements: [autoReq, userReq],
			readiness: null
		});

		// Override requirements route so it returns the COLLECTED row after upload.
		let reqCallCount = 0;
		await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/requirements`, (route) => {
			if (route.request().method() === 'GET') {
				reqCallCount++;
				const reqs =
					reqCallCount > 1
						? [
								autoReq,
								makeRequirement({
									id: USER_REQ_ID,
									document_type: 'BILL_OF_LADING',
									status: 'COLLECTED',
									is_auto_generated: false,
									document_id: FILE_ID
								})
							]
						: [autoReq, userReq];
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(reqs)
				});
			} else {
				route.fallback();
			}
		});

		// Upload endpoint returns COLLECTED requirement.
		await page.route(
			`**/api/v1/shipments/${SHIPMENT_ID}/documents/${USER_REQ_ID}/upload`,
			(route) => {
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(
						makeRequirement({
							id: USER_REQ_ID,
							status: 'COLLECTED',
							is_auto_generated: false,
							document_id: FILE_ID
						})
					)
				});
			}
		);

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		// Auto-generated row: no upload button.
		await expect(page.getByTestId(`shipment-document-row-${AUTO_REQ_ID}`)).toBeVisible();
		await expect(page.getByTestId(`shipment-document-upload-${AUTO_REQ_ID}`)).toHaveCount(0);

		// User-defined PENDING row: upload button visible.
		await expect(page.getByTestId(`shipment-document-row-${USER_REQ_ID}`)).toBeVisible();
		const uploadBtn = page.getByTestId(`shipment-document-upload-${USER_REQ_ID}`);
		await expect(uploadBtn).toBeVisible();

		// VENDOR sees no Add Requirement form, no readiness panel, no action rail.
		await expect(page.getByTestId('shipment-documents-add-form')).toHaveCount(0);
		await expect(page.getByTestId('shipment-readiness-panel')).toHaveCount(0);
		await expect(page.getByTestId('shipment-action-rail')).toHaveCount(0);

		// Trigger upload via the hidden file input (Upload PDF button triggers it via click).
		const fileInput = page.locator('input[type=file]').first();
		await fileInput.setInputFiles({
			name: 'test.pdf',
			mimeType: 'application/pdf',
			buffer: Buffer.from('%PDF-1.4 stub content')
		});

		// Row flips to COLLECTED.
		await expect(page.getByTestId(`shipment-document-status-${USER_REQ_ID}`)).toContainText(
			'COLLECTED'
		);
		// Download link appears.
		await expect(page.getByRole('link', { name: 'Download' })).toBeVisible();
	});

	// -----------------------------------------------------------------------
	// Spec 7: DOCUMENTS_PENDING + FM — add user-defined requirement.
	// Submitting BILL_OF_LADING posts and the new row appears with PENDING status.
	// FM has no upload button on the new row.
	// -----------------------------------------------------------------------
	test('DOCUMENTS_PENDING + FM: add user-defined requirement posts and renders PENDING row', async ({
		page
	}) => {
		const STATUS_DOCS_PENDING = 'DOCUMENTS_PENDING' as ShipmentStatus;
		const NEW_DOC_TYPE = 'BILL_OF_LADING';
		const NEW_REQ_ID = 'req-bol-new';
		const EXISTING_REQ_ID = 'req-pl';

		// The add form only renders when requirements.length > 0 (outside empty state).
		// Start with one auto-generated row so the list renders and the add form is visible.
		const existingReq = makeRequirement({
			id: EXISTING_REQ_ID,
			document_type: 'PACKING_LIST',
			status: 'COLLECTED',
			is_auto_generated: true
		});

		await setupShipmentDetail(page, {
			status: STATUS_DOCS_PENDING,
			role: 'FREIGHT_MANAGER',
			requirements: [existingReq],
			readiness: makeReadiness()
		});

		// Override requirements route: GET returns existing + new row after POST.
		let reqCallCount = 0;
		await page.route(`**/api/v1/shipments/${SHIPMENT_ID}/requirements`, (route) => {
			if (route.request().method() === 'GET') {
				reqCallCount++;
				const reqs =
					reqCallCount > 1
						? [
								existingReq,
								makeRequirement({
									id: NEW_REQ_ID,
									document_type: NEW_DOC_TYPE,
									status: 'PENDING',
									is_auto_generated: false
								})
							]
						: [existingReq];
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(reqs)
				});
			} else if (route.request().method() === 'POST') {
				route.fulfill({
					status: 201,
					contentType: 'application/json',
					body: JSON.stringify(
						makeRequirement({
							id: NEW_REQ_ID,
							document_type: NEW_DOC_TYPE,
							status: 'PENDING',
							is_auto_generated: false
						})
					)
				});
			} else {
				route.fallback();
			}
		});

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		// Add form visible for FM (canManageShipmentRequirements(FM, DOCS_PENDING) = true).
		// The form renders in the non-empty list block — the existing row ensures list is non-empty.
		await expect(page.getByTestId('shipment-documents-add-form')).toBeVisible();

		// Type the document type and submit.
		await page.getByTestId('shipment-documents-add-input').fill(NEW_DOC_TYPE);
		await page.getByTestId('shipment-documents-add-submit').click();

		// New row appears with PENDING status.
		await expect(page.getByTestId(`shipment-document-row-${NEW_REQ_ID}`)).toBeVisible();
		await expect(page.getByTestId(`shipment-document-status-${NEW_REQ_ID}`)).toContainText(
			'PENDING'
		);

		// FM has no upload button on the new row.
		await expect(page.getByTestId(`shipment-document-upload-${NEW_REQ_ID}`)).toHaveCount(0);
	});

	// -----------------------------------------------------------------------
	// Spec 8: READY_TO_SHIP + SM — action rail collapses; documents panel
	// read-only; no Add Requirement form; no upload buttons.
	// -----------------------------------------------------------------------
	test('READY_TO_SHIP + SM: action rail absent; documents read-only; no upload affordance', async ({
		page
	}) => {
		const STATUS_READY = 'READY_TO_SHIP' as ShipmentStatus;
		const REQ_ID = 'req-pl';

		const collectedReq = makeRequirement({
			id: REQ_ID,
			document_type: 'PACKING_LIST',
			status: 'COLLECTED',
			is_auto_generated: true,
			document_id: null
		});

		await setupShipmentDetail(page, {
			status: STATUS_READY,
			role: 'SM',
			requirements: [collectedReq]
			// readiness: uses DEFAULT_READINESS (all-ready). SM can view readiness
			// (canViewShipmentReadiness(SM) = true), so the panel renders — that
			// is acceptable and expected for READY_TO_SHIP. The spec asserts the
			// action rail is gone (canMarkShipmentReady(SM, READY_TO_SHIP) = false).
		});

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		// Action rail absent (no submit, no mark-ready for READY_TO_SHIP + SM).
		await expect(page.getByTestId('shipment-action-rail')).toHaveCount(0);

		// Documents panel visible and read-only (no upload buttons, no add form).
		await expect(page.getByTestId('shipment-documents-panel')).toBeVisible();
		await expect(page.getByTestId(`shipment-document-row-${REQ_ID}`)).toBeVisible();
		await expect(page.getByTestId(`shipment-document-upload-${REQ_ID}`)).toHaveCount(0);
		// SM cannot manage requirements on READY_TO_SHIP (canManageShipmentRequirements = false).
		await expect(page.getByTestId('shipment-documents-add-form')).toHaveCount(0);
	});

	// -----------------------------------------------------------------------
	// Spec 9: Document type labels.
	// Known type BILL_OF_LADING maps to "Bill of Lading".
	// Unknown user-defined type renders verbatim.
	// -----------------------------------------------------------------------
	test('document type labels: BILL_OF_LADING maps to friendly name; unknown string renders verbatim', async ({
		page
	}) => {
		const STATUS_DOCS_PENDING = 'DOCUMENTS_PENDING' as ShipmentStatus;
		const KNOWN_TYPE = 'BILL_OF_LADING';
		const KNOWN_LABEL = 'Bill of Lading';
		const UNKNOWN_TYPE = 'MY_CUSTOM_DOC_TYPE';

		const knownReq = makeRequirement({
			id: 'req-bol',
			document_type: KNOWN_TYPE,
			status: 'PENDING',
			is_auto_generated: false
		});
		const unknownReq = makeRequirement({
			id: 'req-custom',
			document_type: UNKNOWN_TYPE,
			status: 'PENDING',
			is_auto_generated: false
		});

		await setupShipmentDetail(page, {
			status: STATUS_DOCS_PENDING,
			role: 'FREIGHT_MANAGER',
			requirements: [knownReq, unknownReq],
			readiness: makeReadiness()
		});

		await page.goto(`/shipments/${SHIPMENT_ID}`);

		// Known type renders friendly label.
		await expect(page.getByTestId('shipment-document-row-req-bol')).toContainText(KNOWN_LABEL);
		// Unknown type renders verbatim.
		await expect(page.getByTestId('shipment-document-row-req-custom')).toContainText(UNKNOWN_TYPE);
	});
});
