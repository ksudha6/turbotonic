import type { UserRole } from './types';

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
export const canManageProducts = (role: UserRole) => is(role, 'SM');
export const canViewProducts = (role: UserRole) => is(role, 'SM', 'QUALITY_LAB', 'VENDOR', 'PROCUREMENT_MANAGER');
export const canPostMilestone = (role: UserRole) => is(role, 'VENDOR');
export const canViewInvoices = (role: UserRole) => is(role, 'SM', 'VENDOR', 'PROCUREMENT_MANAGER', 'FREIGHT_MANAGER');
// FM sidebar excludes POs (iter 071 matrix), but FM needs PO detail read access
// for iter 073 dashboard's ready-batch click-through. Nav visibility and page-level
// read are decoupled (iter 067 design).
export const canViewPOs = (role: UserRole) => is(role, 'SM', 'VENDOR', 'PROCUREMENT_MANAGER', 'FREIGHT_MANAGER');
export const canMarkAdvancePaid = (role: UserRole) => is(role, 'SM');
export const canModifyPostAccept = (role: UserRole) => is(role, 'SM');
