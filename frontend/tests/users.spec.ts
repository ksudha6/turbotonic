import { test, expect } from '@playwright/test';
import type { Page, Route } from '@playwright/test';

// Iter 100 — ADMIN /users page. Selectors are testid / role / label only per
// CLAUDE.md selector policy. Test data extracted to module-level constants so
// setup and assertions read from the same source.

type UserFixture = {
	id: string;
	username: string;
	display_name: string;
	role: string;
	status: string;
	vendor_id: string | null;
	email: string | null;
};

const ADMIN_USER: UserFixture = {
	id: 'admin-id',
	username: 'alice',
	display_name: 'Alice Admin',
	role: 'ADMIN',
	status: 'ACTIVE',
	vendor_id: null,
	email: 'alice@example.com'
};

const VENDOR_USER: UserFixture = {
	id: 'carol-id',
	username: 'carol',
	display_name: 'Carol Vendor',
	role: 'VENDOR',
	status: 'ACTIVE',
	vendor_id: 'vendor-1',
	email: null
};

const USER_ACTIVE_SM: UserFixture = {
	id: 'sm-1',
	username: 'erin',
	display_name: 'Erin SM',
	role: 'SM',
	status: 'ACTIVE',
	vendor_id: null,
	email: 'erin@example.com'
};

const USER_INACTIVE_SM: UserFixture = {
	id: 'sm-2',
	username: 'gary',
	display_name: 'Gary Gone',
	role: 'SM',
	status: 'INACTIVE',
	vendor_id: null,
	email: null
};

const USER_PENDING_VENDOR: UserFixture = {
	id: 'vendor-pending-1',
	username: 'henry',
	display_name: 'Henry Pending',
	role: 'VENDOR',
	status: 'PENDING',
	vendor_id: 'vendor-1',
	email: null
};

const ALL_USERS = [ADMIN_USER, USER_ACTIVE_SM, USER_INACTIVE_SM, USER_PENDING_VENDOR];

const ACTIVE_VENDOR_ROW = {
	id: 'vendor-1',
	name: 'Acme Corp',
	country: 'CN',
	status: 'ACTIVE',
	vendor_type: 'PROCUREMENT',
	address: '',
	account_details: ''
};

const FRESH_INVITE_TOKEN = 'token-fresh-uuid-1';
const RESET_TOKEN = 'token-reset-uuid-2';
const REISSUED_TOKEN = 'token-reissue-uuid-3';

// Filter the seed list the way the backend does so the table renders the
// matching rows after a filter change. Mock dispatcher reads ?status= / ?role=.
function applyFilters(
	rows: UserFixture[],
	status: string | null,
	role: string | null
): UserFixture[] {
	return rows.filter((u) => {
		if (status && u.status !== status) return false;
		if (role && u.role !== role) return false;
		return true;
	});
}

type UsersPageMocks = {
	users: UserFixture[];
	currentUser?: UserFixture;
	inviteResponse?: { user: UserFixture; invite_token: string };
	inviteStatus?: number;
	inviteDetail?: string;
	patchOverride?: (route: Route) => void;
	deactivateStatus?: number;
	deactivateDetail?: string;
	resetResponse?: { user: UserFixture; invite_token: string };
	reissueResponse?: { user: UserFixture; invite_token: string };
};

