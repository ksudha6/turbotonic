import type { UserRole } from '$lib/types';
import {
	canViewPOs,
	canViewInvoices,
	canManageVendors,
	canViewProducts
} from '$lib/permissions';

export type SidebarItem = {
	href: string;
	label: string;
	match: (pathname: string) => boolean;
};

export function sidebarItemsFor(role: UserRole): SidebarItem[] {
	const items: SidebarItem[] = [];
	items.push({
		href: '/dashboard',
		label: 'Dashboard',
		match: (p) => p === '/' || p.startsWith('/dashboard')
	});
	if (canViewPOs(role)) {
		items.push({
			href: '/po',
			label: 'Purchase Orders',
			match: (p) => p.startsWith('/po') || p.startsWith('/production')
		});
	}
	if (canViewInvoices(role)) {
		items.push({
			href: '/invoices',
			label: 'Invoices',
			match: (p) => p.startsWith('/invoice') || p.startsWith('/invoices')
		});
	}
	if (canManageVendors(role)) {
		items.push({
			href: '/vendors',
			label: 'Vendors',
			match: (p) => p.startsWith('/vendors')
		});
	}
	if (canViewProducts(role)) {
		items.push({
			href: '/products',
			label: 'Products',
			match: (p) => p.startsWith('/products')
		});
	}
	return items;
}
