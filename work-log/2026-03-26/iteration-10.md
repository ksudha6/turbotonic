# Iteration 10 — 2026-03-26

## Context
Bulk action UX refinements. The toolbar needs cross-page selection, auto-clearing feedback, and guidance when no common action exists.

## JTBD
1. **When** I filter POs and want to act on all matches, **I want to** select all matching POs across pages from one click **so that** I don't have to page through and select each page.
2. **When** a bulk action completes, **I want to** see the result message briefly then have it disappear **so that** stale feedback doesn't clutter the screen.
3. **When** I select POs with mixed statuses and no buttons appear, **I want to** understand why **so that** I know to refine my selection.

## Tasks

### Task 1: Select all matching POs across pages
**Scope:** Frontend + Backend
**Files:** `frontend/src/routes/po/+page.svelte`, `frontend/src/lib/api.ts`
**Change:**
- When the user clicks select-all and `total > pos.length` (more items than the current page), show a link in the toolbar: "Select all {total} matching POs"
- Clicking it re-fetches using the existing list endpoint with `page_size=200` (current max) and adds all returned IDs to `selectedIds`
- Also show "Clear selection" to undo
- When cross-page selection is active, the count badge reflects the full total
- **Backlog:** If total exceeds 200, a dedicated `/api/v1/po/ids` endpoint returning only IDs with no page limit will be needed

**Scratch tests** (`frontend/tests/scratch/iteration-010/`):
- Set page_size=10, select all on page, screenshot showing "Select all {total} matching POs" link
- Click the link, screenshot showing full count in badge
- Click "Clear selection", screenshot showing cleared state

---

### Task 2: Auto-clear bulk message after 5 seconds
**Scope:** Frontend only
**Files:** `frontend/src/routes/po/+page.svelte`
**Change:**
- After setting `bulkMessage`, start a 5-second timeout that clears it
- Clear any pending timeout if a new action starts
- Clear on unmount

**Scratch tests** (`frontend/tests/scratch/iteration-010/`):
- Execute a bulk action, screenshot showing message immediately after
- Wait 6 seconds, screenshot showing message cleared

---

### Task 3: Empty-intersection hint
**Scope:** Frontend only
**Files:** `frontend/src/routes/po/+page.svelte`
**Change:**
- When `selectedIds.size > 0` and `validActions.length === 0`, show text in the toolbar: "No common action for selected statuses"
- Style: `font-size: var(--font-size-sm); color: var(--gray-500); font-style: italic;`

**Scratch tests** (`frontend/tests/scratch/iteration-010/`):
- Select one Accepted PO and one Pending PO, screenshot showing hint text in toolbar
