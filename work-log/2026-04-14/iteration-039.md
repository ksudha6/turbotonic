# Iteration 039 -- Quality gate and request flow

## Context

POs have `marketplace` and line items have `product_id` (iter 036), products have qualification requirements (iter 036a), and certificates record fulfillment (iter 038), but nothing connects them at submission time. This iteration adds an advisory quality gate: on PO submit, each line item's product is checked for valid certificates matching the PO's marketplace, and warnings are returned in the response. On QC_PASSED milestone, CERT_REQUESTED activity entries are created for products with missing coverage. The gate is non-blocking by design.

## JTBD (Jobs To Be Done)

- When I submit a PO, I want to see warnings about products that lack required certificates for the target marketplace, so that I can address compliance gaps before production begins
- When production passes QC for a PO, I want the system to automatically request certificates from the quality lab for any products missing coverage, so that compliance is tracked without manual follow-up
- When a line item has no product_id, I want the quality gate to skip it silently, so that legacy POs without product linkage still work

## Tasks

### Quality gate service

#### Create `backend/src/services/quality_gate.py`
- [ ] `CertWarning` dataclass:
  - line_item_index: int
  - part_number: str
  - product_id: str
  - qualification_type_id: str
  - qualification_name: str
  - reason: str (e.g. "MISSING", "EXPIRED")
- [ ] `async check_po_qualifications(po: PurchaseOrder, product_repo: ProductRepository, qualification_repo: QualificationTypeRepository, cert_repo: CertificateRepository) -> list[CertWarning]`
  - For each line item with a product_id:
    1. Load the product's qualifications via qualification_repo.list_by_product(product_id)
    2. For each qualification, check if a valid (non-expired) certificate exists for the PO's marketplace (or target_market matching)
       - Use cert_repo.list_by_product_and_market(product_id, po.marketplace) if marketplace is set
       - Filter: certificate.qualification_type_id matches, certificate.display_status() in ("PENDING", "VALID") -- not "EXPIRED"
       - Actually: only VALID counts. PENDING means cert was created but not confirmed. Check status == VALID and not is_expired().
    3. If no valid cert found: append CertWarning with reason "MISSING"
    4. If cert exists but is expired: append CertWarning with reason "EXPIRED"
  - Line items without product_id: skip (no warning)
  - POs without marketplace: skip quality gate entirely (return empty list)
  - Return list of CertWarning

### DTO additions

#### Modify `backend/src/dto.py`
- [ ] Add `CertWarningResponse(BaseModel)`:
  - line_item_index: int
  - part_number: str
  - product_id: str
  - qualification_name: str
  - reason: str
- [ ] Add `cert_warnings: list[CertWarningResponse]` to `PurchaseOrderResponse` (default empty list)
  - This field is populated only on submit response, not on all GET responses
- [ ] Alternative: create a `SubmitResponse(BaseModel)` wrapping PurchaseOrderResponse + warnings. Preferred, since warnings are transient and shouldn't pollute the standard GET response.
  - `POSubmitResponse(BaseModel)`: po (PurchaseOrderResponse), cert_warnings (list[CertWarningResponse])

### Router changes

#### Modify `backend/src/routers/purchase_order.py`
- [ ] In `submit_po()`:
  1. After `po.submit()` succeeds but before returning:
  2. Run `check_po_qualifications(po, ...)` to get warnings
  3. Return `POSubmitResponse(po=po_response, cert_warnings=warnings)` instead of plain PurchaseOrderResponse
  4. Change response_model to `POSubmitResponse`
  - Import and inject product_repo, qualification_repo, cert_repo as dependencies
- [ ] In `resubmit_po()`: same pattern -- run quality gate, return warnings

