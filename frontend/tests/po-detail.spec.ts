import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Iter 077 — `/po/[id]` revamp under (nexus) shell. Verifies the role × status
// matrix surfaced by PoActionRail, the Advance Payment panel gate state, the
// Cert Warnings banner dismissal lifetime, and the sticky-bottom rail at 390px.
// All selectors use getByTestId / getByRole / getByLabel per CLAUDE.md.
// ---------------------------------------------------------------------------

const PO_ID = 'uuid-detail';

const REFERENCE_DATA = {
	currencies: [{ code: 'USD', label: 'US Dollar' }],
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
	vendor_types: [{ code: 'PROCUREMENT', label: 'Procurement' }],
	po_types: [{ code: 'PROCUREMENT', label: 'Procurement' }]
};

const LINE_ITEM = {
	part_number: 'PART-001',
	description: 'Steel bolt',
	quantity: 100,
	uom: 'pcs',
	unit_price: '15',
	hs_code: '7318.15',
	country_of_origin: 'CN',
	product_id: null,
	status: 'ACCEPTED',
	history: []
};

type POFixture = Record<string, unknown>;

function makePO(overrides: POFixture = {}): POFixture {
	return {
		id: PO_ID,
		po_number: 'PO-20260316-0001',
		status: 'DRAFT',
		po_type: 'PROCUREMENT',
		vendor_id: 'vendor-uuid-1',
		vendor_name: 'Acme Corp',
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
		line_items: [LINE_ITEM],
		rejection_history: [],
		total_value: '1500',
		created_at: '2026-03-16T00:00:00+00:00',
		updated_at: '2026-03-16T00:00:00+00:00',
		round_count: 0,
		last_actor_role: null,
		advance_paid_at: null,
		has_removed_line: false,
		current_milestone: null,
		...overrides
	};
}

const SM_USER = {
	id: 'u-sm',
	username: 'sm',
	display_name: 'SM User',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null
};

