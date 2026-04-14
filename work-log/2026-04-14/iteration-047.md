# Iteration 047 -- Activity log extensions

## Context

The activity log covers PO and invoice events for SM and VENDOR roles. Phase 3 added certificates, packaging, and shipments, but most of their operations do not emit activity events yet. This iteration adds the remaining event types (SHIPMENT_CREATED, SHIPMENT_READY, CERT_REQUESTED, CERT_UPLOADED, CERT_EXPIRED), new target roles (QUALITY_LAB, FREIGHT_MANAGER), and wires event recording into the service methods that are missing it.

## JTBD

- When a shipment is created or becomes ready, I want the relevant roles to be notified so that freight managers and SMs stay informed.
- When a certificate is requested, uploaded, or expires, I want the responsible parties to see it in their activity feed so that quality labs and SMs can act.
- When packaging files are collected or missing, I want SMs to see it in their feed so that they can follow up with vendors.
- When I view the notification bell, I want new event types to appear filtered to my role so that I only see events relevant to me.

## Tasks

### Backend -- Domain (activity.py)
- [ ] Add to `TargetRole` enum: `QUALITY_LAB`, `FREIGHT_MANAGER`
- [ ] Add to `EntityType` enum: `CERTIFICATE`, `SHIPMENT`, `PACKAGING`
- [ ] Add to `ActivityEvent` enum:
  - `SHIPMENT_CREATED`
  - `SHIPMENT_READY`
  - `CERT_REQUESTED`
  - `CERT_UPLOADED`
  - `CERT_EXPIRED`
  - `PACKAGING_COLLECTED` (if not already added in iter 042)
  - `PACKAGING_MISSING` (if not already added in iter 042)
  - `DOCUMENT_UPLOADED` (if not already added in iter 046)
- [ ] Add `EVENT_METADATA` entries for each new event:
  - `SHIPMENT_CREATED`: (`LIVE`, `SM`)
  - `SHIPMENT_READY`: (`LIVE`, `SM`)
  - `CERT_REQUESTED`: (`ACTION_REQUIRED`, `QUALITY_LAB`)
  - `CERT_UPLOADED`: (`LIVE`, `SM`)
  - `CERT_EXPIRED`: (`DELAYED`, `SM`)
  - `PACKAGING_COLLECTED`: (`LIVE`, `SM`) (if not already added)
  - `PACKAGING_MISSING`: (`ACTION_REQUIRED`, `SM`) (if not already added)
  - `DOCUMENT_UPLOADED`: (`LIVE`, `SM`) (if not already added)

### Backend -- Service wiring
- [ ] Shipment creation (iter 043 router): record `SHIPMENT_CREATED` event with entity_type SHIPMENT, entity_id = shipment.id
- [ ] Shipment mark-ready (iter 046 router): record `SHIPMENT_READY` event with entity_type SHIPMENT, entity_id = shipment.id
- [ ] Certificate request (iter 039 quality gate): record `CERT_REQUESTED` event with entity_type CERTIFICATE, entity_id = product.id, detail includes qualification type name
- [ ] Certificate upload (iter 038 router): record `CERT_UPLOADED` event with entity_type CERTIFICATE, entity_id = certificate.id
- [ ] Certificate expiry detection (iter 039 or scheduled): record `CERT_EXPIRED` event with entity_type CERTIFICATE, entity_id = certificate.id, detail includes product name and expiry date
- [ ] Packaging file upload (iter 042 router): record `PACKAGING_COLLECTED` event with entity_type PACKAGING, entity_id = spec.id (if not already wired)
- [ ] Packaging readiness check with missing specs (iter 042): record `PACKAGING_MISSING` event (if not already wired)
- [ ] Document upload against shipment requirement (iter 046 router): record `DOCUMENT_UPLOADED` event (if not already wired)

### Backend -- Notification bell
- [ ] Update activity feed query: include new entity types and events
- [ ] Update unread count query: include new events
- [ ] Ensure target_role filtering works for QUALITY_LAB and FREIGHT_MANAGER users:
  - QUALITY_LAB sees: CERT_REQUESTED events
  - FREIGHT_MANAGER sees: SHIPMENT_CREATED, SHIPMENT_READY, DOCUMENT_UPLOADED events targeted to FREIGHT_MANAGER (if any)
  - SM sees: all SM-targeted events (existing + new)
  - VENDOR sees: existing VENDOR-targeted events (no new VENDOR events in this batch)

### Tests (permanent)
- [ ] TargetRole enum includes QUALITY_LAB and FREIGHT_MANAGER
- [ ] EntityType enum includes CERTIFICATE, SHIPMENT, PACKAGING
- [ ] ActivityEvent enum includes all 8 new events
- [ ] EVENT_METADATA has entries for all new events with correct category and target_role
- [ ] SHIPMENT_CREATED event recorded when shipment is created
- [ ] SHIPMENT_READY event recorded when shipment marked ready
- [ ] CERT_REQUESTED event recorded with correct detail
- [ ] CERT_UPLOADED event recorded with correct entity_id
- [ ] Activity feed filtered by QUALITY_LAB role returns CERT_REQUESTED events
- [ ] Activity feed filtered by SM role returns all SM-targeted events including new ones
- [ ] Unread count includes new event types

### Tests (scratch)
- [ ] None needed; all verification is via API tests

## Acceptance criteria
- [ ] TargetRole has 4 values: SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER
- [ ] EntityType has 5 values: PO, INVOICE, CERTIFICATE, SHIPMENT, PACKAGING
- [ ] ActivityEvent has 20 values (12 existing + 8 new)
- [ ] EVENT_METADATA has entries for all 20 events
- [ ] All certificate, packaging, and shipment operations record the correct activity events
- [ ] Notification bell correctly filters new events by target_role
- [ ] No duplicate event recording (events added in iters 042/046 not re-added)
- [ ] All permanent tests pass
