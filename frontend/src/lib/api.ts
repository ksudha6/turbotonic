import type { ActivityLogEntry, BulkTransitionResult, DashboardData, Invoice, InvoiceLineItemCreate, InvoiceListItem, MilestoneUpdate, PaginatedInvoiceList, PaginatedPOList, Product, ProductInput, ProductListItem, PurchaseOrder, PurchaseOrderInput, ReferenceData, RemainingQuantityResponse, Vendor, VendorInput, VendorListItem } from './types';

async function apiGet<T>(path: string): Promise<T> {
	const res = await fetch(path);
	if (!res.ok) {
		throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
	const res = await fetch(path, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: body !== undefined ? JSON.stringify(body) : undefined
	});
	if (!res.ok) {
		throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

async function apiPut<T>(path: string, body: unknown): Promise<T> {
	const res = await fetch(path, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!res.ok) {
		throw new Error(`PUT ${path} failed: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

export interface POListParams {
	search?: string;
	status?: string;
	vendor_id?: string;
	currency?: string;
	milestone?: string;
	sort_by?: string;
	sort_dir?: string;
	page?: number;
	page_size?: number;
}

export function listPOs(params: POListParams = {}): Promise<PaginatedPOList> {
	const query = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v !== undefined && v !== '') query.set(k, String(v));
	}
	const qs = query.toString();
	return apiGet<PaginatedPOList>(qs ? `/api/v1/po/?${qs}` : '/api/v1/po/');
}

export function getPO(id: string): Promise<PurchaseOrder> {
	return apiGet<PurchaseOrder>(`/api/v1/po/${id}`);
}

export function createPO(data: PurchaseOrderInput): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>('/api/v1/po/', data);
}

export function updatePO(id: string, data: PurchaseOrderInput): Promise<PurchaseOrder> {
	return apiPut<PurchaseOrder>(`/api/v1/po/${id}`, data);
}

export function submitPO(id: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${id}/submit`);
}

export function acceptPO(id: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${id}/accept`);
}

export function rejectPO(id: string, comment: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${id}/reject`, { comment });
}

export function resubmitPO(id: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${id}/resubmit`);
}

export function downloadPoPdf(id: string): void {
	window.open(`/api/v1/po/${id}/pdf`, '_blank');
}

export function downloadInvoicePdf(id: string): void {
	window.open(`/api/v1/invoices/${id}/pdf`, '_blank');
}

export async function downloadBulkInvoicePdf(ids: string[]): Promise<void> {
	const res = await fetch('/api/v1/invoices/bulk/pdf', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ invoice_ids: ids }),
	});
	if (!res.ok) {
		throw new Error(`POST /api/v1/invoices/bulk/pdf failed: ${res.status}`);
	}
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = 'invoices-bulk.pdf';
	a.click();
	URL.revokeObjectURL(url);
}

export function listVendors(params?: { status?: string; vendor_type?: string }): Promise<VendorListItem[]> {
	const query = new URLSearchParams();
	if (params?.status) query.set('status', params.status);
	if (params?.vendor_type) query.set('vendor_type', params.vendor_type);
	const qs = query.toString();
	return apiGet<VendorListItem[]>(qs ? `/api/v1/vendors/?${qs}` : '/api/v1/vendors/');
}

export function getVendor(id: string): Promise<Vendor> {
	return apiGet<Vendor>(`/api/v1/vendors/${id}`);
}

export function createVendor(data: VendorInput): Promise<Vendor> {
	return apiPost<Vendor>('/api/v1/vendors/', data);
}

export function deactivateVendor(id: string): Promise<Vendor> {
	return apiPost<Vendor>(`/api/v1/vendors/${id}/deactivate`);
}

export function reactivateVendor(id: string): Promise<Vendor> {
	return apiPost<Vendor>(`/api/v1/vendors/${id}/reactivate`);
}

export function fetchReferenceData(): Promise<ReferenceData> {
	return apiGet<ReferenceData>('/api/v1/reference-data/');
}

export function fetchDashboard(): Promise<DashboardData> {
	return apiGet<DashboardData>('/api/v1/dashboard/');
}

export function bulkTransition(poIds: string[], action: string, comment?: string): Promise<BulkTransitionResult> {
	return apiPost<BulkTransitionResult>('/api/v1/po/bulk/transition', {
		po_ids: poIds,
		action,
		...(comment !== undefined && { comment })
	});
}

export function getRemainingQuantities(poId: string): Promise<RemainingQuantityResponse> {
	return apiGet<RemainingQuantityResponse>(`/api/v1/invoices/po/${poId}/remaining`);
}

export function createInvoice(poId: string, lineItems?: InvoiceLineItemCreate[]): Promise<Invoice> {
	const body: Record<string, unknown> = { po_id: poId };
	if (lineItems) body.line_items = lineItems;
	return apiPost<Invoice>('/api/v1/invoices/', body);
}

export function getInvoice(id: string): Promise<Invoice> {
	return apiGet<Invoice>(`/api/v1/invoices/${id}`);
}

export function listInvoicesByPO(poId: string): Promise<InvoiceListItem[]> {
	return apiGet<InvoiceListItem[]>(`/api/v1/po/${poId}/invoices`);
}

export function listAllInvoices(params?: {
	status?: string;
	po_number?: string;
	vendor_name?: string;
	invoice_number?: string;
	date_from?: string;
	date_to?: string;
	page?: number;
	page_size?: number;
}): Promise<PaginatedInvoiceList> {
	const query = new URLSearchParams();
	if (params?.status) query.set('status', params.status);
	if (params?.po_number) query.set('po_number', params.po_number);
	if (params?.vendor_name) query.set('vendor_name', params.vendor_name);
	if (params?.invoice_number) query.set('invoice_number', params.invoice_number);
	if (params?.date_from) query.set('date_from', params.date_from);
	if (params?.date_to) query.set('date_to', params.date_to);
	if (params?.page !== undefined) query.set('page', String(params.page));
	if (params?.page_size !== undefined) query.set('page_size', String(params.page_size));
	const qs = query.toString();
	return apiGet<PaginatedInvoiceList>(qs ? `/api/v1/invoices/?${qs}` : '/api/v1/invoices/');
}

export function submitInvoice(id: string): Promise<Invoice> {
	return apiPost<Invoice>(`/api/v1/invoices/${id}/submit`);
}

export function approveInvoice(id: string): Promise<Invoice> {
	return apiPost<Invoice>(`/api/v1/invoices/${id}/approve`);
}

export function payInvoice(id: string): Promise<Invoice> {
	return apiPost<Invoice>(`/api/v1/invoices/${id}/pay`);
}

export function disputeInvoice(id: string, reason: string): Promise<Invoice> {
	return apiPost<Invoice>(`/api/v1/invoices/${id}/dispute`, { reason });
}

export function resolveInvoice(id: string): Promise<Invoice> {
	return apiPost<Invoice>(`/api/v1/invoices/${id}/resolve`);
}

export function listMilestones(poId: string): Promise<MilestoneUpdate[]> {
	return apiGet<MilestoneUpdate[]>(`/api/v1/po/${poId}/milestones`);
}

export function postMilestone(poId: string, milestone: string): Promise<MilestoneUpdate> {
	return apiPost<MilestoneUpdate>(`/api/v1/po/${poId}/milestones`, { milestone });
}

export function fetchActivity(limit: number = 20): Promise<ActivityLogEntry[]> {
	return apiGet<ActivityLogEntry[]>(`/api/v1/activity/?limit=${limit}`);
}

export function fetchActivityForEntity(entityType: string, entityId: string): Promise<ActivityLogEntry[]> {
	return apiGet<ActivityLogEntry[]>(`/api/v1/activity/?entity_type=${entityType}&entity_id=${entityId}`);
}

export function fetchUnreadCount(): Promise<{ count: number }> {
	return apiGet<{ count: number }>('/api/v1/activity/unread-count');
}

export function markActivityRead(eventIds?: string[]): Promise<{ marked: number }> {
	const body = eventIds ? { event_ids: eventIds } : { all: true };
	return apiPost<{ marked: number }>('/api/v1/activity/mark-read', body);
}

export function listProducts(params?: { vendor_id?: string }): Promise<ProductListItem[]> {
	const query = new URLSearchParams();
	if (params?.vendor_id) query.set('vendor_id', params.vendor_id);
	const qs = query.toString();
	return apiGet<ProductListItem[]>(qs ? `/api/v1/products/?${qs}` : '/api/v1/products/');
}

export function getProduct(id: string): Promise<Product> {
	return apiGet<Product>(`/api/v1/products/${id}`);
}

export function createProduct(data: ProductInput): Promise<Product> {
	return apiPost<Product>('/api/v1/products/', data);
}

export async function updateProduct(id: string, data: { description?: string; requires_certification?: boolean }): Promise<Product> {
	const res = await fetch(`/api/v1/products/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	if (!res.ok) {
		throw new Error(`PATCH /api/v1/products/${id} failed: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<Product>;
}
