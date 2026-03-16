import type { PurchaseOrder, PurchaseOrderInput, PurchaseOrderListItem } from './types';

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

export function listPOs(status?: string): Promise<PurchaseOrderListItem[]> {
	const url = status ? `/api/v1/po?status=${encodeURIComponent(status)}` : '/api/v1/po';
	return apiGet<PurchaseOrderListItem[]>(url);
}

export function getPO(id: string): Promise<PurchaseOrder> {
	return apiGet<PurchaseOrder>(`/api/v1/po/${id}`);
}

export function createPO(data: PurchaseOrderInput): Promise<PurchaseOrder> {
	return apiPost<PurchaseOrder>('/api/v1/po', data);
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
