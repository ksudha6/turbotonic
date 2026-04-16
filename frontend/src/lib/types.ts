export type POStatus = 'DRAFT' | 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'REVISED';

export type VendorStatus = 'ACTIVE' | 'INACTIVE';

export type VendorType = 'PROCUREMENT' | 'OPEX' | 'FREIGHT' | 'MISCELLANEOUS';
export type POType = 'PROCUREMENT' | 'OPEX';

export interface VendorListItem {
	id: string;
	name: string;
	country: string;
	status: VendorStatus;
	vendor_type: VendorType;
	address: string;
	account_details: string;
}

export interface Vendor {
	id: string;
	name: string;
	country: string;
	status: VendorStatus;
	vendor_type: VendorType;
	address: string;
	account_details: string;
	created_at: string;
	updated_at: string;
}

export interface VendorInput {
	name: string;
	country: string;
	vendor_type: VendorType;
	address: string;
	account_details: string;
}

export type LineItemStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED';

export interface LineItem {
	part_number: string;
	description: string;
	quantity: number;
	uom: string;
	unit_price: string;
	hs_code: string;
	country_of_origin: string;
	product_id: string | null;
	status: LineItemStatus;
}

export interface LineDecision {
	part_number: string;
	status: 'ACCEPTED' | 'REJECTED';
}

export interface AcceptLinesRequest {
	decisions: LineDecision[];
	comment: string | null;
}

export interface RejectionRecord {
	comment: string;
	rejected_at: string;
}

export interface PurchaseOrderListItem {
	id: string;
	po_number: string;
	status: POStatus;
	po_type: POType;
	vendor_id: string;
	buyer_name: string;
	buyer_country: string;
	vendor_name: string;
	vendor_country: string;
	issued_date: string;
	required_delivery_date: string;
	total_value: string;
	currency: string;
	current_milestone: string | null;
	marketplace: string | null;
}

export interface PaginatedPOList {
	items: PurchaseOrderListItem[];
	total: number;
	page: number;
	page_size: number;
}

export interface PurchaseOrder extends PurchaseOrderListItem {
	ship_to_address: string;
	payment_terms: string;
	terms_and_conditions: string;
	incoterm: string;
	port_of_loading: string;
	port_of_discharge: string;
	country_of_origin: string;
	country_of_destination: string;
	line_items: LineItem[];
	rejection_history: RejectionRecord[];
	created_at: string;
	updated_at: string;
}

export interface LineItemInput {
	part_number: string;
	description: string;
	quantity: number;
	uom: string;
	unit_price: string;
	hs_code: string;
	country_of_origin: string;
	product_id: string | null;
}

export interface ReferenceDataItem {
	code: string;
	label: string;
}

export interface ReferenceData {
	currencies: ReferenceDataItem[];
	incoterms: ReferenceDataItem[];
	payment_terms: ReferenceDataItem[];
	countries: ReferenceDataItem[];
	ports: ReferenceDataItem[];
	vendor_types: ReferenceDataItem[];
	po_types: ReferenceDataItem[];
}

export interface PurchaseOrderInput {
	po_number: string;
	po_type: POType;
	vendor_id: string;
	buyer_name: string;
	buyer_country: string;
	issued_date: string;
	required_delivery_date: string;
	total_value: string;
	currency: string;
	ship_to_address: string;
	payment_terms: string;
	terms_and_conditions: string;
	incoterm: string;
	port_of_loading: string;
	port_of_discharge: string;
	country_of_origin: string;
	country_of_destination: string;
	marketplace: string | null;
	line_items: LineItemInput[];
}

export interface POStatusSummary {
	status: POStatus;
	count: number;
	total_usd: string;
}

export interface VendorSummary {
	active: number;
	inactive: number;
}

export interface RecentPO {
	id: string;
	po_number: string;
	status: POStatus;
	vendor_name: string;
	total_value: string;
	currency: string;
	updated_at: string;
}

export interface ProductionStageSummary {
	milestone: string;
	count: number;
}

export interface OverduePO {
	id: string;
	po_number: string;
	vendor_name: string;
	milestone: string;
	days_since_update: number;
}

