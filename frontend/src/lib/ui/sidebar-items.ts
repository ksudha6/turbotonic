import type { UserRole } from '$lib/types';

export type SidebarItem = {
	href: string;
	label: string;
	match: (pathname: string) => boolean;
};

export type SidebarSection = {
	label: string;
	items: SidebarItem[];
};

const DASHBOARD: SidebarItem = {
	href: '/dashboard',
	label: 'Dashboard',
	match: (p) => p === '/' || p.startsWith('/dashboard')
};

const PURCHASE_ORDERS: SidebarItem = {
	href: '/po',
	label: 'Purchase Orders',
	match: (p) => p.startsWith('/po') || p.startsWith('/production')
};

const INVOICES: SidebarItem = {
	href: '/invoices',
	label: 'Invoices',
	match: (p) => p.startsWith('/invoice') || p.startsWith('/invoices')
};

const VENDORS: SidebarItem = {
	href: '/vendors',
	label: 'Vendors',
	match: (p) => p.startsWith('/vendors')
};

const PRODUCTS: SidebarItem = {
	href: '/products',
	label: 'Products',
	match: (p) => p.startsWith('/products')
};

const USERS: SidebarItem = {
	href: '/users',
	label: 'Users',
	match: (p) => p.startsWith('/users')
};

const BRANDS: SidebarItem = {
	href: '/brands',
	label: 'Brands',
	match: (p) => p.startsWith('/brands')
};

const ROLE_ITEMS: Record<UserRole, SidebarItem[]> = {
	ADMIN: [DASHBOARD, PURCHASE_ORDERS, INVOICES, VENDORS, PRODUCTS, USERS, BRANDS],
	SM: [DASHBOARD, PURCHASE_ORDERS, INVOICES, VENDORS, PRODUCTS],
	VENDOR: [DASHBOARD, PURCHASE_ORDERS, INVOICES, PRODUCTS],
	FREIGHT_MANAGER: [DASHBOARD, INVOICES],
	QUALITY_LAB: [DASHBOARD, PRODUCTS],
	PROCUREMENT_MANAGER: [DASHBOARD, PURCHASE_ORDERS, INVOICES, PRODUCTS]
};

export function sidebarItemsFor(role: UserRole): SidebarSection[] {
	return [{ label: 'Workspace', items: ROLE_ITEMS[role] }];
}