async function setupUsersPage(page: Page, opts: UsersPageMocks) {
	const currentUser = opts.currentUser ?? ADMIN_USER;
	let usersList = [...opts.users];

	// Catch-all is registered first so per-path routes take LIFO priority.
	await page.route('**/api/v1/**', (route) => {
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
	});
	await page.route('**/api/v1/auth/me', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: currentUser })
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
	await page.route('**/api/v1/vendors**', (route) => {
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([ACTIVE_VENDOR_ROW])
		});
	});

	// 8 user endpoints. Playwright routes are LIFO; routes registered later win
	// the match. List + by-id regex are registered first; the more-specific
	// /invite + action paths are registered last so they take priority over
	// the byId regex (which would otherwise match /users/invite as id=invite).
	await page.route('**/api/v1/users/*/deactivate', (route) => {
		if (opts.deactivateStatus && opts.deactivateStatus !== 200) {
			route.fulfill({
				status: opts.deactivateStatus,
				contentType: 'application/json',
				body: JSON.stringify({ detail: opts.deactivateDetail ?? 'deactivate failed' })
			});
			return;
		}
		const id = new URL(route.request().url()).pathname.split('/').slice(-2)[0];
		const target = usersList.find((u) => u.id === id);
		if (!target) {
			route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
			return;
		}
		const updated = { ...target, status: 'INACTIVE' };
		usersList = usersList.map((u) => (u.id === id ? updated : u));
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: updated })
		});
	});

	await page.route('**/api/v1/users/*/reactivate', (route) => {
		const id = new URL(route.request().url()).pathname.split('/').slice(-2)[0];
		const target = usersList.find((u) => u.id === id);
		if (!target) {
			route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
			return;
		}
		const updated = { ...target, status: 'ACTIVE' };
		usersList = usersList.map((u) => (u.id === id ? updated : u));
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: updated })
		});
	});

	await page.route('**/api/v1/users/*/reset-credentials', (route) => {
		const id = new URL(route.request().url()).pathname.split('/').slice(-2)[0];
		const target = usersList.find((u) => u.id === id);
		if (!target) {
			route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
			return;
		}
		const updated = { ...target, status: 'PENDING' };
		usersList = usersList.map((u) => (u.id === id ? updated : u));
		const body = opts.resetResponse ?? { user: updated, invite_token: RESET_TOKEN };
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(body)
		});
	});

	await page.route('**/api/v1/users/*/reissue-invite', (route) => {
		const id = new URL(route.request().url()).pathname.split('/').slice(-2)[0];
		const target = usersList.find((u) => u.id === id);
		if (!target) {
			route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
			return;
		}
		const body = opts.reissueResponse ?? { user: target, invite_token: REISSUED_TOKEN };
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(body)
		});
	});

	// PATCH and GET-by-id share the /api/v1/users/{id} path.
	await page.route(/\/api\/v1\/users\/[^/]+$/, (route) => {
		if (route.request().method() === 'PATCH') {
			if (opts.patchOverride) {
				opts.patchOverride(route);
				return;
			}
			const id = new URL(route.request().url()).pathname.split('/').slice(-1)[0];
			const target = usersList.find((u) => u.id === id);
			if (!target) {
				route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
				return;
			}
			const body = route.request().postDataJSON() as {
				display_name?: string;
				email?: string | null;
			};
			const updated = {
				...target,
				display_name: body.display_name ?? target.display_name,
				email: 'email' in body ? body.email ?? null : target.email
			};
			usersList = usersList.map((u) => (u.id === id ? updated : u));
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ user: updated })
			});
			return;
		}
		// GET single
		const id = new URL(route.request().url()).pathname.split('/').slice(-1)[0];
		const target = usersList.find((u) => u.id === id);
		if (!target) {
			route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
			return;
		}
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: target })
		});
	});

	// LIST: matches /api/v1/users and /api/v1/users/ (with or without trailing slash + query).
	await page.route(/\/api\/v1\/users\/?(\?.*)?$/, (route) => {
		if (route.request().method() !== 'GET') {
			route.fallback();
			return;
		}
		const url = new URL(route.request().url());
		const status = url.searchParams.get('status');
		const role = url.searchParams.get('role');
		const filtered = applyFilters(usersList, status, role);
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ users: filtered })
		});
	});

	// /invite is registered LAST so it wins over the byId regex (which matches
	// /api/v1/users/invite with id=invite otherwise).
	await page.route('**/api/v1/users/invite', (route) => {
		if (opts.inviteStatus && opts.inviteStatus !== 200) {
			route.fulfill({
				status: opts.inviteStatus,
				contentType: 'application/json',
				body: JSON.stringify({ detail: opts.inviteDetail ?? 'invite failed' })
			});
			return;
		}
		const defaultUser: UserFixture = {
			id: 'invited-id',
			username: 'frank',
			display_name: 'Frank New',
			role: 'SM',
			status: 'PENDING',
			vendor_id: null,
			email: null
		};
		const body = opts.inviteResponse ?? { user: defaultUser, invite_token: FRESH_INVITE_TOKEN };
		// Splice the new user into the list so the post-invite refetch shows the row.
		usersList = [...usersList, body.user];
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(body)
		});
	});
}

// ---------------------------------------------------------------------------
// Page mount + permission guard
// ---------------------------------------------------------------------------

