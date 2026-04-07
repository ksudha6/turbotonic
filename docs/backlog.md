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
