import type { UserRole } from './types';

function is(role: UserRole, ...allowed: UserRole[]): boolean {
	return role === 'ADMIN' || allowed.includes(role);
}

export const canCreatePO = (role: UserRole) => is(role, 'SM');
export const canEditPO = (role: UserRole) => is(role, 'SM');
export const canSubmitPO = (role: UserRole) => is(role, 'SM');
export const canAcceptRejectPO = (role: UserRole) => is(role, 'VENDOR');
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
export const canViewPOs = (role: UserRole) => is(role, 'SM', 'VENDOR', 'PROCUREMENT_MANAGER');
export const canMarkAdvancePaid = (role: UserRole) => is(role, 'SM');
export const canModifyPostAccept = (role: UserRole) => is(role, 'SM');