const VENDOR_USER = {
	id: 'u-vendor',
	username: 'vendor',
	display_name: 'Vendor User',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-1'
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

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

function mockUser(page: Page, user: typeof SM_USER) {
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
			body: JSON.stringify(REFERENCE_DATA)
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

function mockApiCatchAll(page: Page) {
	return page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
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

function mockPoInvoices(page: Page) {
	return page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

function mockPoDocuments(page: Page) {
	return page.route('**/api/v1/po/*/documents', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

function mockMilestones(page: Page) {
	return page.route('**/api/v1/po/*/milestones', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

function mockRemainingQuantities(page: Page) {
	return page.route('**/api/v1/invoices/po/*/remaining', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ po_id: PO_ID, lines: [] })
		});
	});
}

// Compose the mocks every detail-page test needs. Always-on order: catch-all
// first (lowest LIFO priority) so per-test overrides land on top.
async function setupDetailPage(page: Page, user: typeof SM_USER, po: POFixture) {
	await mockApiCatchAll(page);
	await mockUser(page, user);
	await mockUnreadCount(page);
	await mockReferenceData(page);
	await mockPoInvoices(page);
	await mockPoDocuments(page);
	await mockMilestones(page);
	await mockRemainingQuantities(page);
	await mockPoDetail(page, po);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test('detail header renders inside (nexus) shell', async ({ page }) => {
	const po = makePO({ status: 'DRAFT' });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();
	// AppShell exposes its inner regions by testid; the outer wrapper testid is
	// caller-provided, so we anchor on the always-present sidebar/topbar/main.
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByTestId('ui-appshell-topbar')).toBeVisible();
	await expect(page.getByTestId('ui-appshell-main')).toBeVisible();

	// Pre-revamp top nav must not render under the (nexus) shell.
	await expect(page.getByRole('link', { name: 'Vendor Portal' })).toHaveCount(0);
});

test('action rail composition for SM on DRAFT', async ({ page }) => {
	const po = makePO({ status: 'DRAFT' });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const rail = page.getByTestId('po-action-rail').first();
	await expect(rail.getByTestId('po-action-edit')).toBeVisible();
	await expect(rail.getByTestId('po-action-submit')).toBeVisible();
	await expect(rail.getByTestId('po-action-accept')).toHaveCount(0);

	// Download PDF lives in the overflow menu when primary actions exist.
	const overflow = rail.getByTestId('po-action-overflow');
	await expect(overflow).toBeVisible();
	await overflow.click();
	await expect(rail.getByTestId('po-action-download-pdf')).toBeVisible();
});

test('action rail composition for VENDOR on PENDING', async ({ page }) => {
	const po = makePO({ status: 'PENDING' });
	await setupDetailPage(page, VENDOR_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const rail = page.getByTestId('po-action-rail').first();
	await expect(rail.getByTestId('po-action-accept')).toBeVisible();
	await expect(rail.getByTestId('po-action-edit')).toHaveCount(0);
	await expect(rail.getByTestId('po-action-submit')).toHaveCount(0);
});

test('action rail composition for VENDOR on ACCEPTED PROCUREMENT shows Create Invoice + Post Milestone', async ({
	page
}) => {
	const po = makePO({
		status: 'ACCEPTED',
		po_type: 'PROCUREMENT'
	});
	await setupDetailPage(page, VENDOR_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const rail = page.getByTestId('po-action-rail').first();
	await expect(rail.getByTestId('po-action-create-invoice')).toBeVisible();

	// Post milestone is the second primary action; it sits inline at >=768px.
	await expect(rail.getByTestId('po-action-post-milestone')).toBeVisible();
});

test('PROCUREMENT_MANAGER sees Download PDF only', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT' });
	await setupDetailPage(page, PROCUREMENT_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const rail = page.getByTestId('po-action-rail').first();
	await expect(rail.getByTestId('po-action-download-pdf')).toBeVisible();
	await expect(rail.getByTestId('po-action-overflow')).toHaveCount(0);
	await expect(rail.getByTestId('po-action-edit')).toHaveCount(0);
	await expect(rail.getByTestId('po-action-submit')).toHaveCount(0);
	await expect(rail.getByTestId('po-action-accept')).toHaveCount(0);
	await expect(rail.getByTestId('po-action-create-invoice')).toHaveCount(0);
});

test('FREIGHT_MANAGER sees Download PDF only', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT' });
	await setupDetailPage(page, FREIGHT_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const rail = page.getByTestId('po-action-rail').first();
	await expect(rail.getByTestId('po-action-download-pdf')).toBeVisible();
	await expect(rail.getByTestId('po-action-overflow')).toHaveCount(0);
});

test('QUALITY_LAB sees Download PDF only', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT' });
	await setupDetailPage(page, QUALITY_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const rail = page.getByTestId('po-action-rail').first();
	await expect(rail.getByTestId('po-action-download-pdf')).toBeVisible();
	await expect(rail.getByTestId('po-action-overflow')).toHaveCount(0);
});

test('Download PDF label says (Modified) when round_count > 0', async ({ page }) => {
	const po = makePO({ status: 'DRAFT', round_count: 1 });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const rail = page.getByTestId('po-action-rail').first();
	await rail.getByTestId('po-action-overflow').click();
	const pdfItem = rail.getByTestId('po-action-download-pdf');
	await expect(pdfItem).toBeVisible();
	await expect(pdfItem).toContainText('(Modified)');
});

test('Advance Payment panel hidden when has_advance is false', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', payment_terms: 'NET30' });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();
	await expect(page.getByTestId('po-advance-panel')).toHaveCount(0);
});

test('Advance Payment panel for SM on ACCEPTED + has_advance + unpaid shows Mark advance paid', async ({
	page
}) => {
	const po = makePO({
		status: 'ACCEPTED',
		payment_terms: 'ADVANCE_30',
		advance_paid_at: null
	});
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	const panel = page.getByTestId('po-advance-panel');
	await expect(panel).toBeVisible();
	await expect(panel.getByTestId('po-action-mark-advance-paid')).toBeVisible();
	await expect(panel).toContainText('window open until advance paid');
});

test('Advance Payment panel post-paid shows closed gate with date', async ({ page }) => {
	const po = makePO({
		status: 'ACCEPTED',
		payment_terms: 'ADVANCE_30',
		advance_paid_at: '2026-04-10T09:00:00+00:00'
	});
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	const panel = page.getByTestId('po-advance-panel');
	await expect(panel).toBeVisible();
	await expect(panel.getByTestId('po-action-mark-advance-paid')).toHaveCount(0);
	await expect(panel).toContainText('Paid on');
	await expect(panel).toContainText('window closed (advance paid)');
});

test('Advance Payment panel for VENDOR is read-only', async ({ page }) => {
	const po = makePO({
		status: 'ACCEPTED',
		payment_terms: 'ADVANCE_30',
		advance_paid_at: null
	});
	await setupDetailPage(page, VENDOR_USER, po);

	await page.goto(`/po/${PO_ID}`);
	const panel = page.getByTestId('po-advance-panel');
	await expect(panel).toBeVisible();
	await expect(panel.getByTestId('po-action-mark-advance-paid')).toHaveCount(0);
});

test('Cert Warnings banner renders when warnings present and is dismissible', async ({ page }) => {
	const po = makePO({ status: 'DRAFT' });
	const certWarnings = [
		{
			line_item_index: 0,
			part_number: 'PART-001',
			product_id: 'prod-1',
			qualification_name: 'CE marking',
			reason: 'MISSING'
		}
	];
	await setupDetailPage(page, SM_USER, po);

	// Override the submit endpoint with a payload that returns cert warnings;
	// the page tucks them under the header after a Submit click.
	await page.route(`**/api/v1/po/${PO_ID}/submit`, (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ ...po, cert_warnings: certWarnings })
		});
	});

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	// Trigger Submit so cert_warnings populate.
	const rail = page.getByTestId('po-action-rail').first();
	await rail.getByTestId('po-action-submit').click();

	const banner = page.getByTestId('po-cert-warnings');
	await expect(banner).toBeVisible();

	await banner.getByTestId('po-cert-warnings-dismiss').click();
	await expect(page.getByTestId('po-cert-warnings')).toHaveCount(0);
});

