import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

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
					vendor_id: null
				}
			})
		});
	});
	// Catch-all first (lower LIFO priority), specific unread-count after (higher priority).
	await page.route('**/api/v1/activity/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/activity/unread-count', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ count: 0 })
		});
	});
});

async function mockAuthRole(
	page: Page,
	role: string,
	overrides: { display_name?: string; vendor_id?: string | null } = {}
) {
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'test-user-id',
					username: `test-${role.toLowerCase()}`,
					display_name: overrides.display_name ?? `Test ${role}`,
					role,
					status: 'ACTIVE',
					vendor_id: overrides.vendor_id ?? null
				}
			})
		});
	});
}

const PO_DRAFT = {
	id: 'uuid-draft',
	po_number: 'PO-20260316-0001',
	status: 'DRAFT',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-A',
	vendor_name: 'Vendor A',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-03-16T00:00:00+00:00',
	required_delivery_date: '2026-04-16T00:00:00+00:00',
	total_value: '1500',
	currency: 'USD'
};

const PO_PENDING = {
	id: 'uuid-pending',
	po_number: 'PO-20260316-0002',
	status: 'PENDING',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-B',
	vendor_name: 'Vendor B',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-03-16T00:00:00+00:00',
	required_delivery_date: '2026-04-16T00:00:00+00:00',
	total_value: '2500',
	currency: 'USD'
};

const PO_ACCEPTED = {
	id: 'uuid-accepted',
	po_number: 'PO-20260316-0003',
	status: 'ACCEPTED',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-C',
	vendor_name: 'Vendor C',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-03-16T00:00:00+00:00',
	required_delivery_date: '2026-04-16T00:00:00+00:00',
	total_value: '3500',
	currency: 'USD'
};

const EMPTY_REF_DATA = {
	currencies: [],
	incoterms: [],
	payment_terms: [],
	countries: [],
	ports: [],
	vendor_types: [
		{ code: 'PROCUREMENT', label: 'Procurement' },
		{ code: 'OPEX', label: 'OpEx' },
		{ code: 'FREIGHT', label: 'Freight' },
		{ code: 'MISCELLANEOUS', label: 'Miscellaneous' }
	],
	po_types: [
		{ code: 'PROCUREMENT', label: 'Procurement' },
		{ code: 'OPEX', label: 'OpEx' }
	]
};

async function mockCommonRoutes(page: Page) {
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/reference-data**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(EMPTY_REF_DATA)
		});
	});
}

test('PO list page loads and shows table', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				items: [PO_DRAFT, PO_PENDING, PO_ACCEPTED],
				total: 3,
				page: 1,
				page_size: 20
			})
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	await expect(page.locator('h1')).toContainText('Purchase Orders');

	const rows = page.locator('[data-testid^="po-row-"]');
	// Desktop and mobile DOM are both present; filter to the desktop tr variant.
	const desktopRows = page.locator('tbody tr[data-testid^="po-row-"]');
	await expect(desktopRows).toHaveCount(3);

	await expect(rows.first()).toBeVisible();
	await expect(page.locator('[data-testid="po-table"]')).toContainText('PO-20260316-0001');
	await expect(page.locator('[data-testid="po-table"]')).toContainText('PO-20260316-0002');
	await expect(page.locator('[data-testid="po-table"]')).toContainText('PO-20260316-0003');

	await expect(page.locator('[data-testid="po-table"]')).toContainText('Vendor A');
	await expect(page.locator('[data-testid="po-table"]')).toContainText('Vendor B');
	await expect(page.locator('[data-testid="po-table"]')).toContainText('Vendor C');

	// StatusPill renders capitalized status text
	await expect(page.locator('[data-testid="po-table"]')).toContainText('Draft');
	await expect(page.locator('[data-testid="po-table"]')).toContainText('Pending');
	await expect(page.locator('[data-testid="po-table"]')).toContainText('Accepted');
});