#### Modify `backend/src/routers/milestone.py`
- [ ] After posting QC_PASSED milestone:
  1. Load the PO to get line items and marketplace
  2. For each line item with product_id:
     - Load product's qualifications
     - Check for valid certificates for the marketplace
     - If missing: create CERT_REQUESTED activity entry
       - entity_type: CERTIFICATE
       - entity_id: product_id (the product needing the cert)
       - event: CERT_REQUESTED
       - category: ACTION_REQUIRED
       - target_role: QUALITY_LAB (will need to add to TargetRole enum -- or use SM for now if QUALITY_LAB role isn't added yet in auth iterations)
       - detail: f"Product {product.part_number} requires {qualification.name} for market {po.marketplace}"
  3. If cert exists and is valid: no action
  4. If line item has no product_id: skip

### Activity log extension

#### `backend/src/domain/activity.py`
- [ ] Add `CERT_REQUESTED` to `ActivityEvent` enum
- [ ] Add metadata entry: `CERT_REQUESTED -> (ACTION_REQUIRED, TargetRole.SM)`
  - Use SM as target_role since QUALITY_LAB role doesn't exist until auth iterations. When auth is added, update to QUALITY_LAB.

### Frontend changes

#### `frontend/src/lib/types.ts`
- [ ] Add `CertWarning` interface: line_item_index, part_number, product_id, qualification_name, reason
- [ ] Add `POSubmitResponse` interface: po (PurchaseOrder), cert_warnings (CertWarning[])

#### `frontend/src/routes/po/[id]/+page.svelte`
- [ ] After submit action: check if response contains cert_warnings
- [ ] Display warnings in a dismissible banner: "The following products are missing certificates for {marketplace}:" followed by the list
- [ ] Warnings are informational, not blocking -- the submit already succeeded

#### `frontend/src/lib/api.ts`
- [ ] Update `submitPO()` return type to `POSubmitResponse`
- [ ] Update `resubmitPO()` return type to `POSubmitResponse`

### Tests (permanent)
- [ ] `backend/tests/test_quality_gate.py` -- service tests:
  - PO with all line items having valid certs for the marketplace: empty warnings
  - PO with line item missing cert: one warning with reason "MISSING"
  - PO with line item having expired cert: one warning with reason "EXPIRED"
  - PO with line item having PENDING cert (not VALID): warning with reason "MISSING" (PENDING doesn't count as valid coverage)
  - PO with line item without product_id: skipped, no warning
  - PO without marketplace: no warnings (gate skipped entirely)
  - PO with multiple line items, mixed coverage: correct warnings for each
- [ ] `backend/tests/test_api_purchase_order.py` (additions):
  - Submit PO with product that has valid cert: response has empty cert_warnings
  - Submit PO with product missing cert: response has cert_warnings with reason "MISSING"
- [ ] `backend/tests/test_api_milestone.py` (additions):
  - Post QC_PASSED milestone on PO with product missing cert: verify CERT_REQUESTED activity created
  - Post QC_PASSED milestone on PO with valid cert: no CERT_REQUESTED activity
  - Post QC_PASSED milestone on PO with no product_id on line items: no CERT_REQUESTED activity

### Tests (scratch)
- [ ] End-to-end flow: create product with qualification, create PO with line item linked to product, submit PO, verify warnings
- [ ] End-to-end flow: create product, PO, milestones through QC_PASSED, verify CERT_REQUESTED activity in feed

## Acceptance criteria
- [ ] PO submit returns `POSubmitResponse` with cert_warnings list
- [ ] Warnings include reason (MISSING or EXPIRED), product info, and qualification name
- [ ] Line items without product_id are skipped (no error, no warning)
- [ ] POs without marketplace skip quality gate entirely
- [ ] QC_PASSED milestone triggers CERT_REQUESTED activity for products with missing certs
- [ ] QC_PASSED milestone creates no activity for products with valid certs
- [ ] Frontend displays cert warnings after PO submit in a dismissible banner
- [ ] All permanent tests pass via `make test`

## Files created
- `backend/src/services/quality_gate.py`
- `backend/tests/test_quality_gate.py`

## Files modified
- `backend/src/dto.py` -- add CertWarningResponse, POSubmitResponse
- `backend/src/routers/purchase_order.py` -- quality gate on submit/resubmit, new response model
- `backend/src/routers/milestone.py` -- CERT_REQUESTED activity on QC_PASSED
- `backend/src/domain/activity.py` -- add CERT_REQUESTED event
- `frontend/src/lib/types.ts` -- add CertWarning, POSubmitResponse
- `frontend/src/lib/api.ts` -- update submit/resubmit return types
- `frontend/src/routes/po/[id]/+page.svelte` -- display cert warnings after submit
- `backend/tests/test_api_purchase_order.py` -- additional test cases
- `backend/tests/test_api_milestone.py` -- additional test cases (if this file exists; create if not)
