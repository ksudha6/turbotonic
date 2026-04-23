import { test, expect } from '@playwright/test';

// Iter 057: covers the per-line negotiation UI: LineNegotiationRow actions by
// role + round, ModifyLineModal (qty=0 -> REMOVED), force-action confirms,
// LineDiff, EditHistoryTimeline collapse state, and the SubmitResponseBar
// confirmation dialog.

const PO_ID = 'po-iter057';

const REF_DATA = {
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
	po_types: [{ code: 'PROCUREMENT', label: 'Procurement' }]
};

// Generic base line item. Tests customise status/history per scenario.
function makeLine(part: string, extra: Record<string, unknown> = {}) {
	return {
		part_number: part,
		description: `Part ${part}`,
		quantity: 10,
		uom: 'EA',
		unit_price: '100.00',
		hs_code: '8471.30',
		country_of_origin: 'CN',
		product_id: null,
		status: 'PENDING',
		history: [],
		...extra
	};
}

function makePO(overrides: Record<string, unknown> = {}) {
	return {
		id: PO_ID,
		po_number: 'PO-NEGOT-001',
		status: 'PENDING',
		po_type: 'PROCUREMENT',
		vendor_id: 'vendor-1',
		vendor_name: 'Acme Corp',
		vendor_country: 'CN',
		buyer_name: 'TurboTonic Ltd',
		buyer_country: 'US',
		ship_to_address: '123 Main St',
		payment_terms: 'NET30',
		currency: 'USD',
		issued_date: '2026-04-01T00:00:00+00:00',
		required_delivery_date: '2026-05-01T00:00:00+00:00',
		terms_and_conditions: '',
		incoterm: 'FOB',
		port_of_loading: 'CNSHA',
		port_of_discharge: 'USLAX',
		country_of_origin: 'CN',
		country_of_destination: 'US',
		marketplace: null,
		line_items: [makeLine('PN-001')],
		rejection_history: [],
		total_value: '1000.00',
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

// Shared beforeEach wires the lowest-priority catch-all plus an SM auth default.
// Specific tests override auth for VENDOR scenarios.
test.beforeEach(async ({ page }) => {
	await page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'u-sm',
					username: 'sm',
					display_name: 'SM User',
					role: 'SM',
					status: 'ACTIVE',
					vendor_id: null
				}
			})
		});
	});
	await page.route('**/api/v1/activity/unread-count*', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
	await page.route('**/api/v1/reference-data/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(REF_DATA) });
	});
	await page.route('**/api/v1/po/*/invoices', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
});

function mockVendor(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'u-vendor',
					username: 'vendor',
					display_name: 'Vendor User',
					role: 'VENDOR',
					status: 'ACTIVE',
					vendor_id: 'vendor-1'
				}
			})
		});
	});
}

// ---------------------------------------------------------------------------
// 1. Vendor modifies a line -> MODIFIED_BY_VENDOR; submit -> round_count 1.
// ---------------------------------------------------------------------------

