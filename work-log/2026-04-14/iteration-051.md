# Iteration 051 -- Dashboard redesign

## Context

The dashboard renders the same flat list of PO/invoice summaries, activity feed, and pipeline tables regardless of role. This iteration rebuilds it with role-specific layouts (SM, Vendor, Quality Lab, Freight Manager) using reusable widget components (StatCard, PipelineChart, AlertList, ActivityFeed). Each role sees only the data relevant to their work.

## JTBD (Jobs To Be Done)

- When I open the app as an SM, I want an overview of all pipelines (PO, invoice, shipment, certificates, packaging), so that I can see the full business state at a glance.
- When I open the app as a Vendor, I want to see my POs, invoices, and milestone progress, so that I can act on what needs my attention.
- When I open the app as a Quality Lab user, I want to see certificate requests and expiry alerts, so that I can prioritize testing work.
- When I open the app as a Freight Manager, I want to see the shipment pipeline and document readiness, so that I can track what's ready to ship.

## Tasks

### Widget components

#### StatCard (`frontend/src/lib/components/widgets/StatCard.svelte`)
- [ ] Props: `label`, `value` (number or formatted string), `trend` (optional: up | down | neutral), `trendValue` (optional string like "+12%"), `href` (optional: click navigates), `color` (primary | success | warning | error)
- [ ] Compact card with large value, label below, optional trend indicator
- [ ] Used for: PO count by status, invoice count by status, shipment count by status, active vendor count

#### PipelineChart (`frontend/src/lib/components/widgets/PipelineChart.svelte`)
- [ ] Props: `stages` (array of `{label, count, color}`), `title`
- [ ] Horizontal segmented bar showing distribution across stages
- [ ] Each segment labeled with count, sized proportionally
- [ ] Click on segment filters the relevant list page
- [ ] Used for: PO status pipeline, invoice status pipeline, shipment status pipeline, production milestone pipeline

#### AlertList (`frontend/src/lib/components/widgets/AlertList.svelte`)
- [ ] Props: `items` (array of `{id, title, subtitle, severity, href}`), `title`, `emptyMessage`
- [ ] Compact list of alerts with severity indicators (error/warning/info dots)
- [ ] Each item clickable, navigates to detail page
- [ ] Used for: overdue production, expiring certificates, packaging gaps, shipments missing documents

#### ActivityFeed (`frontend/src/lib/components/widgets/ActivityFeed.svelte`)
- [ ] Props: `entries` (ActivityLogEntry[]), `limit`, `showViewAll`
- [ ] Compact timeline of recent events with category dots, relative timestamps
- [ ] "View all" link to a full activity page or expanded view
- [ ] Replaces the current inline feed rendering on the dashboard

### SM dashboard layout
- [ ] Row 1: StatCards in a 4-column grid
  - Total POs (all statuses), Pending POs (action required), Open Invoices (submitted + approved), Active Shipments (documents_pending + ready_to_ship)
- [ ] Row 2: Two pipeline charts side-by-side
  - PO status pipeline (Draft | Pending | Accepted | Rejected | Revised)
  - Invoice status pipeline (Draft | Submitted | Approved | Paid | Disputed)
- [ ] Row 3: Two pipeline charts side-by-side
  - Shipment pipeline (Draft | Documents Pending | Ready to Ship)
  - Production milestone pipeline (Raw Materials | Production Started | QC Passed | Ready to Ship | Shipped)
- [ ] Row 4: Two alert lists side-by-side
  - Overdue production (PO#, vendor, milestone, days overdue)
  - Certificate alerts (product, qualification, expiry date or "missing")
- [ ] Row 5: Two panels side-by-side
  - Packaging progress (products with incomplete packaging for active POs)
  - Recent activity feed (last 15 events)
- [ ] Responsive: 2 columns on desktop, stacked on mobile

### VENDOR dashboard layout
- [ ] Row 1: StatCards
  - My Pending POs (awaiting vendor accept/reject), My Accepted POs, My Open Invoices, My Milestones (latest)
- [ ] Row 2: My POs by status (pipeline chart, filtered to this vendor)
- [ ] Row 3: My invoices by status (pipeline chart, filtered to this vendor)
- [ ] Row 4: Milestone progress (list of accepted POs with current milestone stage)
- [ ] Row 5: Certificate requests (products from my POs that need certificates)
- [ ] Row 6: Recent activity (filtered to events targeting VENDOR role)
- [ ] Data source: all API calls include vendor scoping from auth context

### QUALITY_LAB dashboard layout
- [ ] Row 1: StatCards
  - Pending Cert Requests, Certificates Expiring (next 30 days), Valid Certificates, Products Needing Certs
- [ ] Row 2: Certificate requests pending (AlertList: product, qualification type, requesting PO)
- [ ] Row 3: Expiring certificates (AlertList: product, cert type, expiry date, days remaining)
- [ ] Row 4: Recent certificate uploads (ActivityFeed filtered to CERT_* events)
- [ ] Data source: certificate and product APIs

### FREIGHT_MANAGER dashboard layout
- [ ] Row 1: StatCards
  - Draft Shipments, Documents Pending, Ready to Ship, Shipped (last 30 days)
- [ ] Row 2: Shipment pipeline (PipelineChart by shipment status)
- [ ] Row 3: Document readiness (AlertList: shipments with missing documents, per-document breakdown)
- [ ] Row 4: Recent shipment activity (ActivityFeed filtered to SHIPMENT_* events)
- [ ] Data source: shipment and activity APIs

### Dashboard data loading
- [ ] Extend or compose existing `fetchDashboard()` to support role-specific data
- [ ] Dashboard page checks current user role and renders the appropriate layout
- [ ] Each widget loads independently (no single blocking fetch for entire dashboard)
- [ ] Error handling per widget: if one widget's data fails, others still render

### Tests (scratch)
- [ ] Screenshot SM dashboard at 1280px (desktop) and 375px (mobile)
- [ ] Screenshot VENDOR dashboard at 1280px and 375px
- [ ] Screenshot QUALITY_LAB dashboard at 1280px and 375px
- [ ] Screenshot FREIGHT_MANAGER dashboard at 1280px and 375px
- [ ] Screenshot dashboard with empty data (new user, no POs/invoices/shipments)
- [ ] Verify permanent Playwright tests still pass

## Acceptance criteria
- [ ] Dashboard renders a role-specific view based on current user
- [ ] SM dashboard shows all 5 rows of widgets covering POs, invoices, shipments, certificates, packaging, and activity
- [ ] VENDOR dashboard shows only vendor-scoped data
- [ ] QUALITY_LAB dashboard focuses on certificate requests and expiry
- [ ] FREIGHT_MANAGER dashboard focuses on shipment pipeline and document readiness
- [ ] All widget components (StatCard, PipelineChart, AlertList, ActivityFeed) are reusable and exist in `frontend/src/lib/components/widgets/`
- [ ] Dashboard is responsive: 2-3 columns on desktop, single column on mobile
- [ ] Empty states handled gracefully per widget
- [ ] All existing permanent Playwright tests pass without modification
