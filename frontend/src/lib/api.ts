import type { ActivityLogEntry, BulkTransitionResult, Certificate, CertificateCreateInput, CertificateListItem, CertWarning, DashboardData, DashboardSummary, DocumentRequirementStatus, Invoice, InvoiceLineItemCreate, InvoiceListItem, InviteUserInput, InviteUserResponse, MilestoneResponse, PackagingSpec, PackagingSpecInput, PackagingSpecUpdate, PaginatedInvoiceList, PaginatedPOList, PatchUserInput, POSubmitResponse, Product, ProductInput, ProductListItem, PurchaseOrder, PurchaseOrderInput, QualificationType, QualificationTypeListItem, ReadinessResult, ReferenceData, RemainingQuantityResponse, Shipment, ShipmentDocumentRequirement, ShipmentUpdate, User, UserRole, UserStatus, Vendor, VendorInput, VendorListItem } from './types';

async function apiGet<T>(path: string): Promise<T> {
	const res = await fetch(path, { credentials: 'include' });
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
	const res = await fetch(path, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: body !== undefined ? JSON.stringify(body) : undefined,
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

async function apiPut<T>(path: string, body: unknown): Promise<T> {
	const res = await fetch(path, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
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
	marketplace?: string;
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

export function submitPO(id: string): Promise<POSubmitResponse> {
	return apiPost<POSubmitResponse>(`/api/v1/po/${id}/submit`);
}

export function acceptPO(id: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${id}/accept`);
}

export function resubmitPO(id: string): Promise<POSubmitResponse> {
	return apiPost<POSubmitResponse>(`/api/v1/po/${id}/resubmit`);
}

// Iter 056 removed the /reject and /accept-lines endpoints in favour of per-line
// modify / accept / remove / submit-response. Iter 057 wires the UI into these.

// A ModifyLineFields payload carries only the fields the caller wants to change.
// The backend rejects unknown keys and part_number changes.
export type ModifyLineFields = {
	quantity?: number;
	unit_price?: string;
	uom?: string;
	description?: string;
	hs_code?: string;
	country_of_origin?: string;
	required_delivery_date?: string | null;
};

export function modifyLine(poId: string, partNumber: string, fields: ModifyLineFields): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(
		`/api/v1/po/${poId}/lines/${encodeURIComponent(partNumber)}/modify`,
		{ fields }
	);
}

export function acceptLine(poId: string, partNumber: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${poId}/lines/${encodeURIComponent(partNumber)}/accept`, {});
}

export function removeLine(poId: string, partNumber: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${poId}/lines/${encodeURIComponent(partNumber)}/remove`, {});
}

export function forceAcceptLine(poId: string, partNumber: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(
		`/api/v1/po/${poId}/lines/${encodeURIComponent(partNumber)}/force-accept`,
		{}
	);
}

export function forceRemoveLine(poId: string, partNumber: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(
		`/api/v1/po/${poId}/lines/${encodeURIComponent(partNumber)}/force-remove`,
		{}
	);
}

export function submitResponse(poId: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${poId}/submit-response`, {});
}

// Iter 059: advance-payment gate and post-accept line mutations. SM-only.
export function markAdvancePaid(id: string): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>(`/api/v1/po/${id}/mark-advance-paid`, {});
}

export interface PostAcceptLineInput {
	part_number: string;
	description: string;
	quantity: number;
	uom: string;
	unit_price: string;
	hs_code: string;
	country_of_origin: string;
	product_id?: string | null;
}

export async function addLinePostAccept(
	id: string,
	line: PostAcceptLineInput
): Promise<PurchaseOrder> {
	// Iter 082: surface the server's `detail` field so the Add Line dialog can
	// render it inline. apiPost only carries the status text, which is too
	// generic for "duplicate part number" / gate-closed messages.
	const res = await fetch(`/api/v1/po/${id}/lines`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ line }),
		credentials: 'include'
	});
	if (res.ok) {
		return (await res.json()) as PurchaseOrder;
	}
	if (res.status === 401) {
		if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
			const redirect = encodeURIComponent(window.location.pathname + window.location.search);
			window.location.href = `/login?redirect=${redirect}`;
		}
		throw new Error('Not authenticated');
	}
	let detail = `${res.status} ${res.statusText}`;
	try {
		const body = await res.json();
		if (body && typeof body.detail === 'string') detail = body.detail;
	} catch {
		// non-JSON body; keep status-text fallback.
	}
	throw new Error(detail);
}

