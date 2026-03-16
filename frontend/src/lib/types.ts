export type POStatus = 'DRAFT' | 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'REVISED';

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
	issued_date: string;
	required_delivery_date: string;
	total_value: string;
	currency: string;
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

export interface PurchaseOrderInput {
	po_number: string;
	vendor_id: string;
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
