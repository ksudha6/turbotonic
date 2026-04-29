import { test, expect } from '@playwright/test';

const MANUFACTURING_ADDRESS = '456 Industrial Park, Shenzhen';
const EXISTING_MANUFACTURING_ADDRESS = '789 Plant Ave, Taipei';

const VENDOR_ACTIVE = {
	id: 'v1',
	name: 'Acme Corp',
	country: 'CN',
	status: 'ACTIVE',
	vendor_type: 'PROCUREMENT',
	address: '',
	account_details: '',
};

const PRODUCT = {
	id: 'prod-1',
	vendor_id: 'v1',
	part_number: 'PN-001',
	description: 'Test Part',
	manufacturing_address: EXISTING_MANUFACTURING_ADDRESS,
	qualifications: [],
	created_at: '2026-01-01T00:00:00Z',
	updated_at: '2026-01-01T00:00:00Z',
};

// NotificationBell calls unread-count on every page load.
test.beforeEach(async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'test-user-id',
					username: 'test-sm',
					display_name: 'Test User',
					role: 'SM',
					status: 'ACTIVE',
					vendor_id: null,
				},
			}),
		});
	});
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
	});
	await page.route('**/api/v1/qualification-types', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/packaging-specs**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
});

// ---------------------------------------------------------------------------
// Iteration 36 — Product manufacturing_address field
// ---------------------------------------------------------------------------

test('product create form renders manufacturing_address field', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});

	await page.goto('/products/new');
	await expect(page.getByTestId('product-create-form')).toBeVisible();

	await expect(page.getByTestId('product-form-manufacturing-address')).toBeVisible();
	await expect(page.getByTestId('product-form-manufacturing-address')).toHaveValue('');
});

test('product create form submits manufacturing_address', async ({ page }) => {
	let capturedBody: Record<string, unknown> = {};

	await page.route('**/api/v1/vendors**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			route.continue();
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([VENDOR_ACTIVE]),
			});
		}
	});

	await page.route('**/api/v1/products**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			capturedBody = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify({ ...PRODUCT, manufacturing_address: MANUFACTURING_ADDRESS }),
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
		}
	});

	await page.goto('/products/new');
	await expect(page.getByTestId('product-create-form')).toBeVisible();

	await page.getByTestId('product-form-vendor').selectOption('v1');
	await page.getByTestId('product-form-part-number').fill('PN-002');
	await page.getByTestId('product-form-manufacturing-address').fill(MANUFACTURING_ADDRESS);

	await page.getByTestId('product-form-submit').click();
	await page.waitForURL('**/products');

	expect(capturedBody['manufacturing_address']).toBe(MANUFACTURING_ADDRESS);
});

// ---------------------------------------------------------------------------
// Iter 091 — `/products/new` under (nexus) AppShell (additional specs)
// ---------------------------------------------------------------------------

test('product create page mounts under (nexus) AppShell', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.goto('/products/new');
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Create Product', level: 1 })).toBeVisible();
	await expect(page.getByTestId('product-create-form')).toBeVisible();
});

test('product create form blocks submit when vendor unselected', async ({ page }) => {
	let postCalled = false;
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		if (route.request().method() === 'POST') postCalled = true;
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	await page.goto('/products/new');
	await page.getByTestId('product-form-part-number').fill('PN-XYZ');
	await page.getByTestId('product-form-submit').click();

	await expect(page.getByText('Vendor is required.')).toBeVisible();
	expect(postCalled).toBe(false);
});

test('product create form blocks submit when part_number empty', async ({ page }) => {
	let postCalled = false;
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		if (route.request().method() === 'POST') postCalled = true;
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	await page.goto('/products/new');
	await page.getByTestId('product-form-vendor').selectOption('v1');
	await page.getByTestId('product-form-submit').click();

	await expect(page.getByText('Part Number is required.')).toBeVisible();
	expect(postCalled).toBe(false);
});