export async function removeLinePostAccept(
	id: string,
	partNumber: string
): Promise<{ ok: true; po: PurchaseOrder } | { ok: false; status: number; detail: string }> {
	const res = await fetch(`/api/v1/po/${id}/lines/${encodeURIComponent(partNumber)}`, {
		method: 'DELETE',
		credentials: 'include'
	});
	if (res.ok) {
		return { ok: true, po: (await res.json()) as PurchaseOrder };
	}
	let detail = `${res.status} ${res.statusText}`;
	try {
		const body = await res.json();
		if (body && typeof body.detail === 'string') detail = body.detail;
	} catch {
		// non-JSON body; keep status-text fallback.
	}
	return { ok: false, status: res.status, detail };
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
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
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

export function fetchDashboardSummary(): Promise<DashboardSummary> {
	return apiGet<DashboardSummary>('/api/v1/dashboard/summary');
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

export function listMilestones(poId: string): Promise<MilestoneResponse[]> {
	return apiGet<MilestoneResponse[]>(`/api/v1/po/${poId}/milestones`);
}

export function postMilestone(poId: string, milestone: string): Promise<MilestoneResponse> {
	return apiPost<MilestoneResponse>(`/api/v1/po/${poId}/milestones`, { milestone });
}

export function fetchActivity(limit: number = 20, targetRole?: string): Promise<ActivityLogEntry[]> {
	let url = `/api/v1/activity/?limit=${limit}`;
	if (targetRole) url += `&target_role=${targetRole}`;
	return apiGet<ActivityLogEntry[]>(url);
}

export function fetchActivityForEntity(entityType: string, entityId: string): Promise<ActivityLogEntry[]> {
	return apiGet<ActivityLogEntry[]>(`/api/v1/activity/?entity_type=${entityType}&entity_id=${entityId}`);
}

export function fetchUnreadCount(targetRole?: string): Promise<{ count: number }> {
	let url = '/api/v1/activity/unread-count';
	if (targetRole) url += `?target_role=${targetRole}`;
	return apiGet<{ count: number }>(url);
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

export async function updateProduct(id: string, data: { description?: string; requires_certification?: boolean; manufacturing_address?: string }): Promise<Product> {
	const res = await fetch(`/api/v1/products/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data),
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		throw new Error(`PATCH /api/v1/products/${id} failed: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<Product>;
}

export function listQualificationTypes(): Promise<QualificationTypeListItem[]> {
	return apiGet<QualificationTypeListItem[]>('/api/v1/qualification-types');
}

export function createQualificationType(data: { name: string; description?: string; target_market: string; applies_to_category?: string }): Promise<QualificationType> {
	return apiPost<QualificationType>('/api/v1/qualification-types', data);
}

export function assignQualification(productId: string, qualificationTypeId: string): Promise<{ product_id: string; qualification_type_id: string }> {
	return apiPost('/api/v1/products/' + productId + '/qualifications', { qualification_type_id: qualificationTypeId });
}

export async function removeQualification(productId: string, qualificationTypeId: string): Promise<void> {
	const res = await fetch(`/api/v1/products/${productId}/qualifications/${qualificationTypeId}`, {
		method: 'DELETE',
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		throw new Error(`DELETE /api/v1/products/${productId}/qualifications/${qualificationTypeId} failed: ${res.status}`);
	}
}

export function listProductQualifications(productId: string): Promise<QualificationTypeListItem[]> {
	return apiGet<QualificationTypeListItem[]>(`/api/v1/products/${productId}/qualifications`);
}

export function listPackagingSpecs(productId: string, marketplace?: string): Promise<PackagingSpec[]> {
	const query = new URLSearchParams({ product_id: productId });
	if (marketplace) query.set('marketplace', marketplace);
	return apiGet<PackagingSpec[]>(`/api/v1/packaging-specs/?${query.toString()}`);
}

export function createPackagingSpec(data: PackagingSpecInput): Promise<PackagingSpec> {
	return apiPost<PackagingSpec>('/api/v1/packaging-specs/', data);
}

export async function updatePackagingSpec(id: string, data: PackagingSpecUpdate): Promise<PackagingSpec> {
	const res = await fetch(`/api/v1/packaging-specs/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data),
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		throw new Error(`PATCH /api/v1/packaging-specs/${id} failed: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<PackagingSpec>;
}

export async function deletePackagingSpec(id: string): Promise<void> {
	const res = await fetch(`/api/v1/packaging-specs/${id}`, {
		method: 'DELETE',
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		const body = await res.json().catch(() => ({}));
		throw new Error(body.detail ?? `DELETE /api/v1/packaging-specs/${id} failed: ${res.status}`);
	}
}

// Iter 094: Certificates (backend iter 038)
export function listCertificates(productId: string, targetMarket?: string): Promise<CertificateListItem[]> {
	const query = new URLSearchParams({ product_id: productId });
	if (targetMarket) query.set('target_market', targetMarket);
	return apiGet<CertificateListItem[]>(`/api/v1/certificates/?${query.toString()}`);
}

export function createCertificate(data: CertificateCreateInput): Promise<Certificate> {
	return apiPost<Certificate>('/api/v1/certificates/', data);
}

export async function uploadCertificateDocument(certId: string, file: File): Promise<Certificate> {
	const form = new FormData();
	form.append('file', file);
	const res = await fetch(`/api/v1/certificates/${certId}/document`, {
		method: 'POST',
		body: form,
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		const body = await res.json().catch(() => ({}));
		throw new Error(body.detail ?? `POST /api/v1/certificates/${certId}/document failed: ${res.status}`);
	}
	return res.json() as Promise<Certificate>;
}

// Iter 044: Shipment API
export function listShipments(params?: { po_id?: string }): Promise<Shipment[]> {
	const query = new URLSearchParams();
	if (params?.po_id) query.set('po_id', params.po_id);
	const qs = query.toString();
	return apiGet<Shipment[]>(qs ? `/api/v1/shipments/?${qs}` : '/api/v1/shipments/');
}

export function getShipment(id: string): Promise<Shipment> {
	return apiGet<Shipment>(`/api/v1/shipments/${id}`);
}

export async function updateShipmentLineItems(id: string, data: ShipmentUpdate): Promise<Shipment> {
	const res = await fetch(`/api/v1/shipments/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data),
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		const body = await res.json().catch(() => ({}));
		throw new Error(body.detail ?? `PATCH /api/v1/shipments/${id} failed: ${res.status}`);
	}
	return res.json() as Promise<Shipment>;
}

export async function downloadPackingListPdf(id: string, shipmentNumber: string): Promise<void> {
	const res = await fetch(`/api/v1/shipments/${id}/packing-list`, {
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		throw new Error(`GET packing-list failed: ${res.status}`);
	}
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = `packing-list-${shipmentNumber}.pdf`;
	a.click();
	URL.revokeObjectURL(url);
}

export async function downloadCommercialInvoicePdf(id: string, shipmentNumber: string): Promise<void> {
	const res = await fetch(`/api/v1/shipments/${id}/commercial-invoice`, {
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		throw new Error(`GET commercial-invoice failed: ${res.status}`);
	}
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = `commercial-invoice-${shipmentNumber}.pdf`;
	a.click();
	URL.revokeObjectURL(url);
}

// Iter 100: ADMIN /users page clients. Each path that can return a 409 surfaces
// the backend's `detail` string verbatim so the UI can render server-authored
// guard messages (last-active-admin, self-deactivate, already-PENDING, etc.)
// inline. Mirrors the `addLinePostAccept` detail-surfacing pattern.

async function detailOrThrow(res: Response, method: string, path: string): Promise<never> {
	if (res.status === 401) {
		if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
			const redirect = encodeURIComponent(window.location.pathname + window.location.search);
			window.location.href = `/login?redirect=${redirect}`;
		}
		throw new Error('Not authenticated');
	}
	let detail = `${method} ${path} failed: ${res.status} ${res.statusText}`;
	try {
		const body = await res.json();
		if (body && typeof body.detail === 'string') detail = body.detail;
	} catch {
		// non-JSON body; keep status-text fallback.
	}
	throw new Error(detail);
}

export function listUsers(filters?: { status?: UserStatus | ''; role?: UserRole | '' }): Promise<{ users: User[] }> {
	const query = new URLSearchParams();
	if (filters?.status) query.set('status', filters.status);
	if (filters?.role) query.set('role', filters.role);
	const qs = query.toString();
	return apiGet<{ users: User[] }>(qs ? `/api/v1/users/?${qs}` : '/api/v1/users/');
}

export function getUser(id: string): Promise<{ user: User }> {
	return apiGet<{ user: User }>(`/api/v1/users/${id}`);
}

export async function inviteUser(input: InviteUserInput): Promise<InviteUserResponse> {
	const path = '/api/v1/users/invite';
	const res = await fetch(path, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(input),
		credentials: 'include'
	});
	if (!res.ok) await detailOrThrow(res, 'POST', path);
	return (await res.json()) as InviteUserResponse;
}

export async function patchUser(id: string, body: PatchUserInput): Promise<{ user: User }> {
	const path = `/api/v1/users/${id}`;
	const res = await fetch(path, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
		credentials: 'include'
	});
	if (!res.ok) await detailOrThrow(res, 'PATCH', path);
	return (await res.json()) as { user: User };
}

export async function deactivateUser(id: string): Promise<{ user: User }> {
	const path = `/api/v1/users/${id}/deactivate`;
	const res = await fetch(path, { method: 'POST', credentials: 'include' });
	if (!res.ok) await detailOrThrow(res, 'POST', path);
	return (await res.json()) as { user: User };
}

export async function reactivateUser(id: string): Promise<{ user: User }> {
	const path = `/api/v1/users/${id}/reactivate`;
	const res = await fetch(path, { method: 'POST', credentials: 'include' });
	if (!res.ok) await detailOrThrow(res, 'POST', path);
	return (await res.json()) as { user: User };
}

export async function resetCredentials(id: string): Promise<InviteUserResponse> {
	const path = `/api/v1/users/${id}/reset-credentials`;
	const res = await fetch(path, { method: 'POST', credentials: 'include' });
	if (!res.ok) await detailOrThrow(res, 'POST', path);
	return (await res.json()) as InviteUserResponse;
}

export async function reissueInvite(id: string): Promise<InviteUserResponse> {
	const path = `/api/v1/users/${id}/reissue-invite`;
	const res = await fetch(path, { method: 'POST', credentials: 'include' });
	if (!res.ok) await detailOrThrow(res, 'POST', path);
	return (await res.json()) as InviteUserResponse;
}

// Iter 102: Shipment document requirements + readiness + transitions (backend iter 046)

// MarkReadyNotReadyError carries the ReadinessResult from a 409 response so the
// page can render missing items inline rather than as a flat string.
export class MarkReadyNotReadyError extends Error {
	readonly readiness: ReadinessResult;
	constructor(readiness: ReadinessResult) {
		super('Shipment is not ready to ship');
		this.name = 'MarkReadyNotReadyError';
		this.readiness = readiness;
	}
}

export function listShipmentRequirements(id: string): Promise<ShipmentDocumentRequirement[]> {
	return apiGet<ShipmentDocumentRequirement[]>(`/api/v1/shipments/${id}/requirements`);
}

export async function addShipmentRequirement(
	id: string,
	document_type: string
): Promise<ShipmentDocumentRequirement> {
	if (!document_type.trim()) {
		throw new Error('document_type must not be empty');
	}
	return apiPost<ShipmentDocumentRequirement>(`/api/v1/shipments/${id}/requirements`, {
		document_type
	});
}

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export async function uploadShipmentDocument(
	id: string,
	requirementId: string,
	file: File
): Promise<ShipmentDocumentRequirement> {
	if (file.size > MAX_UPLOAD_BYTES) {
		throw new Error('File exceeds the 10 MB limit');
	}
	if (file.type !== 'application/pdf') {
		throw new Error('Only PDF files are accepted');
	}
	const form = new FormData();
	form.append('file', file);
	const res = await fetch(`/api/v1/shipments/${id}/documents/${requirementId}/upload`, {
		method: 'POST',
		body: form,
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		const body = await res.json().catch(() => ({}));
		throw new Error(
			body.detail ??
				`POST /api/v1/shipments/${id}/documents/${requirementId}/upload failed: ${res.status}`
		);
	}
	return res.json() as Promise<ShipmentDocumentRequirement>;
}

export function getShipmentReadiness(id: string): Promise<ReadinessResult> {
	return apiGet<ReadinessResult>(`/api/v1/shipments/${id}/readiness`);
}

export async function submitShipmentForDocuments(id: string): Promise<Shipment> {
	const res = await fetch(`/api/v1/shipments/${id}/submit-for-documents`, {
		method: 'POST',
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		const body = await res.json().catch(() => ({}));
		throw new Error(
			body.detail ?? `POST /api/v1/shipments/${id}/submit-for-documents failed: ${res.status}`
		);
	}
	return res.json() as Promise<Shipment>;
}

export async function markShipmentReady(id: string): Promise<Shipment> {
	const res = await fetch(`/api/v1/shipments/${id}/mark-ready`, {
		method: 'POST',
		credentials: 'include'
	});
	if (!res.ok) {
		if (res.status === 401) {
			if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
				const redirect = encodeURIComponent(window.location.pathname + window.location.search);
				window.location.href = `/login?redirect=${redirect}`;
			}
			throw new Error('Not authenticated');
		}
		const body = await res.json().catch(() => ({}));
		if (res.status === 409) {
			// Backend returns the ReadinessResult in detail when the shipment is not ready.
			throw new MarkReadyNotReadyError(body.detail as ReadinessResult);
		}
		throw new Error(body.detail ?? `POST /api/v1/shipments/${id}/mark-ready failed: ${res.status}`);
	}
	return res.json() as Promise<Shipment>;
}
