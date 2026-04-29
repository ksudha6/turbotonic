# Backlog

## PO Confirmation module

- [ ] Auth and sessions (WebAuthn/passkeys + cookie sessions)
- [ ] Roles: SM vs Vendor views (same data, different controls)
- [ ] Overdue status (time-based trigger past required delivery date)
- [x] In-app notifications / activity feed (iterations 23-24: activity log, dashboard feed, notification bell, detail timelines)
- [ ] Mobile layout
- [ ] Custom value approval for reference data dropdowns
- [ ] Dedicated `/api/v1/po/ids` endpoint (cross-page selection beyond 200)
- [ ] Live/historical exchange rates for dashboard
- [ ] Field-level mutability rules tied to lifecycle status
- [ ] Buyer as first-class entity (currently hardcoded)
- [ ] Partial PO acceptance (accept/reject at line-item level)
- [x] Notifications (in-app alerts for status changes, assignments, deadlines) (iterations 23-24)

## Post-confirmation modules

- [ ] Production status tracking (enabled once PO is Accepted)
- [x] Invoicing (iterations 12, 16, 21, 22)

## Cosmetic / Data Quality

- [x] Vendor country should be a dropdown from reference data (iteration 20)
- [x] HS code format validation (iteration 20)

## Deferred

- [ ] Compliance fields (LC, export license, packing list, bill of lading)
- [ ] Roles and permissions (beyond SM/Vendor split)
- [ ] Email notifications
- [ ] SM internal notes

## Phase 4.2 close-out (deferred, not blocking Phase 4.3)

- [ ] G-28 role-conditional rendering coverage matrix on `/po/*`. Today gating is scattered across page-level `{#if}`, `PoActionRail` internal action-list computation, and panel internals (`PoDocumentsPanel` calls `canViewPOAttachments(user, po)`, `PoAdvancePaymentPanel` calls `canMarkAdvancePaid`, etc.). Audit confirmed P2/P3/P4/P5 already aligned; only P1 (declarative `ROLE_MATRIX` const at the top of each `/po/*` page + a single 6-role × 4-page Playwright spec) is open. Risk if skipped: a future iter adds a new mutation surface, forgets a gate, ships a button that 403s on click. Source: [tools/phase-4-research/phase-4.2-mock-clarity-inventory.md L664](tools/phase-4-research/phase-4.2-mock-clarity-inventory.md). Pre-iter audit notes captured in iter 086 draft (deleted).
- [ ] G-29 99-spec Playwright migration plan for `/po/*`. Adds shared `frontend/tests/fixtures/po.ts` `buildPOFixture` + `buildUser` helpers, new `po-list-bulk.spec.ts` (SM × {DRAFT, REVISED} submit + VENDOR × PENDING accept/reject + empty Valid Actions), new `po-list-row-click.spec.ts`, migrates remaining ~99 specs to new DOM. The fixture refactor naturally absorbs the 13 svelte-check `vendor_id: null` literal-narrowing errors carried since iter 085. Source: [tools/phase-4-research/phase-4.2-mock-clarity-inventory.md L688](tools/phase-4-research/phase-4.2-mock-clarity-inventory.md).

## Type-hardening (deferred from iter 085)

- [ ] 29 svelte-check errors carried since iter 085 close. Splits: 13 in test fixtures (`tests/po-detail.spec.ts`, `po-documents.spec.ts`, `po-negotiation.spec.ts`, `nexus-dashboard.spec.ts`) — same root cause `typeof SM_USER` narrows literal `vendor_id: null` (folds into G-29). 2 in `(nexus)/po/[id]/+page.svelte:330,432` — same `let po: T \| null = $state(null)` narrowing pattern fixed on the edit page in iter 085 (fix: `let po = $state<PurchaseOrder \| null>(null)`). 6 in `(nexus)/dashboard/+page.svelte` — `summary` possibly null. 2 in `routes/shipments/[id]/+page.svelte:53` — same `$state(null)` narrowing. 1 in `routes/products/+page.svelte:78` — orphaned `requires_certification` from iter 036a. 4 in `tests/po-documents.spec.ts` — `Buffer` not found, missing `@types/node`. 1 in `tests/po-lifecycle.spec.ts:545` — null → Record cast (incorrectly noted as fixed in iter 085 summary).
