<script lang="ts">
	import { onMount } from 'svelte';
	import { listAllInvoices, listVendors, downloadBulkInvoicePdf } from '$lib/api';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import type { InvoiceListItemWithContext, VendorListItem } from '$lib/types';

	let selectedStatus: string = $state('');
	let filterPO: string = $state('');
	let filterVendor: string = $state('');
	let filterInvoice: string = $state('');
	let dateFrom: string = $state('');
	let dateTo: string = $state('');
	let invoices: InvoiceListItemWithContext[] = $state([]);
	let loading: boolean = $state(true);
	let selectedIds: Set<string> = $state(new Set());
	const allSelected = $derived(invoices.length > 0 && invoices.every(inv => selectedIds.has(inv.id)));

	let page: number = $state(1);
	let pageSize: number = $state(20);
	let total: number = $state(0);

	let vendors: VendorListItem[] = $state([]);
	let poOptions: string[] = $state([]);
	let invoiceOptions: string[] = $state([]);

	const totalPages = $derived(Math.ceil(total / pageSize) || 1);
	const startItem = $derived((page - 1) * pageSize + 1);
	const endItem = $derived(Math.min(page * pageSize, total));

	onMount(async () => {
		const [vendorList, allData] = await Promise.all([
			listVendors(),
			listAllInvoices({ page_size: 9999 }),
		]);
		vendors = vendorList;
		poOptions = [...new Set(allData.items.map(i => i.po_number))].sort();
		invoiceOptions = [...new Set(allData.items.map(i => i.invoice_number))].sort();
		await fetchInvoices();
	});

	async function fetchInvoices() {
		loading = true;
		try {
			const result = await listAllInvoices({
				...(selectedStatus && { status: selectedStatus }),
				...(filterPO && { po_number: filterPO }),
				...(filterVendor && { vendor_name: filterVendor }),
				...(filterInvoice && { invoice_number: filterInvoice }),
				...(dateFrom && { date_from: dateFrom }),
				...(dateTo && { date_to: dateTo }),
				page,
				page_size: pageSize,
			});
			invoices = result.items;
			total = result.total;
		} finally {
			loading = false;
		}
	}

	function onFilterChange() {
		page = 1;
		selectedIds = new Set();
		fetchInvoices();
	}

	async function handleBulkDownload() {
		await downloadBulkInvoicePdf([...selectedIds]);
		selectedIds = new Set();
	}

	function clearFilters() {
		selectedStatus = '';
		filterPO = '';
		filterVendor = '';
		filterInvoice = '';
		dateFrom = '';
		dateTo = '';
		page = 1;
		fetchInvoices();
	}

	const hasActiveFilter = $derived(
		!!selectedStatus || !!filterPO || !!filterVendor || !!filterInvoice || !!dateFrom || !!dateTo
	);

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatSubtotal(value: string): string {
		return parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}
</script>

<div class="page-header">
	<h1>Invoices</h1>
</div>