test('product create form surfaces 409 conflict inline', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		if (route.request().method() === 'POST') {
			route.fulfill({
				status: 409,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'duplicate' })
			});
		} else {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		}
	});

	await page.goto('/products/new');
	await page.getByTestId('product-form-vendor').selectOption('v1');
	await page.getByTestId('product-form-part-number').fill('PN-001');
	await page.getByTestId('product-form-submit').click();

	await expect(page.getByTestId('product-form-error')).toContainText(
		'A product with this part number already exists for this vendor.'
	);
});

test('product create form Cancel returns to /products', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});

	await page.goto('/products/new');
	await page.getByTestId('product-form-cancel').click();
	await page.waitForURL('**/products');
	expect(page.url()).toContain('/products');
	expect(page.url()).not.toContain('/new');
});

test('product edit form shows existing manufacturing_address', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});

	await page.route('**/api/v1/products/prod-1**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(PRODUCT),
		});
	});

	await page.goto('/products/prod-1/edit');
	await expect(page.getByTestId('product-edit-form')).toBeVisible();

	await expect(page.getByTestId('product-edit-manufacturing-address')).toHaveValue(EXISTING_MANUFACTURING_ADDRESS);
});

// ---------------------------------------------------------------------------
// Iter 092 — `/products/[id]/edit` under (nexus): details + qualifications
// ---------------------------------------------------------------------------

const PRODUCT_WITH_QUAL = {
	...PRODUCT,
	id: 'prod-edit-1',
	qualifications: [
		{
			id: 'qt-iso',
			name: 'ISO 9001',
			target_market: 'AMZ',
			applies_to_category: 'GENERAL'
		}
	]
};

const QT_OPTIONS = [
	{ id: 'qt-iso', name: 'ISO 9001', target_market: 'AMZ', applies_to_category: 'GENERAL' },
	{ id: 'qt-fda', name: 'FDA Approval', target_market: 'AMZ', applies_to_category: 'FOOD' }
];

async function setupEditPage(
	page: import('@playwright/test').Page,
	productOverride: object = {}
) {
	const productPayload = { ...PRODUCT_WITH_QUAL, ...productOverride };
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE])
		});
	});
	await page.route('**/api/v1/qualification-types', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(QT_OPTIONS)
		});
	});
	await page.route(`**/api/v1/products/${productPayload.id}`, (route) => {
		const path = new URL(route.request().url()).pathname;
		if (path === `/api/v1/products/${productPayload.id}`) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(productPayload)
			});
		} else {
			route.continue();
		}
	});
	// listPackagingSpecs hits /api/v1/packaging-specs/?product_id=... per api.ts:458.
	await page.route('**/api/v1/packaging-specs/**', (route) => {
		if (route.request().method() === 'GET') {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		} else {
			route.continue();
		}
	});
}

const SPEC_PENDING = {
	id: 'spec-1',
	product_id: 'prod-edit-1',
	marketplace: 'AMAZON',
	spec_name: 'FNSKU Label',
	description: 'Apply FNSKU on each unit',
	requirements_text: '2x1 inch label, white background',
	status: 'PENDING',
	created_at: '2026-04-01T00:00:00+00:00',
	updated_at: '2026-04-01T00:00:00+00:00'
};

const SPEC_COLLECTED = {
	id: 'spec-2',
	product_id: 'prod-edit-1',
	marketplace: 'WALMART',
	spec_name: 'Outer Carton',
	description: 'Carton dimensions',
	requirements_text: 'Max 24in',
	status: 'COLLECTED',
	created_at: '2026-04-01T00:00:00+00:00',
	updated_at: '2026-04-01T00:00:00+00:00'
};

async function setupEditPageWithSpecs(
	page: import('@playwright/test').Page,
	specsPayload: object[]
) {
	await setupEditPage(page);
	// Override packaging-specs catch-all (registered last → highest LIFO priority).
	await page.route('**/api/v1/packaging-specs/**', (route) => {
		const method = route.request().method();
		if (method === 'GET') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(specsPayload)
			});
		} else {
			route.continue();
		}
	});
}

