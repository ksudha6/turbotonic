import { test, expect } from '@playwright/test';

// iter 101: permanent specs that pin the Phase 4 ports of /login, /register,
// /setup. Selectors are getByRole / getByLabel / getByTestId only. The
// existing dev-login.spec.ts (iter 079) and auth-flow.spec.ts cover the
// dev-login flow and unauthenticated-redirect contract; this file covers the
// new primitive-driven structure (PanelCard + FormField + Input + Button)
// and the register / setup happy paths.

const TEST_TOKEN = '11111111-2222-3333-4444-555555555555';

const PENDING_REGISTER_USER = {
	id: 'pending-user-id',
	username: 'newhire',
	display_name: 'New Hire',
	role: 'PROCUREMENT_MANAGER',
	status: 'PENDING'
};

const REGISTER_OPTIONS = {
	rp: { id: 'localhost', name: 'Vendor Portal' },
	user: {
		id: 'AAAAAA',
		name: 'newhire',
		displayName: 'New Hire'
	},
	challenge: 'AAAAAA',
	pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
	timeout: 60000
};

async function mockUnauthenticated(page: import('@playwright/test').Page) {
	await page.route('**/api/v1/auth/me', (route) =>
		route.fulfill({
			status: 401,
			contentType: 'application/json',
			body: JSON.stringify({ detail: 'Not authenticated' })
		})
	);
}

async function mockDevUsersDisabled(page: import('@playwright/test').Page) {
	await page.route('**/api/v1/auth/dev-users', (route) =>
		route.fulfill({
			status: 404,
			contentType: 'application/json',
			body: JSON.stringify({ detail: 'Not Found' })
		})
	);
}

// Stubs navigator.credentials.create / .get with deterministic responses so
// the WebAuthn-fronted register / login flows resolve in headless chromium
// without touching real platform authenticators. Mirrors the pattern used
// across the codebase for WebAuthn-bearing tests.
async function mockWebAuthn(page: import('@playwright/test').Page) {
	await page.addInitScript(() => {
		const fakeCredential = {
			id: 'fake-credential-id',
			rawId: new ArrayBuffer(8),
			type: 'public-key',
			response: {
				clientDataJSON: new ArrayBuffer(8),
				attestationObject: new ArrayBuffer(8),
				authenticatorData: new ArrayBuffer(8),
				signature: new ArrayBuffer(8)
			}
		};
		Object.defineProperty(window, 'PublicKeyCredential', {
			value: class {},
			configurable: true
		});
		Object.defineProperty(navigator, 'credentials', {
			value: {
				create: async () => fakeCredential,
				get: async () => fakeCredential
			},
			configurable: true
		});
	});
}

// ---------------------------------------------------------------------------
// /login
// ---------------------------------------------------------------------------

test('/login renders PanelCard with Vendor Portal heading and Sign in subtitle', async ({
	page
}) => {
	await mockUnauthenticated(page);
	await mockDevUsersDisabled(page);

	await page.goto('/login');

	await expect(page.getByRole('heading', { name: 'Vendor Portal' })).toBeVisible();
	await expect(page.getByText('Sign in to your account')).toBeVisible();
});

test('/login username field and submit button carry expected testids', async ({ page }) => {
	await mockUnauthenticated(page);
	await mockDevUsersDisabled(page);

	await page.goto('/login');

	await expect(page.getByTestId('login-username')).toBeVisible();
	await expect(page.getByTestId('login-submit')).toBeVisible();
	await expect(page.getByLabel('Username')).toBeVisible();
});

test('/login surfaces backend error inline via login-error testid', async ({ page }) => {
	await mockUnauthenticated(page);
	await mockDevUsersDisabled(page);
	await mockWebAuthn(page);

	await page.route('**/api/v1/auth/login/options', (route) =>
		route.fulfill({
			status: 404,
			contentType: 'application/json',
			body: JSON.stringify({ detail: 'No such user.' })
		})
	);

	await page.goto('/login');
	await page.getByTestId('login-username').fill('ghost');
	await page.getByTestId('login-submit').click();

	await expect(page.getByTestId('login-error')).toHaveText('No such user.');
});

// ---------------------------------------------------------------------------
// /register
// ---------------------------------------------------------------------------

