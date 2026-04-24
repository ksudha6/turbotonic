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