test('Cert Warnings banner is absent when warnings empty', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED' });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();
	await expect(page.getByTestId('po-cert-warnings')).toHaveCount(0);
});

test('sticky bottom action rail at 390px viewport', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });

	const po = makePO({ status: 'DRAFT' });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	// At 390px, the inline rail inside the header is hidden via media query and
	// the page renders a sticky-bottom rail wrapper. The wrapper holds the rail.
	const stickyWrap = page.getByTestId('po-detail-page-rail-mobile');
	await expect(stickyWrap).toBeVisible();

	// The primary action (Edit, the first primary for SM/DRAFT) is visible
	// inline; the rest of the primaries collapse into the overflow at sticky.
	await expect(stickyWrap.getByTestId('po-action-edit')).toBeVisible();

	// Overflow menu opens upward (po-action-rail__menu--up) at sticky-bottom.
	const overflowSummary = stickyWrap.getByTestId('po-action-overflow');
	await expect(overflowSummary).toBeVisible();
	await overflowSummary.click();
	const menuUp = stickyWrap.locator('.po-action-rail__menu--up');
	await expect(menuUp).toBeVisible();

	// Both Submit (overflow primary) and Download PDF (overflow extra) live in
	// the menu; the inline one shows the menu--up modifier.
	await expect(menuUp.getByTestId('po-action-submit')).toBeVisible();
	await expect(menuUp.getByTestId('po-action-download-pdf')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Iter 082 — Tier 4 ACCEPTED-PO surface revamp.
// Covers the new PoMilestoneTimelinePanel, PoLineAcceptedTable, PoAddLineDialog,
// the gate-closed hide behaviour, and per-line + global server-error rendering.
// ---------------------------------------------------------------------------

type MilestoneRow = {
	milestone: string;
	posted_at: string;
	is_overdue: boolean;
	days_overdue: number | null;
};

function mockMilestonesWith(page: Page, rows: MilestoneRow[]) {
	return page.route('**/api/v1/po/*/milestones', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(rows)
		});
	});
}