test('product edit page mounts under (nexus) AppShell', async ({ page }) => {
	await setupEditPage(page);
	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Edit Product', level: 1 })).toBeVisible();
	await expect(page.getByTestId('product-edit-form')).toBeVisible();
});

test('product edit page shows vendor + part_number as readonly values', async ({ page }) => {
	await setupEditPage(page);
	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);

	await expect(page.getByTestId('product-edit-vendor')).toHaveText(VENDOR_ACTIVE.name);
	await expect(page.getByTestId('product-edit-part-number')).toHaveText(PRODUCT_WITH_QUAL.part_number);
});

test('product edit save posts description + manufacturing_address and redirects', async ({ page }) => {
	let captured: Record<string, unknown> = {};
	await setupEditPage(page);
	await page.route(`**/api/v1/products/${PRODUCT_WITH_QUAL.id}`, (route) => {
		const method = route.request().method();
		const path = new URL(route.request().url()).pathname;
		if (method === 'PATCH' || method === 'PUT') {
			captured = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ ...PRODUCT_WITH_QUAL, description: 'updated' })
			});
		} else if (path === `/api/v1/products/${PRODUCT_WITH_QUAL.id}`) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(PRODUCT_WITH_QUAL)
			});
		} else {
			route.continue();
		}
	});

	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	await expect(page.getByTestId('product-edit-form')).toBeVisible();

	await page.getByTestId('product-edit-description').fill('updated');
	await page.getByTestId('product-edit-save').click();
	await page.waitForURL('**/products');

	expect(captured['description']).toBe('updated');
});

test('product edit Cancel returns to /products without saving', async ({ page }) => {
	let postCalled = false;
	await setupEditPage(page);
	await page.route(`**/api/v1/products/${PRODUCT_WITH_QUAL.id}`, (route) => {
		const method = route.request().method();
		const path = new URL(route.request().url()).pathname;
		if (method === 'PATCH' || method === 'PUT') {
			postCalled = true;
			route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
		} else if (path === `/api/v1/products/${PRODUCT_WITH_QUAL.id}`) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(PRODUCT_WITH_QUAL)
			});
		} else {
			route.continue();
		}
	});

	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	await expect(page.getByTestId('product-edit-form')).toBeVisible();

	await page.getByTestId('product-edit-cancel').click();
	await page.waitForURL('**/products');
	expect(postCalled).toBe(false);
	expect(page.url()).toContain('/products');
	expect(page.url()).not.toContain('/edit');
});

test('qualifications panel lists assigned qual with target_market pill', async ({ page }) => {
	await setupEditPage(page);
	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);

	const panel = page.getByTestId('product-qualifications-panel');
	await expect(panel).toBeVisible();
	await expect(panel.getByTestId('product-qualification-row-qt-iso')).toBeVisible();
	await expect(panel).toContainText('ISO 9001');
	await expect(panel).toContainText('AMZ');
});

test('qualifications panel empty state', async ({ page }) => {
	await setupEditPage(page, { qualifications: [] });
	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);

	const panel = page.getByTestId('product-qualifications-panel');
	await expect(panel).toContainText('No qualifications assigned.');
});

test('add qualification flow: select + Add inserts row', async ({ page }) => {
	await setupEditPage(page);
	// assignQualification POSTs to /api/v1/products/{id}/qualifications with body
	// { qualification_type_id: ... } per api.ts line 434.
	await page.route(`**/api/v1/products/${PRODUCT_WITH_QUAL.id}/qualifications`, (route) => {
		if (route.request().method() === 'POST') {
			const body = JSON.parse(route.request().postData() ?? '{}');
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify({
					product_id: PRODUCT_WITH_QUAL.id,
					qualification_type_id: body.qualification_type_id
				})
			});
		} else {
			route.continue();
		}
	});

	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	const panel = page.getByTestId('product-qualifications-panel');
	await panel.getByTestId('product-qualification-add-select').selectOption('qt-fda');
	await panel.getByTestId('product-qualification-add-button').click();

	await expect(panel.getByTestId('product-qualification-row-qt-fda')).toBeVisible();
});

