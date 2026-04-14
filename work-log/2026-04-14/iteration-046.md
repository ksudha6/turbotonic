# Iteration 046 -- Shipment document collection and readiness gate

## Context

Shipments can transition to READY_TO_SHIP (iter 043) but nothing enforces that documents, certificates, and packaging are actually complete. This iteration adds a document requirements checklist per shipment (auto-generated PDFs from iters 044-045 plus user-defined uploads), a readiness endpoint that cross-checks documents, quality certificates, and packaging completeness, and a gate that blocks the READY_TO_SHIP transition until all three pass.

## JTBD

- When a shipment moves to DOCUMENTS_PENDING, I want the system to create a checklist of required documents so that I know exactly what needs to be collected.
- When I upload a document against a requirement, I want its status to update so that I can track progress toward readiness.
- When I check whether a shipment is ready, I want a single readiness check that covers documents, certificates, and packaging so that nothing is missed before shipping.
- When all readiness conditions pass, I want to move the shipment to READY_TO_SHIP so that it can proceed to booking.

## Tasks

### Backend -- Schema
- [ ] Create `shipment_document_requirements` table:
  - `id TEXT PRIMARY KEY`
  - `shipment_id TEXT NOT NULL REFERENCES shipments(id)`
  - `document_type TEXT NOT NULL` (user-defined string, e.g. "PACKING_LIST", "COMMERCIAL_INVOICE", "CERTIFICATE_OF_ORIGIN", "BILL_OF_LADING")
  - `is_auto_generated INTEGER NOT NULL DEFAULT 0` (1 for packing list and commercial invoice)
  - `status TEXT NOT NULL DEFAULT 'PENDING'` (PENDING or COLLECTED)
  - `document_id TEXT REFERENCES files(id)` (nullable; populated when file uploaded or auto-generated)
  - `created_at TEXT NOT NULL`
  - `updated_at TEXT NOT NULL`

### Backend -- Domain
- [ ] New file or extend `src/domain/shipment.py`
- [ ] `DocumentRequirementStatus` enum: `PENDING`, `COLLECTED`
- [ ] `ShipmentDocumentRequirement` dataclass:
  - Fields: `id: str`, `shipment_id: str`, `document_type: str`, `is_auto_generated: bool`, `status: DocumentRequirementStatus`, `document_id: str | None`, `created_at: datetime`, `updated_at: datetime`
- [ ] `collect(document_id: str)` method on `ShipmentDocumentRequirement`:
  - Sets document_id, transitions status to COLLECTED, updates updated_at
  - Raises ValueError if document_id is empty or whitespace-only
- [ ] Default document types created on transition to DOCUMENTS_PENDING:
  - `PACKING_LIST` (is_auto_generated=True)
  - `COMMERCIAL_INVOICE` (is_auto_generated=True)
  - SM can add additional requirement types when creating the shipment or after
- [ ] `ReadinessResult` dataclass:
  - `documents_ready: bool` -- all requirements have status COLLECTED or are auto-generated
  - `certificates_ready: bool` -- all products in shipment have valid certs for required qualifications
  - `packaging_ready: bool` -- all products in shipment have packaging files for shipment's marketplace
  - `is_ready: bool` -- all three are true
  - `missing_documents: list[str]` -- document_type values that are PENDING and not auto-generated
  - `missing_certificates: list[dict[str, str]]` -- product_id + qualification_type pairs missing valid certs
  - `missing_packaging: list[dict[str, str]]` -- product_id + spec_name pairs missing files

### Backend -- Repository
- [ ] Add to `ShipmentRepository` or new repo:
  - `save_requirement(req: ShipmentDocumentRequirement)`
  - `list_requirements(shipment_id: str) -> list[ShipmentDocumentRequirement]`
  - `get_requirement(requirement_id: str) -> ShipmentDocumentRequirement | None`
  - `save_requirements_batch(requirements: list[ShipmentDocumentRequirement])` -- bulk insert on status transition

### Backend -- Service
- [ ] New file or extend: `src/services/shipment_service.py`
- [ ] `create_default_requirements(shipment_id: str) -> list[ShipmentDocumentRequirement]`:
  - Creates PACKING_LIST (auto-generated) and COMMERCIAL_INVOICE (auto-generated) requirements
  - Called when shipment transitions to DOCUMENTS_PENDING
- [ ] `check_readiness(shipment: Shipment, requirements: list[ShipmentDocumentRequirement], ...) -> ReadinessResult`:
  - Documents check: all non-auto-generated requirements must have status COLLECTED. Auto-generated requirements are always considered ready (PDFs can be generated on demand).
  - Certificates check: for each product_id in shipment line items, check if all required qualifications (from product_qualifications join) have valid certificates. Uses certificate repository.
  - Packaging check: for each product_id in shipment line items, call packaging readiness for the shipment's marketplace. Uses packaging repository.
  - Returns `ReadinessResult` with details on what's missing

