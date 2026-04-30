import type { UserRole, User, POType, ShipmentStatus, CertificateStatus } from './types';

function is(role: UserRole, ...allowed: UserRole[]): boolean {
	return role === 'ADMIN' || allowed.includes(role);
}

export const canCreatePO = (role: UserRole) => is(role, 'SM');
export const canEditPO = (role: UserRole) => is(role, 'SM');
export const canSubmitPO = (role: UserRole) => is(role, 'SM');
export const canAcceptRejectPO = (role: UserRole) => is(role, 'VENDOR');
// Bulk PO transitions: SM (submit/resubmit) + VENDOR (accept/reject). Read-only roles excluded.
export const canBulkPO = (role: UserRole) => is(role, 'SM', 'VENDOR');
export const canCreateInvoice = (role: UserRole) => is(role, 'VENDOR');
export const canSubmitInvoice = (role: UserRole) => is(role, 'VENDOR');
export const canApproveInvoice = (role: UserRole) => is(role, 'SM');
export const canPayInvoice = (role: UserRole) => is(role, 'SM');
export const canDisputeInvoice = (role: UserRole) => is(role, 'SM');
export const canResolveInvoice = (role: UserRole) => is(role, 'SM');
export const canManageVendors = (role: UserRole) => is(role, 'SM');
// Iter 100: ADMIN-only /users page guard. is() bypasses on ADMIN, so passing ADMIN
// as the explicit allowed role is a no-op vs e.g. is(role, 'SM'); the form here
// reads as "ADMIN-only" at the call site.
export const canManageUsers = (role: UserRole) => is(role, 'ADMIN');
export const canManageProducts = (role: UserRole) => is(role, 'SM');
// Iter 105: FM added — FM needs to view product cert panels to approve certificates.
export const canViewProducts = (role: UserRole) => is(role, 'SM', 'QUALITY_LAB', 'VENDOR', 'PROCUREMENT_MANAGER', 'FREIGHT_MANAGER');
export const canPostMilestone = (role: UserRole) => is(role, 'VENDOR');
export const canViewInvoices = (role: UserRole) => is(role, 'SM', 'VENDOR', 'PROCUREMENT_MANAGER', 'FREIGHT_MANAGER');
// FM sidebar excludes POs (iter 071 matrix), but FM needs PO detail read access
// for iter 073 dashboard's ready-batch click-through. Nav visibility and page-level
// read are decoupled (iter 067 design).
export const canViewPOs = (role: UserRole) => is(role, 'SM', 'VENDOR', 'PROCUREMENT_MANAGER', 'FREIGHT_MANAGER');
export const canMarkAdvancePaid = (role: UserRole) => is(role, 'SM');
export const canModifyPostAccept = (role: UserRole) => is(role, 'SM');

// Iter 097: SM/FM may edit shipment line items only while the shipment is still
// gathering documentation. Backend remains the source of truth for transitions.
export const canEditShipment = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'SM', 'FREIGHT_MANAGER') && (status === 'DRAFT' || status === 'DOCUMENTS_PENDING');

// Iter 099: Shipment document + readiness permissions.
// SM owns the DRAFT → DOCUMENTS_PENDING handoff; FM drives the requirement list.
export const canSubmitShipmentForDocuments = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'SM') && status === 'DRAFT';

// SM included for ops support; FM owns the requirement list day-to-day.
export const canManageShipmentRequirements = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'SM', 'FREIGHT_MANAGER') && status === 'DOCUMENTS_PENDING';

// VENDOR uploads documents; FM's review action is Mark Ready, not Upload.
export const canUploadShipmentDocument = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'VENDOR') && status === 'DOCUMENTS_PENDING';

// Mark Ready is FM's implicit approval over the uploaded document set.
export const canMarkShipmentReady = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'SM', 'FREIGHT_MANAGER') && status === 'DOCUMENTS_PENDING';

// VENDOR sees the documents panel but not the readiness panel (backend forbids the GET).
export const canViewShipmentReadiness = (role: UserRole): boolean =>
	is(role, 'SM', 'FREIGHT_MANAGER');

// Iter 103: SM and FM book the shipment (READY_TO_SHIP → BOOKED).
export const canBookShipment = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'SM', 'FREIGHT_MANAGER') && status === 'READY_TO_SHIP';

// Iter 103: SM and FM mark the shipment as shipped (BOOKED → SHIPPED).
export const canMarkShipmentShipped = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'SM', 'FREIGHT_MANAGER') && status === 'BOOKED';

// Iter 105: FM approves a certificate after upload+validation (VALID → APPROVED).
// is() bypasses on ADMIN; FREIGHT_MANAGER is the operational owner.
export const canApproveCertificate = (role: UserRole, status: CertificateStatus): boolean =>
	is(role, 'FREIGHT_MANAGER') && status === 'VALID';

// Iter 106: SM and FM set vessel + voyage after booking.
// Allowed on BOOKED and SHIPPED (voyage may need correction after shipping).
export const canSetTransport = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'SM', 'FREIGHT_MANAGER') && (status === 'BOOKED' || status === 'SHIPPED');

// Iter 106: SM and FM record the signatory for the CI customs declaration.
// Allowed in any post-DRAFT status (matches backend declare() method constraints).
export const canDeclareShipment = (role: UserRole, status: ShipmentStatus): boolean =>
	is(role, 'SM', 'FREIGHT_MANAGER') && status !== 'DRAFT';

export function canViewPOAttachments(
	user: User,
	po: { po_type: POType; vendor_id: string }
): boolean {
	if (user.status !== 'ACTIVE') return false;
	if (po.po_type === 'PROCUREMENT') {
		if (is(user.role, 'SM', 'PROCUREMENT_MANAGER', 'FREIGHT_MANAGER', 'QUALITY_LAB')) return true;
		if (user.role === 'VENDOR') return user.vendor_id === po.vendor_id;
		return false;
	}
	// OPEX
	if (is(user.role, 'FREIGHT_MANAGER')) return true;
	if (user.role === 'VENDOR') return user.vendor_id === po.vendor_id;
	return false;
}

export function canManagePOAttachments(
	user: User,
	po: { po_type: POType; vendor_id: string }
): boolean {
	if (user.status !== 'ACTIVE') return false;
	if (po.po_type === 'PROCUREMENT') {
		if (is(user.role, 'SM')) return true;
		if (user.role === 'VENDOR') return user.vendor_id === po.vendor_id;
		return false;
	}
	// OPEX
	return is(user.role, 'FREIGHT_MANAGER');
}
