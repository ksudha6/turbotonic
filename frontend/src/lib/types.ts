export type POStatus = 'DRAFT' | 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'REVISED';

export type VendorStatus = 'ACTIVE' | 'INACTIVE';

export interface VendorListItem {
	id: string;
	name: string;
	country: string;
	status: VendorStatus;
}

export interface Vendor {
	id: string;
	name: string;
	country: string;
	status: VendorStatus;
	created_at: string;
	updated_at: string;
}

export interface VendorInput {
	name: string;
	country: string;
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
}

export interface PurchaseOrderInput {
	po_number: string;
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