function mockRemainingWithLines(
	page: Page,
	lines: Array<{ part_number: string; description: string; ordered: number; invoiced: number; remaining: number }>
) {
	return page.route('**/api/v1/invoices/po/*/remaining', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ po_id: PO_ID, lines })
		});
	});
}

const MILESTONE_FIXTURE_TWO_POSTED: MilestoneRow[] = [
	{
		milestone: 'RAW_MATERIALS',
		posted_at: '2026-04-15T00:00:00+00:00',
		is_overdue: false,
		days_overdue: null
	},
	{
		milestone: 'PRODUCTION_STARTED',
		posted_at: '2026-04-22T00:00:00+00:00',
		is_overdue: false,
		days_overdue: null
	}
];

const MILESTONE_FIXTURE_OVERDUE: MilestoneRow[] = [
	{
		milestone: 'RAW_MATERIALS',
		posted_at: '2026-04-15T00:00:00+00:00',
		is_overdue: true,
		days_overdue: 4
	}
];

const MILESTONE_FIXTURE_ALL_POSTED: MilestoneRow[] = [
	{ milestone: 'RAW_MATERIALS', posted_at: '2026-03-10T00:00:00+00:00', is_overdue: false, days_overdue: null },
	{ milestone: 'PRODUCTION_STARTED', posted_at: '2026-03-18T00:00:00+00:00', is_overdue: false, days_overdue: null },
	{ milestone: 'QC_PASSED', posted_at: '2026-04-01T00:00:00+00:00', is_overdue: false, days_overdue: null },
	{ milestone: 'READY_FOR_SHIPMENT', posted_at: '2026-04-10T00:00:00+00:00', is_overdue: false, days_overdue: null },
	{ milestone: 'SHIPPED', posted_at: '2026-04-20T00:00:00+00:00', is_overdue: false, days_overdue: null }
];

const TWO_LINE_ITEMS = [
	{
		part_number: 'PART-001',
		description: 'Steel bolt',
		quantity: 100,
		uom: 'pcs',
		unit_price: '15',
		hs_code: '7318.15',
		country_of_origin: 'CN',
		product_id: null,
		status: 'ACCEPTED',
		history: []
	},
	{
		part_number: 'PART-002',
		description: 'Brass washer',
		quantity: 50,
		uom: 'pcs',
		unit_price: '3',
		hs_code: '7318.21',
		country_of_origin: 'CN',
		product_id: null,
		status: 'ACCEPTED',
		history: []
	}
];

test('milestone timeline renders posted milestones as done steps', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, VENDOR_USER, po);
	await mockMilestonesWith(page, MILESTONE_FIXTURE_TWO_POSTED);

	await page.goto(`/po/${PO_ID}`);
	const panel = page.getByTestId('po-milestone-timeline');
	await expect(panel).toBeVisible();

	// Five steps: 2 done, 1 current (next-expected), 2 upcoming.
	const steps = panel.locator('ol[aria-label="Production milestones"] li');
	await expect(steps).toHaveCount(5);
	await expect(steps.nth(0)).toHaveClass(/done/);
	await expect(steps.nth(1)).toHaveClass(/done/);
	await expect(steps.nth(2)).toHaveClass(/current/);
	await expect(steps.nth(3)).toHaveClass(/upcoming/);
	await expect(steps.nth(4)).toHaveClass(/upcoming/);

	// Vendor sees the post-next-milestone Button.
	await expect(panel.getByTestId('po-post-next-milestone-btn')).toBeVisible();
});

test('milestone timeline marks latest as overdue when is_overdue=true', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, VENDOR_USER, po);
	await mockMilestonesWith(page, MILESTONE_FIXTURE_OVERDUE);

	await page.goto(`/po/${PO_ID}`);
	const panel = page.getByTestId('po-milestone-timeline');
	await expect(panel).toBeVisible();

	const steps = panel.locator('ol[aria-label="Production milestones"] li');
	await expect(steps.nth(0)).toHaveClass(/overdue/);
	await expect(steps.nth(0)).toContainText('Overdue 4d');
});

