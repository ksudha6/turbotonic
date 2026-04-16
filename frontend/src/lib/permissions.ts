import type { UserRole } from './types';

// ADMIN inherits all SM-side permissions.
function is(role: UserRole, ...allowed: UserRole[]): boolean {
	return role === 'ADMIN' || allowed.includes(role);
}

// Exact match only — ADMIN does not inherit VENDOR-side actions.
function isExact(role: UserRole, ...allowed: UserRole[]): boolean {
	return allowed.includes(role);
}

export const canCreatePO = (role: UserRole) => is(role, 'SM');
export const canEditPO = (role: UserRole) => is(role, 'SM');
export const canSubmitPO = (role: UserRole) => is(role, 'SM');
export const canAcceptRejectPO = (role: UserRole) => isExact(role, 'VENDOR');
export const canCreateInvoice = (role: UserRole) => isExact(role, 'VENDOR');
export const canSubmitInvoice = (role: UserRole) => isExact(role, 'VENDOR');
export const canApproveInvoice = (role: UserRole) => is(role, 'SM');
export const canPayInvoice = (role: UserRole) => is(role, 'SM');
export const canDisputeInvoice = (role: UserRole) => is(role, 'SM');
export const canResolveInvoice = (role: UserRole) => is(role, 'SM');
export const canManageVendors = (role: UserRole) => is(role, 'SM');
export const canManageProducts = (role: UserRole) => is(role, 'SM');
export const canViewProducts = (role: UserRole) => is(role, 'SM', 'QUALITY_LAB');
export const canPostMilestone = (role: UserRole) => isExact(role, 'VENDOR');
export const canViewInvoices = (role: UserRole) => is(role, 'SM', 'VENDOR');
export const canViewPOs = (role: UserRole) => is(role, 'SM', 'VENDOR', 'FREIGHT_MANAGER');
