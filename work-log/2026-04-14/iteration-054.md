# Iteration 054 -- Form pages redesign

## Context

All view pages now use the design system, but every form (PO create/edit, vendor create, product create/edit, invoice create dialog) still uses raw HTML inputs with inline `.form-grid` CSS and no validation UX. This iteration rebuilds all existing forms with the component library (Input, Select, TextArea, Button, FormSection) and builds the three new Phase 3 forms (shipment create, certificate upload, packaging spec create). It also adds a reusable LineItemEditor and FileUpload component.

## JTBD (Jobs To Be Done)

- When filling out a form, I want clear section headers grouping related fields, so that I can process the form in logical chunks.
- When I enter invalid data, I want inline error messages next to the field, so that I can fix issues without reading a summary at the top.
- When a field is required, I want a visible indicator, so that I know before submitting.
- When adding line items to a PO or shipment, I want a dynamic table where I can add/remove rows, so that I can adjust the order.
- When uploading a file (certificate document, packaging file), I want a drag-and-drop zone with progress, so that the upload feels modern.

## Tasks

### Form section component (`frontend/src/lib/components/FormSection.svelte`)
- [ ] Props: `title` (string), `description` (optional string)
- [ ] Renders a Card with header (title + description) and body slot
- [ ] Used to group related fields within a form

### File upload component (`frontend/src/lib/components/FileUpload.svelte`)
- [ ] Props: `label`, `accept` (file types string), `maxSizeMb`, `value` (bindable: File | null), `error`
- [ ] Drag-and-drop zone with dashed border
- [ ] Shows file name and size after selection
- [ ] Remove/replace button
- [ ] Error state for invalid file type or oversized file

### Line item editor component (`frontend/src/lib/components/LineItemEditor.svelte`)
- [ ] Props: `items` (bindable array), `columns` (column definitions with types), `minRows` (default 1)
- [ ] Add row button, remove row button per row
- [ ] Inline validation per cell
- [ ] Responsive: horizontal scroll on mobile
- [ ] Used in PO form and shipment form

### PO create form (`routes/po/new/+page.svelte` + `lib/components/POForm.svelte`)
- [ ] Rebuild POForm using Input, Select, TextArea, Button, FormSection, LineItemEditor
- [ ] Sections:

| Section | Fields |
|---------|--------|
| Order Details | PO Type (Select), Vendor (Select, filtered by type), Marketplace (Select) |
| Buyer | Buyer Name (Input), Buyer Country (Select) |
| Dates & Currency | Currency (Select), Issued Date (Input date), Required Delivery Date (Input date) |
| Shipping | Ship-to Address (TextArea) |
| Payment | Payment Terms (Select) |
| Trade Details | Incoterm (Select), Port of Loading (Select), Port of Discharge (Select), Country of Origin (Select), Country of Destination (Select) |
| Terms & Conditions | Terms (TextArea) |
| Line Items | LineItemEditor: part number, description, qty, UoM, unit price, HS code, country of origin |

- [ ] Validation rules shown to user:
  - Vendor: required
  - Currency: required
  - Issued Date, Delivery Date: required
  - Line items: at least 1 row; part number required; qty > 0; unit price >= 0; HS code format (digits and dots, 4+ chars)
- [ ] Actions: Cancel (secondary, navigates to /po), Create PO (primary, disabled while submitting)
- [ ] Responsive: single column on mobile, 2-column on desktop within each section

### PO edit form (`routes/po/[id]/edit/+page.svelte`)
- [ ] Same as PO create but pre-populated with existing PO data
- [ ] Read-only fields based on mutability rules (iteration 027): PO type, vendor cannot change
- [ ] Actions: Cancel, Save & Revise

### Vendor create form (`routes/vendors/new/+page.svelte`)
- [ ] Rebuild using Input, Select, Button, FormSection
- [ ] Section: Vendor Details
  - Name (Input, required)
  - Country (Select, required)
  - Vendor Type (Select, required)
  - Address (TextArea)
  - Account Details (TextArea)
- [ ] Actions: Cancel (to /vendors), Create Vendor