test('milestone timeline hides post button for SM', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);
	await mockMilestonesWith(page, MILESTONE_FIXTURE_TWO_POSTED);

	await page.goto(`/po/${PO_ID}`);
	const panel = page.getByTestId('po-milestone-timeline');
	await expect(panel).toBeVisible();
	await expect(panel.getByTestId('po-post-next-milestone-btn')).toHaveCount(0);
});

test('milestone timeline hides post button at terminal SHIPPED', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, VENDOR_USER, po);
	await mockMilestonesWith(page, MILESTONE_FIXTURE_ALL_POSTED);

	await page.goto(`/po/${PO_ID}`);
	const panel = page.getByTestId('po-milestone-timeline');
	await expect(panel).toBeVisible();
	await expect(panel.getByTestId('po-post-next-milestone-btn')).toHaveCount(0);
});

test('milestone section omitted for OPEX', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'OPEX', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, VENDOR_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();
	await expect(page.getByTestId('po-milestone-timeline')).toHaveCount(0);
});

test('accepted PO renders line items as cards via PoLineAcceptedTable', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-accepted-line-PART-001')).toBeVisible();
	await expect(page.getByTestId('po-accepted-line-PART-002')).toBeVisible();
	await expect(page.getByTestId('po-accepted-status-PART-001')).toBeVisible();
});

test('accepted PO line cards show invoiced + remaining for procurement', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);
	await mockRemainingWithLines(page, [
		{ part_number: 'PART-001', description: 'Steel bolt', ordered: 100, invoiced: 30, remaining: 70 },
		{ part_number: 'PART-002', description: 'Brass washer', ordered: 50, invoiced: 0, remaining: 50 }
	]);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-accepted-invoiced-PART-001')).toContainText('30');
	await expect(page.getByTestId('po-accepted-remaining-PART-001')).toContainText('70');
	await expect(page.getByTestId('po-accepted-invoiced-PART-002')).toContainText('0');
	await expect(page.getByTestId('po-accepted-remaining-PART-002')).toContainText('50');
});

test('accepted PO line cards omit invoiced/remaining for opex', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'OPEX', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-accepted-line-PART-001')).toBeVisible();
	await expect(page.getByTestId('po-accepted-invoiced-PART-001')).toHaveCount(0);
	await expect(page.getByTestId('po-accepted-remaining-PART-001')).toHaveCount(0);
});

test('add line dialog uses reference-data selects for Country', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('add-line-btn').click();
	const dialog = page.getByTestId('po-add-line-dialog');
	await expect(dialog).toBeVisible();
	await expect(dialog.getByRole('combobox', { name: /country of origin/i })).toBeVisible();
	// UoM and HS code are free-form Inputs (no central reference list); confirm
	// they render as accessible-named text controls inside the dialog.
	await expect(dialog.getByRole('textbox', { name: /unit of measure/i })).toBeVisible();
	await expect(dialog.getByRole('textbox', { name: /hs code/i })).toBeVisible();
});

test('add line dialog server error renders inline at top', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);
	await page.route(`**/api/v1/po/${PO_ID}/lines`, (route) => {
		if (route.request().method() === 'POST') {
			route.fulfill({
				status: 409,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'duplicate part number' })
			});
		} else {
			route.continue();
		}
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('add-line-btn').click();
	const dialog = page.getByTestId('po-add-line-dialog');
	await dialog.getByTestId('po-add-line-part').fill('NEW-1');
	await dialog.getByTestId('po-add-line-description').fill('A new part');
	await dialog.getByTestId('po-add-line-submit').click();

	const error = page.getByTestId('po-add-line-error');
	await expect(error).toBeVisible();
	await expect(error).toContainText('duplicate part number');
});

test('add line button hidden when gate closed by advance', async ({ page }) => {
	const po = makePO({
		status: 'ACCEPTED',
		po_type: 'PROCUREMENT',
		line_items: TWO_LINE_ITEMS,
		payment_terms: 'ADVANCE_30',
		advance_paid_at: '2026-04-10T09:00:00+00:00'
	});
	await setupDetailPage(page, SM_USER, po);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();
	await expect(page.getByTestId('add-line-btn')).toHaveCount(0);
});