test('vendor modifies a line and submits; status flips to MODIFIED_BY_VENDOR and round_count increments', async ({ page }) => {
	await mockVendor(page);

	let currentPo = makePO({
		status: 'PENDING',
		line_items: [makeLine('PN-001', { quantity: 10 })]
	});
	let modifyBody: { fields?: Record<string, unknown> } | null = null;

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		if (route.request().method() === 'GET') {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
		} else {
			route.continue();
		}
	});

	await page.route(`**/api/v1/po/${PO_ID}/lines/PN-001/modify`, (route) => {
		modifyBody = JSON.parse(route.request().postData() ?? '{}');
		currentPo = makePO({
			status: 'MODIFIED',
			line_items: [
				makeLine('PN-001', {
					quantity: 5,
					status: 'MODIFIED_BY_VENDOR',
					history: [
						{
							part_number: 'PN-001',
							round: 0,
							actor_role: 'VENDOR',
							field: 'quantity',
							old_value: '10',
							new_value: '5',
							edited_at: '2026-04-02T00:00:00+00:00'
						}
					]
				})
			]
		});
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});

	let submitResponseCalls = 0;
	await page.route(`**/api/v1/po/${PO_ID}/submit-response`, (route) => {
		submitResponseCalls += 1;
		currentPo = { ...currentPo, round_count: 1, last_actor_role: 'VENDOR' };
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="line-row-PN-001"]');

	// Before modify, round indicator reads Round 1 of 2.
	await expect(page.locator('[data-testid="round-indicator"]')).toHaveText('Round 1 of 2');

	// Open the modify modal, change qty to 5, submit.
	await page.locator('[data-testid="modify-btn-PN-001"]').click();
	await page.waitForSelector('[data-testid="modify-line-modal"]');
	await page.locator('[data-testid="modify-quantity"]').fill('5');
	await page.locator('[data-testid="modify-submit"]').click();

	// Pill now shows MODIFIED_BY_VENDOR.
	await expect(page.locator('[data-testid="line-status-PN-001"]')).toHaveText('Modified by vendor');
	// Only the quantity delta was sent.
	expect(modifyBody).not.toBeNull();
	expect(modifyBody!.fields).toEqual({ quantity: 5 });

	// Submit Response confirms and fires the backend call; after hand-off the
	// vendor is no longer the current actor so the submit bar retracts.
	await page.locator('[data-testid="submit-response-btn"]').click();
	await page.locator('[data-testid="submit-confirm-btn"]').click();

	await expect.poll(() => submitResponseCalls).toBe(1);
	await expect(page.locator('[data-testid="submit-response-bar"]')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 2. SM counter-proposes -> MODIFIED_BY_SM; vendor options flip.
// ---------------------------------------------------------------------------

test('SM counter-proposes; line becomes MODIFIED_BY_SM and vendor Accept action unlocks', async ({ page }) => {
	// Start with a PO already MODIFIED_BY_VENDOR, SM is the current actor.
	const initialPo = makePO({
		status: 'MODIFIED',
		round_count: 0,
		last_actor_role: 'VENDOR',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_VENDOR', quantity: 5 })]
	});

	let currentPo = initialPo;

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});
	await page.route(`**/api/v1/po/${PO_ID}/lines/PN-001/modify`, (route) => {
		currentPo = makePO({
			status: 'MODIFIED',
			round_count: 0,
			last_actor_role: 'VENDOR',
			line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_SM', quantity: 7 })]
		});
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="line-row-PN-001"]');

	// As SM with a MODIFIED_BY_VENDOR line, Accept is offered.
	await expect(page.locator('[data-testid="accept-btn-PN-001"]')).toBeVisible();

	// Counter-propose via Modify.
	await page.locator('[data-testid="modify-btn-PN-001"]').click();
	await page.locator('[data-testid="modify-quantity"]').fill('7');
	await page.locator('[data-testid="modify-submit"]').click();

	// Status flips to MODIFIED_BY_SM.
	await expect(page.locator('[data-testid="line-status-PN-001"]')).toHaveText('Modified by SM');

	// Swap auth to VENDOR and reload: the vendor now sees Accept (since SM was
	// the last modifier) plus the familiar Modify / Remove options.
	currentPo = {
		...currentPo,
		last_actor_role: 'SM',
		round_count: 1
	};
	await mockVendor(page);
	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="line-row-PN-001"]');
	await expect(page.locator('[data-testid="accept-btn-PN-001"]')).toBeVisible();
	await expect(page.locator('[data-testid="modify-btn-PN-001"]')).toBeVisible();
	await expect(page.locator('[data-testid="remove-btn-PN-001"]')).toBeVisible();
});

// ---------------------------------------------------------------------------
// 3. Vendor qty=0 -> REMOVED directly (no intermediate MODIFIED_BY_*).
// ---------------------------------------------------------------------------