### Vendor edit form (`routes/vendors/[id]/edit/+page.svelte`) -- new page
- [ ] Same as create but pre-populated
- [ ] Name is read-only after creation
- [ ] Actions: Cancel, Save Changes

### Product create form (`routes/products/new/+page.svelte`)
- [ ] Rebuild using Input, Select, Button, FormSection
- [ ] Section: Product Details
  - Vendor (Select, required, active vendors only)
  - Part Number (Input, required)
  - Description (Input)
  - Manufacturing Address (Input)
  - Requires Certification (checkbox)
- [ ] Actions: Cancel (to /products), Create Product

### Product edit form (`routes/products/[id]/edit/+page.svelte`)
- [ ] Rebuild using the component library
- [ ] Vendor and Part Number are read-only (displayed as text, not editable)
- [ ] Editable: Description, Manufacturing Address, Requires Certification
- [ ] Actions: Cancel, Save Changes

### Invoice create (within PO detail, modal)
- [ ] Rebuild CreateInvoiceDialog using Modal + DataTable
- [ ] Table shows remaining quantities per line item
- [ ] Quantity input per row (0 to remaining, validated inline)
- [ ] Actions: Cancel, Create Invoice

### Shipment create form (`routes/shipments/new/+page.svelte`) -- new in Phase 3
- [ ] Section: Shipment Details
  - Source PO (Select, accepted POs only)
  - Marketplace (auto-filled from PO, read-only)
- [ ] Section: Line Items
  - LineItemEditor: select from PO's accepted lines, set quantity (up to shipped remaining), net weight, gross weight, package count, dimensions
- [ ] Actions: Cancel (to /shipments), Create Shipment

### Certificate upload form (`routes/certificates/new/+page.svelte`) -- new in Phase 3
- [ ] Section: Certificate Details
  - Product (Select, required)
  - Qualification Type (Select, required, filtered to product's assigned qualifications)
  - Certificate Number (Input, required)
  - Issuer (Input, required)
  - Testing Lab (Input)
  - Test Date (Input date)
  - Issue Date (Input date, required)
  - Expiry Date (Input date, optional)
  - Target Market (Input)
- [ ] Section: Document
  - FileUpload (accept PDF/image, max 10MB)
- [ ] Actions: Cancel (to /certificates), Upload Certificate

### Packaging spec create form (`routes/packaging/new/+page.svelte`) -- new in Phase 3
- [ ] Section: Spec Details
  - Product (Select, required)
  - Marketplace (Select, required)
  - Spec Name (Input, required)
  - Description (TextArea)
  - Requirements (TextArea)
- [ ] Actions: Cancel (to /packaging), Create Spec

### Tests (scratch)
- [ ] Screenshot PO create form at 1280px: all sections visible, line items with 3 rows
- [ ] Screenshot PO create form at 375px: single column, horizontal scroll on line items
- [ ] Screenshot PO create form with validation errors on multiple fields
- [ ] Screenshot vendor create form at 1280px and 375px
- [ ] Screenshot product create form at 1280px and 375px
- [ ] Screenshot shipment create form at 1280px
- [ ] Screenshot certificate upload form at 1280px with file selected
- [ ] Screenshot packaging spec create form at 1280px
- [ ] Verify permanent Playwright tests still pass

## Acceptance criteria
- [ ] All form fields use Input, Select, TextArea, or FileUpload components
- [ ] All action buttons use Button component
- [ ] All form sections use FormSection component
- [ ] PO line items and shipment line items use LineItemEditor component
- [ ] Every required field shows an asterisk indicator
- [ ] Every field with a validation error shows an inline error message below the field
- [ ] All forms responsive: 2-column on desktop, single column on mobile
- [ ] FileUpload supports drag-and-drop with file type and size validation
- [ ] Vendor edit page exists at `/vendors/[id]/edit` (new)
- [ ] No inline `.form-grid`, `.form-group`, `.form-actions`, `.action-buttons` CSS in page files
- [ ] All existing permanent Playwright tests pass without modification
