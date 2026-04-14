# Iteration 033 -- Frontend auth flow

## Context

The backend enforces auth (iter 030), role guards (iter 031), and vendor scoping (iter 032), but the frontend has no auth awareness. All 11 pages load without checking identity, so every API call now returns 401. This iteration adds a login page with WebAuthn passkey flow, a session check in `+layout.svelte` that redirects unauthenticated users to `/login`, and a logout flow. After this, the current user object is available in layout context for role-conditional rendering (iter 034).

## JTBD (Jobs To Be Done)

- When I open the app without a session, I want to be redirected to the login page, so that I must authenticate before using any feature
- When I am on the login page, I want to register a new passkey or authenticate with an existing one, so that I can access the system
- When I am logged in, I want every page to know who I am, so that role-conditional rendering (iter 034) can use my identity
- When I click logout, I want my session to end and be returned to the login page, so that no one else can use my session

## Tasks

### Login page
- [ ] Create `frontend/src/routes/login/+page.svelte`
  - Two modes: Register and Login (tab or toggle)
  - Register mode: username, display_name, role dropdown (SM/VENDOR/QUALITY_LAB/FREIGHT_MANAGER), vendor dropdown (shown only when role=VENDOR, populated from /api/v1/vendors/), register button
  - Login mode: username field, login button
  - Register flow:
    1. POST /api/v1/auth/register/options with {username, display_name, role, vendor_id?}
    2. Call `navigator.credentials.create()` with returned options
    3. POST /api/v1/auth/register/verify with credential response
    4. On success: redirect to /dashboard
  - Login flow:
    1. POST /api/v1/auth/login/options with {username}
    2. Call `navigator.credentials.get()` with returned options
    3. POST /api/v1/auth/login/verify with auth response
    4. On success: redirect to /dashboard
  - Error handling: display error messages inline (e.g., "Username already taken", "Passkey not recognized", "WebAuthn not supported by this browser")
  - WebAuthn browser support check: if `window.PublicKeyCredential` is undefined, show "WebAuthn is not supported in this browser"

### WebAuthn helper module
- [ ] Create `frontend/src/lib/webauthn.ts`
  - `startRegistration(options)` -- converts base64url fields to ArrayBuffer, calls `navigator.credentials.create()`, converts response back to base64url for server
  - `startAuthentication(options)` -- converts base64url fields to ArrayBuffer, calls `navigator.credentials.get()`, converts response back to base64url for server
  - Handle ArrayBuffer <-> base64url encoding (WebAuthn uses binary data, JSON API uses base64url strings)

### Auth API client
- [ ] Create `frontend/src/lib/auth.ts`
  - `registerOptions(username, display_name, role, vendor_id?)` -- POST /api/v1/auth/register/options
  - `registerVerify(credential)` -- POST /api/v1/auth/register/verify
  - `loginOptions(username)` -- POST /api/v1/auth/login/options
  - `loginVerify(credential)` -- POST /api/v1/auth/login/verify
  - `logout()` -- POST /api/v1/auth/logout
  - `me()` -- GET /api/v1/auth/me, returns user or null
  - All functions use fetch with `credentials: 'include'` for cookie handling

### User type definition
- [ ] Create `frontend/src/lib/types/user.ts` (or add to existing types file)
  - `type UserRole = 'SM' | 'VENDOR' | 'QUALITY_LAB' | 'FREIGHT_MANAGER'`
  - `type User = { id: string, username: string, display_name: string, role: UserRole, vendor_id: string | null }`

### Layout: session check and user context
- [ ] Update `frontend/src/routes/+layout.svelte` (or create `+layout.ts` / `+layout.server.ts`)
  - On layout load: call `GET /api/v1/auth/me`
  - If 401 and current route is NOT /login: redirect to /login
  - If valid user: store in layout context (Svelte context API or page store)
  - Make current user accessible to all child pages via `getContext('user')` or `$page.data.user`
- [ ] The /login route must NOT trigger the auth redirect (avoid redirect loop)

### Logout flow
- [ ] Add logout button to the app layout (header/nav area)
  - Calls `POST /api/v1/auth/logout`
  - On success: redirect to /login
  - Clear any client-side user state

### API fetch wrapper update
- [ ] Ensure all existing API calls include `credentials: 'include'` so the session cookie is sent
  - Check how existing pages make API calls (likely fetch in load functions or onMount)
  - If there is a shared fetch utility, add credentials there
  - If not, add credentials to each fetch call or create a shared wrapper

### Handle 401 in API calls
- [ ] Create or update a shared fetch wrapper that intercepts 401 responses
  - On 401: redirect to /login (session expired while using the app)
  - Avoid redirect loops (don't redirect if already on /login)

### Tests (permanent)
- [ ] `frontend/tests/auth-flow.spec.ts` (Playwright)
  - Visiting /dashboard without a session redirects to /login
  - Visiting /po without a session redirects to /login
  - Visiting /login does not redirect (no loop)
  - After login (mock WebAuthn -- Playwright cannot do real passkeys without virtual authenticator setup), user lands on /dashboard
  - After logout, visiting /dashboard redirects to /login
  - Note: full WebAuthn flow requires Playwright's `cdpSession.send('WebAuthn.enable')` and virtual authenticator. If too complex for permanent tests, test the redirect behavior with mocked /api/v1/auth/me responses instead.

### Tests (scratch)
- [ ] Screenshot: login page in both register and login modes
- [ ] Screenshot: redirect from /dashboard to /login when unauthenticated
- [ ] Screenshot: logged-in state with user info visible in nav/header
- [ ] Screenshot: post-logout redirect to /login

## Acceptance criteria
- [ ] /login page renders with register and login modes
- [ ] Register mode shows username, display_name, role dropdown; shows vendor dropdown only when role=VENDOR
- [ ] WebAuthn registration calls navigator.credentials.create() with server options, then verifies with server
- [ ] WebAuthn login calls navigator.credentials.get() with server options, then verifies with server
- [ ] Successful register/login sets session cookie and redirects to /dashboard
- [ ] Unauthenticated access to any page (except /login) redirects to /login
- [ ] /login does not redirect to /login (no infinite loop)
- [ ] Current user is available in layout context for all pages
- [ ] Logout button calls /api/v1/auth/logout, clears state, redirects to /login
- [ ] All existing API fetch calls include `credentials: 'include'`
- [ ] 401 responses from any API call trigger redirect to /login
- [ ] `make test-browser` passes with new Playwright tests
