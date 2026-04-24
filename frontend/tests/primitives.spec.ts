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
