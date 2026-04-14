# Iteration 050 -- Layout and navigation

## Context

The current layout is a flat top nav bar with hardcoded links identical for all four roles and no sidebar, breadcrumbs, or user menu. This iteration replaces it with an AppShell (sidebar + top bar + content), adds role-based menu filtering, breadcrumbs, a user menu, and responsive mobile navigation. It depends on the component library from iteration 049.

## JTBD (Jobs To Be Done)

- When I log in, I want to see only the navigation items relevant to my role, so that I am not confused by features I cannot access.
- When navigating deep into the app (e.g., PO > PO-2024-001 > Edit), I want breadcrumbs showing my path, so that I can orient myself and go back.
- When using the app on a phone, I want the sidebar to collapse and a bottom nav or hamburger menu to appear, so that I can navigate without losing screen space.
- When I want to log out or see my role, I want a user menu in the top bar, so that account actions are always accessible.

## Tasks

### App shell component (`frontend/src/lib/components/AppShell.svelte`)
- [ ] Three-zone layout: sidebar (left), top bar (top), content (main area)
- [ ] Sidebar: fixed 240px width on desktop, contains logo/brand, nav menu, collapse toggle
- [ ] Top bar: breadcrumbs (left), notification bell + user menu (right)
- [ ] Content area: scrollable, receives page slot

### Sidebar navigation (`frontend/src/lib/components/Sidebar.svelte`)
- [ ] Role-based menu items with icons:

**SM (Supply Manager) -- all items visible:**
| Item | Route | Icon concept |
|------|-------|-------------|
| Dashboard | `/dashboard` | grid/chart |
| Purchase Orders | `/po` | clipboard |
| Invoices | `/invoices` | file-text |
| Vendors | `/vendors` | users |
| Products | `/products` | package |
| Certificates | `/certificates` | shield-check |
| Packaging | `/packaging` | box |
| Shipments | `/shipments` | truck |

**VENDOR -- limited view:**
| Item | Route |
|------|-------|
| Dashboard | `/dashboard` |
| My POs | `/po` |
| My Invoices | `/invoices` |
| Milestones | `/po` (filtered) |
| Certificates | `/certificates` |

**QUALITY_LAB -- certificate focus:**
| Item | Route |
|------|-------|
| Dashboard | `/dashboard` |
| Products | `/products` |
| Certificates | `/certificates` |

**FREIGHT_MANAGER -- shipment focus:**
| Item | Route |
|------|-------|
| Dashboard | `/dashboard` |
| Purchase Orders | `/po` |
| Shipments | `/shipments` |

- [ ] Active route highlighting: current route's menu item gets a distinct background color
- [ ] Collapse toggle: sidebar collapses to icon-only (56px width) on user click; state persisted in localStorage
- [ ] Section dividers between logical groups (e.g., "Orders" group, "Logistics" group)

### Breadcrumb component (`frontend/src/lib/components/Breadcrumb.svelte`)
- [ ] Auto-generated from current route path
- [ ] Route-to-label mappings:

| Route pattern | Breadcrumb path |
|---------------|----------------|
| `/dashboard` | Dashboard |
| `/po` | Purchase Orders |
| `/po/new` | Purchase Orders > New |
| `/po/[id]` | Purchase Orders > {po_number} |
| `/po/[id]/edit` | Purchase Orders > {po_number} > Edit |
| `/invoices` | Invoices |
| `/invoice/[id]` | Invoices > {invoice_number} |
| `/vendors` | Vendors |
| `/vendors/new` | Vendors > New |
| `/products` | Products |
| `/products/new` | Products > New |
| `/products/[id]/edit` | Products > {part_number} > Edit |
| `/certificates` | Certificates |
| `/certificates/[id]` | Certificates > {cert_number} |
| `/packaging` | Packaging |
| `/packaging/[id]` | Packaging > {spec_name} |
| `/shipments` | Shipments |
| `/shipments/new` | Shipments > New |
| `/shipments/[id]` | Shipments > {shipment_number} |

- [ ] Dynamic segments ([id]) resolve to entity name/number via page data
- [ ] Each breadcrumb segment is a link except the last (current page)

### Top bar (`frontend/src/lib/components/TopBar.svelte`)
- [ ] Left: Breadcrumb component
- [ ] Right: NotificationBell (from iter 049, rebuilt with Dropdown), UserMenu
- [ ] Fixed at top of content area

### User menu (`frontend/src/lib/components/UserMenu.svelte`)
- [ ] Trigger: avatar circle with initials + chevron
- [ ] Dropdown contents: display name, role badge (using Badge component), divider, Logout button
- [ ] Logout calls `/api/v1/auth/logout` and redirects to login page

### Responsive behavior
- [ ] Breakpoint: 768px
- [ ] Below 768px: sidebar hidden, hamburger icon in top bar opens sidebar as overlay (slide-in from left)
- [ ] Below 768px: optionally show bottom nav bar with 4-5 primary items (role-dependent)
- [ ] Sidebar overlay: closes on route navigation, closes on overlay click
- [ ] Top bar adjusts: breadcrumbs truncated or hidden on very narrow screens (below 480px)

### Layout integration (`frontend/src/routes/+layout.svelte`)
- [ ] Replace current top nav with AppShell
- [ ] AppShell wraps the page slot
- [ ] Current user loaded from `/api/v1/auth/me` in layout load function
- [ ] User context available to all pages via SvelteKit layout data
- [ ] Redirect to `/login` if not authenticated

### Tests (scratch)
- [ ] Screenshot sidebar at 1280px: SM role (all items), VENDOR role, QUALITY_LAB role, FREIGHT_MANAGER role
- [ ] Screenshot sidebar collapsed state (icon-only)
- [ ] Screenshot breadcrumbs on PO detail page, invoice detail page, product edit page
- [ ] Screenshot user menu open state
- [ ] Screenshot mobile layout at 375px: hamburger menu, sidebar overlay open
- [ ] Screenshot mobile layout at 768px: tablet breakpoint
- [ ] Verify existing permanent Playwright tests still pass

## Acceptance criteria
- [ ] AppShell renders sidebar + top bar + content on desktop (above 768px)
- [ ] Sidebar shows only role-appropriate menu items
- [ ] Active route is visually highlighted in sidebar
- [ ] Sidebar collapses to icon-only mode; state persists across page navigations
- [ ] Breadcrumbs render correct path for every route listed above
- [ ] Dynamic breadcrumb segments show entity identifiers (po_number, invoice_number, etc.), not raw UUIDs
- [ ] User menu shows display name, role badge, and working logout
- [ ] Mobile (below 768px): sidebar hidden, hamburger opens overlay, overlay closes on navigation
- [ ] All existing permanent Playwright tests pass without modification
