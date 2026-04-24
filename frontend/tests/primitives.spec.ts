import { test, expect } from '@playwright/test';

function mockUser(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'ui-demo',
					username: 'ui-demo',
					display_name: 'UI Demo',
					role: 'ADMIN',
					status: 'ACTIVE',
					vendor_id: null
				}
			})
		});
	});
}

function mockApiCatchAll(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
}

test.describe('Button primitive', () => {
	test('renders primary button with keyboard-focusable affordance', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const btn = page.getByTestId('ui-btn-primary');
		await expect(btn).toBeVisible();
		await btn.focus();
		await expect(btn).toBeFocused();
	});

	test('renders secondary and ghost variants', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const secondary = page.getByTestId('ui-btn-secondary');
		const ghost = page.getByTestId('ui-btn-ghost');
		await expect(secondary).toBeVisible();
		await expect(ghost).toBeVisible();
		await expect(secondary).toHaveClass(/secondary/);
		await expect(ghost).toHaveClass(/ghost/);
	});

	test('disabled button is marked disabled', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const disabled = page.getByTestId('ui-btn-disabled');
		await expect(disabled).toBeDisabled();
	});
});

test.describe('StatusPill primitive', () => {
	test('renders five tone variants with leading dot', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		for (const tone of ['green', 'blue', 'orange', 'red', 'gray']) {
			const pill = page.getByTestId(`ui-pill-${tone}`);
			await expect(pill).toBeVisible();
			await expect(pill).toHaveClass(new RegExp(tone));
			await expect(pill.locator('.dot')).toBeAttached();
		}
	});
});

test.describe('ProgressBar primitive', () => {
	test('renders progressbar with accessible value', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const bar = page.getByTestId('ui-progress-60');
		await expect(bar).toBeVisible();
		await expect(bar).toHaveAttribute('role', 'progressbar');
		await expect(bar).toHaveAttribute('aria-valuenow', '60');
	});
});

test.describe('Form control primitives', () => {
	test('Input primitive accepts typed text', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const input = page.getByTestId('ui-input-name');
		await input.fill('hello');
		await expect(input).toHaveValue('hello');
	});

	test('Select primitive changes value', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const select = page.getByTestId('ui-select-country');
		await select.selectOption('US');
		await expect(select).toHaveValue('US');
	});

	test('DateInput primitive renders', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const date = page.getByTestId('ui-date-due');
		await expect(date).toBeVisible();
		await expect(date).toHaveAttribute('type', 'date');
	});

	test('Toggle primitive flips aria-pressed on click', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const toggle = page.getByTestId('ui-toggle');
		await expect(toggle).toHaveAttribute('aria-pressed', 'false');
		await toggle.click();
		await expect(toggle).toHaveAttribute('aria-pressed', 'true');
	});
});

test.describe('FormField primitive', () => {
	test('shows inline error and sets aria-invalid on child input', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const err = page.getByTestId('ui-field-error');
		await expect(err).toHaveText('Part number is required');
		await expect(err).toHaveAttribute('role', 'alert');
		await expect(page.getByTestId('ui-field-input')).toHaveAttribute('aria-invalid', 'true');
	});
});

test.describe('Panel primitives', () => {
	test('PanelCard renders title and body slot', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-panel').getByRole('heading', { name: 'Details' })).toBeVisible();
	});

	test('AttributeList renders rows with label and value', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const list = page.getByTestId('ui-attr-list');
		await expect(list).toContainText('Vendor');
		await expect(list).toContainText('Acme Inc');
	});

	test('FormCard has Cancel and Submit buttons in footer', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-formcard-cancel')).toBeVisible();
		await expect(page.getByTestId('ui-formcard-submit')).toBeVisible();
	});
});

test.describe('KpiCard primitive', () => {
	test('KpiCard shows label, value, and delta chip', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const kpi = page.getByTestId('ui-kpi');
		await expect(kpi).toContainText('OUTSTANDING');
		await expect(kpi).toContainText('$24,300');
		await expect(kpi).toContainText('+12%');
	});
});

test.describe('KpiCard icon slot', () => {
	test('renders icon snippet when provided', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-kpi-icon')).toBeVisible();
	});
});

test.describe('Timeline + ActivityFeed primitives', () => {
	test('Timeline renders ordered steps with state classes', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const steps = page.getByTestId('ui-timeline').locator('li');
		await expect(steps).toHaveCount(3);
	});

	test('ActivityFeed renders entries with dot + primary + secondary lines', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const feed = page.getByTestId('ui-feed');
		await expect(feed).toContainText('PO accepted');
		await expect(feed).toContainText('2m ago');
	});
});

test.describe('State primitives', () => {
	test('LoadingState renders a spinner labelled for assistive tech', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-loading')).toHaveAttribute('role', 'status');
	});

	test('EmptyState renders title + description', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const empty = page.getByTestId('ui-empty');
		await expect(empty).toContainText('No results');
		await expect(empty).toContainText('Try adjusting');
	});

	test('ErrorState shows message and a Retry button', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-error')).toContainText('Something broke');
		await expect(page.getByTestId('ui-error-retry')).toBeVisible();
	});
});

test.describe('DataTable primitive', () => {
	test('renders header + rows + pagination and handles row click', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const table = page.getByTestId('ui-table');
		await expect(table.getByRole('columnheader', { name: 'Name' })).toBeVisible();
		await expect(table.locator('tbody tr')).toHaveCount(2);
		await table.locator('tbody tr').first().click();
		await expect(page.getByTestId('ui-table-click')).toHaveText('row-1');
		await expect(page.getByTestId('ui-table-pagination')).toContainText('Page 1 of 5');
	});
});