test('users page mounts under (nexus) AppShell for ADMIN', async ({ page }) => {
	await setupUsersPage(page, { users: ALL_USERS });
	await page.goto('/users');
	await expect(page.getByTestId('ui-appshell-sidebar')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Users', level: 1 })).toBeVisible();
});

test('non-ADMIN role redirects to /dashboard', async ({ page }) => {
	await setupUsersPage(page, { users: ALL_USERS, currentUser: VENDOR_USER });
	await page.goto('/users');
	await page.waitForURL(/\/dashboard/);
});

// ---------------------------------------------------------------------------
// List rendering + filters
// ---------------------------------------------------------------------------

test('ADMIN list renders mixed-status rows with their pills', async ({ page }) => {
	await setupUsersPage(page, { users: ALL_USERS });
	await page.goto('/users');

	const desktop = page.getByTestId('user-table-desktop');
	await expect(desktop.getByTestId(`user-row-${ADMIN_USER.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`user-row-${USER_ACTIVE_SM.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`user-row-${USER_INACTIVE_SM.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`user-row-${USER_PENDING_VENDOR.id}`)).toBeVisible();

	await expect(desktop.getByTestId(`user-row-status-${ADMIN_USER.id}`)).toContainText('Active');
	await expect(desktop.getByTestId(`user-row-status-${USER_INACTIVE_SM.id}`)).toContainText(
		'Inactive'
	);
	await expect(desktop.getByTestId(`user-row-status-${USER_PENDING_VENDOR.id}`)).toContainText(
		'Pending'
	);
});

test('status filter narrows to PENDING rows only', async ({ page }) => {
	await setupUsersPage(page, { users: ALL_USERS });
	await page.goto('/users');

	const desktop = page.getByTestId('user-table-desktop');
	await expect(desktop.getByTestId(`user-row-${ADMIN_USER.id}`)).toBeVisible();

	await page.getByTestId('user-filter-status').selectOption('PENDING');

	await expect(desktop.getByTestId(`user-row-${USER_PENDING_VENDOR.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`user-row-${ADMIN_USER.id}`)).toHaveCount(0);
	await expect(desktop.getByTestId(`user-row-${USER_ACTIVE_SM.id}`)).toHaveCount(0);
});

test('role filter narrows to VENDOR rows only', async ({ page }) => {
	await setupUsersPage(page, { users: ALL_USERS });
	await page.goto('/users');

	await page.getByTestId('user-filter-role').selectOption('VENDOR');
	const desktop = page.getByTestId('user-table-desktop');
	await expect(desktop.getByTestId(`user-row-${USER_PENDING_VENDOR.id}`)).toBeVisible();
	await expect(desktop.getByTestId(`user-row-${ADMIN_USER.id}`)).toHaveCount(0);
	await expect(desktop.getByTestId(`user-row-${USER_ACTIVE_SM.id}`)).toHaveCount(0);
});

test('empty state appears when filters return no rows', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER] });
	await page.goto('/users');
	await expect(page.getByTestId('user-table-desktop')).toBeVisible();
	await page.getByTestId('user-filter-role').selectOption('VENDOR');
	await expect(page.getByText('No matching users')).toBeVisible();
});

test('error+retry on list fetch failure', async ({ page }) => {
	let attempt = 0;
	// Override the catch-all + me/activity first.
	await page.route('**/api/v1/**', (route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
	);
	await page.route('**/api/v1/auth/me', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ user: ADMIN_USER })
		})
	);
	await page.route('**/api/v1/activity/**', (route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
	);
	await page.route(/\/api\/v1\/users\/?(\?.*)?$/, (route) => {
		attempt += 1;
		if (attempt === 1) {
			route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' });
		} else {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ users: [ADMIN_USER] })
			});
		}
	});

	await page.goto('/users');
	await expect(page.getByRole('alert')).toBeVisible();
	await page.getByRole('button', { name: /retry/i }).click();
	await expect(page.getByTestId(`user-row-${ADMIN_USER.id}`).first()).toBeVisible();
});

// ---------------------------------------------------------------------------
// Invite flow
// ---------------------------------------------------------------------------

test('invite flow opens modal, submits, shows InviteLinkPanel and refetches', async ({ page }) => {
	const newUser: UserFixture = {
		id: 'invited-id',
		username: 'newbie',
		display_name: 'New B',
		role: 'SM',
		status: 'PENDING',
		vendor_id: null,
		email: null
	};
	await setupUsersPage(page, {
		users: [ADMIN_USER],
		inviteResponse: { user: newUser, invite_token: FRESH_INVITE_TOKEN }
	});
	await page.goto('/users');

	await page.getByTestId('user-page-header-action').click();
	await expect(page.getByTestId('user-invite-modal')).toBeVisible();
	await page.getByTestId('user-invite-username').fill(newUser.username);
	await page.getByTestId('user-invite-role').selectOption('SM');
	await page.getByTestId('user-invite-display-name').fill(newUser.display_name);
	await page.getByTestId('user-invite-submit').click();

	await expect(page.getByTestId('user-invite-modal')).toHaveCount(0);
	await expect(page.getByTestId('invite-link-panel')).toBeVisible();
	await expect(page.getByTestId('invite-link-url')).toContainText(FRESH_INVITE_TOKEN);
	await expect(page.getByTestId('invite-link-url')).toContainText('/register?token=');

	// Refetch surfaces the new row.
	await expect(page.getByTestId(`user-row-${newUser.id}`).first()).toBeVisible();
});