export interface DashboardData {
	po_summary: POStatusSummary[];
	vendor_summary: VendorSummary;
	recent_pos: RecentPO[];
	invoice_summary: InvoiceStatusSummary[];
	production_summary: ProductionStageSummary[];
	overdue_pos: OverduePO[];
}

export interface BulkTransitionItemResult {
	po_id: string;
	success: boolean;
	error: string | null;
	new_status: string | null;
}

export interface BulkTransitionResult {
	results: BulkTransitionItemResult[];
}

export type InvoiceStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'PAID' | 'DISPUTED';

export interface InvoiceLineItem {
	part_number: string;
	description: string;
	quantity: number;
	uom: string;
	unit_price: string;
}

export interface InvoiceListItem {
	id: string;
	invoice_number: string;
	status: InvoiceStatus;
	subtotal: string;
	created_at: string;
}

export interface InvoiceListItemWithContext {
	id: string;
	invoice_number: string;
	status: InvoiceStatus;
	subtotal: string;
	created_at: string;
	po_id: string;
	po_number: string;
	vendor_name: string;
}

export interface InvoiceStatusSummary {
	status: InvoiceStatus;
	count: number;
	total_usd: string;
}

export interface Invoice {
	id: string;
	invoice_number: string;
	po_id: string;
	status: InvoiceStatus;
	payment_terms: string;
	currency: string;
	line_items: InvoiceLineItem[];
	subtotal: string;
	dispute_reason: string;
	created_at: string;
	updated_at: string;
}

export interface RemainingLine {
	part_number: string;
	description: string;
	ordered: number;
	invoiced: number;
	remaining: number;
}

export interface RemainingQuantityResponse {
	po_id: string;
	lines: RemainingLine[];
}

export interface InvoiceLineItemCreate {
	part_number: string;
	quantity: number;
}

export interface PaginatedInvoiceList {
	items: InvoiceListItemWithContext[];
	total: number;
	page: number;
	page_size: number;
}

export type ProductionMilestone = 'RAW_MATERIALS' | 'PRODUCTION_STARTED' | 'QC_PASSED' | 'READY_TO_SHIP' | 'SHIPPED';

export interface MilestoneUpdate {
	milestone: ProductionMilestone;
	posted_at: string;
}

export type NotificationCategory = 'LIVE' | 'ACTION_REQUIRED' | 'DELAYED';
export type EntityType = 'PO' | 'INVOICE';

export interface ActivityLogEntry {
	id: string;
	entity_type: EntityType;
	entity_id: string;
	event: string;
	category: NotificationCategory;
	target_role: string | null;
	detail: string | null;
	read_at: string | null;
	created_at: string;
}

export interface QualificationTypeListItem {
	id: string;
	name: string;
	target_market: string;
	applies_to_category: string;
}

export interface QualificationType extends QualificationTypeListItem {
	description: string;
	created_at: string;
}

export interface ProductListItem {
	id: string;
	vendor_id: string;
	part_number: string;
	description: string;
	manufacturing_address: string;
	qualifications: QualificationTypeListItem[];
}

export interface Product extends ProductListItem {
	created_at: string;
	updated_at: string;
}

export interface ProductInput {
	vendor_id: string;
	part_number: string;
	description: string;
	manufacturing_address: string;
}

export type PackagingSpecStatus = 'PENDING';

export interface PackagingSpec {
	id: string;
	product_id: string;
	marketplace: string;
	spec_name: string;
	description: string;
	requirements_text: string;
	status: PackagingSpecStatus;
	created_at: string;
	updated_at: string;
}

export interface PackagingSpecInput {
	product_id: string;
	marketplace: string;
	spec_name: string;
	description: string;
	requirements_text: string;
}

export interface PackagingSpecUpdate {
	spec_name?: string;
	description?: string;
	requirements_text?: string;
}

export type UserRole = 'ADMIN' | 'PROCUREMENT_MANAGER' | 'SM' | 'VENDOR' | 'QUALITY_LAB' | 'FREIGHT_MANAGER';
export type UserStatus = 'ACTIVE' | 'INACTIVE' | 'PENDING';

export interface User {
	id: string;
	username: string;
	display_name: string;
	role: UserRole;
	status: UserStatus;
	vendor_id: string | null;
}
