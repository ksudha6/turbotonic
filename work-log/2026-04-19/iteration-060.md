# Iteration 060 -- Email notifications

## Context
The in-app bell from iter 024 covers users logged into the portal, but counterparties also need email for key PO events. This iter adds SMTP infrastructure (aiosmtplib, env-driven config), Jinja2 templates per event type, a notification dispatcher decoupled from the activity repository, recipient resolution per role and vendor scope, and a test harness that stubs email by default so no test hits the network.

## JTBD (Jobs To Be Done)
- As a vendor offline, when an SM accepts my PO, I want an email so I do not miss the transition.
- As an SM, when a vendor modifies a line, I want an email with the diff so I can review without opening the portal.
- As a vendor, when an SM marks advance paid, I want an email so I can start production.
- As an operator, when email fails, I want a structured log entry so I know which counterparties missed a message.
- As a developer, when running tests, I want email calls mocked by default so tests do not require network.

## Tasks

### Configuration
- [ ] Add env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_TLS` (default True), `EMAIL_ENABLED` (default False in tests, True when SMTP_HOST set).
- [ ] Development mode (SMTP_HOST unset): log the payload via logging, return success, do not attempt network.
- [ ] Document env-var matrix in `README.md` or similar (no README created unless user explicitly wants).

### Backend -- Email service (`backend/src/services/email.py`)
- [ ] `class EmailService`. Methods:
  - `async send(to: list[str], subject: str, body_html: str, body_text: str) -> None`
- [ ] Uses `aiosmtplib` when EMAIL_ENABLED, else the logging path.
- [ ] Adds `aiosmtplib` to `[dependency-groups]` in `pyproject.toml`.
- [ ] Sends multipart/alternative with both HTML and text bodies.

### Backend -- Templates (`backend/src/services/email_templates/`)
- [ ] Directory with paired `.html.j2` and `.txt.j2` templates per event:
  - `po_modified`
  - `po_line_modified`
  - `po_advance_paid`
  - `po_accepted`
- [ ] Template context fields: PO number, PO URL, vendor name, line detail, round indicator.
- [ ] Subject line pattern: `[TurboTonic] PO <po_number> {event summary}` for inbox triage.
- [ ] Use `Jinja2` or Svelte's server-side equivalent; recommend jinja2 for standard practice.

### Backend -- Dispatcher (`backend/src/services/notifications.py`)
- [ ] `class NotificationDispatcher`. Method `async dispatch(event: ActivityLogEntry) -> None`.
- [ ] Subscribes via a small dispatcher pattern (not tightly coupled to `ActivityLogRepository.append`). In 058, the append function returns the event; this iter hooks into that return to call `dispatch`.
- [ ] Chooses template and recipients based on event type.
- [ ] Passes rendered HTML/text to `EmailService.send`.

### Backend -- Recipient resolution
- [ ] SM-targeted events: all active users of role SM or ADMIN.
- [ ] Vendor-targeted events: all active users of role VENDOR with `vendor_id` matching the PO's vendor.
- [ ] Skip users with `status != ACTIVE`.
- [ ] Skip users with no email (after schema add).

### Schema
- [ ] Add `email TEXT NULL` to `users` table if not present (check iter 030 scope; most likely missing).
- [ ] Idempotent ALTER.
- [ ] Seed script: populate synthetic emails for seed users (`bob@acme.example`, `cara@beta.example`, etc.).

### Test harness
- [ ] Pytest fixture `fake_email_service` recording calls as tuples `(to, template_name, context)`.
- [ ] Tests assert template name + recipient set rather than SMTP bytes.
- [ ] Default in `conftest.py`: fake service bound unless a test requests the real one.

## Tests (permanent)

### Existing test impact
- Activity tests from 058 now run under the fake email service fixture. Each existing test assertion is extended to check dispatcher was called or not.
- Any test that currently writes `users` rows: add an `email` field where present. If absent, migration default makes it null and existing assertions pass.
- No Playwright tests affected; email has no UI.

### New unit tests (~8 tests in `backend/tests/test_email_service.py`)
- Each template renders with required fields.
- Missing template raises a clear error.
- Development mode logs payload and returns success.
- Production mode serializes multipart alternative correctly.
- Recipient resolver returns SM+ADMIN set for SM-targeted events.
- Recipient resolver returns vendor-scoped set for VENDOR-targeted events.
- Inactive users excluded.
- Users with no email excluded.

### New integration tests (~4 tests in `backend/tests/test_notifications.py`)
- PO accept convergence triggers one `po_accepted` send to the vendor.
- Submit-response round 1 triggers `po_modified` to the counterparty.
- `mark-advance-paid` triggers `po_advance_paid` to the vendor.
- `modify_line` triggers `po_line_modified` to the counterparty with field delta in context.

## Tests (scratch)
None. Email has no UI.

## Notes
- Provider choice: SMTP via aiosmtplib. Works with any transactional relay (SES, SendGrid, Resend, Mailgun). No SDK lock-in.
- User opt-out preferences are out of scope for this iter. Add to backlog.
- Email failure is logged to activity_log as a new `EMAIL_SEND_FAILED` row with category DELAYED. Does not retry automatically; operator can replay if needed.
- Subject lines include PO number and vendor name for inbox filtering.

### Closing summary
SMTP via aiosmtplib was chosen over any HTTP SDK so the backend works with any transactional provider (SES, SendGrid relay, Resend, Mailgun) through env config, with no SDK lock-in. Development mode is selected by leaving SMTP_HOST unset: the service logs the rendered payload via logging and returns success, so tests and local dev never touch the network unless SMTP_HOST is set explicitly. NotificationDispatcher lives in `backend/src/services/notifications.py` and stays decoupled from ActivityLogRepository.append so tests stub it via the FakeEmailService fixture. Four templates cover the first wave (po_accepted, po_modified, po_line_modified, po_advance_paid), which matches the 4 user-visible transitions worth emailing; other activity events stay in-app only. Recipient resolution sends SM-targeted events to SM plus ADMIN and VENDOR-targeted events to VENDOR users scoped by vendor_id, excluding inactive users and users with no email. Delivery failures append an activity row of type EMAIL_SEND_FAILED with category DELAYED and do not automatically retry. The `users.email` column was added nullable, existing rows got null, and seed data backfills synthetic emails for seeded users. Two late-breaking test-harness issues were fixed: `backend/tests/test_vendor_scoping.py::vendor_scoping_env` still called `_setup_overrides(conn, upload_dir)` with the iter-056 signature, so the call site was updated to construct a FakeEmailService and pass it through as the new `fake_email` parameter; separately, the same fixture was re-running `init_db(conn)` on its own connection and race-ALTERed the users table while other connections held locks, so the redundant call was removed since the conftest session fixture already migrates the schema.

## Acceptance criteria
- [ ] `aiosmtplib` and `jinja2` added to backend dependencies.
- [ ] `EmailService.send` works in development mode (log) and production mode (SMTP).
- [ ] Four templates (HTML + text) present: po_modified, po_line_modified, po_advance_paid, po_accepted.
- [ ] `NotificationDispatcher` subscribes to activity events and dispatches the right template to the right recipients.
- [ ] Recipient resolution respects role, vendor scope, active status, email presence.
- [ ] `users.email` column added and migrated.
- [ ] Seed data populates emails.
- [ ] Fake email service fixture is default in tests.
- [ ] All unit and integration tests pass.