### Backend -- Router
- [ ] `POST /api/v1/shipments/{shipment_id}/requirements` -- add a custom document requirement
  - Request body: `{"document_type": "CERTIFICATE_OF_ORIGIN"}`
  - Only allowed in DRAFT or DOCUMENTS_PENDING status
  - Returns 201 with created requirement
  - Returns 409 if shipment is READY_TO_SHIP
  - Role guard: SM and FREIGHT_MANAGER
- [ ] `POST /api/v1/shipments/{shipment_id}/documents/{requirement_id}/upload` -- upload a document against a requirement
  - Accepts multipart file upload
  - Stores file via file storage service
  - Calls `requirement.collect(document_id)`
  - Returns updated requirement
  - Returns 404 if shipment or requirement not found
  - Returns 409 if shipment is READY_TO_SHIP
  - Role guard: SM, VENDOR, FREIGHT_MANAGER
- [ ] `GET /api/v1/shipments/{shipment_id}/requirements` -- list all document requirements for a shipment
  - Returns list of requirements with status, document_type, is_auto_generated, document_id
  - Role guard: SM, VENDOR, FREIGHT_MANAGER
- [ ] `GET /api/v1/shipments/{shipment_id}/readiness` -- full readiness check
  - Returns `ReadinessResult` with documents_ready, certificates_ready, packaging_ready, is_ready, and missing details
  - Role guard: SM and FREIGHT_MANAGER
- [ ] `POST /api/v1/shipments/{shipment_id}/mark-ready` -- transition DOCUMENTS_PENDING -> READY_TO_SHIP
  - Runs readiness check first; rejects with 409 and readiness details if not ready
  - Returns updated shipment with READY_TO_SHIP status
  - Role guard: SM and FREIGHT_MANAGER
- [ ] Update `POST /api/v1/shipments/{shipment_id}/submit-for-documents` (from iter 043):
  - After status transition, auto-create default document requirements (PACKING_LIST, COMMERCIAL_INVOICE)

### Backend -- Activity log
- [ ] Add `DOCUMENT_UPLOADED` to `ActivityEvent` enum
- [ ] Add EVENT_METADATA entry: `DOCUMENT_UPLOADED`: category `LIVE`, target_role `SM`
- [ ] Record `DOCUMENT_UPLOADED` event when file uploaded against a requirement

### Frontend
- [ ] Shipment detail page: "Documents" section listing all requirements
  - Each requirement shows: document_type, status pill (PENDING grey / COLLECTED green), is_auto_generated badge
  - Auto-generated docs show "Generate" link instead of upload (links to packing list / CI PDF download)
  - Uploaded docs show file name and download link
- [ ] Upload button per non-auto-generated requirement; file picker and upload flow
- [ ] "Add Requirement" button (SM and FREIGHT_MANAGER): text input for document_type
- [ ] Readiness panel on shipment detail:
  - Three sections: Documents, Certificates, Packaging
  - Each shows pass/fail with details on what's missing
  - "Mark Ready to Ship" button enabled only when all three pass
- [ ] Dashboard: shipment counts by status (DRAFT, DOCUMENTS_PENDING, READY_TO_SHIP)

### Tests (permanent)
- [ ] Submit for documents: creates PACKING_LIST and COMMERCIAL_INVOICE requirements automatically
- [ ] Add custom requirement: returns 201, document_type stored correctly
- [ ] Add requirement on READY_TO_SHIP shipment: returns 409
- [ ] Upload document against requirement: status becomes COLLECTED, document_id set
- [ ] Upload against nonexistent requirement: returns 404
- [ ] List requirements: returns all requirements for shipment
- [ ] Readiness check with all documents collected, certs valid, packaging complete: is_ready true
- [ ] Readiness check with missing document: is_ready false, missing_documents populated
- [ ] Readiness check with missing certificate: is_ready false, missing_certificates populated
- [ ] Readiness check with missing packaging: is_ready false, missing_packaging populated
- [ ] Mark ready when ready: status becomes READY_TO_SHIP
- [ ] Mark ready when not ready: returns 409 with readiness details
- [ ] Auto-generated requirements always pass documents_ready check
- [ ] Activity log: DOCUMENT_UPLOADED event recorded on upload

### Tests (scratch)
- [ ] Screenshot: shipment detail with documents section showing mix of collected and pending
- [ ] Screenshot: readiness panel showing pass/fail for each category
- [ ] Screenshot: dashboard with shipment status counts

## Acceptance criteria
- [ ] Default requirements (PACKING_LIST, COMMERCIAL_INVOICE) auto-created on submit-for-documents
- [ ] Custom requirements can be added (user-defined document_type strings)
- [ ] File upload against a requirement transitions it to COLLECTED
- [ ] Auto-generated requirements always pass the documents readiness check
- [ ] Readiness check integrates: documents + certificates + packaging
- [ ] mark-ready blocked unless all three readiness checks pass; returns 409 with details
- [ ] mark-ready transitions DOCUMENTS_PENDING -> READY_TO_SHIP
- [ ] Dashboard shows shipment counts by status
- [ ] Activity log records DOCUMENT_UPLOADED events
- [ ] Role guards: SM and FREIGHT_MANAGER manage; VENDOR can upload docs
- [ ] All permanent tests pass
