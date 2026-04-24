# Iteration 061 -- Revamp foundations: permissions ADMIN inheritance + seed variety

## Context

First iteration of Phase 4.0 (UI revamp foundation). No UI ships here. Two non-UI prerequisites land before any primitive component gets built:

1. `frontend/src/lib/permissions.ts` uses `isExact` for four VENDOR-only capabilities (`canAcceptRejectPO`, `canCreateInvoice`, `canSubmitInvoice`, `canPostMilestone`). ADMIN does not inherit these, which contradicts the backlog rule "ADMIN inherits all actions". Fix now so every primitive built later (ActionRail, Sidebar, role-gated buttons) inherits the corrected rule.
2. `backend/src/seed.py` produces minimal fixtures. The dashboard phase (iter 062+) cannot be validated visually until the seed produces varied data across every aggregate. Memory rule: dashboard must show varied seeded data on fresh local runs.

Phase 4.0 ship gates apply: mock-clarity (no UI touched, so not applicable here), past-flow (`make test-browser` green), future-flow (no primitives added yet so nothing to regress).

## JTBD (Jobs To Be Done)

- As an ADMIN using the portal for support, when I open a PO, I want to accept/reject, post milestones, and create invoices, so I can unblock stuck workflows without switching accounts.
- As a developer spinning up a fresh local environment, when I run the seed script, I want varied POs, invoices, milestones, and activity across multiple vendors and user roles, so I can validate Dashboard, Production, Invoice, Vendor, and Product pages against realistic data.
- As a reviewer reading this iteration, I want the first commits of Phase 4.0 to be pure backend/logic fixes with no UI surface, so I can audit the foundation layer separately from the shell.

## Tasks

### Task 1 -- Fix `permissions.ts` ADMIN inheritance (DONE, commit `3e74811`)
- [x] Remove `isExact` helper entirely.
- [x] All four sites (`canAcceptRejectPO`, `canCreateInvoice`, `canSubmitInvoice`, `canPostMilestone`) use `is(role, 'VENDOR')`; ADMIN inherits via the `role === 'ADMIN'` short-circuit.
- [x] Append ADMIN regression spec to `frontend/tests/role-rendering.spec.ts` (100 tests still pass).

### Task 2 -- Overhaul `backend/src/seed.py` for varied dev data (pending)
- [x] Read `backend/src/seed.py` (715 lines) to map current fixture shape. Identify which aggregates produce a single row.
- [x] Create `backend/tests/test_seed.py` asserting minimum variety: >=5 vendors, >=3 vendor types, >=10 POs, >=4 PO statuses, >=6 invoices, >=3 invoice statuses, >=6 milestone updates, >=3 milestone stages, >=15 activity entries, >=3 user roles.
- [x] Expand `seed.py` to satisfy assertions. Preserve existing deterministic fixture IDs/usernames; add new rows rather than mutating existing ones.
- [x] Run `make test` -- new seed test passes, existing backend tests still pass.
- [x] Commit.

## Existing test impact

Pre-iteration spec audit:
- `frontend/tests/role-rendering.spec.ts` (381 LOC, 16 tests) -- Task 1 appended one ADMIN test; all 16 existing tests still pass under the new `is()` helper because no existing assertion depended on `isExact`'s exclusion behavior. Verified in the Task 1 run.
- `frontend/tests/po-lifecycle.spec.ts`, `po-negotiation.spec.ts`, `po-list.spec.ts`, `invoice-list.spec.ts`, `vendor.spec.ts`, `product.spec.ts`, `dashboard.spec.ts`, `activity-timeline.spec.ts`, `notification-bell.spec.ts`, `dashboard-activity.spec.ts`, `auth-flow.spec.ts`, `po-negotiation-events.spec.ts` -- untouched by Task 1; all 100 tests pass.
- Backend pytest suite -- Task 2 will add `backend/tests/test_seed.py`. Existing tests that depend on seed fixtures (check for hard-coded IDs/usernames) must keep passing; the rule is add-only, never renumber or rename existing rows.

If any existing backend test breaks when Task 2 expands the seed, investigate before flipping: a break signals the test was coupled to a specific row count rather than a specific row. Fix the coupling, not the seed.

No fixture/mock/helper updates needed beyond these.

## Tests

### Permanent tests added this iteration
- `frontend/tests/role-rendering.spec.ts` -- `ADMIN sees vendor-side actions (post milestone, accept/reject PO, create invoice)`: visits `/po` as ADMIN, asserts no redirect. Weak guard (documented concern: the assertion does not exercise the `isExact` sites directly because the failing-first test's assertion was prescribed verbatim by the plan). Full regression is carried by the existing 100-test suite.
- `backend/tests/test_seed.py` -- `test_seed_variety`: runs `run_seed` in a rolled-back transaction, asserts minimum row counts and distinct-value counts per aggregate.

### Scratch tests
None. Both tasks are logic/data fixes with no UI; scratch screenshot capture is not applicable.

### Logs
- Task 1: `logs/playwright-test-browser.log` (100 passed, 12.6s).
- Task 2: `logs/make-test.log` (on completion).

## Notes

Iter 061 closed on 2026-04-24. Three commits landed on `phase-4-0-foundation`: `3e74811` (permissions.ts fix), `f34fa15` (seed.py initial expansion), `b268f51` (seed.py EVENT_METADATA derivation fix from code-quality review). 591 backend tests + 100 Playwright specs green at close.

No new domain terms introduced, so `docs/ddd-vocab.md` is unchanged.

Decisions:
- Task 1's failing-first test had a weak assertion (only guarded against redirect off `/po`) and passed pre-fix. The plan prescribed that exact assertion verbatim; we followed the plan rather than unilaterally strengthening it. Full-suite green carries the regression guard.
- `backend/src/seed.py` was pre-existing on disk but untracked in git. This iteration is the first commit that adds it to the repo; most of the 715-line file is pre-existing bulk. Only the activity-log expansion and the `EVENT_METADATA` derivation are this iteration's direct contribution.
- Code-quality review flagged pre-existing issues that are out of scope for this iteration: non-deterministic UUIDs (`uuid4()` unaffected by `random.seed`), `_PAYMENT_TERMS_CYCLE` dead branches (CIA, 100_PCT_ADVANCE unreachable), module-level `random.seed(1729)` and `_NOW = datetime.now(UTC)` side effects at import time, missing docstrings, per-test fixture overhead, `actor_id: None` on activity rows. These are logged in the backlog for a future seed-hardening iteration; they do not block Phase 4.0 downstream work.

Backlog additions for later:
- Deterministic seeded UUIDs (use `uuid.uuid5` with stable natural-key namespace)
- Prune `_PAYMENT_TERMS_CYCLE` dead branches or extend the cycle to cover them
- Move `random.seed` and `_NOW` capture inside `seed()` to remove import-time side effects
- Add module/function docstrings to `seed.py` and `test_seed.py`
- Consider session-scoped `seeded_conn` fixture if seed grows

Carried forward: none. Both tasks completed.
