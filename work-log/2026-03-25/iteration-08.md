# Iteration 08 — 2026-03-25

## Context
I want to bulk change the POs by selecting the filter. I want to bulk change the POs by selecting the POs using a check box. I want to be able see more POs on the page using pagination filter.

## JTBD
1. **When** I have a filtered list of POs, **I want to** apply a bulk status change to all visible results **so that** I don't update them one by one.
2. **When** I need to update specific POs, **I want to** select them individually with checkboxes and apply a change **so that** I can precisely control which POs are affected.
3. **When** I'm reviewing POs, **I want to** control how many POs appear per page (10/20/50/100/200) **so that** I can see more at once.

## Tasks

### Task 1: Raise page_size cap to 200
**Scope:** Backend only
**Files:** `backend/src/routers/purchase_order.py`
**Change:** Line 110 validation from `1 <= page_size <= 100` to `1 <= page_size <= 200`. Update error message.

**Permanent tests** (`backend/tests/test_api_purchase_order.py`):
- `test_list_pos_page_size_200_accepted` — request with `page_size=200` returns 200 OK
- `test_list_pos_page_size_201_rejected` — request with `page_size=201` returns 422

---

### Task 2: Page size selector dropdown
**Scope:** Frontend only
**Files:** `frontend/src/routes/po/+page.svelte`
**Change:** Add a `<select>` with options 10, 20, 50, 100, 200 in the pagination controls. Bind to `pageSize`. Reset `page` to 1 when `pageSize` changes. Pass `page_size` to `listPOs()` in `fetchPOs()`. Add `pageSize` to the reactive dependency list and to URL params.

**Scratch test** (`frontend/tests/scratch/iteration-008/`):
- Screenshot the pagination area showing the dropdown with 20 selected (default)
- Change to 50, screenshot showing fewer pages / more rows

---

### Task 3: Bulk status transition endpoint
**Scope:** Backend only
**Files:** `backend/src/dto.py`, `backend/src/routers/purchase_order.py`
**Change:**
- New DTO `BulkTransitionRequest`: `po_ids: list[str]`, `action: str` (one of `submit`, `accept`, `reject`, `resubmit`), `comment: str | None`
- New DTO `BulkTransitionResult`: `results: list[BulkTransitionItemResult]` where each item has `po_id: str`, `success: bool`, `error: str | None`, `new_status: str | None`
- New endpoint `POST /api/v1/po/bulk/transition` that:
  - Validates action is one of the four allowed values
  - Validates `comment` is provided when action is `reject`
  - Validates `po_ids` is non-empty (max 200)
  - Iterates each PO: loads, calls domain method, saves. On ValueError, records failure for that PO, continues to next
  - Returns 200 with per-PO results (not 409 on partial failure)

**Permanent tests** (`backend/tests/test_api_purchase_order.py`):
- `test_bulk_submit_transitions_drafts_to_pending` — create 3 DRAFT POs, bulk submit, all succeed with PENDING
- `test_bulk_accept_transitions_pending_to_accepted` — create and submit 2 POs, bulk accept, all succeed with ACCEPTED
- `test_bulk_reject_requires_comment` — bulk reject without comment returns 422
- `test_bulk_reject_with_comment_succeeds` — bulk reject PENDING POs with comment, all succeed with REJECTED
- `test_bulk_transition_partial_failure` — mix of DRAFT and ACCEPTED POs, bulk submit: DRAFTs succeed, ACCEPTED ones fail with error message
- `test_bulk_transition_invalid_action` — action "delete" returns 422
- `test_bulk_transition_empty_po_ids` — empty list returns 422
- `test_bulk_transition_nonexistent_po` — unknown po_id records failure for that PO, others still processed

---

### Task 4: Checkbox selection column
**Scope:** Frontend only
**Files:** `frontend/src/routes/po/+page.svelte`
**Change:**
- Add `selectedIds: Set<string>` state
- Add `<th>` with select-all checkbox in header. Checked when all visible POs are selected. Toggles all on/off.
- Add `<td>` with per-row checkbox. Click on checkbox must NOT navigate to detail page (stopPropagation).
- Selection count badge above the table: "{N} selected" (hidden when 0)
- Clear selection when filters, search, sort, page, or pageSize change

**Scratch test** (`frontend/tests/scratch/iteration-008/`):
- Screenshot list with checkboxes visible
- Screenshot with 2 rows checked, showing "2 selected" badge
- Screenshot after clicking select-all, showing all checked

---

### Task 5: Bulk action toolbar
**Scope:** Frontend only (depends on Tasks 3 + 4)
**Files:** `frontend/src/routes/po/+page.svelte`, `frontend/src/lib/api.ts`
**Change:**
- New API function `bulkTransition(poIds: string[], action: string, comment?: string)` in `api.ts`
- Toolbar appears when `selectedIds.size > 0`, positioned between filter bar and table
- Buttons: Submit, Accept, Reject, Resubmit
- Reject button opens a prompt/modal for comment input
- On action: call bulk endpoint, show result summary (N succeeded, M failed), refresh list, clear selection
- Disable toolbar buttons while request is in flight

**Scratch test** (`frontend/tests/scratch/iteration-008/`):
- Screenshot showing toolbar with action buttons when POs are selected
- Screenshot showing result after a bulk action
