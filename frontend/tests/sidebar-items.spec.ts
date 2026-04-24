import { test, expect } from '@playwright/test';
import { sidebarItemsFor } from '../src/lib/ui/sidebar-items';

test('sidebarItemsFor returns sections keyed by label', () => {
	const sections = sidebarItemsFor('ADMIN');
	expect(sections).toHaveLength(1);
	expect(sections[0].label).toBe('Workspace');
	expect(Array.isArray(sections[0].items)).toBe(true);
});

test('sidebar items for ADMIN include all aggregates plus Users', () => {
	const items = sidebarItemsFor('ADMIN').flatMap((s) => s.items).map((i) => i.label);
	expect(items).toEqual([
		'Dashboard',
		'Purchase Orders',
		'Invoices',
		'Vendors',
		'Products',
		'Users'
	]);
});

test('sidebar items for SM include all aggregates without Users', () => {
	const items = sidebarItemsFor('SM').flatMap((s) => s.items).map((i) => i.label);
	expect(items).toEqual([
		'Dashboard',
		'Purchase Orders',
		'Invoices',
		'Vendors',
		'Products'
	]);
});

test('sidebar items for VENDOR are Dashboard + POs + Invoices exactly', () => {
	const items = sidebarItemsFor('VENDOR').flatMap((s) => s.items).map((i) => i.label);
	expect(items).toEqual(['Dashboard', 'Purchase Orders', 'Invoices']);
});

test('sidebar items for FREIGHT_MANAGER now include Invoices', () => {
	const items = sidebarItemsFor('FREIGHT_MANAGER').flatMap((s) => s.items).map((i) => i.label);
	expect(items).toEqual(['Dashboard', 'Purchase Orders', 'Invoices']);
});

test('sidebar items for QUALITY_LAB are Dashboard + Products exactly', () => {
	const items = sidebarItemsFor('QUALITY_LAB').flatMap((s) => s.items).map((i) => i.label);
	expect(items).toEqual(['Dashboard', 'Products']);
});

test('sidebar items for PROCUREMENT_MANAGER are Dashboard only', () => {
	const items = sidebarItemsFor('PROCUREMENT_MANAGER').flatMap((s) => s.items).map((i) => i.label);
	expect(items).toEqual(['Dashboard']);
});