test('remove qualification flow: Remove deletes row', async ({ page }) => {
	await setupEditPage(page);
	await page.route(`**/api/v1/products/${PRODUCT_WITH_QUAL.id}/qualifications/qt-iso`, (route) => {
		if (route.request().method() === 'DELETE') {
			route.fulfill({ status: 204, contentType: 'application/json', body: '' });
		} else {
			route.continue();
		}
	});

	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	const panel = page.getByTestId('product-qualifications-panel');
	await expect(panel.getByTestId('product-qualification-row-qt-iso')).toBeVisible();
	await panel.getByTestId('product-qualification-remove-qt-iso').click();
	await expect(panel.getByTestId('product-qualification-row-qt-iso')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Iter 093 — packaging specs panel on `/products/[id]/edit`
// ---------------------------------------------------------------------------

test('packaging panel mounts with empty state when no specs', async ({ page }) => {
	await setupEditPage(page);
	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);

	const panel = page.getByTestId('product-packaging-panel');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText('No packaging specs defined yet.');
});

test('packaging panel groups specs by marketplace with status pills', async ({ page }) => {
	await setupEditPageWithSpecs(page, [SPEC_PENDING, SPEC_COLLECTED]);
	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);

	const panel = page.getByTestId('product-packaging-panel');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText('AMAZON');
	await expect(panel).toContainText('WALMART');
	await expect(panel.getByTestId(`product-packaging-row-${SPEC_PENDING.id}`)).toContainText(
		SPEC_PENDING.spec_name
	);
	await expect(panel.getByTestId(`product-packaging-row-status-${SPEC_PENDING.id}`)).toContainText(
		'PENDING'
	);
	await expect(panel.getByTestId(`product-packaging-row-status-${SPEC_COLLECTED.id}`)).toContainText(
		'COLLECTED'
	);
});

test('packaging add flow inserts row and auto-closes form', async ({ page }) => {
	await setupEditPage(page);
	const NEW_SPEC = {
		id: 'spec-new',
		product_id: PRODUCT_WITH_QUAL.id,
		marketplace: 'EBAY',
		spec_name: 'Polybag',
		description: '',
		requirements_text: '',
		status: 'PENDING',
		created_at: '2026-04-29T00:00:00+00:00',
		updated_at: '2026-04-29T00:00:00+00:00'
	};
	await page.route('**/api/v1/packaging-specs/**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			route.fulfill({
				status: 201,
				contentType: 'application/json',
				body: JSON.stringify(NEW_SPEC)
			});
		} else if (method === 'GET') {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		} else {
			route.continue();
		}
	});

	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	const panel = page.getByTestId('product-packaging-panel');
	await panel.getByTestId('product-packaging-add-trigger').click();
	await expect(panel.getByTestId('product-packaging-add-form')).toBeVisible();

	await panel.getByTestId('product-packaging-add-marketplace').fill(NEW_SPEC.marketplace);
	await panel.getByTestId('product-packaging-add-spec-name').fill(NEW_SPEC.spec_name);
	await panel.getByTestId('product-packaging-add-submit').click();

	await expect(panel.getByTestId(`product-packaging-row-${NEW_SPEC.id}`)).toBeVisible();
	await expect(panel.getByTestId('product-packaging-add-form')).toHaveCount(0);
});

