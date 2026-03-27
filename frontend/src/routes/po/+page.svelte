<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as pageStore } from '$app/stores';
	import { listPOs, listVendors, fetchReferenceData, bulkTransition } from '$lib/api';
	import type { POListParams } from '$lib/api';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import type { BulkTransitionItemResult, PurchaseOrderListItem, VendorListItem, ReferenceDataItem } from '$lib/types';

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

	let selectedIds: Set<string> = $state(new Set());
	const allSelected = $derived(pos.length > 0 && pos.every(po => selectedIds.has(po.id)));

	const STATUS_ACTIONS: Record<string, string[]> = {
		DRAFT: ['submit'],
		PENDING: ['accept', 'reject'],
		REJECTED: ['resubmit'],
		REVISED: ['resubmit'],
		ACCEPTED: [],
	};

	const selectedStatuses = $derived(new Set(
		pos.filter(po => selectedIds.has(po.id)).map(po => po.status)
	));

	const validActions: string[] = $derived.by(() => {
		const statuses = [...selectedStatuses];
		if (statuses.length === 0) return [];
		const actionSets = statuses.map(s => new Set(STATUS_ACTIONS[s] ?? []));
		const first = actionSets[0];
		return [...first].filter(action => actionSets.every(set => set.has(action)));
	});

	let bulkLoading: boolean = $state(false);
	let bulkMessage: string = $state('');
	let bulkHadFailures: boolean = $state(false);
	let rejectComment: string = $state('');
	let showRejectModal: boolean = $state(false);

	let crossPageSelected: boolean = $state(false);

	async function selectAllMatching() {
		const params: POListParams = {};
		if (debouncedSearch) params.search = debouncedSearch;
		if (selectedStatus) params.status = selectedStatus;
		if (selectedVendor) params.vendor_id = selectedVendor;
		if (selectedCurrency) params.currency = selectedCurrency;
		params.page_size = 200;
		const result = await listPOs(params);
		selectedIds = new Set(result.items.map(item => item.id));
		crossPageSelected = true;
	}

	function clearSelection() {
		selectedIds = new Set();
		crossPageSelected = false;
	}

	let bulkMessageTimer: ReturnType<typeof setTimeout>;

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

	let pageSizeInitialized = false;
	$effect(() => {
		const _ = pageSize;
		if (!pageSizeInitialized) {
			pageSizeInitialized = true;
			return;
		}
		page = 1;
	});

	let initialized = false;
	$effect(() => {
		// Touch all reactive dependencies
		debouncedSearch; selectedStatus; selectedVendor; selectedCurrency;
		sortBy; sortDir; page; pageSize;

		if (!initialized) {
			initialized = true;
			return;
		}
		fetchPOs();
	});

	let selectionClearInitialized = false;
	$effect(() => {
		// Touch all context-change dependencies
		debouncedSearch; selectedStatus; selectedVendor; selectedCurrency;
		sortBy; sortDir; page; pageSize;

		if (!selectionClearInitialized) {
			selectionClearInitialized = true;
			return;
		}
		selectedIds = new Set();
		crossPageSelected = false;
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
		pageSize = parseInt(params.get('page_size') ?? '20', 10);

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
			params.page_size = pageSize;

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

	async function handleBulkAction(action: string) {
		if (action === 'reject') {
			showRejectModal = true;
			return;
		}
		await executeBulkAction(action);
	}

	async function executeBulkAction(action: string, comment?: string) {
		clearTimeout(bulkMessageTimer);
		bulkLoading = true;
		bulkMessage = '';
		try {
			const ids = [...selectedIds];
			const result = await bulkTransition(ids, action, comment);
			const succeeded = result.results.filter((r: BulkTransitionItemResult) => r.success).length;
			const failed = result.results.filter((r: BulkTransitionItemResult) => !r.success).length;
			bulkHadFailures = failed > 0;
			if (failed === 0) {
				bulkMessage = `${succeeded} PO(s) updated`;
			} else {
				bulkMessage = `${succeeded} updated, ${failed} failed`;
			}
			clearTimeout(bulkMessageTimer);
			bulkMessageTimer = setTimeout(() => { bulkMessage = ''; }, 5000);
			selectedIds = new Set();
			showRejectModal = false;
			rejectComment = '';
			await fetchPOs();
		} catch {
			bulkMessage = 'Bulk action failed';
			clearTimeout(bulkMessageTimer);
			bulkMessageTimer = setTimeout(() => { bulkMessage = ''; }, 5000);
		} finally {
			bulkLoading = false;
		}
	}

	async function confirmBulkReject() {
		if (!rejectComment.trim()) return;
		await executeBulkAction('reject', rejectComment.trim());
	}

	function cancelRejectModal() {
		showRejectModal = false;
		rejectComment = '';
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
	{#if selectedIds.size > 0}
		<div class="bulk-toolbar">
			<span class="selection-count">{selectedIds.size} selected</span>
			{#if allSelected && total > pos.length && !crossPageSelected}
				<button class="btn-link" onclick={selectAllMatching}>Select all {total} matching POs</button>
			{/if}
			{#if crossPageSelected}
				<button class="btn-link" onclick={clearSelection}>Clear selection</button>
			{/if}
			{#if validActions.length > 0}
				<div class="bulk-actions">
					{#each validActions as action}
						<button class="btn btn-secondary" disabled={bulkLoading} onclick={() => handleBulkAction(action)}>
							{action[0].toUpperCase() + action.slice(1)}
						</button>
					{/each}
				</div>
			{:else}
				<span class="no-common-action">No common action for selected statuses</span>
			{/if}
		</div>
	{/if}
	{#if bulkMessage}
		<div class={bulkHadFailures ? 'bulk-message bulk-message-error' : 'bulk-message'}>{bulkMessage}</div>
	{/if}
	<div class="card">
		<table class="table">
			<thead>
				<tr>
					<th class="checkbox-col">
						<input type="checkbox" checked={allSelected} onchange={() => {
							if (allSelected) {
								selectedIds = new Set();
								crossPageSelected = false;
							} else {
								selectedIds = new Set(pos.map(p => p.id));
							}
						}} />
					</th>
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
						<td class="checkbox-col" onclick={(e) => e.stopPropagation()}>
							<input type="checkbox" checked={selectedIds.has(po.id)} onchange={() => {
								const next = new Set(selectedIds);
								if (next.has(po.id)) { next.delete(po.id); } else { next.add(po.id); }
								selectedIds = next;
							}} />
						</td>
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
		<select class="page-size-select" value={pageSize} onchange={(e) => { pageSize = parseInt(e.currentTarget.value); page = 1; }}>
			<option value={10}>10 / page</option>
			<option value={20}>20 / page</option>
			<option value={50}>50 / page</option>
			<option value={100}>100 / page</option>
			<option value={200}>200 / page</option>
		</select>
		<div class="pagination-controls">
			<button class="btn btn-secondary" disabled={page <= 1} onclick={() => page--}>Previous</button>
			<span class="pagination-page">Page {page} of {totalPages}</span>
			<button class="btn btn-secondary" disabled={page >= totalPages} onclick={() => page++}>Next</button>
		</div>
	</div>
{/if}

{#if showRejectModal}
	<div class="modal-backdrop" role="presentation" onclick={cancelRejectModal} onkeydown={(e) => e.key === 'Escape' && cancelRejectModal()}>
		<div class="modal" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
			<h3>Reject {selectedIds.size} PO(s)</h3>
			<textarea class="input" rows="3" placeholder="Rejection comment (required)" bind:value={rejectComment}></textarea>
			<div class="modal-actions">
				<button class="btn btn-secondary" onclick={cancelRejectModal}>Cancel</button>
				<button class="btn btn-primary" disabled={!rejectComment.trim() || bulkLoading} onclick={confirmBulkReject}>Reject</button>
			</div>
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

	.page-size-select {
		width: auto;
		font-size: var(--font-size-sm);
	}

	.checkbox-col {
		width: 40px;
		text-align: center;
	}

	.selection-count {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		font-weight: 500;
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

	.bulk-actions {
		display: flex;
		gap: var(--space-2);
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

	.no-common-action {
		font-size: var(--font-size-sm);
		color: var(--gray-500, #6b7280);
		font-style: italic;
	}

	.bulk-message {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		margin-bottom: var(--space-2);
	}

	.bulk-message-error {
		color: var(--red-600, #dc2626);
		font-weight: 600;
		font-size: var(--font-size-base, 1rem);
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.modal {
		background: white;
		padding: var(--space-6);
		border-radius: var(--radius);
		width: 400px;
		max-width: 90vw;
	}

	.modal h3 {
		margin-bottom: var(--space-3);
	}

	.modal textarea {
		width: 100%;
		margin-bottom: var(--space-3);
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-2);
	}
</style>
