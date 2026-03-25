<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as pageStore } from '$app/stores';
	import { listPOs, listVendors, fetchReferenceData } from '$lib/api';
	import type { POListParams } from '$lib/api';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import type { PurchaseOrderListItem, VendorListItem, ReferenceDataItem } from '$lib/types';

	let search: string = $state('');
	let debouncedSearch: string = $state('');
	let selectedStatus: string = $state('');
	let selectedVendor: string = $state('');
	let selectedCurrency: string = $state('');
	let sortBy: string = $state('created_at');
	let sortDir: string = $state('desc');
	let page: number = $state(1);
	let pageSize: number = $state(20);
	let total: number = $state(0);
	let pos: PurchaseOrderListItem[] = $state([]);
	let loading: boolean = $state(true);
	let vendors: VendorListItem[] = $state([]);
	let currencies: ReferenceDataItem[] = $state([]);

	let debounceTimer: ReturnType<typeof setTimeout>;
	$effect(() => {
		const s = search;
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			debouncedSearch = s;
			page = 1;
		}, 300);
		return () => clearTimeout(debounceTimer);
	});

	let initialized = false;
	$effect(() => {
		// Touch all reactive dependencies
		debouncedSearch; selectedStatus; selectedVendor; selectedCurrency;
		sortBy; sortDir; page;

		if (!initialized) {
			initialized = true;
			return;
		}
		fetchPOs();
	});

	onMount(async () => {
		const params = $pageStore.url.searchParams;
		search = params.get('search') ?? '';
		debouncedSearch = search;
		selectedStatus = params.get('status') ?? '';
		selectedVendor = params.get('vendor_id') ?? '';
		selectedCurrency = params.get('currency') ?? '';
		sortBy = params.get('sort_by') ?? 'created_at';
		sortDir = params.get('sort_dir') ?? 'desc';
		page = parseInt(params.get('page') ?? '1', 10);

		const [vendorList, refData] = await Promise.all([
			listVendors(),
			fetchReferenceData()
		]);
		vendors = vendorList;
		currencies = refData.currencies;

		await fetchPOs();
	});

	async function fetchPOs() {
		loading = true;
		try {
			const params: POListParams = {};
			if (debouncedSearch) params.search = debouncedSearch;
			if (selectedStatus) params.status = selectedStatus;
			if (selectedVendor) params.vendor_id = selectedVendor;
			if (selectedCurrency) params.currency = selectedCurrency;
			if (sortBy !== 'created_at') params.sort_by = sortBy;
			if (sortDir !== 'desc') params.sort_dir = sortDir;
			if (page > 1) params.page = page;

			const result = await listPOs(params);
			pos = result.items;
			total = result.total;

			updateUrl(params);
		} finally {
			loading = false;
		}
	}

	function updateUrl(params: POListParams) {
		const query = new URLSearchParams();
		for (const [k, v] of Object.entries(params)) {
			if (v !== undefined && v !== '') query.set(k, String(v));
		}
		const qs = query.toString();
		const newUrl = qs ? `/po?${qs}` : '/po';
		goto(newUrl, { replaceState: true, keepFocus: true, noScroll: true });
	}

	function onFilterChange() {
		page = 1;
	}

	function toggleSort(column: string) {
		if (sortBy === column) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortBy = column;
			sortDir = 'desc';
		}
		page = 1;
	}

	const totalPages = $derived(Math.ceil(total / pageSize) || 1);
	const startItem = $derived((page - 1) * pageSize + 1);
	const endItem = $derived(Math.min(page * pageSize, total));

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatValue(value: string, currency: string): string {
		return `${parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
	}
</script>

<div class="page-header">
	<h1>Purchase Orders</h1>
	<a href="/po/new" class="btn btn-primary">New PO</a>
</div>

<div class="filter-bar">
	<input
		type="text"
		class="input search-input"
		placeholder="Search PO#, vendor, buyer..."
		bind:value={search}
	/>
	<select class="select filter-select" bind:value={selectedStatus} onchange={onFilterChange}>
		<option value="">All Statuses</option>
		<option value="DRAFT">Draft</option>
		<option value="PENDING">Pending</option>
		<option value="ACCEPTED">Accepted</option>
		<option value="REJECTED">Rejected</option>
		<option value="REVISED">Revised</option>
	</select>
	<select class="select filter-select" bind:value={selectedVendor} onchange={onFilterChange}>
		<option value="">All Vendors</option>
		{#each vendors as v}
			<option value={v.id}>{v.name}</option>
		{/each}
	</select>
	<select class="select filter-select" bind:value={selectedCurrency} onchange={onFilterChange}>
		<option value="">All Currencies</option>
		{#each currencies as c}
			<option value={c.code}>{c.code} — {c.label}</option>
		{/each}
	</select>
</div>

{#if loading}
	<p>Loading...</p>
{:else if pos.length === 0}
	<p>No purchase orders found.</p>
{:else}
	<div class="card">
		<table class="table">
			<thead>
				<tr>
					<th class="sortable" onclick={() => toggleSort('po_number')}>
						PO Number {sortBy === 'po_number' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
					</th>
					<th>Vendor</th>
					<th class="sortable" onclick={() => toggleSort('issued_date')}>
						Issued Date {sortBy === 'issued_date' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
					</th>
					<th class="sortable" onclick={() => toggleSort('required_delivery_date')}>
						Delivery Date {sortBy === 'required_delivery_date' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
					</th>
					<th class="sortable" onclick={() => toggleSort('total_value')}>
						Total Value {sortBy === 'total_value' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
					</th>
					<th>Status</th>
				</tr>
			</thead>
			<tbody>
				{#each pos as po}
					<tr onclick={() => goto(`/po/${po.id}`)}>
						<td>{po.po_number}</td>
						<td>{po.vendor_name}</td>
						<td>{formatDate(po.issued_date)}</td>
						<td>{formatDate(po.required_delivery_date)}</td>
						<td>{formatValue(po.total_value, po.currency)}</td>
						<td><StatusPill status={po.status} /></td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class="pagination">
		<span class="pagination-info">Showing {startItem}–{endItem} of {total}</span>
		<div class="pagination-controls">
			<button class="btn btn-secondary" disabled={page <= 1} onclick={() => page--}>Previous</button>
			<span class="pagination-page">Page {page} of {totalPages}</span>
			<button class="btn btn-secondary" disabled={page >= totalPages} onclick={() => page++}>Next</button>
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
		gap: var(--space-3);
		margin-bottom: var(--space-4);
		flex-wrap: wrap;
	}

	.search-input {
		flex: 1;
		min-width: 200px;
	}

	.filter-select {
		width: auto;
		min-width: 150px;
	}

	tbody tr {
		cursor: pointer;
	}

	tbody tr:hover td {
		background-color: var(--gray-50);
	}

	th.sortable {
		cursor: pointer;
		user-select: none;
	}

	th.sortable:hover {
		color: var(--gray-900);
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
</style>
