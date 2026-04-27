<script lang="ts">
	import Select from '$lib/ui/Select.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { VendorListItem, ReferenceDataItem } from '$lib/types';

	let {
		search = $bindable(''),
		status = $bindable(''),
		vendor = $bindable(''),
		currency = $bindable(''),
		milestone = $bindable(''),
		marketplace = $bindable(''),
		vendors,
		currencies,
		marketplaces,
		showVendorFilter = true,
		'data-testid': testid
	}: {
		search?: string;
		status?: string;
		vendor?: string;
		currency?: string;
		milestone?: string;
		marketplace?: string;
		vendors: VendorListItem[];
		currencies: ReferenceDataItem[];
		marketplaces: ReferenceDataItem[];
		showVendorFilter?: boolean;
		'data-testid'?: string;
	} = $props();

	const STATUS_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: '', label: 'All Statuses' },
		{ value: 'DRAFT', label: 'Draft' },
		{ value: 'PENDING', label: 'Pending' },
		{ value: 'MODIFIED', label: 'Modified' },
		{ value: 'ACCEPTED', label: 'Accepted' },
		{ value: 'REJECTED', label: 'Rejected' },
		{ value: 'REVISED', label: 'Revised' }
	];

	const MILESTONE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: '', label: 'All Milestones' },
		{ value: 'RAW_MATERIALS', label: 'Raw Materials' },
		{ value: 'PRODUCTION_STARTED', label: 'Production Started' },
		{ value: 'QC_PASSED', label: 'QC Passed' },
		{ value: 'READY_FOR_SHIPMENT', label: 'Ready for Shipment' },
		{ value: 'SHIPPED', label: 'Shipped' }
	];

	const vendorOptions = $derived([
		{ value: '', label: 'All Vendors' },
		...vendors.map((v) => ({ value: v.id, label: v.name }))
	]);

	const currencyOptions = $derived([
		{ value: '', label: 'All Currencies' },
		...currencies.map((c) => ({ value: c.code, label: `${c.code} — ${c.label}` }))
	]);

	const marketplaceOptions = $derived([
		{ value: '', label: 'All Marketplaces' },
		...marketplaces.map((m) => ({ value: m.code, label: m.label }))
	]);

	const activeCount = $derived(
		(status ? 1 : 0) +
			(showVendorFilter && vendor ? 1 : 0) +
			(currency ? 1 : 0) +
			(milestone ? 1 : 0) +
			(marketplace ? 1 : 0) +
			(search.trim() ? 1 : 0)
	);

	let mobilePanelOpen = $state(false);
	function toggleMobilePanel() {
		mobilePanelOpen = !mobilePanelOpen;
	}
</script>

<div class="po-list-filters" data-testid={testid ?? 'po-filters'}>
	<div class="po-list-filters__mobile-trigger">
		<Button variant="secondary" onclick={toggleMobilePanel} data-testid="po-filters-toggle">
			Filters{#if activeCount > 0}<span class="po-list-filters__badge">{activeCount}</span>{/if}
		</Button>
	</div>

	<div class="po-list-filters__row" class:po-list-filters__row--open={mobilePanelOpen}>
		<div class="po-list-filters__search">
			<Input
				bind:value={search}
				placeholder="Search PO#, vendor, buyer..."
				data-testid="po-filter-search"
			/>
		</div>
		<div class="po-list-filters__select">
			<Select bind:value={status} options={[...STATUS_OPTIONS]} data-testid="po-filter-status" />
		</div>
		{#if showVendorFilter}
			<div class="po-list-filters__select">
				<Select bind:value={vendor} options={vendorOptions} data-testid="po-filter-vendor" />
			</div>
		{/if}
		<div class="po-list-filters__select">
			<Select bind:value={currency} options={currencyOptions} data-testid="po-filter-currency" />
		</div>
		<div class="po-list-filters__select">
			<Select
				bind:value={marketplace}
				options={marketplaceOptions}
				data-testid="po-filter-marketplace"
			/>
		</div>
		<div class="po-list-filters__select">
			<Select
				bind:value={milestone}
				options={[...MILESTONE_OPTIONS]}
				data-testid="po-filter-milestone"
			/>
		</div>
	</div>
</div>

<style>
	.po-list-filters {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.po-list-filters__mobile-trigger {
		display: block;
	}
	.po-list-filters__badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 1.25rem;
		height: 1.25rem;
		padding: 0 var(--space-2);
		margin-left: var(--space-2);
		background-color: var(--brand-accent);
		color: var(--white);
		font-size: var(--font-size-xs);
		font-weight: 600;
		border-radius: 999px;
	}
	.po-list-filters__row {
		display: none;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.po-list-filters__row--open {
		display: flex;
	}
	.po-list-filters__search,
	.po-list-filters__select {
		width: 100%;
	}
	@media (min-width: 768px) {
		.po-list-filters__mobile-trigger {
			display: none;
		}
		.po-list-filters__row {
			display: flex;
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			padding: 0;
			background: transparent;
			border: none;
		}
		.po-list-filters__search {
			flex: 1 1 240px;
			min-width: 200px;
		}
		.po-list-filters__select {
			flex: 0 1 180px;
			min-width: 160px;
			width: auto;
		}
	}
</style>
