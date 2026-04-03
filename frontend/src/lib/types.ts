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
}

export interface Vendor {
	id: string;
	name: string;
	country: string;
	status: VendorStatus;
	vendor_type: VendorType;
	created_at: string;
	updated_at: string;
}

export interface VendorInput {
	name: string;
	country: string;
	vendor_type: VendorType;
}

export interface LineItem {
	part_number: string;
	description: string;
	quantity: number;
	uom: string;
	unit_price: string;
	hs_code: string;
	country_of_origin: string;
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

export interface DashboardData {
	po_summary: POStatusSummary[];
	vendor_summary: VendorSummary;
	recent_pos: RecentPO[];
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
