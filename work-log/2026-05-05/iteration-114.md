# Iteration 114

## Context

- Six roles exist: `ADMIN`, `SM`, `VENDOR`, `FREIGHT_MANAGER`, `QUALITY_LAB`, `PROCUREMENT_MANAGER`. `/dashboard` today only branches three ways: `ADMIN`+`SM`+`PM` share one operational 4-KPI grid, `FM` has its own 4-KPI grid, the rest hit a placeholder.
- `VENDOR` and `QUALITY_LAB` have no dashboard.
- `ADMIN` is currently aliased to `SM`. Iter 107 routed six `USER_*` events and iter 108 routed six `BRAND_*` events to `TargetRole.ADMIN`, but the SM grid surfaces neither.
- `PROCUREMENT_MANAGER` shares the SM grid; its activity panel is near-empty because no events fan out to PM.
- **Production milestone state machine** (`backend/src/domain/milestone.py`): strict sequence `RAW_MATERIALS → PRODUCTION_STARTED → QC_PASSED → READY_FOR_SHIPMENT → SHIPPED`. `MILESTONE_OVERDUE_THRESHOLDS`: 7d / 7d / 3d / 3d (SHIPPED is terminal, never overdue). `READY_FOR_SHIPMENT` is the FM hand-off signal: production + QC done, batch packed. `QC_PASSED` is the QL hand-off signal: emits `CERT_REQUESTED` for products lacking valid certs (iter 039).
- **Shipment state machine** (`backend/src/domain/shipment.py`): `DRAFT → DOCUMENTS_PENDING → READY_TO_SHIP → BOOKED → SHIPPED`. No `DELIVERED` state today; no `CUSTOMS_*` state today.
- `ProductionStageSummary` aggregate (`po_summary_by_status`, `_IN_PRODUCTION_MILESTONES`) already returns counts per milestone for the existing grid. This iter reuses it across roles.
- This iter is a definition iter. No code lands. Output is a per-role read model: KPI tile set + secondary panels + primary action target. Implementation iters split per role downstream. New backend modules (e.g. delivered tracking, customs tracking) are deferred — dashboard surfaces them as placeholders so the layout doesn't churn when those modules land.

## JTBD

As a `<role>` user, I open `/dashboard` to see only the work I am responsible for, ranked by what is blocking value, so I can act without scanning the whole system.

Per-role specialisations (from user clarification):

- **ADMIN** — tech admin with access to all data and all actions. Vendor-management actions are pending and ship later; the dashboard surfaces vendor data read-only until then. ADMIN sees the union view: every role's KPIs visible, plus user + brand estate health.
- **PM (Procurement Manager)** — everything procurement, cross-vendor: POs, invoices, pending-for-shipment, quality pending. PM owns the procurement pipeline end-to-end up to FM hand-off.
- **SM (Supply Manager)** — vendor-scoped: POs, invoices, pending-for-shipment, all up to and including `READY_FOR_SHIPMENT` (FM takes it from there). SM works *in the context of a vendor*.
- **QUALITY_LAB** — pending certificates for POs that require qualification. Single-purpose queue.
- **FREIGHT_MANAGER** — shipment lifecycle, five stages: pending-for-shipment → booked → in transit → customs pending → delivered.
- **VENDOR** — their own POs, their own invoices, their own tasks (action queue). Vendor-scoped automatically by `vendor_id` on the session — no selector.

## Production milestone integration

Milestones surface in three ways across dashboards:

1. **Stage breakdown panel** — count of ACCEPTED PROCUREMENT POs per `MILESTONE_ORDER` stage. Reuses `ProductionStageSummary`. Click a stage → `/po?milestone=<stage>` (route filter does not exist yet; backlog).
2. **Overdue alert KPI** — count of POs whose latest milestone is past its `MILESTONE_OVERDUE_THRESHOLDS` value. Reuses iter 082 `is_overdue` / `days_overdue` computation.
3. **Hand-off queues** — POs at `QC_PASSED` (QL queue: products needing certs) and POs at `READY_FOR_SHIPMENT` (FM queue: batches awaiting shipment creation).

The `SHIPPED` milestone marks production exit; the shipment state machine takes over. Roles whose work starts after `READY_FOR_SHIPMENT` (FM) read shipment statuses, not milestones. Roles whose work ends at `READY_FOR_SHIPMENT` (SM, PM until FM hand-off) read milestones.

