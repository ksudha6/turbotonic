<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as pageStore } from '$app/stores';
	import { page as appPage } from '$app/state';
	import { listPOs, listVendors, fetchReferenceData, bulkTransition } from '$lib/api';
	import { canCreatePO, canBulkPO } from '$lib/permissions';
	import type { POListParams } from '$lib/api';
	import type {
		BulkTransitionItemResult,
		PurchaseOrderListItem,
		VendorListItem,
		ReferenceDataItem,
		UserRole
	} from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import Button from '$lib/ui/Button.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import PoListFilters from '$lib/po/PoListFilters.svelte';
	import PoListBulkBar from '$lib/po/PoListBulkBar.svelte';
	import PoListTable from '$lib/po/PoListTable.svelte';
	import PoListPagination from '$lib/po/PoListPagination.svelte';

	// Marketplace is a closed four-enum. Single source of truth used for filters
	// and any future column rendering. Kept as a tuple-of-objects (immutable).
	const MARKETPLACES: ReadonlyArray<ReferenceDataItem> = [
		{ code: 'AMAZON_US', label: 'Amazon US' },
		{ code: 'AMAZON_EU', label: 'Amazon EU' },
		{ code: 'WALMART_US', label: 'Walmart US' },
		{ code: 'EBAY_US', label: 'eBay US' }
	] as const;

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let search: string = $state('');
	let debouncedSearch: string = $state('');
	let selectedStatus: string = $state('');
	let selectedVendor: string = $state('');
	let selectedCurrency: string = $state('');
	let selectedMilestone: string = $state('');
	let selectedMarketplace: string = $state('');
	let sortBy: string = $state('created_at');
	let sortDir: 'asc' | 'desc' = $state('desc');
	let page: number = $state(1);
	let pageSize: number = $state(20);
	let total: number = $state(0);
	let pos: PurchaseOrderListItem[] = $state([]);
	let loading: boolean = $state(true);
	let errorMessage: string = $state('');
	let vendors: VendorListItem[] = $state([]);
	let currencies: ReferenceDataItem[] = $state([]);

	let selectedIds: Set<string> = $state(new Set());

	const STATUS_ACTIONS: Record<string, string[]> = {
		DRAFT: ['submit'],
		PENDING: ['accept', 'reject'],
		REJECTED: ['resubmit'],
		REVISED: ['resubmit'],
		ACCEPTED: []
	};

	const selectedStatuses = $derived(
		new Set(pos.filter((po) => selectedIds.has(po.id)).map((po) => po.status))
	);

	const validActions: string[] = $derived.by(() => {
		const statuses = [...selectedStatuses];
		if (statuses.length === 0) return [];
		const actionSets = statuses.map((s) => new Set(STATUS_ACTIONS[s] ?? []));
		const first = actionSets[0];
		return [...first].filter((action) => actionSets.every((set) => set.has(action)));
	});

	let bulkLoading: boolean = $state(false);
	let bulkMessage: string = $state('');
	let bulkHadFailures: boolean = $state(false);
	let rejectComment: string = $state('');
	let showRejectModal: boolean = $state(false);

	let crossPageSelected: boolean = $state(false);

	const user = $derived(appPage.data.user);
	const role = $derived((user?.role as UserRole | undefined) ?? 'ADMIN');
	const name = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);

	const crossPagePromotable = $derived(
		pos.length > 0 &&
			pos.every((p) => selectedIds.has(p.id)) &&
			total > pos.length &&
			!crossPageSelected
	);

	const bulkBanner = $derived(
		bulkMessage
			? { tone: bulkHadFailures ? 'error' : 'success', text: bulkMessage } as const
			: null
	);

	const hasAnyFilter = $derived(
		Boolean(
			debouncedSearch ||
				selectedStatus ||
				selectedVendor ||
				selectedCurrency ||
				selectedMilestone ||
				selectedMarketplace
		)
	);

	async function selectAllMatching() {
		const params: POListParams = {};
		if (debouncedSearch) params.search = debouncedSearch;
		if (selectedStatus) params.status = selectedStatus;
		if (selectedVendor) params.vendor_id = selectedVendor;
		if (selectedCurrency) params.currency = selectedCurrency;
		if (selectedMilestone) params.milestone = selectedMilestone;
		if (selectedMarketplace) params.marketplace = selectedMarketplace;
		params.page_size = 200;
		const result = await listPOs(params);
		selectedIds = new Set(result.items.map((item) => item.id));
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
		debouncedSearch;
		selectedStatus;
		selectedVendor;
		selectedCurrency;
		selectedMilestone;
		selectedMarketplace;
		sortBy;
		sortDir;
		page;
		pageSize;

		if (!initialized) {
			initialized = true;
			return;
		}
		fetchPOs();
	});

	let selectionClearInitialized = false;
	$effect(() => {
		// Touch all context-change dependencies
		debouncedSearch;
		selectedStatus;
		selectedVendor;
		selectedCurrency;
		selectedMilestone;
		selectedMarketplace;
		sortBy;
		sortDir;
		page;
		pageSize;

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
		selectedMilestone = params.get('milestone') ?? '';
		selectedMarketplace = params.get('marketplace') ?? '';
		sortBy = params.get('sort_by') ?? 'created_at';
		sortDir = params.get('sort_dir') === 'asc' ? 'asc' : 'desc';
		page = parseInt(params.get('page') ?? '1', 10);
		pageSize = parseInt(params.get('page_size') ?? '20', 10);

		try {
			const [vendorList, refData] = await Promise.all([listVendors(), fetchReferenceData()]);
			vendors = vendorList;
			currencies = refData.currencies;
		} catch {
			// Reference data fetch failure leaves the page usable (vendor/currency
			// dropdowns just stay empty); the PO fetch surfaces a real error state.
		}

		await fetchPOs();
	});

	async function fetchPOs() {
		loading = true;
		errorMessage = '';
		try {
			const params: POListParams = {};
			if (debouncedSearch) params.search = debouncedSearch;
			if (selectedStatus) params.status = selectedStatus;
			if (selectedVendor) params.vendor_id = selectedVendor;
			if (selectedCurrency) params.currency = selectedCurrency;
			if (selectedMilestone) params.milestone = selectedMilestone;
			if (selectedMarketplace) params.marketplace = selectedMarketplace;
			if (sortBy !== 'created_at') params.sort_by = sortBy;
			if (sortDir !== 'desc') params.sort_dir = sortDir;
			if (page > 1) params.page = page;
			params.page_size = pageSize;

			const result = await listPOs(params);
			pos = result.items;
			total = result.total;

			updateUrl(params);
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Failed to load purchase orders';
			pos = [];
			total = 0;
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
			const succeeded = result.results.filter(
				(r: BulkTransitionItemResult) => r.success
			).length;
			const failed = result.results.filter(
				(r: BulkTransitionItemResult) => !r.success
			).length;
			bulkHadFailures = failed > 0;
			if (failed === 0) {
				bulkMessage = `${succeeded} PO(s) updated`;
			} else {
				bulkMessage = `${succeeded} updated, ${failed} failed`;
			}
			clearTimeout(bulkMessageTimer);
			bulkMessageTimer = setTimeout(() => {
				bulkMessage = '';
			}, 5000);
			selectedIds = new Set();
			showRejectModal = false;
			rejectComment = '';
			await fetchPOs();
		} catch {
			bulkMessage = 'Bulk action failed';
			bulkHadFailures = true;
			clearTimeout(bulkMessageTimer);
			bulkMessageTimer = setTimeout(() => {
				bulkMessage = '';
			}, 5000);
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

<svelte:head>
	<title>Purchase Orders</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Purchase Orders">
	{#snippet userMenu()}
		<UserMenu {name} {role} />
	{/snippet}

	<PageHeader title="Purchase Orders">
		{#snippet action()}
			{#if canCreatePO(role)}
				<Button onclick={() => goto('/po/new')} data-testid="po-page-header-action">
					New PO
				</Button>
			{/if}
		{/snippet}
	</PageHeader>

	<div class="po-list-page">
		<PoListFilters
			bind:search
			bind:status={selectedStatus}
			bind:vendor={selectedVendor}
			bind:currency={selectedCurrency}
			bind:milestone={selectedMilestone}
			bind:marketplace={selectedMarketplace}
			{vendors}
			{currencies}
			marketplaces={[...MARKETPLACES]}
			showVendorFilter={role !== 'VENDOR'}
		/>

		<PoListBulkBar
			selectedCount={selectedIds.size}
			totalMatching={total}
			{validActions}
			{crossPagePromotable}
			crossPageActive={crossPageSelected}
			{bulkLoading}
			{bulkBanner}
			onAction={handleBulkAction}
			onPromoteCrossPage={selectAllMatching}
			onClear={clearSelection}
		/>

		{#if errorMessage && !loading}
			<ErrorState message={errorMessage} onRetry={fetchPOs} />
		{:else if loading && pos.length === 0}
			<LoadingState label="Loading purchase orders" />
		{:else if pos.length === 0}
			{#if hasAnyFilter}
				<EmptyState
					title="No matching POs"
					description="Try adjusting filters."
				/>
			{:else}
				<EmptyState
					title="No purchase orders yet"
					description="Create your first purchase order to get started."
				>
					{#snippet action()}
						{#if canCreatePO(role)}
							<Button onclick={() => goto('/po/new')} data-testid="po-empty-cta">
								Create the first PO
							</Button>
						{/if}
					{/snippet}
				</EmptyState>
			{/if}
		{:else}
			<div class="po-list-table-region">
				<PoListTable
					rows={pos}
					bind:selectedIds
					canBulk={canBulkPO(role)}
					bind:sortBy
					bind:sortDir
					onRowClick={(id) => goto(`/po/${id}`)}
				/>
				{#if loading && pos.length > 0}
					<div class="po-list-loading-overlay">
						<LoadingState label="Refreshing" data-testid="po-list-loading" />
					</div>
				{/if}
			</div>
			<PoListPagination bind:page bind:pageSize {total} />
		{/if}
	</div>

	{#if showRejectModal}
		<div
			class="modal-backdrop"
			role="presentation"
			onclick={cancelRejectModal}
			onkeydown={(e) => e.key === 'Escape' && cancelRejectModal()}
		>
			<div
				class="modal"
				role="dialog"
				tabindex="-1"
				onclick={(e) => e.stopPropagation()}
				onkeydown={(e) => e.stopPropagation()}
			>
				<h3>Reject {selectedIds.size} PO(s)</h3>
				<textarea
					class="input"
					rows="3"
					placeholder="Rejection comment (required)"
					bind:value={rejectComment}
				></textarea>
				<div class="modal-actions">
					<Button variant="secondary" onclick={cancelRejectModal}>Cancel</Button>
					<Button
						disabled={!rejectComment.trim() || bulkLoading}
						onclick={confirmBulkReject}
					>
						Reject
					</Button>
				</div>
			</div>
		</div>
	{/if}
</AppShell>

<style>
	.po-list-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.po-list-table-region {
		position: relative;
	}

	.po-list-loading-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(255, 255, 255, 0.6);
		z-index: 1;
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
		border-radius: var(--radius-md);
		width: 400px;
		max-width: 90vw;
	}

	.modal h3 {
		margin-bottom: var(--space-3);
	}

	.modal textarea {
		width: 100%;
		margin-bottom: var(--space-3);
		font-family: inherit;
		padding: var(--space-2);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-sm);
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-2);
	}
</style>