test('invite validation blocks submit when username is empty', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER] });
	await page.goto('/users');
	await page.getByTestId('user-page-header-action').click();
	// Role is also required, but the username error fires too. Filling role narrows
	// the assertion to a single error.
	await page.getByTestId('user-invite-role').selectOption('SM');
	await page.getByTestId('user-invite-submit').click();
	await expect(page.getByTestId('user-invite-username-field-error')).toBeVisible();
	await expect(page.getByTestId('user-invite-modal')).toBeVisible();
});

test('invite 409 on duplicate username renders inline error', async ({ page }) => {
	const conflictMessage = 'Username already taken';
	await setupUsersPage(page, {
		users: [ADMIN_USER],
		inviteStatus: 409,
		inviteDetail: conflictMessage
	});
	await page.goto('/users');
	await page.getByTestId('user-page-header-action').click();
	await page.getByTestId('user-invite-username').fill('alice');
	await page.getByTestId('user-invite-role').selectOption('SM');
	await page.getByTestId('user-invite-submit').click();

	await expect(page.getByTestId('user-invite-error')).toContainText(conflictMessage);
	await expect(page.getByTestId('user-invite-modal')).toBeVisible();
});

test('invite vendor field appears only when role is VENDOR', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER] });
	await page.goto('/users');
	await page.getByTestId('user-page-header-action').click();
	await expect(page.getByTestId('user-invite-vendor-field')).toHaveCount(0);
	await page.getByTestId('user-invite-role').selectOption('VENDOR');
	await expect(page.getByTestId('user-invite-vendor-field')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Edit flow
// ---------------------------------------------------------------------------

test('edit flow updates display_name and reflects in row', async ({ page }) => {
	const newDisplayName = 'Erin Renamed';
	await setupUsersPage(page, { users: [ADMIN_USER, USER_ACTIVE_SM] });
	await page.goto('/users');

	const desktop = page.getByTestId('user-table-desktop');
	await desktop.getByTestId(`user-row-edit-${USER_ACTIVE_SM.id}`).click();
	await expect(page.getByTestId('user-edit-modal')).toBeVisible();
	await page.getByTestId('user-edit-display-name').fill(newDisplayName);
	await page.getByTestId('user-edit-submit').click();

	await expect(page.getByTestId('user-edit-modal')).toHaveCount(0);
	await expect(desktop.getByTestId(`user-row-${USER_ACTIVE_SM.id}`)).toContainText(newDisplayName);
});

test('edit blank-email path sends explicit null and clears the cell', async ({ page }) => {
	let lastPatchBody: { display_name?: string; email?: string | null } | null = null;
	await setupUsersPage(page, {
		users: [ADMIN_USER, USER_ACTIVE_SM],
		patchOverride: (route) => {
			lastPatchBody = route.request().postDataJSON() as typeof lastPatchBody;
			const updated = {
				...USER_ACTIVE_SM,
				display_name: lastPatchBody?.display_name ?? USER_ACTIVE_SM.display_name,
				email: 'email' in (lastPatchBody ?? {}) ? lastPatchBody!.email ?? null : USER_ACTIVE_SM.email
			};
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ user: updated })
			});
		}
	});
	await page.goto('/users');

	const desktop = page.getByTestId('user-table-desktop');
	await desktop.getByTestId(`user-row-edit-${USER_ACTIVE_SM.id}`).click();
	await page.getByTestId('user-edit-email').fill('');
	await page.getByTestId('user-edit-submit').click();

	await expect(page.getByTestId('user-edit-modal')).toHaveCount(0);
	expect(lastPatchBody).not.toBeNull();
	expect(lastPatchBody!.email).toBeNull();
	await expect(desktop.getByTestId(`user-row-email-${USER_ACTIVE_SM.id}`)).toHaveText('');
});

// ---------------------------------------------------------------------------
// Deactivate / Reactivate
// ---------------------------------------------------------------------------