## Per-role metrics

Each role gets: 4-5 KPI tiles, 1-3 secondary panels, 1 activity feed scoped to that role's `TargetRole`. Tiles deep-link to a pre-filtered list. Modules that don't exist yet (DELIVERED, CUSTOMS_*) ship as placeholder tiles displaying `—` until their backend lands.

### PM (Procurement Manager) — primary owner of the procurement pipeline

PM is cross-vendor, end-to-end procurement. Diverges from today's SM-aliased grid.

| Slot | Metric | Source | Click target |
|------|--------|--------|--------------|
| KPI 1 | Pending POs (DRAFT + PENDING + MODIFIED) | `purchase_orders.status IN (DRAFT, PENDING, MODIFIED)` | `/po?status=DRAFT,PENDING,MODIFIED` |
| KPI 2 | In production | latest milestone IN `_IN_PRODUCTION_MILESTONES` | `/po?status=ACCEPTED&production=true` |
| KPI 3 | Quality pending | POs at `QC_PASSED` with `CERT_REQUESTED` outstanding | `/po?milestone=QC_PASSED&cert=pending` |
| KPI 4 | Pending for shipment | POs at `READY_FOR_SHIPMENT` with no shipment yet, OR with shipments still in `DRAFT`/`DOCUMENTS_PENDING` | `/po?milestone=READY_FOR_SHIPMENT&shipment=pending` |
| KPI 5 | Outstanding A/P (USD) | invoices in `APPROVED` not yet `PAID` | `/invoices?status=APPROVED` |
| Panel A | Production stage breakdown (5 bars: RAW_MATERIALS / PRODUCTION_STARTED / QC_PASSED / READY_FOR_SHIPMENT / SHIPPED) | `ProductionStageSummary` | per-bar `/po?milestone=<stage>` |
| Panel B | Overdue milestones (count + per-row PO + days_overdue) | iter 082 | per-row PO link |
| Panel C | Recent activity, role-curated | `target_role=PROCUREMENT_MANAGER` (today empty — see backend gaps) | activity entry |

Notes: PM is the only role whose KPI 4 covers both "ready milestone" and "shipment not yet created/staged" — this is the bridge KPI between production exit and FM hand-off.

### SM (Supply Manager) — vendor-scoped subset of PM

SM works in the context of a vendor. Dashboard requires a vendor selector at the top (header dropdown). All KPIs and panels are scoped to the selected vendor. This is a behavioural change from today's all-vendor grid.