test('add line button hidden when gate closed by milestone', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);
	await mockMilestonesWith(page, MILESTONE_FIXTURE_TWO_POSTED);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();
	await expect(page.getByTestId('add-line-btn')).toHaveCount(0);
});

test('remove line buttons hidden when gate closed', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);
	await mockMilestonesWith(page, MILESTONE_FIXTURE_TWO_POSTED);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-accepted-line-PART-001')).toBeVisible();
	await expect(page.getByTestId('po-accepted-remove-PART-001')).toHaveCount(0);
	await expect(page.getByTestId('po-accepted-remove-PART-002')).toHaveCount(0);
});

test('gate-closed note renders for SM', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);
	await mockMilestonesWith(page, MILESTONE_FIXTURE_TWO_POSTED);

	await page.goto(`/po/${PO_ID}`);
	const note = page.getByTestId('po-post-accept-gate-closed-note');
	await expect(note).toBeVisible();
	await expect(note).toContainText('Post-acceptance line edits closed');
});

test('gate-closed note hidden for VENDOR', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, VENDOR_USER, po);
	await mockMilestonesWith(page, MILESTONE_FIXTURE_TWO_POSTED);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();
	await expect(page.getByTestId('po-post-accept-gate-closed-note')).toHaveCount(0);
});

test('remove line server error renders inline below row', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT', line_items: TWO_LINE_ITEMS });
	await setupDetailPage(page, SM_USER, po);
	await page.route(`**/api/v1/po/${PO_ID}/lines/PART-001`, (route) => {
		if (route.request().method() === 'DELETE') {
			route.fulfill({
				status: 409,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Cannot remove: invoice INV-1 references this line' })
			});
		} else {
			route.continue();
		}
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-accepted-remove-PART-001').click();

	const error = page.getByTestId('po-accepted-error-PART-001');
	await expect(error).toBeVisible();
	await expect(error).toContainText('Cannot remove: invoice INV-1 references this line');
	// Error scoped to the row that failed; the other row carries no error block.
	await expect(page.getByTestId('po-accepted-error-PART-002')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Iter 083 — Tier 5: metadata panels, rejection history, invoices, activity
// ---------------------------------------------------------------------------

function mockPoActivity(page: Page, entries: object[]) {
	return page.route('**/api/v1/activity/**', (route) => {
		const url = route.request().url();
		if (url.includes('unread-count')) {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(entries) });
		}
	});
}

function makeActivityEntry(overrides: Record<string, unknown> = {}): Record<string, unknown> {
	return {
		id: 'act-1',
		entity_type: 'PO',
		entity_id: PO_ID,
		event: 'PO_CREATED',
		category: 'LIVE',
		target_role: null,
		detail: null,
		read_at: null,
		created_at: '2026-03-16T00:00:00+00:00',
		...overrides
	};
}

test('metadata trade summary panel renders six rows when marketplace set', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', marketplace: 'AMZ' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const panel = page.getByTestId('po-metadata-trade-summary');
	await expect(panel).toBeVisible();
	// All six rows present: Currency, Issued Date, Delivery Date, Total Value, Payment Terms, Marketplace.
	await expect(panel.getByRole('term').filter({ hasText: 'Currency' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Issued Date' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Delivery Date' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Total Value' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Payment Terms' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Marketplace' })).toBeVisible();
});

test('metadata trade summary hides marketplace row when null', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', marketplace: null });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	const panel = page.getByTestId('po-metadata-trade-summary');
	await expect(panel).toBeVisible();
	// Marketplace row absent when po.marketplace is null.
	await expect(panel.getByRole('term').filter({ hasText: 'Marketplace' })).toHaveCount(0);
});

test('buyer panel renders name and country with resolved label', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', buyer_country: 'US', buyer_name: 'TurboTonic Ltd' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-metadata-buyer');
	await expect(panel).toBeVisible();
	// Country code resolved via reference data; REFERENCE_DATA has US → "United States".
	await expect(panel).toContainText('United States');
	await expect(panel).toContainText('TurboTonic Ltd');
});

test('trade details panel renders five rows', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-metadata-trade-details');
	await expect(panel).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Incoterm' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Port of Loading' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Port of Discharge' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Country of Origin' })).toBeVisible();
	await expect(panel.getByRole('term').filter({ hasText: 'Country of Destination' })).toBeVisible();
});

