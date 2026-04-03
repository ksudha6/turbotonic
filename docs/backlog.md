# Backlog

## PO Confirmation module

- [ ] Auth and sessions (WebAuthn/passkeys + cookie sessions)
- [ ] Roles: SM vs Vendor views (same data, different controls)
- [ ] Overdue status (time-based trigger past required delivery date)
- [ ] In-app notifications / activity feed (status changes with actor, action, timestamp)
- [ ] Mobile layout
- [ ] Custom value approval for reference data dropdowns
- [ ] Dedicated `/api/v1/po/ids` endpoint (cross-page selection beyond 200)
- [ ] Live/historical exchange rates for dashboard
- [ ] Field-level mutability rules tied to lifecycle status
- [ ] Buyer as first-class entity (currently hardcoded)
- [ ] Partial PO acceptance (accept/reject at line-item level)
- [ ] Notifications (in-app alerts for status changes, assignments, deadlines)

## Post-confirmation modules

- [ ] Production status tracking (enabled once PO is Accepted)
- [ ] Invoicing (enabled once PO is Accepted)

## Cosmetic / Data Quality

- [ ] Vendor country should be a dropdown from reference data (currently free-text; allows inconsistent entries like In, India, Ind)
- [ ] HS code format validation (currently free-form string with no checks; at minimum enforce digits/dots, 4+ characters)

## Deferred

- [ ] Compliance fields (LC, export license, packing list, bill of lading)
- [ ] Roles and permissions (beyond SM/Vendor split)
- [ ] Email notifications
- [ ] SM internal notes