test('deactivate flow flips ACTIVE row to INACTIVE and swaps action', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER, USER_ACTIVE_SM] });
	await page.goto('/users');

	const desktop = page.getByTestId('user-table-desktop');
	await desktop.getByTestId(`user-row-deactivate-${USER_ACTIVE_SM.id}`).click();
	await expect(page.getByTestId('user-action-confirm')).toBeVisible();
	await page.getByTestId('user-action-submit').click();

	await expect(page.getByTestId('user-action-confirm')).toHaveCount(0);
	await expect(desktop.getByTestId(`user-row-status-${USER_ACTIVE_SM.id}`)).toContainText(
		'Inactive'
	);
	await expect(desktop.getByTestId(`user-row-reactivate-${USER_ACTIVE_SM.id}`)).toBeVisible();
});

test('deactivate self-self-409 surfaces the server message inline', async ({ page }) => {
	const selfMessage = 'cannot deactivate yourself';
	await setupUsersPage(page, {
		users: [ADMIN_USER, USER_ACTIVE_SM],
		deactivateStatus: 409,
		deactivateDetail: selfMessage
	});
	await page.goto('/users');

	const desktop = page.getByTestId('user-table-desktop');
	await desktop.getByTestId(`user-row-deactivate-${ADMIN_USER.id}`).click();
	await page.getByTestId('user-action-submit').click();

	await expect(page.getByTestId('user-action-error')).toContainText(selfMessage);
	await expect(page.getByTestId('user-action-confirm')).toBeVisible();
});

test('reactivate flow flips INACTIVE row to ACTIVE', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER, USER_INACTIVE_SM] });
	await page.goto('/users');
	const desktop = page.getByTestId('user-table-desktop');
	await desktop.getByTestId(`user-row-reactivate-${USER_INACTIVE_SM.id}`).click();
	await expect(desktop.getByTestId(`user-row-status-${USER_INACTIVE_SM.id}`)).toContainText(
		'Active'
	);
});

// ---------------------------------------------------------------------------
// Reset credentials / Reissue invite
// ---------------------------------------------------------------------------

test('reset credentials flow renders InviteLinkPanel and flips row to PENDING', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER, USER_ACTIVE_SM] });
	await page.goto('/users');

	const desktop = page.getByTestId('user-table-desktop');
	await desktop.getByTestId(`user-row-reset-${USER_ACTIVE_SM.id}`).click();
	await page.getByTestId('user-action-submit').click();

	await expect(page.getByTestId('invite-link-panel')).toBeVisible();
	await expect(page.getByTestId('invite-link-url')).toContainText(RESET_TOKEN);
	await expect(desktop.getByTestId(`user-row-status-${USER_ACTIVE_SM.id}`)).toContainText('Pending');
});

test('reissue invite flow renders InviteLinkPanel and keeps PENDING', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER, USER_PENDING_VENDOR] });
	await page.goto('/users');

	const desktop = page.getByTestId('user-table-desktop');
	await desktop.getByTestId(`user-row-reissue-${USER_PENDING_VENDOR.id}`).click();
	await page.getByTestId('user-action-submit').click();

	await expect(page.getByTestId('invite-link-panel')).toBeVisible();
	await expect(page.getByTestId('invite-link-url')).toContainText(REISSUED_TOKEN);
	await expect(desktop.getByTestId(`user-row-status-${USER_PENDING_VENDOR.id}`)).toContainText(
		'Pending'
	);
});

// ---------------------------------------------------------------------------
// Action visibility
// ---------------------------------------------------------------------------

test('reset-credentials hidden on PENDING rows', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER, USER_PENDING_VENDOR] });
	await page.goto('/users');
	const desktop = page.getByTestId('user-table-desktop');
	await expect(desktop.getByTestId(`user-row-reset-${USER_PENDING_VENDOR.id}`)).toHaveCount(0);
});

test('reissue-invite hidden on ACTIVE and INACTIVE rows', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER, USER_ACTIVE_SM, USER_INACTIVE_SM] });
	await page.goto('/users');
	const desktop = page.getByTestId('user-table-desktop');
	await expect(desktop.getByTestId(`user-row-reissue-${USER_ACTIVE_SM.id}`)).toHaveCount(0);
	await expect(desktop.getByTestId(`user-row-reissue-${USER_INACTIVE_SM.id}`)).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Mobile
// ---------------------------------------------------------------------------

test('mobile (390px) renders user cards instead of desktop table', async ({ page }) => {
	await setupUsersPage(page, { users: [ADMIN_USER, USER_PENDING_VENDOR] });
	await page.setViewportSize({ width: 390, height: 844 });
	await page.goto('/users');

	const mobile = page.getByTestId('user-table-mobile');
	await expect(mobile).toBeVisible();
	await expect(mobile.getByTestId(`user-row-${ADMIN_USER.id}`)).toBeVisible();
	await expect(page.getByTestId('user-filters-toggle')).toBeVisible();
});