test('vendor sets qty=0 via modify modal; line jumps to REMOVED without a MODIFIED intermediate', async ({ page }) => {
	await mockVendor(page);

	let currentPo = makePO({
		status: 'PENDING',
		line_items: [makeLine('PN-001', { quantity: 10 })]
	});

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});
	await page.route(`**/api/v1/po/${PO_ID}/lines/PN-001/modify`, (route) => {
		currentPo = makePO({
			status: 'MODIFIED',
			line_items: [makeLine('PN-001', { quantity: 0, status: 'REMOVED' })]
		});
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="line-row-PN-001"]');

	await page.locator('[data-testid="modify-btn-PN-001"]').click();
	await page.locator('[data-testid="modify-quantity"]').fill('0');

	// Modal shows the removal hint before submit.
	await expect(page.locator('[data-testid="qty-zero-hint"]')).toBeVisible();

	await page.locator('[data-testid="modify-submit"]').click();

	await expect(page.locator('[data-testid="line-status-PN-001"]')).toHaveText('Removed');
	// No MODIFIED_BY_VENDOR pill ever appeared.
	await expect(page.locator('[data-testid="line-status-PN-001"]')).not.toHaveText('Modified by vendor');
});

// ---------------------------------------------------------------------------
// 4. Round 2: Force Accept/Remove visible for SM only; hidden for VENDOR.
// ---------------------------------------------------------------------------

test('round 2: Force Accept and Force Remove visible only for SM; hidden for VENDOR', async ({ page }) => {
	const round2Po = makePO({
		status: 'MODIFIED',
		round_count: 2,
		last_actor_role: 'VENDOR',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_VENDOR' })]
	});

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(round2Po) });
	});

	// SM view.
	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="line-row-PN-001"]');
	await expect(page.locator('[data-testid="force-accept-btn-PN-001"]')).toBeVisible();
	await expect(page.locator('[data-testid="force-remove-btn-PN-001"]')).toBeVisible();

	// Now swap to VENDOR. Force buttons must be hidden.
	await mockVendor(page);
	// Flip last_actor_role so VENDOR is the current actor; otherwise the
	// negotiation list renders but no actor-scoped actions appear.
	const vendorRound2 = { ...round2Po, last_actor_role: 'SM' };
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(vendorRound2) });
	});
	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="line-row-PN-001"]');
	await expect(page.locator('[data-testid="force-accept-btn-PN-001"]')).toHaveCount(0);
	await expect(page.locator('[data-testid="force-remove-btn-PN-001"]')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 5. Force Accept opens a confirmation; only on confirm does the call fire.
// ---------------------------------------------------------------------------

test('force accept opens confirmation; only on confirm does the backend call fire', async ({ page }) => {
	let forceAcceptCalled = 0;
	let currentPo = makePO({
		status: 'MODIFIED',
		round_count: 2,
		last_actor_role: 'VENDOR',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_VENDOR' })]
	});

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});
	await page.route(`**/api/v1/po/${PO_ID}/lines/PN-001/force-accept`, (route) => {
		forceAcceptCalled += 1;
		currentPo = { ...currentPo, line_items: [{ ...currentPo.line_items[0], status: 'ACCEPTED' }] };
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="line-row-PN-001"]');

	await page.locator('[data-testid="force-accept-btn-PN-001"]').click();

	// Confirmation is now open; backend call has NOT fired.
	await expect(page.locator('[data-testid="force-accept-confirm"]')).toBeVisible();
	expect(forceAcceptCalled).toBe(0);

	// Confirm the action; backend fires exactly once.
	await page.locator('[data-testid="force-accept-confirm-btn"]').click();
	await expect(page.locator('[data-testid="line-status-PN-001"]')).toHaveText('Accepted');
	expect(forceAcceptCalled).toBe(1);
});

// ---------------------------------------------------------------------------
// 6. Line diff renders correct before/after after one modification.
// ---------------------------------------------------------------------------

