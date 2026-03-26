# Iteration 09 — 2026-03-26

## Context
The bulk action toolbar shows all four actions (Submit, Accept, Reject, Resubmit) regardless of what's selected. A user selecting only PENDING POs should not see Submit or Resubmit. The bulk result message uses grey text for failures, which is not visible enough.

## JTBD
1. **When** I select POs for a bulk action, **I want to** see only the actions valid for those POs' statuses **so that** I don't trigger actions that will fail.
2. **When** a bulk action completes with failures, **I want to** clearly see the failure count **so that** I know something went wrong.

## Tasks

### Task 1: Context-aware bulk action buttons
**Scope:** Frontend only
**Files:** `frontend/src/routes/po/+page.svelte`
**Change:**
- Derive the set of statuses present in `selectedIds` from `pos`
- Compute which actions are valid using the transition map:
  - DRAFT: submit
  - PENDING: accept, reject
  - REJECTED: resubmit
  - REVISED: resubmit
  - ACCEPTED: (none)
- Show the intersection of valid actions across all selected statuses
- If the intersection is empty, show no action buttons (just the selection count)

### Task 2: Style bulk result message for failures
**Scope:** Frontend only
**Files:** `frontend/src/routes/po/+page.svelte`
**Change:**
- When the bulk message contains failures, render with bold text, slightly larger font, red color
- When all succeeded, keep the current grey style
- Track whether the last bulk action had failures via a boolean state variable
