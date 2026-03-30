# Backlog

## PO Confirmation module

- [ ] Auth and sessions (WebAuthn/passkeys + cookie sessions)
- [ ] Roles: SM vs Vendor views (same data, different controls)
- [ ] Overdue status (time-based trigger past required delivery date)
- [ ] In-app notifications / activity feed (status changes with actor, action, timestamp)
- [ ] Mobile layout
- [ ] Label resolution on PO detail view (raw codes to human-readable)
- [ ] Custom value approval for reference data dropdowns
- [ ] Dedicated `/api/v1/po/ids` endpoint (cross-page selection beyond 200)
- [ ] Live/historical exchange rates for dashboard
- [ ] Field-level mutability rules tied to lifecycle status
- [ ] Buyer as first-class entity (currently hardcoded)

## Post-confirmation modules

- [ ] Production status tracking (enabled once PO is Accepted)
- [ ] Invoicing (enabled once PO is Accepted)

## Deferred

- [ ] Compliance fields (LC, export license, packing list, bill of lading)
- [ ] Roles and permissions (beyond SM/Vendor split)
- [ ] Email notifications
- [ ] SM internal notes