test('status filter narrows displayed POs', async ({ page }) => {
	let lastUrl = '';

	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		lastUrl = route.request().url();
		const url = new URL(route.request().url());
		const status = url.searchParams.get('status');

		if (status === 'DRAFT') {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ items: [PO_DRAFT], total: 1, page: 1, page_size: 20 })
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [PO_DRAFT, PO_PENDING, PO_ACCEPTED],
					total: 3,
					page: 1,
					page_size: 20
				})
			});
		}
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');
	await expect(page.locator('tbody tr[data-testid^="po-row-"]')).toHaveCount(3);

	await page.locator('[data-testid="po-filter-status"]').selectOption('DRAFT');
	await expect(page.locator('tbody tr[data-testid^="po-row-"]')).toHaveCount(1);
	expect(lastUrl).toContain('status=DRAFT');
});

test('click row navigates to detail', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		const url = route.request().url();
		// Detail page will also call /api/v1/po/{id}; return minimal valid response
		if (url.includes('/uuid-draft') && !url.match(/\/po\??/)) {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					...PO_DRAFT,
					ship_to_address: '',
					payment_terms: 'NET30',
					terms_and_conditions: '',
					incoterm: 'FOB',
					port_of_loading: 'Shanghai',
					port_of_discharge: 'Los Angeles',
					country_of_origin: 'CN',
					country_of_destination: 'US',
					line_items: [],
					rejection_history: [],
					created_at: '2026-03-16T00:00:00+00:00',
					updated_at: '2026-03-16T00:00:00+00:00'
				})
			});
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ items: [PO_DRAFT], total: 1, page: 1, page_size: 20 })
			});
		}
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	await page.locator('tbody tr[data-testid="po-row-uuid-draft"]').click();
	await page.waitForURL('**/po/uuid-draft');

	expect(page.url()).toContain('/po/uuid-draft');
});

test('empty list shows message', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await expect(page.locator('body')).toContainText('No purchase orders yet');
});

test('filter bar renders search input and dropdowns', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-filters"]');

	await expect(page.locator('[data-testid="po-filter-search"]')).toBeVisible();
	await expect(page.locator('[data-testid="po-filter-status"]')).toBeVisible();
	await expect(page.locator('[data-testid="po-filter-vendor"]')).toBeVisible();
	await expect(page.locator('[data-testid="po-filter-currency"]')).toBeVisible();
	await expect(page.locator('[data-testid="po-filter-marketplace"]')).toBeVisible();
	await expect(page.locator('[data-testid="po-filter-milestone"]')).toBeVisible();
});

test('pagination controls appear when total exceeds page size', async ({ page }) => {
	await mockCommonRoutes(page);
	const items = Array.from({ length: 20 }, (_, i) => ({
		...PO_DRAFT,
		id: `uuid-${i}`,
		po_number: `PO-2026-${String(i).padStart(4, '0')}`
	}));
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items, total: 45, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-pagination"]');

	await expect(page.locator('[data-testid="po-pagination"]')).toContainText(
		'Showing 1-20 of 45'
	);
	await expect(page.locator('[data-testid="po-pagination-next"]')).not.toBeDisabled();
});

test('URL state preserved on navigation', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		const url = new URL(route.request().url());
		const status = url.searchParams.get('status');
		const items = status === 'DRAFT' ? [PO_DRAFT] : [PO_DRAFT, PO_PENDING, PO_ACCEPTED];
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				items,
				total: items.length,
				page: 1,
				page_size: 20
			})
		});
	});

	await page.goto('/po?status=DRAFT&search=foo');
	await page.waitForSelector('[data-testid="po-filters"]');

	await expect(page.locator('[data-testid="po-filter-search"]')).toHaveValue('foo');
	await expect(page.locator('[data-testid="po-filter-status"]')).toHaveValue('DRAFT');
});

// ---------------------------------------------------------------------------
// Iteration 22 — Production column and milestone filter
// ---------------------------------------------------------------------------

const PO_ACCEPTED_PROCUREMENT = {
	id: 'uuid-accepted-proc',
	po_number: 'PO-20260401-0010',
	status: 'ACCEPTED',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-D',
	vendor_name: 'Vendor D',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	total_value: '8000',
	currency: 'USD',
	current_milestone: 'RAW_MATERIALS'
};

