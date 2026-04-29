<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import { listAllInvoices, listVendors, downloadBulkInvoicePdf } from '$lib/api';
	import type {
		InvoiceListItemWithContext,
		VendorListItem,
		UserRole
	} from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import InvoiceListFilters from '$lib/invoice/InvoiceListFilters.svelte';
	import InvoiceListBulkBar from '$lib/invoice/InvoiceListBulkBar.svelte';
	import InvoiceListTable from '$lib/invoice/InvoiceListTable.svelte';
	import InvoiceListPagination from '$lib/invoice/InvoiceListPagination.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let status: string = $state('');
	let invoiceNumber: string = $state('');
	let poNumber: string = $state('');
	let vendor: string = $state('');
	let dateFrom: string = $state('');
	let dateTo: string = $state('');

	let invoices: InvoiceListItemWithContext[] = $state([]);
	let loading: boolean = $state(true);
	let errorMessage: string = $state('');
	let initialFetchComplete: boolean = $state(false);

	let page: number = $state(1);
	let pageSize: number = $state(20);
	let total: number = $state(0);

	let vendors: VendorListItem[] = $state([]);
	let invoiceOptions: string[] = $state([]);
	let poOptions: string[] = $state([]);

	let selectedIds: Set<string> = $state(new Set());
	let bulkLoading: boolean = $state(false);

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);
	const showVendorFilter = $derived(role !== 'VENDOR');

	const hasAnyFilter = $derived(
		Boolean(status || invoiceNumber || poNumber || vendor || dateFrom || dateTo)
	);

	let initialized = false;
	$effect(() => {
		// Touch reactive deps so refetch fires on changes
		status;
		invoiceNumber;
		poNumber;
		vendor;
		dateFrom;
		dateTo;
		page;
		pageSize;

		if (!initialized) {
			initialized = true;
			return;
		}
		fetchInvoices();
	});

	let selectionResetInitialized = false;
	$effect(() => {
		// Filter changes clear selection
		status;
		invoiceNumber;
		poNumber;
		vendor;
		dateFrom;
		dateTo;

		if (!selectionResetInitialized) {
			selectionResetInitialized = true;
			return;
		}
		selectedIds = new Set();
		page = 1;
	});

	onMount(async () => {
		try {
			const [vendorList, allData] = await Promise.all([
				listVendors(),
				listAllInvoices({ page_size: 9999 })
			]);
			vendors = vendorList;
			invoiceOptions = [...new Set(allData.items.map((i) => i.invoice_number))].sort();
			poOptions = [...new Set(allData.items.map((i) => i.po_number))].sort();
		} catch {
			// Pre-fill failures leave dropdowns empty; the main fetch surfaces a real error state.
		}
		await fetchInvoices();
	});

	async function fetchInvoices() {
		loading = true;
		errorMessage = '';
		try {
			const result = await listAllInvoices({
				...(status && { status }),
				...(invoiceNumber && { invoice_number: invoiceNumber }),
				...(poNumber && { po_number: poNumber }),
				...(vendor && { vendor_name: vendor }),
				...(dateFrom && { date_from: dateFrom }),
				...(dateTo && { date_to: dateTo }),
				page,
				page_size: pageSize
			});
			invoices = result.items;
			total = result.total;
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Failed to load invoices';
			invoices = [];
			total = 0;
		} finally {
			loading = false;
			initialFetchComplete = true;
		}
	}

	function clearFilters() {
		status = '';
		invoiceNumber = '';
		poNumber = '';
		vendor = '';
		dateFrom = '';
		dateTo = '';
	}

	async function handleBulkDownload() {
		bulkLoading = true;
		try {
			await downloadBulkInvoicePdf([...selectedIds]);
			selectedIds = new Set();
		} finally {
			bulkLoading = false;
		}
	}

	function clearSelection() {
		selectedIds = new Set();
	}
</script>

<svelte:head>
	<title>Invoices</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Invoices">
	{#snippet userMenu()}
		<UserMenu name={userName} {role} />
	{/snippet}

	<PageHeader title="Invoices" />

	<div class="invoice-list-page">
		<InvoiceListFilters
			bind:status
			bind:invoiceNumber
			bind:poNumber
			bind:vendor
			bind:dateFrom
			bind:dateTo
			{vendors}
			{invoiceOptions}
			{poOptions}
			{showVendorFilter}
			onClear={clearFilters}
		/>

		<InvoiceListBulkBar
			selectedCount={selectedIds.size}
			loading={bulkLoading}
			onDownload={handleBulkDownload}
			onClear={clearSelection}
		/>

		{#if errorMessage && !loading}
			<ErrorState message={errorMessage} onRetry={fetchInvoices} />
		{:else if loading && !initialFetchComplete}
			<LoadingState label="Loading invoices" data-testid="invoice-list-loading" />
		{:else if invoices.length === 0}
			{#if hasAnyFilter}
				<EmptyState
					title="No matching invoices"
					description="Try adjusting filters."
				/>
			{:else}
				<EmptyState
					title="No invoices yet"
					description="Invoices appear here once a vendor creates them from a PO."
				/>
			{/if}
		{:else}
			<div class="invoice-list-table-region">
				<InvoiceListTable
					rows={invoices}
					bind:selectedIds
					onRowClick={(id) => goto(`/invoice/${id}`)}
				/>
				{#if loading && invoices.length > 0}
					<div class="invoice-list-loading-overlay">
						<LoadingState label="Refreshing" data-testid="invoice-list-loading" />
					</div>
				{/if}
			</div>
			<InvoiceListPagination bind:page bind:pageSize {total} />
		{/if}
	</div>
</AppShell>

<style>
	.invoice-list-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.invoice-list-table-region {
		position: relative;
	}

	.invoice-list-loading-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(255, 255, 255, 0.6);
		z-index: 1;
	}
</style>
