import type { BulkTransitionResult, DashboardData, Invoice, InvoiceListItem, PaginatedPOList, PurchaseOrder, PurchaseOrderInput, ReferenceData, Vendor, VendorInput, VendorListItem } from './types';

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

export function createInvoice(poId: string): Promise<Invoice> {
	return apiPost<Invoice>('/api/v1/invoices/', { po_id: poId });
}

export function getInvoice(id: string): Promise<Invoice> {
	return apiGet<Invoice>(`/api/v1/invoices/${id}`);
}

export function listInvoicesByPO(poId: string): Promise<InvoiceListItem[]> {
	return apiGet<InvoiceListItem[]>(`/api/v1/po/${poId}/invoices`);
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