test('packaging add flow surfaces server error inline', async ({ page }) => {
	await setupEditPage(page);
	await page.route('**/api/v1/packaging-specs/**', (route) => {
		const method = route.request().method();
		if (method === 'POST') {
			route.fulfill({
				status: 500,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'boom' })
			});
		} else if (method === 'GET') {
			route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
		} else {
			route.continue();
		}
	});

	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	const panel = page.getByTestId('product-packaging-panel');
	await panel.getByTestId('product-packaging-add-trigger').click();
	await panel.getByTestId('product-packaging-add-marketplace').fill('AMAZON');
	await panel.getByTestId('product-packaging-add-spec-name').fill('FNSKU');
	await panel.getByTestId('product-packaging-add-submit').click();

	await expect(panel.getByTestId('product-packaging-add-error')).toBeVisible();
	await expect(panel.getByTestId('product-packaging-add-form')).toBeVisible();
});

test('packaging delete flow removes row when confirm accepted', async ({ page }) => {
	await setupEditPageWithSpecs(page, [SPEC_PENDING]);
	await page.route(`**/api/v1/packaging-specs/${SPEC_PENDING.id}`, (route) => {
		if (route.request().method() === 'DELETE') {
			route.fulfill({ status: 204, contentType: 'application/json', body: '' });
		} else {
			route.continue();
		}
	});
	page.on('dialog', (dialog) => dialog.accept());

	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	const panel = page.getByTestId('product-packaging-panel');
	await expect(panel.getByTestId(`product-packaging-row-${SPEC_PENDING.id}`)).toBeVisible();
	await panel.getByTestId(`product-packaging-row-delete-${SPEC_PENDING.id}`).click();

	await expect(panel.getByTestId(`product-packaging-row-${SPEC_PENDING.id}`)).toHaveCount(0);
});

test('packaging delete flow keeps row when confirm dismissed', async ({ page }) => {
	await setupEditPageWithSpecs(page, [SPEC_PENDING]);
	let deleteCalled = false;
	await page.route(`**/api/v1/packaging-specs/${SPEC_PENDING.id}`, (route) => {
		if (route.request().method() === 'DELETE') {
			deleteCalled = true;
			route.fulfill({ status: 204, contentType: 'application/json', body: '' });
		} else {
			route.continue();
		}
	});
	page.on('dialog', (dialog) => dialog.dismiss());

	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);
	const panel = page.getByTestId('product-packaging-panel');
	await panel.getByTestId(`product-packaging-row-delete-${SPEC_PENDING.id}`).click();

	await expect(panel.getByTestId(`product-packaging-row-${SPEC_PENDING.id}`)).toBeVisible();
	expect(deleteCalled).toBe(false);
});

test('packaging delete button hidden on COLLECTED specs', async ({ page }) => {
	await setupEditPageWithSpecs(page, [SPEC_COLLECTED]);
	await page.goto(`/products/${PRODUCT_WITH_QUAL.id}/edit`);

	const panel = page.getByTestId('product-packaging-panel');
	await expect(panel.getByTestId(`product-packaging-row-${SPEC_COLLECTED.id}`)).toBeVisible();
	await expect(
		panel.getByTestId(`product-packaging-row-delete-${SPEC_COLLECTED.id}`)
	).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Iter 090 — `/products` list under (nexus) AppShell
// ---------------------------------------------------------------------------

const PRODUCT_NO_QUALS = {
	id: 'prod-list-1',
	vendor_id: 'v1',
	part_number: 'PN-LIST-001',
	description: 'Steel bolt M8',
	manufacturing_address: '',
	qualifications: []
};

const QUAL_ITEM = {
	id: 'qt-1',
	name: 'QUALITY_CERTIFICATE',
	target_market: 'AMZ',
	applies_to_category: 'GENERAL'
};

const PRODUCT_WITH_QUALS = {
	id: 'prod-list-2',
	vendor_id: 'v1',
	part_number: 'PN-LIST-002',
	description: 'Steel bolt M10',
	manufacturing_address: '',
	qualifications: [QUAL_ITEM]
};

test('product list page mounts under (nexus) AppShell', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PRODUCT_NO_QUALS]),
		});
	});

	await page.goto('/products');
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByTestId('ui-appshell-topbar')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Vendor Portal' })).toHaveCount(0);
});