test('terms panel renders free-text body', async ({ page }) => {
	const termsText = 'Net 30 from invoice';
	const po = makePO({ status: 'ACCEPTED', terms_and_conditions: termsText });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-metadata-terms');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText(termsText);
});

test('rejection history panel hides when no records', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', rejection_history: [] });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	await expect(page.getByTestId('po-rejection-history-panel')).toHaveCount(0);
});

test('rejection history panel renders records latest-first', async ({ page }) => {
	const olderComment = 'First rejection comment';
	const newerComment = 'Second rejection comment';
	const po = makePO({
		status: 'REJECTED',
		rejection_history: [
			{ comment: olderComment, rejected_at: '2026-02-01T00:00:00+00:00' },
			{ comment: newerComment, rejected_at: '2026-03-01T00:00:00+00:00' }
		]
	});
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-rejection-history-panel');
	await expect(panel).toBeVisible();
	// Latest-first: index 0 is the newer record.
	await expect(page.getByTestId('po-rejection-record-0')).toContainText(newerComment);
	await expect(page.getByTestId('po-rejection-record-1')).toContainText(olderComment);
});

test('invoices panel hides when no invoices and not OPEX', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);
	await expect(page.getByTestId('po-detail-header')).toBeVisible();

	await expect(page.getByTestId('po-invoices-panel')).toHaveCount(0);
});

test('invoices panel shows remaining subtitle for procurement', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);
	// Override remaining quantities to total 50 units.
	await page.route('**/api/v1/invoices/po/*/remaining', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				po_id: PO_ID,
				lines: [
					{ part_number: 'PART-001', description: 'Steel bolt', ordered: 100, invoiced: 50, remaining: 50 }
				]
			})
		});
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([{
				id: 'inv-1',
				invoice_number: 'INV-001',
				status: 'APPROVED',
				subtotal: '750.00',
				created_at: '2026-03-16T00:00:00+00:00'
			}])
		});
	});

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-invoices-panel');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText('50 units remaining to invoice');
});

test('invoices panel renders datatable rows', async ({ page }) => {
	const inv1Id = 'inv-uuid-1';
	const inv2Id = 'inv-uuid-2';
	const po = makePO({ status: 'ACCEPTED', po_type: 'PROCUREMENT' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([
				{ id: inv1Id, invoice_number: 'INV-001', status: 'APPROVED', subtotal: '750.00', created_at: '2026-03-10T00:00:00+00:00' },
				{ id: inv2Id, invoice_number: 'INV-002', status: 'DRAFT', subtotal: '300.00', created_at: '2026-03-20T00:00:00+00:00' }
			])
		});
	});

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-invoices-panel');
	await expect(panel).toBeVisible();
	await expect(page.getByTestId(`po-invoices-row-${inv1Id}`)).toBeVisible();
	await expect(page.getByTestId(`po-invoices-row-${inv2Id}`)).toBeVisible();
	await expect(page.getByTestId(`po-invoices-row-${inv1Id}`)).toContainText('INV-001');
	await expect(page.getByTestId(`po-invoices-row-${inv2Id}`)).toContainText('INV-002');
});

