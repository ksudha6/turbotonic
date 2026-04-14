# Iteration 048 -- Dashboard updates for Phase 3 features

## Context

The dashboard shows PO, vendor, invoice, and production pipeline data but has no visibility into Phase 3 features. This iteration adds three new dashboard sections: shipment pipeline (counts by status), certificate expiry alerts (within 30 days or already expired), and packaging collection progress (per-marketplace completion). The notification bell also gains routing for the new event types added in iter 047.

## JTBD

- When I open the dashboard, I want to see how many shipments are in each status so that I can prioritize document collection and readiness reviews.
- When certificates are expiring soon, I want to see alerts on the dashboard so that I can request renewals before they expire.
- When I manage packaging across products, I want to see collection progress per marketplace so that I can identify which products still need packaging files.
- When new Phase 3 events occur, I want them to appear in my notification bell filtered to my role so that I stay informed without noise.

## Tasks

### Backend -- Dashboard endpoint
- [ ] Extend dashboard response DTO with new sections:
  - `shipment_pipeline: ShipmentPipelineResponse` -- counts by status
  - `certificate_alerts: list[CertificateAlertResponse]` -- certificates expiring within 30 days or already expired
  - `packaging_progress: list[PackagingProgressResponse]` -- per-marketplace readiness summary

### Backend -- DTOs
- [ ] `ShipmentPipelineResponse` (Pydantic):
  - `draft_count: int`
  - `documents_pending_count: int`
  - `ready_to_ship_count: int`
  - `total_count: int`
- [ ] `CertificateAlertResponse` (Pydantic):
  - `certificate_id: str`
  - `product_id: str`
  - `product_part_number: str`
  - `qualification_type_name: str`
  - `expiry_date: str`
  - `days_until_expiry: int` (negative if already expired)
  - `status: str` (VALID or EXPIRED)
- [ ] `PackagingProgressResponse` (Pydantic):
  - `marketplace: str`
  - `total_specs: int`
  - `collected_specs: int`
  - `pending_specs: int`
  - `completion_percentage: int` (0-100)

### Backend -- Repository queries
- [ ] Shipment pipeline query: `SELECT status, COUNT(*) FROM shipments GROUP BY status`
- [ ] Certificate expiry query: select certificates where `expiry_date` is not null and `expiry_date` is within 30 days of today (either future or past). Join with products and qualification_types for display fields. Compute `days_until_expiry` and `status` (EXPIRED if expiry_date < today, else VALID).
- [ ] Packaging progress query: `SELECT marketplace, status, COUNT(*) FROM packaging_specs GROUP BY marketplace, status`. Aggregate into per-marketplace totals.

### Backend -- Router
- [ ] Update `GET /api/v1/dashboard` response to include new sections
  - Shipment pipeline: always included
  - Certificate alerts: always included (empty list if none expiring)
  - Packaging progress: always included (empty list if no specs exist)
  - Role-based filtering:
    - SM sees all sections
    - FREIGHT_MANAGER sees shipment pipeline only (no cert alerts, no packaging progress)
    - QUALITY_LAB sees certificate alerts only
    - VENDOR sees none of the new sections (existing sections only)

### Frontend -- Dashboard
- [ ] Shipment pipeline widget:
  - Three status cards: Draft, Documents Pending, Ready to Ship
  - Each shows count
  - Click navigates to shipment list filtered by that status
  - Position: below production pipeline section
- [ ] Certificate expiry alerts widget:
  - Table or card list: product part_number, qualification type, expiry date, days until expiry, status pill
  - Status pill: "Expiring" (yellow, within 30 days) or "Expired" (red, past expiry)
  - Sorted by days_until_expiry ascending (most urgent first)
  - Position: below shipment pipeline
- [ ] Packaging collection progress widget:
  - One row per marketplace: marketplace name, progress bar (collected/total), percentage
  - Click navigates to product list filtered by marketplace (or packaging specs list)
  - Position: below certificate alerts

### Frontend -- Notification bell
- [ ] Route new event types to correct roles:
  - QUALITY_LAB users see CERT_REQUESTED in bell
  - FREIGHT_MANAGER users see SHIPMENT_CREATED, DOCUMENT_UPLOADED in bell
  - SM users see all new SM-targeted events in bell
- [ ] New events render with appropriate icons/labels in the notification dropdown:
  - SHIPMENT_CREATED: shipment icon
  - SHIPMENT_READY: checkmark icon
  - CERT_REQUESTED: certificate icon
  - CERT_UPLOADED: certificate icon
  - CERT_EXPIRED: warning icon
  - PACKAGING_COLLECTED: package icon
  - PACKAGING_MISSING: warning icon
  - DOCUMENT_UPLOADED: document icon
- [ ] Mark-read works for new event types (uses existing mark-read endpoint)

### Tests (permanent)
- [ ] Dashboard includes shipment_pipeline with correct counts (test with 0, 1, multiple shipments in different statuses)
- [ ] Dashboard includes certificate_alerts for certificates expiring within 30 days
- [ ] Dashboard includes certificates already expired in alerts
- [ ] Dashboard excludes certificates with no expiry_date from alerts
- [ ] Dashboard excludes certificates expiring more than 30 days from now
- [ ] Certificate alert days_until_expiry is correct (positive for future, negative for past)
- [ ] Dashboard includes packaging_progress with correct counts per marketplace
- [ ] Packaging progress completion_percentage computed correctly (e.g. 3 of 5 = 60)
- [ ] Packaging progress with 0 specs for a marketplace: not included in response
- [ ] Role-based filtering: SM sees all sections, FREIGHT_MANAGER sees shipment pipeline only, QUALITY_LAB sees cert alerts only, VENDOR sees no new sections
- [ ] Notification bell shows new events filtered by target_role

### Tests (scratch)
- [ ] Screenshot: dashboard with shipment pipeline widget
- [ ] Screenshot: dashboard with certificate expiry alerts
- [ ] Screenshot: dashboard with packaging collection progress bars
- [ ] Screenshot: notification bell dropdown showing new event types

## Acceptance criteria
- [ ] Dashboard response includes shipment_pipeline, certificate_alerts, packaging_progress sections
- [ ] Shipment pipeline shows counts by status: DRAFT, DOCUMENTS_PENDING, READY_TO_SHIP
- [ ] Certificate alerts show certificates expiring within 30 days or already expired, sorted by urgency
- [ ] Packaging progress shows per-marketplace collection counts and percentage
- [ ] Role-based dashboard: SM sees all; FREIGHT_MANAGER sees shipments; QUALITY_LAB sees certs; VENDOR sees no new sections
- [ ] Notification bell routes new events to correct roles with appropriate labels
- [ ] All permanent tests pass