| Slot | Metric | Source | Click target |
|------|--------|--------|--------------|
| Header | Vendor selector (active vendors, sticky in user prefs) | `/vendors?status=ACTIVE` | n/a |
| KPI 1 | Pending POs (vendor-scoped) | as PM, filtered by `vendor_id` | `/po?vendor=<id>&status=DRAFT,PENDING,MODIFIED` |
| KPI 2 | In production (vendor-scoped) | as PM, filtered by `vendor_id` | `/po?vendor=<id>&production=true` |
| KPI 3 | Quality pending (vendor-scoped) | as PM, filtered | `/po?vendor=<id>&milestone=QC_PASSED&cert=pending` |
| KPI 4 | Pending for shipment (vendor-scoped, capped at `READY_FOR_SHIPMENT` — SM does not see post-handoff state) | latest milestone = `READY_FOR_SHIPMENT` AND no shipment OR shipment in `DRAFT`/`DOCUMENTS_PENDING` | `/po?vendor=<id>&milestone=READY_FOR_SHIPMENT` |
| KPI 5 | Outstanding A/P (vendor-scoped, USD) | invoices for vendor, status `APPROVED` | `/invoices?vendor=<id>&status=APPROVED` |
| Panel A | Production stage breakdown for vendor (4 bars: stops at READY_FOR_SHIPMENT — post-shipment is FM's view) | `ProductionStageSummary` filtered by `vendor_id` | per-bar `/po?vendor=<id>&milestone=<stage>` |
| Panel B | Overdue milestones for vendor | iter 082 filtered | per-row PO link |
| Panel C | Recent activity, vendor-scoped | `target_role=SM` filtered by entity-vendor join | activity entry |

Notes: "up to that milestone" interpreted as up to and including `READY_FOR_SHIPMENT`. After that the PO is FM's responsibility on the shipment side. SM still sees the PO in lists, but the dashboard surface ends there.

### QUALITY_LAB — narrow cert queue

QL has one job: process certification work for POs that require a qualification.

| Slot | Metric | Source | Click target |
|------|--------|--------|--------------|
| KPI 1 | Cert requests open | `CERT_REQUESTED` activity events with no superseding `CERT_UPLOADED` for the same (product, marketplace) | `/certificates?status=requested` (route does not exist yet) |
| KPI 2 | Certs PENDING (uploaded by vendor, awaiting validation) | `certificates.status=PENDING` | `/certificates?status=PENDING` |
| KPI 3 | Certs expiring within 30 days | `certificates.expiry_date BETWEEN now AND now+30d AND status IN (VALID, APPROVED)` | `/certificates?expiring=30` |
| KPI 4 | Certs expired | computed `EXPIRED` | `/certificates?status=expired` |
| Panel A | POs at `QC_PASSED` awaiting cert (drives KPI 1) | latest milestone = `QC_PASSED` AND any line product lacks valid cert for marketplace | per-row PO link with cert-summary chip |
| Panel B | Recent CERT_REQUESTED events | activity log | activity entry |
| Activity | QL-scoped feed | `target_role=QUALITY_LAB` | activity entry |

Open question: does QL pre-validate cert content before FM final-approves (iter 105)? If yes, KPI 2 splits into "to validate" (QL) and "validated awaiting FM approval". Today's code has only one explicit approval step, owned by FM. State your model and we'll align.

### FREIGHT_MANAGER — five-stage shipment lifecycle

FM owns from `READY_FOR_SHIPMENT` milestone hand-off through final delivery. The user's brief lists five stages; map them onto current + future state.

| Slot | Metric | Source | Click target |
|------|--------|--------|--------------|
| KPI 1 | Pending for shipment | POs at `READY_FOR_SHIPMENT` with no shipment yet, OR shipment in `DRAFT` / `DOCUMENTS_PENDING` / `READY_TO_SHIP` | `/shipments?stage=pending` |
| KPI 2 | Shipments booked | `shipments.status=BOOKED` | `/shipments?status=BOOKED` |
| KPI 3 | Shipments in transit | `shipments.status=SHIPPED` AND no delivered timestamp | `/shipments?status=SHIPPED` |
| KPI 4 | Customs pending | _module pending_ — placeholder tile rendering `—` | n/a until module lands |
| KPI 5 | Shipments delivered | _module pending_ — placeholder tile rendering `—` | n/a until module lands |
| Panel A | Booked shipments missing transport metadata (`vessel_name` OR `voyage_number` IS NULL) | iter 106 | per-row shipment link |
| Panel B | Booked/shipped without declaration (`declared_at` IS NULL) | iter 106 | per-row shipment link |
| Panel C | Certs awaiting your sign-off (`status=VALID`) | iter 105 | per-row cert link on `/products/[id]/edit` |
| Activity | FM-scoped feed | `target_role=FREIGHT_MANAGER` (today only `CERT_UPLOADED` would naturally route here — needs fan-out, see backend gaps) | activity entry |

KPI 4 (Customs pending) and KPI 5 (Shipments delivered) require new shipment-state-machine extensions (a `CUSTOMS_*` interim state and a `DELIVERED` terminal state). Capture as separate iters per user direction "we will add their modules slightly later". Tiles ship now as placeholders so the layout is stable when modules land.

KPI 1 collapses two existing FM tiles ("Ready batches", "Docs missing") into one "Pending for shipment" tile per the brief. The detail (which sub-state) lives in the click-through list, not on the dashboard.

### ADMIN — union view + estate health

ADMIN is the tech admin. Sees all role-scoped panels and adds user/brand health KPIs. Vendor-management UI is pending (separate iter); for now ADMIN reads vendor data through the same lists as everyone else.

| Slot | Metric | Source | Click target |
|------|--------|--------|--------------|
| KPI 1 | Pending POs (system-wide) | as PM KPI 1 | `/po?status=DRAFT,PENDING,MODIFIED` |
| KPI 2 | Pending for shipment (system-wide) | as PM KPI 4 | `/po?milestone=READY_FOR_SHIPMENT&shipment=pending` |
| KPI 3 | Outstanding A/P (USD, system-wide) | as PM KPI 5 | `/invoices?status=APPROVED` |
| KPI 4 | Pending invites | `users.status=PENDING` | `/users?status=PENDING` |
| KPI 5 | Inactive brands/vendors with active POs (data-quality alarm) | `brands` or `vendors` deactivated AND open POs | `/brands?status=INACTIVE` or `/vendors?status=INACTIVE` |
| Panel A | Production stage breakdown (system-wide, all 5 stages including SHIPPED) | `ProductionStageSummary` | per-bar `/po?milestone=<stage>` |
| Panel B | Shipment status breakdown (5 stages: DRAFT / DOCUMENTS_PENDING / READY_TO_SHIP / BOOKED / SHIPPED) | new `ShipmentStatusSummary` aggregate | per-bar `/shipments?status=<status>` |
| Panel C | Recent USER_* + BRAND_* events | `target_role=ADMIN` | activity entry |
| Activity | Full ADMIN feed | `target_role=ADMIN` | activity entry |

ADMIN's "see all data" property is satisfied by deep-link routes, not by surfacing every other role's panels on the dashboard itself. Otherwise the dashboard becomes unreadable. If you want a "view as <role>" toggle, capture as a separate iter — it changes the auth shape (impersonation, audit), not just the dashboard read model.

### VENDOR — POs, invoices, tasks

VENDOR is auto-scoped to their `vendor_id` (existing `check_vendor_access` pattern). Three concerns: their POs, their invoices, their action queue ("tasks"). A task is anything `target_role=VENDOR AND category=ACTION_REQUIRED` whose underlying entity is still in the action-required state — derived, not persisted.

| Slot | Metric | Source | Click target |
|------|--------|--------|--------------|
| KPI 1 | POs awaiting your response | PENDING + MODIFIED where `last_actor_role=SM` | `/po?awaiting=me` |
| KPI 2 | Drafts to invoice | ACCEPTED PROCUREMENT POs with `remaining_qty > 0` | `/invoices/new` (or `/po?invoiceable=me`) |
| KPI 3 | Disputed invoices | `invoices.status=DISPUTED` | `/invoices?status=DISPUTED` |
| KPI 4 | Tasks open | sum of action-required entities (KPI 1 + KPI 3 + shipments to populate + certs to upload + milestones to post) | `/tasks` (route does not exist yet) |
| Panel A | Tasks list (action queue) | combined view: POs awaiting response, invoices to submit, invoices to resolve, shipments to populate (DRAFT or DOCUMENTS_PENDING with PENDING user-defined doc reqs), certs to upload (products on accepted POs lacking VALID/APPROVED cert for marketplace), milestones to post (active POs where next milestone is due) | per-row entity link |
| Panel B | Production milestones due | latest milestone per active PO + threshold check (drives "milestones to post" rows in Panel A) | per-row PO link |
| Panel C | Recent activity, vendor-scoped | `target_role=VENDOR` filtered to vendor's own entities | activity entry |

Notes:
- VENDOR has no production stage breakdown panel: they don't manage portfolio shape, they execute milestones one at a time.
- "Tasks" is the primary affordance. Panel A is the densest part of the dashboard. KPI 4 is the headline number.
- Backend `/dashboard/summary` has no VENDOR branch today. Need a `_vendor_summary()` helper. The `vendor_id` already flows through the legacy `/dashboard/` aggregate, so the join shapes are known.

## Cross-cutting decisions

- **All KPI tiles deep-link.** No tile shows a number without a list to drill into. This is the contract that distinguishes a dashboard from a status page.
- **Single `/dashboard/summary` endpoint, role-branched.** Same shape as today: a discriminated union per role. Do not split into `/dashboard/admin`, `/dashboard/vendor`, etc.
- **Placeholder tiles for unbuilt modules.** FM KPI 4 + KPI 5 ship as `—` placeholders so the grid layout is stable when CUSTOMS_* and DELIVERED modules land. No backend stub.
- **No new event types.** Where activity panels are sparse (PM, FM), the fix is fan-out routing in `EVENT_METADATA`, not new events.
- **No new persistence.** Where derived state is needed (cert EXPIRED, vendor-scoped remaining-qty, milestone hand-off detection), surface it via SQL expression, not a column.
- **List-route filters do not exist for several KPI click-throughs.** The dashboard iter must NOT introduce them — they belong to their respective list-page iters. Dashboard click-throughs can land before the filters and degrade to the unfiltered list, which is acceptable for one iter.

## Out of scope

- Implementation. Each role becomes its own iter (FM extension and PM split can ship together since they overlap).
- Notification-bell routing changes (iter 048 backlog).
- `CUSTOMS_*` and `DELIVERED` shipment states (separate iters per user).
- A `/brands` frontend route (Phase 4.x iter independent of dashboards).
- "View as <role>" impersonation toggle for ADMIN.
- Per-user dashboard widget reordering / customisation.
- Real-time push (everything stays request/response on page load).

## Backend gaps to resolve before implementation iters land

Order of dependency:

1. **PM / SM event fan-out.** `PROCUREMENT_MANAGER` and `SM` activity feeds are sparse. Decide which existing events fan out where in `EVENT_METADATA`.
2. **Shipment-status aggregate query** (`ShipmentStatusSummary`). Mirrors `po_summary_by_status` shape. Drives ADMIN Panel B and FM KPIs 1-3 if they share a query.
3. **Milestone-to-shipment join query** for "POs at READY_FOR_SHIPMENT with no/staged shipment". Single SQL, parameterised by vendor_id (None for PM/ADMIN, set for SM).
4. **Cert-pending aggregate** for QL KPI 1 + Panel A. Joins `purchase_orders` (latest milestone = QC_PASSED) × line items × products × qualifications × certificates. Today's per-PO `cert_warnings` query exists; aggregate it.
5. **Certificate expiry queries.** No API surface today for "expiring in N days" or "expired". `EXPIRED` is computed at DTO time; aggregate KPI counts need a SQL expression that re-derives it.
6. **FM event fan-out.** `CERT_UPLOADED` should fan out to `FREIGHT_MANAGER` so the cert-approval queue panel matches the inbox.
7. **Inactive-but-referenced drift scans.** ADMIN KPI 5. Today partially covered by deactivate-time 409s; no post-hoc scan.
8. **Vendor-scoped dashboard summary endpoint.** Today `/dashboard/summary` does not accept `vendor_id` for the SM branch. SM iter must add it.

## Tests

### Existing test impact

No code lands in this iter. No tests change.

## Open questions

1. **QL approval pre-step** — does QL validate cert content before FM final-approves, or is QL purely a notification target?
2. **SM vendor selector behaviour** — single-vendor at a time (sticky in user prefs), or multi-vendor multi-select with combined view? Single-vendor is simpler and matches the brief literally.
3. **`Customs pending` semantics** — interim shipment state between SHIPPED and DELIVERED, or a separate gate (e.g. customs documents collected) that runs in parallel with transit? Definition affects state-machine shape when that module lands.
4. **`Delivered` confirmation source** — manual mark-delivered by FM, carrier webhook, or POD upload? Affects state-machine shape and FM KPI 5 query.
5. **VENDOR `/tasks` route** — does VENDOR get a dedicated tasks page (KPI 4 click-through), or does the dashboard panel suffice and the KPI deep-links to a filtered activity feed?

## Notes

Six roles get distinct dashboard read models: ADMIN, PM, SM, QL, FM, and VENDOR no longer alias each other. Production milestones surface in three ways -- stage breakdown panel, overdue alert KPI, and hand-off queues at QC_PASSED (QL inbox) and READY_FOR_SHIPMENT (FM inbox). SM is a vendor-scoped subset of PM, capped at READY_FOR_SHIPMENT via a header-level vendor selector; post-handoff state is FM's surface. VENDOR's primary affordance is the Tasks queue, derived from ACTION_REQUIRED activity events filtered to entities still in that state; KPI 4 "Tasks open" is the headline number. FM gets five-stage shipment lifecycle KPIs with CUSTOMS_* and DELIVERED tiles rendering as placeholder `—` until those state-machine extensions land in their own iters. ADMIN stays readable by combining PM-style procurement numbers with estate health (pending invites, inactive-but-referenced drift), capped at three secondary panels; no "view as role" toggle ships in this iter. The single `/dashboard/summary` endpoint stays role-branched; sparse activity panels fix via fan-out routing in EVENT_METADATA, not new event types. Eight backend gaps are queued in dependency order and must be resolved before any per-role implementation iter can run.
