<script lang="ts">
	import PoListFilters from '$lib/po/PoListFilters.svelte';
	import PoListBulkBar from '$lib/po/PoListBulkBar.svelte';
	import PoStatusPills from '$lib/po/PoStatusPills.svelte';
	import PoListTable from '$lib/po/PoListTable.svelte';
	import PoListPagination from '$lib/po/PoListPagination.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Select from '$lib/ui/Select.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import type {
		PurchaseOrderListItem,
		POStatus,
		POType,
		UserRole,
		VendorListItem,
		ReferenceDataItem
	} from '$lib/types';

	const STATUS_ACTIONS: Readonly<Record<POStatus, readonly string[]>> = {
		DRAFT: ['submit'],
		PENDING: ['accept', 'reject'],
		REJECTED: ['resubmit'],
		REVISED: ['resubmit'],
		ACCEPTED: [],
		MODIFIED: []
	};

	const ALL_STATUSES: ReadonlyArray<POStatus> = [
		'DRAFT',
		'PENDING',
		'MODIFIED',
		'ACCEPTED',
		'REJECTED',
		'REVISED'
	];

	const VENDORS: VendorListItem[] = [
		{
			id: 'v-1',
			name: 'Acme Manufacturing',
			country: 'CN',
			status: 'ACTIVE',
			vendor_type: 'PROCUREMENT',
			address: '',
			account_details: ''
		},
		{
			id: 'v-2',
			name: 'Globex Industrial',
			country: 'VN',
			status: 'ACTIVE',
			vendor_type: 'PROCUREMENT',
			address: '',
			account_details: ''
		},
		{
			id: 'v-3',
			name: 'Initech OPEX Supplies',
			country: 'US',
			status: 'ACTIVE',
			vendor_type: 'OPEX',
			address: '',
			account_details: ''
		}
	];

	const CURRENCIES: ReferenceDataItem[] = [
		{ code: 'USD', label: 'US Dollar' },
		{ code: 'EUR', label: 'Euro' },
		{ code: 'GBP', label: 'British Pound' }
	];

	const MARKETPLACES: ReferenceDataItem[] = [
		{ code: 'AMAZON_US', label: 'Amazon US' },
		{ code: 'AMAZON_EU', label: 'Amazon EU' },
		{ code: 'WALMART_US', label: 'Walmart US' },
		{ code: 'EBAY_US', label: 'eBay US' }
	];

	function makeRow(args: {
		id: string;
		po_number: string;
		status: POStatus;
		po_type: POType;
		vendor: VendorListItem;
		issued_date: string;
		required_delivery_date: string;
		total_value: string;
		currency: string;
		current_milestone: string | null;
		marketplace: string | null;
		has_removed_line?: boolean;
	}): PurchaseOrderListItem {
		const row: PurchaseOrderListItem = {
			id: args.id,
			po_number: args.po_number,
			status: args.status,
			po_type: args.po_type,
			vendor_id: args.vendor.id,
			buyer_name: 'Turbo Tonic Inc.',
			buyer_country: 'US',
			vendor_name: args.vendor.name,
			vendor_country: args.vendor.country,
			issued_date: args.issued_date,
			required_delivery_date: args.required_delivery_date,
			total_value: args.total_value,
			currency: args.currency,
			current_milestone: args.current_milestone,
			marketplace: args.marketplace,
			has_removed_line: args.has_removed_line ?? false,
			round_count: 0
		};
		return row;
	}

	const ALL_ROWS: PurchaseOrderListItem[] = [
		makeRow({
			id: 'po-1',
			po_number: 'PO-2026-0001',
			status: 'PENDING',
			po_type: 'PROCUREMENT',
			vendor: VENDORS[0],
			issued_date: '2026-04-01',
			required_delivery_date: '2026-06-01',
			total_value: '12450.00',
			currency: 'USD',
			current_milestone: null,
			marketplace: 'AMAZON_US'
		}),
		makeRow({
			id: 'po-2',
			po_number: 'PO-2026-0002',
			status: 'ACCEPTED',
			po_type: 'PROCUREMENT',
			vendor: VENDORS[1],
			issued_date: '2026-03-21',
			required_delivery_date: '2026-05-15',
			total_value: '48200.00',
			currency: 'EUR',
			current_milestone: 'PRODUCTION_STARTED',
			marketplace: 'AMAZON_EU'
		}),
		makeRow({
			id: 'po-3',
			po_number: 'PO-2026-0003',
			status: 'ACCEPTED',
			po_type: 'PROCUREMENT',
			vendor: VENDORS[0],
			issued_date: '2026-03-12',
			required_delivery_date: '2026-05-10',
			total_value: '7800.00',
			currency: 'USD',
			current_milestone: 'QC_PASSED',
			marketplace: 'AMAZON_US',
			has_removed_line: true
		}),
		makeRow({
			id: 'po-4',
			po_number: 'PO-2026-0004',
			status: 'DRAFT',
			po_type: 'OPEX',
			vendor: VENDORS[2],
			issued_date: '2026-04-18',
			required_delivery_date: '2026-05-30',
			total_value: '1240.00',
			currency: 'USD',
			current_milestone: null,
			marketplace: null
		}),
		makeRow({
			id: 'po-5',
			po_number: 'PO-2026-0005',
			status: 'REJECTED',
			po_type: 'PROCUREMENT',
			vendor: VENDORS[1],
			issued_date: '2026-04-05',
			required_delivery_date: '2026-06-22',
			total_value: '23400.00',
			currency: 'GBP',
			current_milestone: null,
			marketplace: 'WALMART_US'
		}),
		makeRow({
			id: 'po-6',
			po_number: 'PO-2026-0006',
			status: 'MODIFIED',
			po_type: 'PROCUREMENT',
			vendor: VENDORS[0],
			issued_date: '2026-04-09',
			required_delivery_date: '2026-06-30',
			total_value: '15600.00',
			currency: 'USD',
			current_milestone: null,
			marketplace: 'AMAZON_US'
		}),
		makeRow({
			id: 'po-7',
			po_number: 'PO-2026-0007',
			status: 'REVISED',
			po_type: 'PROCUREMENT',
			vendor: VENDORS[1],
			issued_date: '2026-04-12',
			required_delivery_date: '2026-07-01',
			total_value: '32100.00',
			currency: 'EUR',
			current_milestone: null,
			marketplace: 'AMAZON_EU'
		})
	];

	function repeatTo(target: number): PurchaseOrderListItem[] {
		const result: PurchaseOrderListItem[] = [];
		let i = 0;
		while (result.length < target) {
			const base = ALL_ROWS[i % ALL_ROWS.length];
			const dupe: PurchaseOrderListItem = {
				...base,
				id: `${base.id}-clone-${result.length}`,
				po_number: `PO-2026-${String(result.length + 1).padStart(4, '0')}`
			};
			result.push(dupe);
			i++;
		}
		return result;
	}

	const ROW_FIVE: PurchaseOrderListItem[] = ALL_ROWS.slice(0, 5);
	const ROW_TWENTY: PurchaseOrderListItem[] = repeatTo(20);

	const ROLE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: 'ADMIN', label: 'ADMIN' },
		{ value: 'SM', label: 'SM' },
		{ value: 'VENDOR', label: 'VENDOR' },
		{ value: 'PROCUREMENT_MANAGER', label: 'PROCUREMENT_MANAGER' },
		{ value: 'FREIGHT_MANAGER', label: 'FREIGHT_MANAGER' }
	];

	type DataState =
		| 'zero'
		| 'mid'
		| 'full'
		| 'cross'
		| 'loading'
		| 'error'
		| 'bulk-success'
		| 'bulk-partial';
	const DATA_STATE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: 'zero', label: 'Zero rows' },
		{ value: 'mid', label: 'Mid (5 rows)' },
		{ value: 'full', label: 'Full page (20 rows)' },
		{ value: 'cross', label: 'Cross-page (20 of 217)' },
		{ value: 'loading', label: 'Loading' },
		{ value: 'error', label: 'Error' },
		{ value: 'bulk-success', label: 'Bulk success' },
		{ value: 'bulk-partial', label: 'Bulk partial failure' }
	];

	type SelectionState = 'none' | 'two' | 'all-on-page';
	const SELECTION_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: 'none', label: 'None selected' },
		{ value: 'two', label: 'Two selected' },
		{ value: 'all-on-page', label: 'All on page selected' }
	];

	let role: string = $state<UserRole>('ADMIN');
	let dataState: string = $state<DataState>('mid');
	let selectionState: string = $state<SelectionState>('none');

	const showVendorFilter = $derived(role !== 'VENDOR');
	const canBulk = $derived(
		role === 'ADMIN' || role === 'SM' || role === 'VENDOR'
	);
	const canCreate = $derived(role === 'ADMIN' || role === 'SM');

	const tableRows = $derived.by<PurchaseOrderListItem[]>(() => {
		if (dataState === 'zero') return [];
		if (dataState === 'mid') return ROW_FIVE;
		if (dataState === 'full' || dataState === 'cross') return ROW_TWENTY;
		if (dataState === 'loading' || dataState === 'error') return ROW_FIVE;
		if (dataState === 'bulk-success' || dataState === 'bulk-partial') return ROW_FIVE;
		return ROW_FIVE;
	});

	const totalMatching = $derived(dataState === 'cross' ? 217 : tableRows.length);

	let selectedIds: Set<string> = $state(new Set<string>());
	let crossPageActive = $state(false);

	$effect(() => {
		const sel = selectionState;
		const rows = tableRows;
		const next = new Set<string>();
		if (sel === 'two') {
			for (let i = 0; i < Math.min(2, rows.length); i++) {
				next.add(rows[i].id);
			}
		} else if (sel === 'all-on-page') {
			for (const r of rows) next.add(r.id);
		}
		selectedIds = next;
		crossPageActive = false;
	});

	const selectedStatuses = $derived(
		new Set(tableRows.filter((r) => selectedIds.has(r.id)).map((r) => r.status))
	);

	const validActionsAll = $derived.by<string[]>(() => {
		const statuses = [...selectedStatuses];
		if (statuses.length === 0) return [];
		const sets = statuses.map((s) => new Set(STATUS_ACTIONS[s] ?? []));
		const first = sets[0];
		return [...first].filter((a) => sets.every((set) => set.has(a)));
	});

	const validActions = $derived.by<string[]>(() => {
		const filtered: string[] = [];
		for (const a of validActionsAll) {
			if ((a === 'submit' || a === 'resubmit') && (role === 'ADMIN' || role === 'SM'))
				filtered.push(a);
			else if (
				(a === 'accept' || a === 'reject') &&
				(role === 'ADMIN' || role === 'VENDOR')
			)
				filtered.push(a);
		}
		return filtered;
	});

	const crossPagePromotable = $derived(
		tableRows.length > 0 &&
			tableRows.every((r) => selectedIds.has(r.id)) &&
			totalMatching > tableRows.length
	);

	const bulkBanner = $derived.by<{ tone: 'success' | 'partial' | 'error'; text: string } | null>(
		() => {
			if (dataState === 'bulk-success')
				return { tone: 'success', text: '5 Purchase Orders updated.' };
			if (dataState === 'bulk-partial')
				return {
					tone: 'partial',
					text: '3 updated, 2 failed. PO-2026-0004: invalid status. PO-2026-0005: not authorized.'
				};
			return null;
		}
	);

	function onPromoteCrossPage() {
		const next = new Set<string>();
		for (const r of tableRows) next.add(r.id);
		selectedIds = next;
		crossPageActive = true;
	}

	function onClearSelection() {
		selectedIds = new Set();
		crossPageActive = false;
	}

	function onBulkAction(action: string) {
		console.log('bulk action', action);
	}

	function onRowClick(id: string) {
		console.log('row click', id);
	}

	let filterSearch = $state('');
	let filterStatus = $state('');
	let filterVendor = $state('');
	let filterCurrency = $state('');
	let filterMilestone = $state('');
	let filterMarketplace = $state('');

	let tableSortBy = $state('issued_date');
	let tableSortDir = $state<'asc' | 'desc'>('desc');

	let pagPage = $state(4);
	let pagPageSize = $state(20);

	const STATUS_GRID: ReadonlyArray<{ status: POStatus; partial: boolean; key: string }> = [
		{ status: 'DRAFT', partial: false, key: 'draft' },
		{ status: 'PENDING', partial: false, key: 'pending' },
		{ status: 'MODIFIED', partial: false, key: 'modified' },
		{ status: 'ACCEPTED', partial: false, key: 'accepted' },
		{ status: 'ACCEPTED', partial: true, key: 'accepted-partial' },
		{ status: 'REJECTED', partial: false, key: 'rejected' },
		{ status: 'REVISED', partial: false, key: 'revised' }
	];