test('line diff renders before/after after one modification', async ({ page }) => {
	const po = makePO({
		status: 'MODIFIED',
		round_count: 0,
		last_actor_role: 'VENDOR',
		line_items: [
			makeLine('PN-001', {
				quantity: 5,
				unit_price: '120.00',
				status: 'MODIFIED_BY_VENDOR',
				history: [
					{
						part_number: 'PN-001',
						round: 0,
						actor_role: 'VENDOR',
						field: 'quantity',
						old_value: '10',
						new_value: '5',
						edited_at: '2026-04-02T00:00:00+00:00'
					},
					{
						part_number: 'PN-001',
						round: 0,
						actor_role: 'VENDOR',
						field: 'unit_price',
						old_value: '100.00',
						new_value: '120.00',
						edited_at: '2026-04-02T00:00:00+00:00'
					}
				]
			})
		]
	});

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="line-diff"]');

	const diff = page.locator('[data-testid="line-diff"]');
	await expect(diff.locator('tr[data-field="quantity"] .before')).toHaveText('10');
	await expect(diff.locator('tr[data-field="quantity"] .after')).toHaveText('5');
	await expect(diff.locator('tr[data-field="unit_price"] .before')).toHaveText('100.00');
	await expect(diff.locator('tr[data-field="unit_price"] .after')).toHaveText('120.00');
});

// ---------------------------------------------------------------------------
// 7. Edit history timeline collapses on ACCEPTED / REMOVED lines; expandable.
// ---------------------------------------------------------------------------

test('edit history timeline collapses on ACCEPTED lines and is expandable on click', async ({ page }) => {
	// An ACCEPTED line with prior history: timeline should default to collapsed.
	const po = makePO({
		status: 'ACCEPTED',
		round_count: 1,
		last_actor_role: 'VENDOR',
		line_items: [
			makeLine('PN-001', {
				quantity: 5,
				status: 'ACCEPTED',
				history: [
					{
						part_number: 'PN-001',
						round: 0,
						actor_role: 'VENDOR',
						field: 'quantity',
						old_value: '10',
						new_value: '5',
						edited_at: '2026-04-02T00:00:00+00:00'
					}
				]
			})
		]
	});

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});
	await page.route('**/api/v1/invoices/po/*/remaining', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ po_id: PO_ID, lines: [] }) });
	});
	await page.route('**/api/v1/po/*/milestones', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	await page.goto(`/po/${PO_ID}`);
	// ACCEPTED PO renders the legacy table (not the negotiation list) so the
	// EditHistoryTimeline isn't shown. Instead, verify the table renders.
	await page.waitForSelector('.table');
	await expect(page.locator('[data-testid="edit-history-timeline"]')).toHaveCount(0);

	// Now simulate the same line on a MODIFIED PO (in-flight): timeline shows.
	const inflightPo = { ...po, status: 'MODIFIED' };
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(inflightPo) });
	});
	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="edit-history-timeline"]');

	// An ACCEPTED line in a MODIFIED PO renders collapsed by default.
	const toggle = page.locator('[data-testid="edit-history-toggle"]');
	await expect(toggle).toHaveAttribute('data-expanded', 'false');
	await expect(page.locator('[data-testid="edit-history-list"]')).toHaveCount(0);

	// Clicking expands the list.
	await toggle.click();
	await expect(toggle).toHaveAttribute('data-expanded', 'true');
	await expect(page.locator('[data-testid="edit-history-list"]')).toBeVisible();
});

// ---------------------------------------------------------------------------
// 8. Submit Response confirmation dialog shows the delta summary.
// ---------------------------------------------------------------------------

test('submit response confirmation dialog shows the delta summary', async ({ page }) => {
	await mockVendor(page);

	const po = makePO({
		status: 'PENDING',
		last_actor_role: null,
		line_items: [
			makeLine('PN-001', { status: 'ACCEPTED' }),
			makeLine('PN-002', { status: 'MODIFIED_BY_VENDOR' }),
			makeLine('PN-003', { status: 'REMOVED' })
		]
	});

	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.waitForSelector('[data-testid="submit-response-bar"]');

	await page.locator('[data-testid="submit-response-btn"]').click();

	await expect(page.locator('[data-testid="submit-confirm-dialog"]')).toBeVisible();
	await expect(page.locator('[data-testid="delta-accepted"]')).toHaveText('1');
	await expect(page.locator('[data-testid="delta-modified"]')).toHaveText('1');
	await expect(page.locator('[data-testid="delta-removed"]')).toHaveText('1');
});
