// Shared dictionary of ActivityLogEntry.event codes to human-readable labels.
// Source of truth for PO + Invoice activity surfaces.
export const EVENT_LABELS = {
	PO_CREATED: 'PO created',
	PO_SUBMITTED: 'PO submitted',
	PO_ACCEPTED: 'PO accepted',
	PO_REJECTED: 'PO rejected',
	PO_REVISED: 'PO revised',
	PO_LINE_MODIFIED: 'Line modified',
	PO_LINE_ACCEPTED: 'Line accepted',
	PO_LINE_REMOVED: 'Line removed',
	PO_FORCE_ACCEPTED: 'Override: line force-accepted',
	PO_FORCE_REMOVED: 'Override: line force-removed',
	PO_MODIFIED: 'Round submitted',
	PO_CONVERGED: 'Negotiation converged',
	INVOICE_CREATED: 'Invoice created',
	INVOICE_SUBMITTED: 'Invoice submitted',
	INVOICE_APPROVED: 'Invoice approved',
	INVOICE_PAID: 'Invoice paid',
	INVOICE_DISPUTED: 'Invoice disputed',
	MILESTONE_POSTED: 'Milestone posted',
	MILESTONE_OVERDUE: 'Milestone overdue',
	// Iter 109: Brand lifecycle events (ADMIN activity feed).
	BRAND_CREATED: 'Brand created',
	BRAND_UPDATED: 'Brand updated',
	BRAND_DEACTIVATED: 'Brand deactivated',
	BRAND_REACTIVATED: 'Brand reactivated',
	BRAND_VENDOR_ASSIGNED: 'Vendor assigned to brand',
	BRAND_VENDOR_UNASSIGNED: 'Vendor removed from brand'
} as const satisfies Record<string, string>;

// Maps ActivityLogEntry.category to the tone used by ActivityFeed dot coloring.
// LIVE = informational (blue), ACTION_REQUIRED = warning (orange),
// DELAYED = error (red), unknown = neutral (gray).
export function categoryToTone(category: string): 'green' | 'blue' | 'orange' | 'red' | 'gray' {
	switch (category) {
		case 'LIVE':
			return 'blue';
		case 'ACTION_REQUIRED':
			return 'orange';
		case 'DELAYED':
			return 'red';
		default:
			return 'gray';
	}
}