</script>

<svelte:head>
	<title>PO list preview - Phase 4.2</title>
</svelte:head>

<div class="ui-demo-po">
	<PageHeader title="Purchase Orders" subtitle="Phase 4.2 component preview">
		{#snippet action()}
			{#if canCreate}
				<Button data-testid="po-demo-new">+ New PO</Button>
			{/if}
		{/snippet}
	</PageHeader>

	<h1>PO list preview - Phase 4.2 Tier 1 (G-01..G-06)</h1>

	<div class="ui-demo-po__notice">
		Resize your viewport to 390px to verify mobile reflow. Toggle role + state controls below to
		drive each gap.
	</div>

	<div class="ui-demo-po__controls">
		<label class="ui-demo-po__control">
			<span>Role</span>
			<Select bind:value={role} options={[...ROLE_OPTIONS]} data-testid="po-demo-role" />
		</label>
		<label class="ui-demo-po__control">
			<span>Data state</span>
			<Select
				bind:value={dataState}
				options={[...DATA_STATE_OPTIONS]}
				data-testid="po-demo-data-state"
			/>
		</label>
		<label class="ui-demo-po__control">
			<span>Selection</span>
			<Select
				bind:value={selectionState}
				options={[...SELECTION_OPTIONS]}
				data-testid="po-demo-selection"
			/>
		</label>
	</div>

	<section>
		<h2>G-01 Filter bar</h2>
		<p class="ui-demo-po__desc">
			Top region above the data table. Vendor filter is hidden for VENDOR role; mobile collapses
			to a Filters button with a numeric badge.
		</p>
		<PoListFilters
			bind:search={filterSearch}
			bind:status={filterStatus}
			bind:vendor={filterVendor}
			bind:currency={filterCurrency}
			bind:milestone={filterMilestone}
			bind:marketplace={filterMarketplace}
			vendors={VENDORS}
			currencies={CURRENCIES}
			marketplaces={MARKETPLACES}
			showVendorFilter={showVendorFilter}
			data-testid="po-demo-filters"
		/>
	</section>

	<section>
		<h2>G-02 Bulk action bar</h2>
		<p class="ui-demo-po__desc">
			Between filter bar and table when rows are selected. Sticky bottom on mobile; reject opens a
			modal in the real list (logged here).
		</p>
		<PoListBulkBar
			selectedCount={selectedIds.size}
			totalMatching={totalMatching}
			validActions={validActions}
			crossPagePromotable={crossPagePromotable}
			crossPageActive={crossPageActive}
			bulkLoading={false}
			bulkBanner={bulkBanner}
			onAction={onBulkAction}
			onPromoteCrossPage={onPromoteCrossPage}
			onClear={onClearSelection}
			data-testid="po-demo-bulkbar"
		/>
	</section>

	<section>
		<h2>G-03 Status pills</h2>
		<p class="ui-demo-po__desc">
			Status column. Partial renders as a secondary pill alongside ACCEPTED.
		</p>
		<div class="ui-demo-po__pills">
			{#each STATUS_GRID as cell (cell.key)}
				<div class="ui-demo-po__pill-cell">
					<span class="ui-demo-po__pill-label"
						>{cell.status}{cell.partial ? ' + Partial' : ''}</span
					>
					<PoStatusPills status={cell.status} partial={cell.partial} />
				</div>
			{/each}
		</div>
	</section>

	<section>
		<h2>G-04 Row tap target + mobile milestone column</h2>
		<p class="ui-demo-po__desc">
			Rows in the list. Resize to 390px to see card-stack reflow with checkbox as a leading
			control.
		</p>
		{#if dataState === 'loading'}
			<div class="ui-demo-po__overlay-wrap">
				<PoListTable
					rows={tableRows}
					bind:selectedIds={selectedIds}
					canBulk={canBulk}
					bind:sortBy={tableSortBy}
					bind:sortDir={tableSortDir}
					onRowClick={onRowClick}
					data-testid="po-demo-table"
				/>
				<div class="ui-demo-po__overlay">
					<LoadingState />
				</div>
			</div>
		{:else if dataState === 'error'}
			<ErrorState
				message="Could not load Purchase Orders."
				onRetry={() => console.log('retry')}
			/>
		{:else if tableRows.length === 0}
			<EmptyState
				title="No Purchase Orders yet"
				description="Create your first Purchase Order to get started."
			>
				{#snippet action()}
					{#if canCreate}
						<Button>+ New PO</Button>
					{/if}
				{/snippet}
			</EmptyState>
		{:else}
			<PoListTable
				rows={tableRows}
				bind:selectedIds={selectedIds}
				canBulk={canBulk}
				bind:sortBy={tableSortBy}
				bind:sortDir={tableSortDir}
				onRowClick={onRowClick}
				data-testid="po-demo-table"
			/>
		{/if}
	</section>

	<section>
		<h2>G-05 Pagination</h2>
		<p class="ui-demo-po__desc">
			Footer below the table. Page-size 10/20/50/100/200; Prev/Next collapse to icon buttons at
			480px.
		</p>
		<PoListPagination
			bind:page={pagPage}
			bind:pageSize={pagPageSize}
			total={217}
			data-testid="po-demo-pagination"
		/>
	</section>

	<section>
		<h2>G-06 States</h2>
		<p class="ui-demo-po__desc">
			Empty / loading / error variants for the table area.
		</p>
		<div class="ui-demo-po__states">
			<div class="ui-demo-po__state">
				<h3>Empty (zero ever)</h3>
				<EmptyState
					title="No Purchase Orders yet"
					description="Create your first Purchase Order to get started."
				>
					{#snippet action()}
						{#if canCreate}
							<Button>+ New PO</Button>
						{/if}
					{/snippet}
				</EmptyState>
			</div>
			<div class="ui-demo-po__state">
				<h3>Empty (filtered)</h3>
				<EmptyState
					title="No matches"
					description="No Purchase Orders match the current filters."
				/>
			</div>
			<div class="ui-demo-po__state">
				<h3>Loading</h3>
				<LoadingState />
			</div>
			<div class="ui-demo-po__state">
				<h3>Error</h3>
				<ErrorState
					message="Could not load Purchase Orders."
					onRetry={() => console.log('retry')}
				/>
			</div>
		</div>
	</section>
</div>

<style>
	.ui-demo-po {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
		padding: var(--space-4);
		max-width: 1200px;
		margin-inline: auto;
	}
	.ui-demo-po__notice {
		padding: var(--space-3);
		background-color: var(--blue-100);
		color: var(--blue-800);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
	}
	.ui-demo-po__controls {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.ui-demo-po__control {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		font-size: var(--font-size-xs);
		color: var(--gray-600);
		min-width: 12rem;
	}
	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-4);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	h2 {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.ui-demo-po__desc {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		margin: 0;
	}
	.ui-demo-po__pills {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: var(--space-3);
	}
	.ui-demo-po__pill-cell {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-3);
		border: 1px dashed var(--gray-200);
		border-radius: var(--radius-sm);
	}
	.ui-demo-po__pill-label {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
		text-transform: uppercase;
		letter-spacing: var(--letter-spacing-wide);
	}
	.ui-demo-po__states {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: var(--space-4);
	}
	.ui-demo-po__state {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-3);
		border: 1px dashed var(--gray-200);
		border-radius: var(--radius-sm);
	}
	.ui-demo-po__state h3 {
		font-size: var(--font-size-sm);
		font-weight: 600;
		color: var(--gray-700);
		margin: 0;
	}
	.ui-demo-po__overlay-wrap {
		position: relative;
	}
	.ui-demo-po__overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(255, 255, 255, 0.7);
	}
</style>