<div class="filter-bar">
	<div class="filter-group">
		<label class="filter-label">Status</label>
		<select class="select filter-select" bind:value={selectedStatus} onchange={onFilterChange}>
			<option value="">All Statuses</option>
			<option value="DRAFT">Draft</option>
			<option value="SUBMITTED">Submitted</option>
			<option value="APPROVED">Approved</option>
			<option value="PAID">Paid</option>
			<option value="DISPUTED">Disputed</option>
		</select>
	</div>

	<div class="filter-group">
		<label class="filter-label">Invoice #</label>
		<select class="select filter-select" bind:value={filterInvoice} onchange={onFilterChange}>
			<option value="">All Invoices</option>
			{#each invoiceOptions as inv}
				<option value={inv}>{inv}</option>
			{/each}
		</select>
	</div>

	<div class="filter-group">
		<label class="filter-label">PO #</label>
		<select class="select filter-select" bind:value={filterPO} onchange={onFilterChange}>
			<option value="">All POs</option>
			{#each poOptions as po}
				<option value={po}>{po}</option>
			{/each}
		</select>
	</div>

	<div class="filter-group">
		<label class="filter-label">Vendor</label>
		<select class="select filter-select" bind:value={filterVendor} onchange={onFilterChange}>
			<option value="">All Vendors</option>
			{#each vendors as v}
				<option value={v.name}>{v.name}</option>
			{/each}
		</select>
	</div>

	<div class="filter-group">
		<label class="filter-label">From</label>
		<input
			type="date"
			class="filter-input"
			bind:value={dateFrom}
			onchange={onFilterChange}
		/>
	</div>

	<div class="filter-group">
		<label class="filter-label">To</label>
		<input
			type="date"
			class="filter-input"
			bind:value={dateTo}
			onchange={onFilterChange}
		/>
	</div>

	{#if hasActiveFilter}
		<div class="filter-group filter-group-clear">
			<label class="filter-label">&nbsp;</label>
			<button class="btn btn-secondary" onclick={clearFilters}>Clear</button>
		</div>
	{/if}
</div>

{#if selectedIds.size > 0}
	<div class="bulk-toolbar">
		<span class="selection-count">{selectedIds.size} selected</span>
		<button class="btn btn-secondary" onclick={handleBulkDownload}>Download PDFs</button>
		<button class="btn-link" onclick={() => { selectedIds = new Set(); }}>Clear</button>
	</div>
{/if}

{#if loading}
	<p>Loading...</p>
{:else if invoices.length === 0}
	<p>No invoices found.</p>
{:else}
	<div class="card">
		<table class="table">
			<thead>
				<tr>
					<th class="checkbox-col">
						<input type="checkbox" checked={allSelected} onchange={() => {
							if (allSelected) {
								selectedIds = new Set();
							} else {
								selectedIds = new Set(invoices.map(i => i.id));
							}
						}} />
					</th>
					<th>Invoice #</th>
					<th>PO #</th>
					<th>Vendor</th>
					<th>Status</th>
					<th>Subtotal</th>
					<th>Created</th>
				</tr>
			</thead>
			<tbody>
				{#each invoices as invoice}
					<tr>
						<td class="checkbox-col" onclick={(e) => e.stopPropagation()}>
							<input type="checkbox" checked={selectedIds.has(invoice.id)} onchange={() => {
								const next = new Set(selectedIds);
								if (next.has(invoice.id)) { next.delete(invoice.id); } else { next.add(invoice.id); }
								selectedIds = next;
							}} />
						</td>
						<td><a href="/invoice/{invoice.id}">{invoice.invoice_number}</a></td>
						<td><a href="/po/{invoice.po_id}">{invoice.po_number}</a></td>
						<td>{invoice.vendor_name}</td>
						<td><StatusPill status={invoice.status} /></td>
						<td>{formatSubtotal(invoice.subtotal)}</td>
						<td>{formatDate(invoice.created_at)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class="pagination">
		<span class="pagination-info">Showing {startItem}–{endItem} of {total}</span>
		<select class="page-size-select" value={pageSize} onchange={(e) => { pageSize = parseInt(e.currentTarget.value); page = 1; fetchInvoices(); }}>
			<option value={10}>10 / page</option>
			<option value={20}>20 / page</option>
			<option value={50}>50 / page</option>
		</select>
		<div class="pagination-controls">
			<button class="btn btn-secondary" disabled={page <= 1} onclick={() => { page--; fetchInvoices(); }}>Previous</button>
			<span class="pagination-page">Page {page} of {totalPages}</span>
			<button class="btn btn-secondary" disabled={page >= totalPages} onclick={() => { page++; fetchInvoices(); }}>Next</button>
		</div>
	</div>
{/if}

<style>
	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-6);
	}

	.filter-bar {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
		align-items: end;
		margin-bottom: var(--space-4);
	}

	.filter-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.filter-group-clear {
		justify-content: flex-end;
	}

	.filter-label {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}

	.filter-select {
		width: auto;
		min-width: 140px;
	}

	.filter-input {
		min-width: 120px;
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius);
		font-size: var(--font-size-sm);
		background-color: white;
		color: var(--gray-900);
	}

	.filter-input:focus {
		outline: none;
		border-color: var(--blue-500, #3b82f6);
		box-shadow: 0 0 0 2px var(--blue-100, #dbeafe);
	}

	tbody tr:hover td {
		background-color: var(--gray-50);
	}

	.pagination {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: var(--space-4);
		font-size: var(--font-size-sm);
	}

	.pagination-controls {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.pagination-page {
		color: var(--gray-600);
	}

	.pagination-info {
		color: var(--gray-600);
	}

	.page-size-select {
		width: auto;
		font-size: var(--font-size-sm);
	}

	.checkbox-col {
		width: 40px;
		text-align: center;
	}

	.bulk-toolbar {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: var(--space-3);
		padding: var(--space-3);
		background-color: var(--gray-50);
		border-radius: var(--radius);
	}

	.selection-count {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		font-weight: 500;
	}

	.btn-link {
		background: none;
		border: none;
		color: var(--blue-600, #2563eb);
		cursor: pointer;
		font-size: var(--font-size-sm);
		padding: 0;
		text-decoration: underline;
	}

	.btn-link:hover {
		color: var(--blue-800, #1e40af);
	}
</style>
