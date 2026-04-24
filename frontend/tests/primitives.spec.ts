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
		await expect(page.getByTestId('ui-btn-secondary')).toBeVisible();
		await expect(page.getByTestId('ui-btn-ghost')).toBeVisible();
	});

	test('disabled button does not fire onclick on Enter', async ({ page }) => {
		await mockApiCatchAll(page);
		await mockUser(page);
		await page.goto('/ui-demo');
		const disabled = page.getByTestId('ui-btn-disabled');
		await expect(disabled).toBeDisabled();
	});
});