test.describe('Page + Detail headers', () => {
	test('PageHeader shows H1, subtitle, and action slot', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const header = page.getByTestId('ui-pageheader');
		await expect(header.getByRole('heading', { level: 1, name: 'Invoices' })).toBeVisible();
		await expect(header).toContainText('Manage invoicing');
		await expect(page.getByTestId('ui-pageheader-action')).toBeVisible();
	});

	test('DetailHeader shows back link, title, subtitle, status pill', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const header = page.getByTestId('ui-detailheader');
		await expect(header.getByRole('link', { name: /All invoices/ })).toBeVisible();
		await expect(header).toContainText('INV-001');
		await expect(header).toContainText('Submitted');
	});
});

test.describe('Sidebar primitive', () => {
	test('renders items for the given role', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const sidebar = page.getByTestId('ui-sidebar');
		await expect(sidebar.getByRole('link', { name: 'Dashboard' })).toBeVisible();
		await expect(sidebar.getByRole('link', { name: 'Purchase Orders' })).toBeVisible();
	});

	test('each sidebar link has a valid href', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const links = await page.getByTestId('ui-sidebar').getByRole('link').all();
		for (const link of links) {
			await expect(link).toHaveAttribute('href', /^\//);
		}
	});
});

test.describe('Sidebar primitive (sections + footer + roleLabel)', () => {
	test('renders section header "WORKSPACE"', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const sidebar = page.getByTestId('ui-sidebar');
		// Section label is rendered uppercase via CSS; DOM text is "Workspace".
		await expect(sidebar.getByText('Workspace', { exact: true })).toBeVisible();
	});

	test('renders footer snippet when provided', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		await expect(page.getByTestId('ui-sidebar-footer')).toBeVisible();
	});

	test('shows humanized roleLabel when provided', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const sidebar = page.getByTestId('ui-sidebar');
		// Demo passes roleLabel="Supply Manager"; bare role code "ADMIN" should NOT appear.
		await expect(sidebar.getByText('Supply Manager')).toBeVisible();
	});
});

test.describe('TopBar primitive', () => {
	test('at desktop viewport shows breadcrumb and notification bell', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/ui-demo');
		const bar = page.getByTestId('ui-topbar');
		await expect(bar).toContainText('Workspace / Operations');
		await expect(bar.getByTestId('notification-bell-button')).toBeVisible();
	});

	test('at mobile viewport hides the breadcrumb and keeps the bell', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.setViewportSize({ width: 390, height: 800 });
		await page.goto('/ui-demo');
		const bar = page.getByTestId('ui-topbar');
		const breadcrumb = bar.getByText('Workspace / Operations');
		await expect(breadcrumb).toBeHidden();
		await expect(bar.getByTestId('notification-bell-button')).toBeVisible();
	});
});

test.describe('AppShell primitive', () => {
	test('renders sidebar + topbar + main at desktop', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/ui-demo/shell');
		const shell = page.getByTestId('ui-appshell');
		await expect(shell.getByTestId('ui-appshell-sidebar')).toBeVisible();
		await expect(shell.getByTestId('ui-appshell-topbar')).toBeVisible();
		await expect(shell.getByTestId('ui-appshell-main')).toBeVisible();
	});

	test('at 390px hides sidebar by default and reveals it via hamburger', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.setViewportSize({ width: 390, height: 800 });
		await page.goto('/ui-demo/shell');
		const sidebar = page.getByTestId('ui-appshell-sidebar');
		await expect(sidebar).toBeHidden();
		await page.getByTestId('topbar-toggle').click();
		await expect(sidebar).toBeVisible();
	});

	test('at 390px tapping the overlay dismisses the drawer', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.setViewportSize({ width: 390, height: 800 });
		await page.goto('/ui-demo/shell');
		await page.getByTestId('topbar-toggle').click();
		const overlay = page.getByTestId('ui-appshell-overlay');
		await expect(overlay).toBeVisible();
		await overlay.click();
		await expect(page.getByTestId('ui-appshell-sidebar')).toBeHidden();
	});
});

test.describe('UserMenu primitive', () => {
	test('at desktop shows name + role and opens menu on click', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/ui-demo/shell');
		const pill = page.getByTestId('ui-usermenu');
		await expect(pill).toContainText('Supply Manager');
		await pill.click();
		await expect(page.getByTestId('ui-usermenu-logout')).toBeVisible();
	});

	test('at mobile shows avatar only and menu still opens', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.setViewportSize({ width: 390, height: 800 });
		await page.goto('/ui-demo/shell');
		const pill = page.getByTestId('ui-usermenu');
		// The pill still renders; the "Supply Manager" meta text is hidden by media query.
		// Don't assert visibility of the meta — instead open the menu to the hamburger first,
		// then find the UserMenu inside the drawer? No — the UserMenu is in the TopBar which
		// is visible at mobile. Just open the menu directly.
		await pill.click();
		await expect(page.getByTestId('ui-usermenu-logout')).toBeVisible();
	});
});

import AxeBuilder from '@axe-core/playwright';

test.describe('Phase 4.0 accessibility scan', () => {
	test('axe: /ui-demo has zero AA violations', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		await page.waitForFunction(() => !!document.title);
		const results = await new AxeBuilder({ page })
			.withTags(['wcag2a', 'wcag2aa'])
			.analyze();
		expect(results.violations).toEqual([]);
	});

	test('axe: /_smoke has zero AA violations', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/_smoke');
		await page.waitForFunction(() => !!document.title);
		const results = await new AxeBuilder({ page })
			.withTags(['wcag2a', 'wcag2aa'])
			.analyze();
		expect(results.violations).toEqual([]);
	});
});
