# Iteration 055 -- Mobile pass

## Context

All pages use the design system, but responsive behavior has not been tested end-to-end at device sizes. Tables overflow without horizontal scroll, touch targets are undersized, modals don't adapt to small screens, and filter bars wrap ungracefully. This iteration is a dedicated fix pass at 375px and 768px across every page, covering touch targets, table scroll, form layout, modal full-screen behavior, and mobile navigation.

## JTBD (Jobs To Be Done)

- When using the app on my phone, I want every page to be usable without horizontal scrolling of the page itself, so that I can work on the go.
- When tapping buttons or links on mobile, I want touch targets of at least 44px, so that I don't mis-tap.
- When viewing a data table on mobile, I want to see the most important columns and horizontally scroll for the rest, so that I don't lose context.
- When filling out a form on mobile, I want full-width single-column inputs, so that I can type without fighting the layout.
- When a modal opens on mobile, I want it to fill the screen, so that I have room to read and interact.

## Tasks

### Touch targets audit
- [ ] Audit every interactive element across all pages at 375px
- [ ] Elements to check: all Button instances, all links, checkbox inputs, select inputs, tab headers, dropdown items, sidebar menu items, pagination controls, notification bell, user menu
- [ ] Minimum size: 44x44px (Apple HIG) for tap targets
- [ ] Fix any elements below 44px: increase padding, min-height, or min-width

### Table mobile behavior
- [ ] DataTable: wrap in a horizontally scrollable container on mobile
- [ ] Priority columns: first 2-3 columns stick or remain visible; remaining columns scroll
- [ ] Per-page column visibility adjustments:

| Page | Always visible (mobile) | Scrollable |
|------|------------------------|------------|
| PO list | PO Number, Status | Type, Vendor, Issued Date, Delivery Date, Total Value, Production |
| Invoice list | Invoice #, Status | PO #, Vendor, Subtotal, Created |
| Vendor list | Name, Status | Country, Type, Actions |
| Product list | Part Number, Vendor | Description, Requires Cert, Actions |
| Certificate list | Cert #, Status | Product, Qualification, Issuer, Issue Date, Expiry Date, Market |
| Packaging list | Spec Name, Status | Product, Marketplace, Actions |
| Shipment list | Shipment #, Status | PO #, Marketplace, Created |

- [ ] Consider expandable rows on mobile: tap a row to show hidden columns inline below the row (optional, if horizontal scroll feels insufficient)

### Form mobile layout
- [ ] All form sections: single column layout below 768px
- [ ] All inputs: full width (100%)
- [ ] FormSection: reduce horizontal padding on mobile
- [ ] LineItemEditor: horizontal scroll on mobile, each row's fields stay in a single scrollable row
- [ ] File upload zone: full width, taller drop zone on mobile (easier to tap)

### Modal mobile behavior
- [ ] Below 768px: modal renders full-screen (inset: 0, border-radius: 0, max-height: 100vh)
- [ ] Modal header becomes sticky at top of full-screen view
- [ ] Modal footer (actions) becomes sticky at bottom
- [ ] Scrollable body between header and footer

### Navigation mobile behavior
- [ ] Sidebar: hidden below 768px, hamburger icon in top bar opens slide-in overlay
- [ ] Slide-in overlay: full height, 280px width, slides from left, semi-transparent backdrop
- [ ] Closes on: route navigation, backdrop click, Escape key, swipe left (optional)
- [ ] Bottom nav (optional alternative to hamburger):
  - 4-5 role-dependent primary items
  - Active route highlighted
  - Fixed at bottom, 56px height, above page content
  - Icons with labels below
- [ ] Top bar on mobile: compact height (48px), breadcrumbs hidden below 480px, only show notification bell and hamburger

### Dashboard mobile layout
- [ ] StatCards: 2 columns at 768px, 1 column at 375px
- [ ] PipelineChart: stacked segments instead of horizontal bar at 375px (or simplified bar)
- [ ] AlertList: full width, compact padding
- [ ] ActivityFeed: full width
- [ ] All widgets: no horizontal overflow

### Detail pages mobile layout
- [ ] InfoGrid: single column below 768px
- [ ] Tabs: scrollable horizontal tab bar (tabs don't wrap to new line, swipe to see more)
- [ ] Action buttons: full width, stacked vertically below 768px
- [ ] MilestoneTimeline: compact vertical layout instead of horizontal at 375px

### Scroll behavior
- [ ] Page-level vertical scroll only (no horizontal page scroll on any page)
- [ ] Tables: horizontal scroll within their container only
- [ ] Modals: vertical scroll within modal body
- [ ] Sidebar overlay: body scroll locked while overlay is open

### Specific known issues to fix

| Page | Issue | Fix |
|------|-------|-----|
| PO list | Filter bar wraps ungracefully at narrow widths | Stack filters vertically or use a collapsible filter panel ("Filters" toggle) |
| PO list | Bulk toolbar wraps and overlaps | Stack selection count and actions vertically |
| PO detail | Info grid columns don't collapse | Use InfoGrid responsive behavior |
| PO detail | Line items table overflows without scroll | DataTable horizontal scroll |
| PO form | Line item editor overflows | Horizontal scroll container |
| Invoice list | Date range inputs too narrow | Full width on mobile |
| Dashboard | Summary cards don't stack | CSS grid responsive adjustment |
| Vendor list | Deactivate/Reactivate buttons too small | 44px min touch target |
| Product list | Edit button too small | 44px min touch target |
| Notification bell dropdown | Dropdown overflows viewport on small screens | Full-width dropdown on mobile, positioned below top bar |

### Tests (scratch)
- [ ] Screenshot every page at 375px (iPhone SE):
  - Login page
  - Dashboard (SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER)
  - PO list (with filters open, with bulk selection)
  - PO detail (each tab)
  - PO create form
  - Invoice list
  - Invoice detail
  - Vendor list
  - Vendor create
  - Vendor detail
  - Product list
  - Product create
  - Product detail
  - Certificate list
  - Certificate detail
  - Certificate upload
  - Packaging spec list
  - Packaging spec create
  - Shipment list
  - Shipment detail (readiness tab)
  - Shipment create
- [ ] Screenshot every page at 768px (iPad):
  - Same set as 375px
- [ ] Screenshot mobile navigation: hamburger menu open, sidebar overlay
- [ ] Screenshot modal on mobile: full-screen behavior
- [ ] Tap target audit: screenshot showing touch target boundaries on interactive elements
- [ ] Verify all permanent Playwright tests still pass

## Acceptance criteria
- [ ] Every page renders without horizontal page scroll at 375px and 768px
- [ ] Every interactive element has a minimum touch target of 44x44px
- [ ] Tables horizontally scroll within their container on mobile
- [ ] Forms render single-column with full-width inputs below 768px
- [ ] Modals render full-screen below 768px with sticky header/footer
- [ ] Sidebar collapses to hamburger below 768px; overlay opens and closes correctly
- [ ] Dashboard widgets stack vertically on mobile
- [ ] Detail page info grids collapse to single column on mobile
- [ ] Tab bars are horizontally scrollable on mobile (no wrapping)
- [ ] MilestoneTimeline renders in compact vertical layout on mobile
- [ ] Notification dropdown doesn't overflow viewport on mobile
- [ ] Filter bars collapse or stack on mobile
- [ ] Every page usable on iPhone SE (375px) and iPad (768px)
- [ ] All existing permanent Playwright tests pass without modification