test('activity panel shows loading state then entries', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED' });
	await setupDetailPage(page, SM_USER, po);

	// Delay the activity response briefly so LoadingState is observable.
	let resolveActivity!: (value: unknown) => void;
	const activityBarrier = new Promise((resolve) => { resolveActivity = resolve; });
	await page.route('**/api/v1/activity/**', async (route) => {
		const url = route.request().url();
		if (url.includes('unread-count')) {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
			return;
		}
		await activityBarrier;
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([
				makeActivityEntry({ id: 'a1', event: 'PO_CREATED' }),
				makeActivityEntry({ id: 'a2', event: 'PO_SUBMITTED' }),
				makeActivityEntry({ id: 'a3', event: 'PO_ACCEPTED' })
			])
		});
	});

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-activity-panel');
	// LoadingState renders role=status while loading.
	await expect(panel.getByRole('status')).toBeVisible();

	// Unblock the activity fetch.
	resolveActivity(undefined);

	// After loading: feed appears with 3 entries.
	const feed = page.getByTestId('po-activity-feed');
	await expect(feed).toBeVisible();
	await expect(feed.locator('li')).toHaveCount(3);
});

test('activity panel renders empty state when no entries', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, []);

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-activity-panel');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText('No activity yet.');
	await expect(page.getByTestId('po-activity-feed')).toHaveCount(0);
});

test('activity show-more reveals next batch', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED' });
	await setupDetailPage(page, SM_USER, po);
	// 25 entries: initial render shows 10, Show more reveals 10 more.
	const entries = Array.from({ length: 25 }, (_, i) =>
		makeActivityEntry({ id: `act-${i}`, event: 'PO_CREATED', created_at: `2026-03-${String(i + 1).padStart(2, '0')}T00:00:00+00:00` })
	);
	await mockPoActivity(page, entries);

	await page.goto(`/po/${PO_ID}`);

	const feed = page.getByTestId('po-activity-feed');
	await expect(feed.locator('li')).toHaveCount(10);

	const showMoreBtn = page.getByTestId('po-activity-show-more-btn');
	await expect(showMoreBtn).toBeVisible();
	await showMoreBtn.click();

	await expect(feed.locator('li')).toHaveCount(20);
});

test('activity show-more hides when all rows visible', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED' });
	await setupDetailPage(page, SM_USER, po);
	// 8 entries: less than initial visibleCount of 10, so Show more never appears.
	const entries = Array.from({ length: 8 }, (_, i) =>
		makeActivityEntry({ id: `act-${i}`, event: 'PO_CREATED' })
	);
	await mockPoActivity(page, entries);

	await page.goto(`/po/${PO_ID}`);

	const feed = page.getByTestId('po-activity-feed');
	await expect(feed.locator('li')).toHaveCount(8);
	await expect(page.getByTestId('po-activity-show-more-btn')).toHaveCount(0);
});

test('activity row primary uses event label dictionary', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, [makeActivityEntry({ event: 'PO_LINE_MODIFIED', category: 'LIVE' })]);

	await page.goto(`/po/${PO_ID}`);

	const feed = page.getByTestId('po-activity-feed');
	await expect(feed.locator('.primary').first()).toContainText('Line modified');
});

test('activity row tone reflects category', async ({ page }) => {
	const po = makePO({ status: 'ACCEPTED' });
	await setupDetailPage(page, SM_USER, po);
	await mockPoActivity(page, [
		makeActivityEntry({ id: 'live-1', event: 'PO_CREATED', category: 'LIVE', created_at: '2026-03-18T00:00:00+00:00' }),
		makeActivityEntry({ id: 'action-1', event: 'PO_SUBMITTED', category: 'ACTION_REQUIRED', created_at: '2026-03-17T00:00:00+00:00' }),
		makeActivityEntry({ id: 'delayed-1', event: 'MILESTONE_OVERDUE', category: 'DELAYED', created_at: '2026-03-16T00:00:00+00:00' })
	]);

	await page.goto(`/po/${PO_ID}`);

	const panel = page.getByTestId('po-activity-panel');
	const feed = page.getByTestId('po-activity-feed');
	await expect(feed.locator('li')).toHaveCount(3);

	// Dot tones: ActivityFeed renders <span class="dot {tone}">.
	// LIVE → blue, ACTION_REQUIRED → orange, DELAYED → red.
	const dots = panel.locator('.dot');
	await expect(dots.nth(0)).toHaveClass(/blue/);
	await expect(dots.nth(1)).toHaveClass(/orange/);
	await expect(dots.nth(2)).toHaveClass(/red/);
});
