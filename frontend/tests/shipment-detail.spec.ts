import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import type { ShipmentStatus, User, UserRole } from '../src/lib/types';

// ---------------------------------------------------------------------------
// Iter 097 — `/shipments/[id]` shell port + line items panel.
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

const SM_USER: User = {
	id: 'u-sm',
	username: 'sm',
	display_name: 'SM User',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null
};

const VENDOR_USER: User = {
	id: 'u-v',
	username: 'vendor',
	display_name: 'Vendor User',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-1'
};

function userForRole(role: UserRole): User {
	if (role === 'SM') return SM_USER;
	if (role === 'VENDOR') return VENDOR_USER;
	return { ...SM_USER, role };
}

async function setupShipmentDetail(
	page: Page,
	opts: {
		status?: ShipmentStatus;
		role?: UserRole;
		shipmentOverride?: ShipmentFixture;
	} = {}
) {
	const status = opts.status ?? 'DRAFT';
	const role = opts.role ?? 'SM';
	const fixture = makeShipment({ status, ...opts.shipmentOverride });

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
}

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
