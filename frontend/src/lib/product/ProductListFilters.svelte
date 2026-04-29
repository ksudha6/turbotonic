<script lang="ts">
	import Select from '$lib/ui/Select.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { VendorListItem } from '$lib/types';

	let {
		vendor = $bindable(''),
		vendors,
		onClear,
		'data-testid': testid
	}: {
		vendor?: string;
		vendors: VendorListItem[];
		onClear: () => void;
		'data-testid'?: string;
	} = $props();

	const vendorOptions = $derived([
		{ value: '', label: 'All Vendors' },
		...vendors.map((v) => ({ value: v.id, label: v.name }))
	]);

	const activeCount = $derived(vendor ? 1 : 0);

	let mobilePanelOpen = $state(false);
	function toggleMobilePanel() {
		mobilePanelOpen = !mobilePanelOpen;
	}
</script>

<div class="product-list-filters" data-testid={testid ?? 'product-filters'}>
	<div class="product-list-filters__mobile-trigger">
		<Button variant="secondary" onclick={toggleMobilePanel} data-testid="product-filters-toggle">
			Filters{#if activeCount > 0}<span class="product-list-filters__badge">{activeCount}</span>{/if}
		</Button>
	</div>

	<div class="product-list-filters__row" class:product-list-filters__row--open={mobilePanelOpen}>
		<div class="product-list-filters__select">
			<Select
				bind:value={vendor}
				options={vendorOptions}
				ariaLabel="Vendor filter"
				data-testid="product-filter-vendor"
			/>
		</div>
		<div class="product-list-filters__clear">
			<Button
				variant="ghost"
				onclick={onClear}
				disabled={activeCount === 0}
				data-testid="product-filter-clear"
			>
				Clear
			</Button>
		</div>
	</div>
</div>

<style>
	.product-list-filters {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.product-list-filters__mobile-trigger { display: block; }
	.product-list-filters__badge {
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
	.product-list-filters__row {
		display: none;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.product-list-filters__row--open { display: flex; }
	.product-list-filters__select,
	.product-list-filters__clear { width: 100%; }
	@media (min-width: 768px) {
		.product-list-filters__mobile-trigger { display: none; }
		.product-list-filters__row {
			display: flex;
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			padding: 0;
			background: transparent;
			border: none;
		}
		.product-list-filters__select { flex: 0 1 240px; min-width: 200px; width: auto; }
		.product-list-filters__clear { flex: 0 0 auto; width: auto; margin-left: auto; }
	}
</style>