test('product list loads and renders rows', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PRODUCT_NO_QUALS, PRODUCT_WITH_QUALS]),
		});
	});

	await page.goto('/products');
	await expect(page.getByRole('heading', { name: 'Products', level: 1 })).toBeVisible();

	const desktop = page.getByTestId('product-table-desktop');
	await expect(desktop.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`product-row-${PRODUCT_WITH_QUALS.id}`)).toBeVisible();
	await expect(desktop).toContainText('PN-LIST-001');
	await expect(desktop).toContainText('PN-LIST-002');
	await expect(desktop).toContainText('Acme Corp');
});

test('qualification pill shows count for products with qualifications and "None" otherwise', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PRODUCT_NO_QUALS, PRODUCT_WITH_QUALS]),
		});
	});

	await page.goto('/products');
	const desktop = page.getByTestId('product-table-desktop');
	await expect(desktop.getByTestId(`product-row-quals-${PRODUCT_NO_QUALS.id}`)).toContainText('None');
	await expect(desktop.getByTestId(`product-row-quals-${PRODUCT_WITH_QUALS.id}`)).toContainText('1 qualification');
});

test('vendor filter narrows product list', async ({ page }) => {
	const VENDOR_OTHER = { ...VENDOR_ACTIVE, id: 'v2', name: 'Beta LLC' };
	const PRODUCT_V2 = { ...PRODUCT_NO_QUALS, id: 'prod-list-3', vendor_id: 'v2', part_number: 'PN-V2' };

	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE, VENDOR_OTHER]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		const url = new URL(route.request().url());
		const vId = url.searchParams.get('vendor_id');
		const rows = vId === 'v2' ? [PRODUCT_V2] : vId === 'v1' ? [PRODUCT_NO_QUALS] : [PRODUCT_NO_QUALS, PRODUCT_V2];
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(rows),
		});
	});

	await page.goto('/products');
	const desktop = page.getByTestId('product-table-desktop');
	await expect(desktop.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`product-row-${PRODUCT_V2.id}`)).toBeVisible();

	await page.getByTestId('product-filter-vendor').selectOption('v2');
	await expect(desktop.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`)).toHaveCount(0);
	await expect(desktop.getByTestId(`product-row-${PRODUCT_V2.id}`)).toBeVisible();
});

test('product list shows empty state when filter returns no rows', async ({ page }) => {
	let firstCall = true;
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		const body = firstCall ? [PRODUCT_NO_QUALS] : [];
		firstCall = false;
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(body),
		});
	});

	await page.goto('/products');
	await expect(page.getByTestId('product-table-desktop')).toBeVisible();

	await page.getByTestId('product-filter-vendor').selectOption('v1');
	await expect(page.getByTestId('product-table-desktop')).toHaveCount(0);
	await expect(page.getByText('No matching products')).toBeVisible();
});

test('product list shows error state with retry', async ({ page }) => {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});

	let attempt = 0;
	await page.route('**/api/v1/products**', (route) => {
		attempt += 1;
		if (attempt === 1) {
			route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' });
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([PRODUCT_NO_QUALS]),
			});
		}
	});

	await page.goto('/products');
	await expect(page.getByRole('alert')).toBeVisible();
	await page.getByRole('button', { name: /retry/i }).click();
	await expect(page.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`).first()).toBeVisible();
});

test('mobile (390px) renders product cards instead of desktop table', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([VENDOR_ACTIVE]),
		});
	});
	await page.route('**/api/v1/products**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([PRODUCT_NO_QUALS]),
		});
	});

	await page.goto('/products');
	await expect(page.getByTestId('product-table-mobile')).toBeVisible();
	const mobile = page.getByTestId('product-table-mobile');
	await expect(mobile.getByTestId(`product-row-${PRODUCT_NO_QUALS.id}`)).toBeVisible();
	await expect(mobile).toContainText('PN-LIST-001');
});
