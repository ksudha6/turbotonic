<script lang="ts">
	import Select from '$lib/ui/Select.svelte';
	import Button from '$lib/ui/Button.svelte';

	let {
		status = $bindable(''),
		vendorType = $bindable(''),
		onClear,
		'data-testid': testid
	}: {
		status?: string;
		vendorType?: string;
		onClear: () => void;
		'data-testid'?: string;
	} = $props();

	const STATUS_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: '', label: 'All Statuses' },
		{ value: 'ACTIVE', label: 'Active' },
		{ value: 'INACTIVE', label: 'Inactive' }
	];

	const VENDOR_TYPE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: '', label: 'All Types' },
		{ value: 'PROCUREMENT', label: 'Procurement' },
		{ value: 'OPEX', label: 'OpEx' },
		{ value: 'FREIGHT', label: 'Freight' },
		{ value: 'MISCELLANEOUS', label: 'Miscellaneous' }
	];

	const activeCount = $derived((status ? 1 : 0) + (vendorType ? 1 : 0));

	let mobilePanelOpen = $state(false);
	function toggleMobilePanel() {
		mobilePanelOpen = !mobilePanelOpen;
	}
</script>

<div class="vendor-list-filters" data-testid={testid ?? 'vendor-filters'}>
	<div class="vendor-list-filters__mobile-trigger">
		<Button variant="secondary" onclick={toggleMobilePanel} data-testid="vendor-filters-toggle">
			Filters{#if activeCount > 0}<span class="vendor-list-filters__badge">{activeCount}</span>{/if}
		</Button>
	</div>

	<div class="vendor-list-filters__row" class:vendor-list-filters__row--open={mobilePanelOpen}>
		<div class="vendor-list-filters__select">
			<Select
				bind:value={status}
				options={[...STATUS_OPTIONS]}
				ariaLabel="Vendor status filter"
				data-testid="vendor-filter-status"
			/>
		</div>
		<div class="vendor-list-filters__select">
			<Select
				bind:value={vendorType}
				options={[...VENDOR_TYPE_OPTIONS]}
				ariaLabel="Vendor type filter"
				data-testid="vendor-filter-type"
			/>
		</div>
		<div class="vendor-list-filters__clear">
			<Button
				variant="ghost"
				onclick={onClear}
				disabled={activeCount === 0}
				data-testid="vendor-filter-clear"
			>
				Clear
			</Button>
		</div>
	</div>
</div>

<style>
	.vendor-list-filters {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.vendor-list-filters__mobile-trigger {
		display: block;
	}
	.vendor-list-filters__badge {
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
	.vendor-list-filters__row {
		display: none;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.vendor-list-filters__row--open {
		display: flex;
	}
	.vendor-list-filters__select,
	.vendor-list-filters__clear {
		width: 100%;
	}
	@media (min-width: 768px) {
		.vendor-list-filters__mobile-trigger { display: none; }
		.vendor-list-filters__row {
			display: flex;
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			padding: 0;
			background: transparent;
			border: none;
		}
		.vendor-list-filters__select { flex: 0 1 200px; min-width: 160px; width: auto; }
		.vendor-list-filters__clear { flex: 0 0 auto; width: auto; margin-left: auto; }
	}
</style>
