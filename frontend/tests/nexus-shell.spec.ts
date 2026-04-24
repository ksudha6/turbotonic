import { test, expect } from '@playwright/test';

function mockUser(page: import('@playwright/test').Page, role: string = 'ADMIN') {
	return page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					id: 'smoke',
					username: 'smoke',
					display_name: 'Smoke User',
					role,
					status: 'ACTIVE',
					vendor_id: null
				}
			})
		});
	});
}

function mockApiCatchAll(page: import('@playwright/test').Page) {
	return page.route('**/api/v1/**', (route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
	);
}

test('nexus shell renders ADMIN sidebar with all six items', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'ADMIN');
	await page.goto('/_smoke');
	const sidebar = page.getByTestId('ui-appshell-sidebar');
	await expect(sidebar.getByRole('link', { name: 'Dashboard' })).toBeVisible();
	await expect(sidebar.getByRole('link', { name: 'Purchase Orders' })).toBeVisible();
	await expect(sidebar.getByRole('link', { name: 'Invoices' })).toBeVisible();
	await expect(sidebar.getByRole('link', { name: 'Vendors' })).toBeVisible();
	await expect(sidebar.getByRole('link', { name: 'Products' })).toBeVisible();
	await expect(sidebar.getByRole('link', { name: 'Users' })).toBeVisible();
});

test('nexus shell hides Vendors for VENDOR role', async ({ page }) => {
	await mockApiCatchAll(page);
	await mockUser(page, 'VENDOR');
	await page.goto('/_smoke');
	const sidebar = page.getByTestId('ui-appshell-sidebar');
	await expect(sidebar.getByRole('link', { name: 'Vendors' })).toHaveCount(0);
	await expect(sidebar.getByRole('link', { name: 'Dashboard' })).toBeVisible();
});

test('nexus shell redirects unauthenticated requests to /login', async ({ page }) => {
	await page.route('**/api/v1/auth/me', (route) =>
		route.fulfill({ status: 401, contentType: 'application/json', body: '{}' })
	);
	await page.goto('/_smoke');
	await expect(page).toHaveURL(/\/login/);
});
