import { test, expect } from '@playwright/test';

// Iter 081: covers the per-line negotiation UI under the new Phase 4.2 components
// (PoLineNegotiationTable, PoLineNegotiationRow, PoLineModifyModal, PoLineDiff,
// PoLineEditHistoryTimeline, PoSubmitResponseBar). The eight legacy specs from
// iter 057 are migrated to the new testid contract; fourteen new specs cover
// the role x round x status matrix that drives a different action surface.

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

// ===========================================================================
// Iter 057 specs migrated to the iter 081 testid contract
// ===========================================================================

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
		currentPo = { ...currentPo, round_count: 1, last_actor_role: 'VENDOR' as const };
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentPo) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	// Submit-bar round indicator reads "Round 1 of 2" (next round computed
	// from round_count 0 -> 1).
	await expect(page.getByTestId('po-submit-response-round')).toHaveText('Round 1 of 2');

	// Open the modify modal, change qty to 5, submit.
	await page.getByTestId('po-line-action-modify-PN-001').click();
	await page.getByTestId('po-line-modify-modal-PN-001').waitFor();
	await page.getByTestId('po-line-modify-quantity').fill('5');
	await page.getByTestId('po-line-modify-submit').click();

	// Pill now shows MODIFIED_BY_VENDOR.
	await expect(page.getByTestId('po-line-status-PN-001')).toHaveText('Modified by vendor');
	// Only the quantity delta was sent.
	expect(modifyBody).not.toBeNull();
	expect(modifyBody!.fields).toEqual({ quantity: 5 });

	// Submit Response confirms and fires the backend call; after hand-off the
	// vendor is no longer the current actor so the submit bar retracts.
	await page.getByTestId('po-submit-response-btn').click();
	await page.getByTestId('po-submit-response-confirm-btn').click();

	await expect.poll(() => submitResponseCalls).toBe(1);
	await expect(page.getByTestId('po-submit-response-bar')).toHaveCount(0);
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
	await page.getByTestId('po-line-PN-001').waitFor();

	// As SM with a MODIFIED_BY_VENDOR line, Accept is offered.
	await expect(page.getByTestId('po-line-action-accept-PN-001')).toBeVisible();

	// Counter-propose via Modify.
	await page.getByTestId('po-line-action-modify-PN-001').click();
	await page.getByTestId('po-line-modify-quantity').fill('7');
	await page.getByTestId('po-line-modify-submit').click();

	// Status flips to MODIFIED_BY_SM.
	await expect(page.getByTestId('po-line-status-PN-001')).toHaveText('Modified by SM');

	// Swap auth to VENDOR and reload: the vendor now sees Accept (since SM was
	// the last modifier) plus the familiar Modify / Remove options.
	currentPo = {
		...currentPo,
		last_actor_role: 'SM' as const,
		round_count: 1
	};
	await mockVendor(page);
	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();
	await expect(page.getByTestId('po-line-action-accept-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-modify-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-remove-PN-001')).toBeVisible();
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
	await page.getByTestId('po-line-PN-001').waitFor();

	await page.getByTestId('po-line-action-modify-PN-001').click();
	await page.getByTestId('po-line-modify-quantity').fill('0');

	// Modal flips Save button label to "Remove line" before submit.
	await expect(page.getByTestId('po-line-modify-submit')).toHaveText('Remove line');

	await page.getByTestId('po-line-modify-submit').click();

	await expect(page.getByTestId('po-line-status-PN-001')).toHaveText('Removed');
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
	await page.getByTestId('po-line-PN-001').waitFor();
	await expect(page.getByTestId('po-line-action-force-accept-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-force-remove-PN-001')).toBeVisible();

	// Now swap to VENDOR. Force buttons must be hidden.
	await mockVendor(page);
	// Flip last_actor_role so VENDOR is the current actor; otherwise the
	// negotiation list renders but no actor-scoped actions appear.
	const vendorRound2 = { ...round2Po, last_actor_role: 'SM' as const };
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(vendorRound2) });
	});
	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();
	await expect(page.getByTestId('po-line-action-force-accept-PN-001')).toHaveCount(0);
	await expect(page.getByTestId('po-line-action-force-remove-PN-001')).toHaveCount(0);
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
	await page.getByTestId('po-line-PN-001').waitFor();

	await page.getByTestId('po-line-action-force-accept-PN-001').click();

	// Confirmation is now open; backend call has NOT fired.
	await expect(page.getByTestId('po-line-force-accept-confirm-PN-001')).toBeVisible();
	expect(forceAcceptCalled).toBe(0);

	// Confirm the action; backend fires exactly once.
	await page.getByTestId('po-line-action-force-accept-confirm-PN-001').click();
	await expect(page.getByTestId('po-line-status-PN-001')).toHaveText('Accepted');
	expect(forceAcceptCalled).toBe(1);
});

