# Iteration 077 — `/po/[id]` detail revamp (Phase 4.2 Tier 2, header + action rail + advance + cert + PDF)

## Context

Phase 4.2 Tier 2 of the mock-clarity inventory ([tools/phase-4-research/phase-4.2-mock-clarity-inventory.md](tools/phase-4-research/phase-4.2-mock-clarity-inventory.md), gaps G-13, G-14, G-17, G-20, G-23) has resolved decisions for the `/po/[id]` shell. Reusable components landed in [frontend/src/lib/po/](frontend/src/lib/po/) ahead of this iter via the visual-mock work at [/ui-demo/po-detail](frontend/src/routes/ui-demo/po-detail/+page.svelte): [`PoDetailHeader`](frontend/src/lib/po/PoDetailHeader.svelte), [`PoActionRail`](frontend/src/lib/po/PoActionRail.svelte), [`PoAdvancePaymentPanel`](frontend/src/lib/po/PoAdvancePaymentPanel.svelte), [`PoCertWarningsBanner`](frontend/src/lib/po/PoCertWarningsBanner.svelte). The current pre-revamp page lives at [frontend/src/routes/po/[id]/+page.svelte](frontend/src/routes/po/[id]/+page.svelte) (781 LOC) and will be moved under `(nexus)` to inherit AppShell + Sidebar + TopBar (precedent: iters 071-076). The Post-Acceptance Gate state surfaced by the Advance Payment panel comes from the backend domain rule at [backend/src/domain/purchase_order.py:595](backend/src/domain/purchase_order.py#L595) (`can_modify_post_acceptance`).

## JTBD

When I open `/po/[id]` as SM/ADMIN, I want a `(nexus)`-shell page with a compact header (back link, PO number, vendor + issued date subtitle, status pill), a single role-aware action rail at top-right that collapses into an overflow menu on mobile, an Advance Payment panel above Line Items that surfaces the Post-Acceptance Gate state, and a Cert Warnings banner between header and detail when the server returned warnings, so I can act on the PO without scrolling through a five-card pre-revamp layout. As VENDOR I want my action rail (Accept on Pending; Create Invoice / Post Milestone on Accepted) and no Mark-advance-paid button. As PROCUREMENT_MANAGER, FREIGHT_MANAGER, or QUALITY_LAB I want only Download PDF and no other rail.

## Tasks

1. Frontend: move the page from [frontend/src/routes/po/[id]/+page.svelte](frontend/src/routes/po/[id]/+page.svelte) to `frontend/src/routes/(nexus)/po/[id]/+page.svelte` so it inherits AppShell + Sidebar + TopBar. Remove the file at the old path. Keep the `[id]/edit` route in place for now (Tier 5 owns the create/edit revamp).
2. Frontend: replace the inline header card markup at [`+page.svelte:338-385`](frontend/src/routes/po/[id]/+page.svelte#L338) with [`PoDetailHeader`](frontend/src/lib/po/PoDetailHeader.svelte). Pass `po`, `role`, and the action-rail props through. Subtitle = `vendor_name` + Issued Date.
3. Frontend: replace the footer button row at [`+page.svelte:625-650`](frontend/src/routes/po/[id]/+page.svelte#L625) and the inline Mark-advance-paid block at [`+page.svelte:371-384`](frontend/src/routes/po/[id]/+page.svelte#L371) with [`PoActionRail`](frontend/src/lib/po/PoActionRail.svelte) inside the header (`mode="inline"` at >=768px, `mode="sticky-bottom"` at <768px). Wire the `onEdit`, `onSubmit`, `onResubmit`, `onAccept`, `onCreateInvoice`, `onPostMilestone`, `onDownloadPdf` callbacks to the existing handler functions in the page. The `onMarkAdvancePaid` callback is unused on the rail (the panel owns it) but still required by the prop contract.
4. Frontend: add a [`PoAdvancePaymentPanel`](frontend/src/lib/po/PoAdvancePaymentPanel.svelte) above the Line Items section, rendering only when `po.payment_terms?.has_advance` and `po.status` ∈ {PENDING, MODIFIED, ACCEPTED, REJECTED, REVISED}. VENDOR sees a status-only readout (no Mark-advance-paid button); SM/ADMIN see the button when `canMarkAdvancePaid(role)`. Surface the Post-Acceptance Gate state inline ("Add/remove window open until advance paid or first milestone" while open; "Closed: advance paid {date}" or "Closed: first milestone posted {date}" when shut). Wire the existing `markAdvancePaid` mutation through the panel and route `advanceError` to its error slot.
5. Frontend: add [`PoCertWarningsBanner`](frontend/src/lib/po/PoCertWarningsBanner.svelte) between the header and the first PanelCard, visible when `certWarnings.length > 0 && !certWarningsDismissed`. Keep the existing in-memory dismissal (no per-PO sticky persistence). Banner does not block the rail; it is advisory only.
6. Frontend: rewire `downloadPoPdf` so the action label says "Download PDF (Modified)" when `po.round_count > 0` (the rail component already handles this via `pdfLabel()`; verify the page passes the correct `po` reference). PDF action stays in the overflow menu on both viewports.
7. Frontend: update [frontend/src/routes/+layout.svelte](frontend/src/routes/+layout.svelte) `isRevampRoute` derivation to match `/po/{id}` paths (currently matches `/po` and `/po/`); change to a prefix match so `/po`, `/po/`, `/po/123`, `/po/new`, and `/po/123/edit` all hide the pre-revamp top nav. Confirm `/po/new` and `/po/[id]/edit` still render correctly after the change (those routes are pre-revamp and stay that way).
8. Frontend: keep the line-items section, milestone timeline, invoices sub-list, rejection history, and activity feed in their existing pre-revamp shape. Wrap each in a [`PanelCard`](frontend/src/lib/ui/PanelCard.svelte) only if doing so requires zero structural change to the children; otherwise leave the legacy markup until the relevant tier lands.
9. Frontend: keep all existing data-fetching (`getPO`, `listInvoicesByPO`, `fetchReferenceData`, `getRemainingQuantities`, `listMilestones`, `listProducts`), all line-negotiation handlers, all milestone post handlers, and all add/remove-line handlers untouched. This iter swaps shells and primitives, not behavior.
10. DDD vocab: assess whether "Post-Acceptance Gate" or "Advance Payment" need fresh entries (they appear in code at `can_modify_post_acceptance` and `markAdvancePaid` but check [docs/ddd-vocab.md](docs/ddd-vocab.md) for canonical phrasing). Update only if a term is missing or its phrasing diverges from the panel copy.

## Tests

### Existing test impact

- [frontend/tests/po-lifecycle.spec.ts](frontend/tests/po-lifecycle.spec.ts) — exercises the detail page through the lifecycle (Draft → Pending → Accepted; reject; revise). Currently relies on tag selectors (`button[type="submit"]`), text selectors (`getByText('Mark advance paid')`), and inline class selectors on the action row. Expected impact: ~10-15 of these tests need selector updates to `[data-testid="po-action-{id}"]`, `[data-testid="po-advance-panel"]`, `[data-testid="po-detail-header"]`. Re-target assertions to:
  - `data-testid="po-detail-header"` and `data-testid="po-detail-title"` on header.
  - `data-testid="po-action-{action}"` for each action button (already used by `PoActionRail`).
  - `data-testid="po-action-overflow"` for the overflow menu summary.
  - `data-testid="po-advance-panel"`, `data-testid="po-advance-mark-paid"`, `data-testid="po-advance-gate-state"` on the panel.
  - `data-testid="po-cert-warnings"` on the banner.
- [frontend/tests/po-negotiation.spec.ts](frontend/tests/po-negotiation.spec.ts), [frontend/tests/po-negotiation-events.spec.ts](frontend/tests/po-negotiation-events.spec.ts) — these primarily exercise the line-negotiation surface and the SubmitResponseBar, both unchanged in this iter. The detail-page entry point may need the same `[data-testid="po-action-accept"]` selector update if the test clicks Accept; otherwise unchanged.
- [frontend/tests/po-pdf.spec.ts](frontend/tests/po-pdf.spec.ts) (if it exists; otherwise the assertion lives in `po-lifecycle.spec.ts`) — the Download PDF click target moves into the overflow menu. Tests that click the visible "Download PDF" button directly need to first click `[data-testid="po-action-overflow"]` then `[data-testid="po-action-download-pdf"]`.
- [frontend/tests/po-list.spec.ts](frontend/tests/po-list.spec.ts) — list page only; unchanged. The list → detail row click already uses `[data-testid^="po-row-"]` after iter 076.
- Backend pytest suite — no changes; this iter is markup-only.

### Permanent — frontend

1. `po-detail.spec.ts::detail header renders inside (nexus) shell` — load `/po/{id}` as SM, assert `[data-testid="app-shell"]` is present (from AppShell), `[data-testid="po-detail-header"]` is present, and the pre-revamp top nav is not (per `isRevampRoute` change).
2. `po-detail.spec.ts::action rail composition for SM on DRAFT` — seed PO with `status=DRAFT`, role=SM; assert `[data-testid="po-action-edit"]` and `[data-testid="po-action-submit"]` are visible, `[data-testid="po-action-accept"]` is absent, and `[data-testid="po-action-overflow"]` reveals `[data-testid="po-action-download-pdf"]`.
3. `po-detail.spec.ts::action rail composition for VENDOR on PENDING` — seed PO with `status=PENDING`, role=VENDOR; assert `[data-testid="po-action-accept"]` is visible and SM-only actions absent.
4. `po-detail.spec.ts::action rail composition for VENDOR on ACCEPTED PROCUREMENT shows Create Invoice + Post Milestone` — seed PO with `status=ACCEPTED`, `po_type=PROCUREMENT`, role=VENDOR; assert `[data-testid="po-action-create-invoice"]` is visible (primary) and `[data-testid="po-action-post-milestone"]` is reachable.
5. `po-detail.spec.ts::PROCUREMENT_MANAGER sees Download PDF only` — role=PM; assert `[data-testid="po-action-download-pdf"]` is the only action and no overflow menu renders (`[data-testid="po-action-overflow"]` absent).
6. `po-detail.spec.ts::FREIGHT_MANAGER sees Download PDF only` — same as #5 for FM.
7. `po-detail.spec.ts::QUALITY_LAB sees Download PDF only` — same as #5 for QL.
8. `po-detail.spec.ts::Download PDF label says (Modified) when round_count > 0` — seed PO with `round_count=1`; assert the overflow menu item label includes "(Modified)".
9. `po-detail.spec.ts::Advance Payment panel hidden when has_advance is false` — seed PO without advance payment terms; assert `[data-testid="po-advance-panel"]` is absent.
10. `po-detail.spec.ts::Advance Payment panel for SM on ACCEPTED + has_advance + unpaid shows Mark advance paid` — assert `[data-testid="po-advance-mark-paid"]` is visible and `[data-testid="po-advance-gate-state"]` reads "open".
11. `po-detail.spec.ts::Advance Payment panel post-paid shows closed gate with date` — seed PO with `advance_paid_at` set; assert `[data-testid="po-advance-mark-paid"]` is absent and `[data-testid="po-advance-gate-state"]` reads "closed: advance paid".
12. `po-detail.spec.ts::Advance Payment panel for VENDOR is read-only` — role=VENDOR, has_advance=true, ACCEPTED, unpaid; assert `[data-testid="po-advance-panel"]` renders but `[data-testid="po-advance-mark-paid"]` is absent.
13. `po-detail.spec.ts::Cert Warnings banner renders when warnings present and is dismissible` — seed `certWarnings` array via mocked submit response; assert `[data-testid="po-cert-warnings"]` is visible, click `[data-testid="po-cert-warnings-dismiss"]`, assert banner disappears in the same session.
14. `po-detail.spec.ts::Cert Warnings banner is absent when warnings empty` — assert no banner renders on a freshly-loaded PO with no warnings.
15. `po-detail.spec.ts::sticky bottom action rail at 390px viewport` — set viewport `390x844`, role=SM, status=DRAFT; assert the rail uses `data-testid="po-action-rail"` and the rail's mode-sticky styling (a `position:sticky` ancestor) is in effect. Primary action button is visible; overflow opens upward (`po-action-rail__menu--up` class on the menu container).

### Scratch

None. The fifteen permanent tests cover the role × status matrix verified against the Tier 2 mock plus the gate-state copy for G-17 and the dismissal lifetime for G-20.

## Notes

The Tier 2 mock at `/ui-demo/po-detail` (committed at e2fe699 ahead of this iter) was the verification surface for the four reusable components; the production page at `(nexus)/po/[id]/+page.svelte` adopted them without further design rounds. The legacy line items, milestone timeline, invoices, rejection history, and activity sections stayed in their pre-revamp shape on purpose; they belong to Tier 3+ scope and would have ballooned the iter past its scope-fence. Iter 077 ran in parallel with iter 080 (primitive label/aria-label retrofit) with zero file overlap: this iter touched `routes/(nexus)/po/[id]/`, `routes/+layout.svelte`, and `frontend/tests/po-detail.spec.ts`; iter 080 touched `frontend/src/lib/ui/` and `primitives.spec.ts`. The dev quick-login from iter 079 enabled cross-role visual verification of the new action rail without re-registering passkeys per role.