const PO_DRAFT_NO_MILESTONE = {
	id: 'uuid-draft-no-ms',
	po_number: 'PO-20260401-0011',
	status: 'DRAFT',
	po_type: 'PROCUREMENT',
	vendor_id: 'VENDOR-E',
	vendor_name: 'Vendor E',
	vendor_country: 'CN',
	buyer_name: 'TurboTonic Ltd',
	buyer_country: 'US',
	issued_date: '2026-04-01T00:00:00+00:00',
	required_delivery_date: '2026-05-01T00:00:00+00:00',
	total_value: '1000',
	currency: 'USD',
	current_milestone: null
};

test('PO list shows production column for accepted procurement PO', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				items: [PO_ACCEPTED_PROCUREMENT],
				total: 1,
				page: 1,
				page_size: 20
			})
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	// The Current Milestone column header must be present
	await expect(page.locator('thead')).toContainText('Current Milestone');
	// The milestone label for RAW_MATERIALS must appear in the row
	await expect(page.locator('tbody')).toContainText('Raw Materials');
});

test('PO list shows blank production cell for non-accepted PO', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				items: [PO_DRAFT_NO_MILESTONE],
				total: 1,
				page: 1,
				page_size: 20
			})
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	// A DRAFT PO with no milestone should not surface a milestone label.
	await expect(page.locator('tbody')).not.toContainText('Raw Materials');
});

test('milestone filter dropdown exists with milestone options', async ({ page }) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-filters"]');

	const milestoneSelect = page.locator('[data-testid="po-filter-milestone"]');
	await expect(milestoneSelect).toBeVisible();
	await expect(milestoneSelect).toContainText('Raw Materials');
	await expect(milestoneSelect).toContainText('Production Started');
	await expect(milestoneSelect).toContainText('QC Passed');
});

// ---------------------------------------------------------------------------
// Iter 076 — Phase 4.2 Tier 1 list revamp
// ---------------------------------------------------------------------------

test('filter bar exposes marketplace filter', async ({ page }) => {
	await mockCommonRoutes(page);
	const captured: string[] = [];
	await page.route('**/api/v1/po**', (route) => {
		captured.push(route.request().url());
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-filters"]');

	const marketplace = page.locator('[data-testid="po-filter-marketplace"]');
	await expect(marketplace).toBeVisible();
	await expect(marketplace).toContainText('Amazon US');
	await expect(marketplace).toContainText('Amazon EU');
	await expect(marketplace).toContainText('Walmart US');
	await expect(marketplace).toContainText('eBay US');
	// "All" option for unfiltered selection
	await expect(marketplace).toContainText('All Marketplaces');

	await marketplace.selectOption('AMAZON_US');

	await expect.poll(() => captured.some((u) => u.includes('marketplace=AMAZON_US'))).toBe(true);
	await expect.poll(() => page.url()).toContain('marketplace=AMAZON_US');
});

test('vendor filter hidden for VENDOR role', async ({ page }) => {
	await mockAuthRole(page, 'VENDOR', { display_name: 'Vendor User' });
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-filters"]');

	await expect(page.locator('[data-testid="po-filter-vendor"]')).toHaveCount(0);

	// Other four filters still render
	await expect(page.locator('[data-testid="po-filter-status"]')).toBeVisible();
	await expect(page.locator('[data-testid="po-filter-currency"]')).toBeVisible();
	await expect(page.locator('[data-testid="po-filter-marketplace"]')).toBeVisible();
	await expect(page.locator('[data-testid="po-filter-milestone"]')).toBeVisible();
});

test('PROCUREMENT_MANAGER sees no selection column and no New PO button', async ({
	page
}) => {
	await mockAuthRole(page, 'PROCUREMENT_MANAGER', { display_name: 'PM User' });
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [PO_DRAFT], total: 1, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	// No bulk-select checkbox in the row
	await expect(page.locator('[data-testid="po-row-select-uuid-draft"]')).toHaveCount(0);
	// No header action button
	await expect(page.locator('[data-testid="po-page-header-action"]')).toHaveCount(0);
});

test('FREIGHT_MANAGER sees no selection column', async ({ page }) => {
	await mockAuthRole(page, 'FREIGHT_MANAGER', { display_name: 'FM User' });
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [PO_DRAFT], total: 1, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	await expect(page.locator('[data-testid="po-row-select-uuid-draft"]')).toHaveCount(0);
	await expect(page.locator('[data-testid="po-page-header-action"]')).toHaveCount(0);
});

test('Partial pill renders for ACCEPTED with has_removed_line', async ({ page }) => {
	await mockCommonRoutes(page);
	const PO_PARTIAL = {
		...PO_ACCEPTED,
		id: 'uuid-partial',
		po_number: 'PO-20260316-PART',
		has_removed_line: true
	};
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				items: [PO_PARTIAL],
				total: 1,
				page: 1,
				page_size: 20
			})
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	const row = page.locator('tbody tr[data-testid="po-row-uuid-partial"]');
	await expect(row).toContainText('Accepted');
	await expect(row.locator('[data-testid="po-status-partial"]')).toBeVisible();
});