// ---------------------------------------------------------------------------
// 6. Line diff renders before/after after one modification.
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
	await page.getByTestId('po-line-PN-001').waitFor();

	// Diff hides behind the View changes toggle.
	await page.getByTestId('po-line-details-toggle-PN-001').click();

	const diff = page.getByTestId('po-line-diff-PN-001');
	await expect(diff).toBeVisible();
	await expect(diff).toContainText('quantity');
	await expect(diff).toContainText('10');
	await expect(diff).toContainText('5');
	await expect(diff).toContainText('unit_price');
	await expect(diff).toContainText('100.00');
	await expect(diff).toContainText('120.00');
});

// ---------------------------------------------------------------------------
// 7. Edit history toggle reveals the list when expanded; in-flight only.
// ---------------------------------------------------------------------------

test('edit history is hidden on ACCEPTED PO and revealed by toggle on in-flight PO', async ({ page }) => {
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
	// PoLineEditHistoryTimeline isn't shown. Verify the history primitive is
	// absent.
	await expect(page.getByTestId('po-line-history-PN-001')).toHaveCount(0);

	// Now simulate a non-terminal line on a MODIFIED PO (in-flight): the
	// PoLineEditHistoryTimeline auto-expands when the line status is not
	// ACCEPTED/REMOVED, so once the row's View changes toggle is clicked the
	// list renders without an extra inner toggle.
	const inflightPo = {
		...po,
		status: 'MODIFIED',
		line_items: [{ ...po.line_items[0], status: 'MODIFIED_BY_VENDOR' }]
	};
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(inflightPo) });
	});
	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	// The View changes toggle reveals the diff and the history primitive.
	await page.getByTestId('po-line-details-toggle-PN-001').click();
	await expect(page.getByTestId('po-line-history-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-history-list-PN-001')).toBeVisible();
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
	await page.getByTestId('po-submit-response-bar').waitFor();

	await page.getByTestId('po-submit-response-btn').click();

	await expect(page.getByTestId('po-submit-response-confirm')).toBeVisible();
	await expect(page.getByTestId('po-submit-response-delta-accepted')).toHaveText('1');
	await expect(page.getByTestId('po-submit-response-delta-modified')).toHaveText('1');
	await expect(page.getByTestId('po-submit-response-delta-removed')).toHaveText('1');
});

// ===========================================================================
// Iter 081 new specs: role x round x status matrix coverage
// ===========================================================================

// ---------------------------------------------------------------------------
// 9. Vendor on PENDING line sees Modify and Remove, no Accept.
// ---------------------------------------------------------------------------

