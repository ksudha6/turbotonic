import { test, expect } from '@playwright/test';
import { sidebarItemsFor } from '../src/lib/ui/sidebar-items';

test('sidebar items for ADMIN include all aggregates', () => {
	const items = sidebarItemsFor('ADMIN').map((i) => i.label);
	expect(items).toEqual(expect.arrayContaining(['Dashboard', 'Purchase Orders', 'Invoices', 'Vendors', 'Products']));
});

test('sidebar items for VENDOR exclude Vendors management', () => {
	const items = sidebarItemsFor('VENDOR').map((i) => i.label);
	expect(items).toContain('Purchase Orders');
	expect(items).toContain('Invoices');
	expect(items).not.toContain('Vendors');
});

test('sidebar items for QUALITY_LAB include Dashboard + Products only', () => {
	const items = sidebarItemsFor('QUALITY_LAB').map((i) => i.label);
	expect(items).toEqual(expect.arrayContaining(['Dashboard', 'Products']));
	expect(items).not.toContain('Purchase Orders');
	expect(items).not.toContain('Invoices');
});

test('sidebar items for FREIGHT_MANAGER include Dashboard + Purchase Orders', () => {
	const items = sidebarItemsFor('FREIGHT_MANAGER').map((i) => i.label);
	expect(items).toContain('Dashboard');
	expect(items).toContain('Purchase Orders');
	expect(items).not.toContain('Invoices');
	expect(items).not.toContain('Vendors');
});