test('mobile reflow at 390px stacks rows as cards', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				items: [PO_DRAFT],
				total: 1,
				page: 1,
				page_size: 20
			})
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');

	const card = page.locator('div[data-testid="po-row-uuid-draft"]');
	await expect(card).toBeVisible();
	await expect(card).toHaveClass(/po-row-card/);
	// On mobile the desktop tr is hidden, so visible row count is the card.
	await expect(page.locator('[data-testid="po-row-uuid-draft"]:visible')).toHaveCount(1);
});

test('empty-after-filter does not show New PO CTA; empty-because-none-exist does', async ({
	page
}) => {
	await mockCommonRoutes(page);
	await page.route('**/api/v1/po**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});

	await page.goto('/po?status=DRAFT');
	await page.waitForSelector('[data-testid="po-filters"]');

	// Filtered empty state — no CTA
	await expect(page.locator('body')).toContainText('No matching POs');
	await expect(page.locator('[data-testid="po-empty-cta"]')).toHaveCount(0);

	// Clear the filter via the URL and re-load — table empty-because-none-exist
	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-filters"]');

	await expect(page.locator('body')).toContainText('No purchase orders yet');
	await expect(page.locator('[data-testid="po-empty-cta"]')).toBeVisible();
});

test('filter-refetch keeps prior rows visible with loading overlay', async ({ page }) => {
	await mockCommonRoutes(page);
	let requestCount = 0;
	await page.route('**/api/v1/po**', async (route) => {
		requestCount++;
		if (requestCount === 1) {
			// First load — return rows immediately.
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					items: [PO_DRAFT, PO_PENDING],
					total: 2,
					page: 1,
					page_size: 20
				})
			});
			return;
		}
		// Subsequent load — delay so the overlay is observable.
		await new Promise((r) => setTimeout(r, 800));
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				items: [PO_DRAFT],
				total: 1,
				page: 1,
				page_size: 20
			})
		});
	});

	await page.goto('/po');
	await page.waitForSelector('[data-testid="po-table"]');
	await expect(page.locator('tbody tr[data-testid^="po-row-"]')).toHaveCount(2);

	// Trigger a refetch by changing the status filter.
	await page.locator('[data-testid="po-filter-status"]').selectOption('DRAFT');

	// Mid-flight: prior rows still rendered AND overlay visible.
	await expect(page.locator('[data-testid="po-list-loading"]')).toBeVisible();
	await expect(page.locator('tbody tr[data-testid="po-row-uuid-draft"]')).toBeVisible();
	await expect(page.locator('tbody tr[data-testid="po-row-uuid-pending"]')).toBeVisible();

	// After the delay completes, the overlay disappears and rows update.
	await expect(page.locator('[data-testid="po-list-loading"]')).toHaveCount(0);
	await expect(page.locator('tbody tr[data-testid^="po-row-"]')).toHaveCount(1);
});