test('vendor on PENDING line sees Modify and Remove, no Accept', async ({ page }) => {
	await mockVendor(page);
	const po = makePO({
		status: 'PENDING',
		round_count: 0,
		last_actor_role: null,
		line_items: [makeLine('PN-001', { status: 'PENDING' })]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	await expect(page.getByTestId('po-line-action-modify-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-remove-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-accept-PN-001')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 10. Vendor on MODIFIED_BY_SM line sees Accept, Modify, Remove.
// ---------------------------------------------------------------------------

test('vendor on MODIFIED_BY_SM sees Accept, Modify, Remove and no force actions', async ({ page }) => {
	await mockVendor(page);
	const po = makePO({
		status: 'MODIFIED',
		round_count: 1,
		last_actor_role: 'SM',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_SM' })]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	await expect(page.getByTestId('po-line-action-accept-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-modify-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-remove-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-force-accept-PN-001')).toHaveCount(0);
	await expect(page.getByTestId('po-line-action-force-remove-PN-001')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 11. SM on MODIFIED_BY_VENDOR (round 1) sees Accept, Modify, Remove.
// ---------------------------------------------------------------------------

test('sm on MODIFIED_BY_VENDOR at round 1 sees Accept, Modify, Remove and no force actions', async ({ page }) => {
	const po = makePO({
		status: 'MODIFIED',
		round_count: 1,
		last_actor_role: 'VENDOR',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_VENDOR' })]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	await expect(page.getByTestId('po-line-action-accept-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-modify-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-remove-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-force-accept-PN-001')).toHaveCount(0);
	await expect(page.getByTestId('po-line-action-force-remove-PN-001')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 12. SM at round 2 on MODIFIED_BY_VENDOR sees Force Accept and Force Remove.
// ---------------------------------------------------------------------------

test('sm at round 2 on MODIFIED_BY_VENDOR sees Force Accept and Force Remove alongside Accept/Modify/Remove', async ({ page }) => {
	const po = makePO({
		status: 'MODIFIED',
		round_count: 2,
		last_actor_role: 'VENDOR',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_VENDOR' })]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	await expect(page.getByTestId('po-line-action-accept-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-modify-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-remove-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-force-accept-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-action-force-remove-PN-001')).toBeVisible();
});

// ---------------------------------------------------------------------------
// 13. Vendor at round 2 sees no force actions.
// ---------------------------------------------------------------------------

test('vendor at round 2 sees no force actions', async ({ page }) => {
	await mockVendor(page);
	const po = makePO({
		status: 'MODIFIED',
		round_count: 2,
		last_actor_role: 'SM',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_SM' })]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	await expect(page.getByTestId('po-line-action-force-accept-PN-001')).toHaveCount(0);
	await expect(page.getByTestId('po-line-action-force-remove-PN-001')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 14. Terminal lines (ACCEPTED, REMOVED) render no actions.
// ---------------------------------------------------------------------------

test('terminal lines render no actions in their action group', async ({ page }) => {
	const po = makePO({
		status: 'MODIFIED',
		round_count: 1,
		last_actor_role: 'VENDOR',
		line_items: [
			makeLine('PN-A', { status: 'ACCEPTED' }),
			makeLine('PN-R', { status: 'REMOVED' })
		]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-A').waitFor();

	// The actions container exists in the DOM but renders no buttons for
	// terminal lines (the empty flex container collapses to zero height,
	// so we assert presence + button count, not visibility).
	const acceptedActions = page.getByTestId('po-line-actions-PN-A');
	await expect(acceptedActions).toHaveCount(1);
	await expect(acceptedActions.getByRole('button')).toHaveCount(0);

	const removedActions = page.getByTestId('po-line-actions-PN-R');
	await expect(removedActions).toHaveCount(1);
	await expect(removedActions.getByRole('button')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 15. Force accept opens confirm dialog and routes the action through the API.
// ---------------------------------------------------------------------------

test('force accept opens confirm dialog and routes the action', async ({ page }) => {
	let forceAcceptCalled = 0;
	const po = makePO({
		status: 'MODIFIED',
		round_count: 2,
		last_actor_role: 'VENDOR',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_VENDOR' })]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});
	await page.route(`**/api/v1/po/${PO_ID}/lines/PN-001/force-accept`, (route) => {
		forceAcceptCalled += 1;
		const after = {
			...po,
			line_items: [{ ...po.line_items[0], status: 'ACCEPTED' as const }]
		};
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(after) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	await page.getByTestId('po-line-action-force-accept-PN-001').click();
	await expect(page.getByTestId('po-line-force-accept-confirm-PN-001')).toBeVisible();
	expect(forceAcceptCalled).toBe(0);

	await page.getByTestId('po-line-action-force-accept-confirm-PN-001').click();
	await expect.poll(() => forceAcceptCalled).toBe(1);
});

// ---------------------------------------------------------------------------
// 16. Modify modal validates required text fields.
// ---------------------------------------------------------------------------

test('modify modal validates required text fields and keeps modal open', async ({ page }) => {
	const po = makePO({
		status: 'PENDING',
		round_count: 0,
		last_actor_role: null,
		line_items: [makeLine('PN-001')]
	});
	await mockVendor(page);
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	await page.getByTestId('po-line-action-modify-PN-001').click();
	await page.getByTestId('po-line-modify-modal-PN-001').waitFor();

	// Clear UoM to empty, attempt submit.
	await page.getByTestId('po-line-modify-uom').fill('');
	await page.getByTestId('po-line-modify-submit').click();

	// Modal stays open; FormField error slot is populated for UoM.
	await expect(page.getByTestId('po-line-modify-modal-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-modify-uom-field-error')).toBeVisible();
	await expect(page.getByTestId('po-line-modify-uom-field-error')).toContainText('UoM');
});

// ---------------------------------------------------------------------------
// 17. Modify modal q=0 hint and submit label flips to Remove line.
// ---------------------------------------------------------------------------

test('modify modal q=0 surfaces hint and submit button reads Remove line', async ({ page }) => {
	const po = makePO({
		status: 'PENDING',
		round_count: 0,
		last_actor_role: null,
		line_items: [makeLine('PN-001', { quantity: 10 })]
	});
	await mockVendor(page);
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	await page.getByTestId('po-line-action-modify-PN-001').click();
	await page.getByTestId('po-line-modify-modal-PN-001').waitFor();

	await page.getByTestId('po-line-modify-quantity').fill('0');

	// FormField hint is rendered inside the quantity field; locate by field
	// container scope and the hint copy from PoLineModifyModal.
	const qtyField = page.getByTestId('po-line-modify-quantity-field');
	await expect(qtyField).toContainText('Quantity 0 will remove the line from the PO.');

	// Submit button text flips.
	await expect(page.getByTestId('po-line-modify-submit')).toHaveText('Remove line');
});

// ---------------------------------------------------------------------------
// 18. View-changes toggle reveals diff and history.
// ---------------------------------------------------------------------------

test('view-changes toggle reveals diff and history then hides them again', async ({ page }) => {
	const historyEntry = {
		part_number: 'PN-001',
		round: 0,
		actor_role: 'VENDOR',
		field: 'quantity',
		old_value: '10',
		new_value: '5',
		edited_at: '2026-04-02T00:00:00+00:00'
	};
	const po = makePO({
		status: 'MODIFIED',
		round_count: 0,
		last_actor_role: 'VENDOR',
		line_items: [
			makeLine('PN-001', {
				quantity: 5,
				status: 'MODIFIED_BY_VENDOR',
				history: [historyEntry]
			})
		]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	// Hidden initially.
	await expect(page.getByTestId('po-line-diff-PN-001')).toHaveCount(0);
	await expect(page.getByTestId('po-line-history-PN-001')).toHaveCount(0);

	// Toggle to expand.
	await page.getByTestId('po-line-details-toggle-PN-001').click();
	await expect(page.getByTestId('po-line-diff-PN-001')).toBeVisible();
	await expect(page.getByTestId('po-line-history-PN-001')).toBeVisible();

	// Toggle again to collapse.
	await page.getByTestId('po-line-details-toggle-PN-001').click();
	await expect(page.getByTestId('po-line-diff-PN-001')).toHaveCount(0);
	await expect(page.getByTestId('po-line-history-PN-001')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// 19. Submit bar disabled while unaddressed lines remain.
// ---------------------------------------------------------------------------

test('submit bar is disabled while unaddressed lines remain and shows count hint', async ({ page }) => {
	await mockVendor(page);
	const po = makePO({
		status: 'PENDING',
		round_count: 0,
		last_actor_role: null,
		line_items: [makeLine('PN-001'), makeLine('PN-002')]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-submit-response-bar').waitFor();

	await expect(page.getByTestId('po-submit-response-btn')).toBeDisabled();
	await expect(page.getByTestId('po-submit-response-hint')).toHaveText('2 lines still need a decision');
});

// ---------------------------------------------------------------------------
// 20. Submit bar enabled when all addressed; confirm dialog shows delta.
// ---------------------------------------------------------------------------

test('submit bar enables when all addressed and confirm dialog reports the delta', async ({ page }) => {
	await mockVendor(page);
	const po = makePO({
		status: 'PENDING',
		round_count: 0,
		last_actor_role: null,
		line_items: [
			makeLine('PN-001', { status: 'MODIFIED_BY_VENDOR' }),
			makeLine('PN-002', { status: 'MODIFIED_BY_VENDOR' })
		]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-submit-response-bar').waitFor();

	await expect(page.getByTestId('po-submit-response-btn')).toBeEnabled();
	await page.getByTestId('po-submit-response-btn').click();

	await expect(page.getByTestId('po-submit-response-confirm')).toBeVisible();
	await expect(page.getByTestId('po-submit-response-delta-accepted')).toHaveText('0');
	await expect(page.getByTestId('po-submit-response-delta-modified')).toHaveText('2');
	await expect(page.getByTestId('po-submit-response-delta-removed')).toHaveText('0');
});

// ---------------------------------------------------------------------------
// 21. Submit bar at round 1 shows force-only warning.
// ---------------------------------------------------------------------------

test('submit bar at round 1 with all addressed shows the force-override warning', async ({ page }) => {
	const po = makePO({
		status: 'MODIFIED',
		round_count: 1,
		last_actor_role: 'VENDOR',
		line_items: [
			makeLine('PN-001', { status: 'ACCEPTED' }),
			makeLine('PN-002', { status: 'MODIFIED_BY_SM' })
		]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-submit-response-bar').waitFor();

	await expect(page.getByTestId('po-submit-response-hint')).toContainText('force-override only');
});

// ---------------------------------------------------------------------------
// 22. Mobile 390px: actions stack two-per-row.
// ---------------------------------------------------------------------------

test('mobile 390x844: action buttons sit at roughly half the row width so two actions fit per row', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });

	const po = makePO({
		status: 'MODIFIED',
		round_count: 1,
		last_actor_role: 'VENDOR',
		line_items: [makeLine('PN-001', { status: 'MODIFIED_BY_VENDOR' })]
	});
	await page.route(`**/api/v1/po/${PO_ID}`, (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(po) });
	});

	await page.goto(`/po/${PO_ID}`);
	await page.getByTestId('po-line-PN-001').waitFor();

	const actionsGroup = page.getByTestId('po-line-actions-PN-001');
	const groupBox = await actionsGroup.boundingBox();
	expect(groupBox).not.toBeNull();
	const groupWidth = groupBox!.width;

	const buttonTestids: ReadonlyArray<string> = [
		'po-line-action-accept-PN-001',
		'po-line-action-modify-PN-001',
		'po-line-action-remove-PN-001'
	] as const;

	// At 390px the SM-on-MODIFIED_BY_VENDOR matrix yields 3 actions sharing a
	// flex-wrap row with a 50%-of-container flex-basis. Two of the three sit
	// per row at ~50%; the orphaned third grows to fill its row. Assert at
	// least two buttons land in the 40%-60% window so the two-per-row layout
	// is guaranteed.
	const ratios: number[] = [];
	for (const tid of buttonTestids) {
		const box = await page.getByTestId(tid).boundingBox();
		expect(box).not.toBeNull();
		ratios.push(box!.width / groupWidth);
	}
	const halfWidthCount = ratios.filter((r) => r >= 0.4 && r <= 0.6).length;
	expect(halfWidthCount).toBeGreaterThanOrEqual(2);
});