test('/register without ?token shows invalid invite link error', async ({ page }) => {
	await mockUnauthenticated(page);

	await page.goto('/register');

	await expect(page.getByTestId('register-error')).toHaveText('Invalid invite link.');
	await expect(page.getByRole('link', { name: 'Go to sign in' })).toBeVisible();
});

test('/register?token=<valid> renders register card and submit button', async ({ page }) => {
	await mockUnauthenticated(page);

	await page.route('**/api/v1/auth/register/options', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: PENDING_REGISTER_USER, options: REGISTER_OPTIONS })
		})
	);

	await page.goto(`/register?token=${TEST_TOKEN}`);

	await expect(page.getByRole('heading', { name: 'Register Your Account' })).toBeVisible();
	await expect(page.getByText('Welcome, New Hire')).toBeVisible();
	await expect(page.getByTestId('register-submit')).toBeVisible();
});

test('/register form submit calls registerVerify with token from URL', async ({ page }) => {
	await mockUnauthenticated(page);
	await mockWebAuthn(page);

	await page.route('**/api/v1/auth/register/options', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: PENDING_REGISTER_USER, options: REGISTER_OPTIONS })
		})
	);

	let verifyPayload: { token?: string; credential?: unknown } | null = null;
	await page.route('**/api/v1/auth/register/verify', async (route) => {
		verifyPayload = route.request().postDataJSON() as {
			token?: string;
			credential?: unknown;
		} | null;
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: { ...PENDING_REGISTER_USER, status: 'ACTIVE' } })
		});
	});

	await page.goto(`/register?token=${TEST_TOKEN}`);
	await expect(page.getByTestId('register-submit')).toBeVisible();
	await page.getByTestId('register-submit').click();

	await expect.poll(() => verifyPayload?.token).toBe(TEST_TOKEN);
	expect(verifyPayload?.credential).toBeDefined();
});

// ---------------------------------------------------------------------------
// /setup
// ---------------------------------------------------------------------------

test('/setup renders PanelCard with two FormFields and submit button', async ({ page }) => {
	await mockUnauthenticated(page);

	await page.goto('/setup');

	await expect(page.getByRole('heading', { name: 'System Setup' })).toBeVisible();
	await expect(page.getByText('Create the first admin account')).toBeVisible();
	await expect(page.getByTestId('setup-username')).toBeVisible();
	await expect(page.getByTestId('setup-display-name')).toBeVisible();
	await expect(page.getByTestId('setup-submit')).toBeVisible();
});

test('/setup happy path bootstraps and redirects to /dashboard', async ({ page }) => {
	await mockUnauthenticated(page);
	await mockWebAuthn(page);

	// Catch-all registered FIRST so the more specific handlers below take
	// priority. Playwright resolves matching routes in reverse-registration
	// order; the catch-all here only fires for /dashboard's data fan-out
	// after the specific bootstrap and register/verify mocks have run.
	await page.route('**/api/v1/**', (route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
	);

	await page.route('**/api/v1/auth/bootstrap', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: { ...PENDING_REGISTER_USER, username: 'admin', display_name: 'Admin' },
				options: REGISTER_OPTIONS,
				invite_token: TEST_TOKEN
			})
		})
	);

	let verifyPayload: { token?: string } | null = null;
	await page.route('**/api/v1/auth/register/verify', async (route) => {
		verifyPayload = route.request().postDataJSON() as { token?: string } | null;
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				user: {
					...PENDING_REGISTER_USER,
					username: 'admin',
					display_name: 'Admin',
					status: 'ACTIVE'
				}
			})
		});
	});

	await page.goto('/setup');
	await page.getByTestId('setup-username').fill('admin');
	await page.getByTestId('setup-display-name').fill('Admin');
	await page.getByTestId('setup-submit').click();

	await expect.poll(() => verifyPayload?.token).toBe(TEST_TOKEN);
});

test('/setup shows already-configured panel when bootstrap reports admin exists', async ({
	page
}) => {
	await mockUnauthenticated(page);
	await mockWebAuthn(page);

	await page.route('**/api/v1/auth/bootstrap', (route) =>
		route.fulfill({
			status: 409,
			contentType: 'application/json',
			body: JSON.stringify({ detail: 'Admin already exists' })
		})
	);

	await page.goto('/setup');
	await page.getByTestId('setup-username').fill('admin');
	await page.getByTestId('setup-display-name').fill('Admin');
	await page.getByTestId('setup-submit').click();

	await expect(page.getByText('System already configured.')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Go to login' })).toBeVisible();
});
