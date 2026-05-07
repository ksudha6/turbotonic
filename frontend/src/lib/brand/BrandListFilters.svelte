<script lang="ts">
	import Select from '$lib/ui/Select.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { BrandStatus } from '$lib/types';

	let {
		status = $bindable('' as BrandStatus | ''),
		onClear,
		'data-testid': testid
	}: {
		status?: BrandStatus | '';
		onClear: () => void;
		'data-testid'?: string;
	} = $props();

	const STATUS_OPTIONS: ReadonlyArray<{ value: '' | BrandStatus; label: string }> = [
		{ value: '', label: 'All Statuses' },
		{ value: 'ACTIVE', label: 'Active' },
		{ value: 'INACTIVE', label: 'Inactive' }
	];

	const activeCount = $derived(status ? 1 : 0);

	let mobilePanelOpen = $state(false);
	function toggleMobilePanel() {
		mobilePanelOpen = !mobilePanelOpen;
	}
</script>

<div class="brand-list-filters" data-testid={testid ?? 'brand-filters'}>
	<div class="brand-list-filters__mobile-trigger">
		<Button variant="secondary" onclick={toggleMobilePanel} data-testid="brand-filters-toggle">
			Filters{#if activeCount > 0}<span class="brand-list-filters__badge">{activeCount}</span>{/if}
		</Button>
	</div>

	<div class="brand-list-filters__row" class:brand-list-filters__row--open={mobilePanelOpen}>
		<div class="brand-list-filters__select">
			<Select
				bind:value={status}
				options={[...STATUS_OPTIONS]}
				ariaLabel="Brand status filter"
				data-testid="brand-filter-status"
			/>
		</div>
		<div class="brand-list-filters__clear">
			<Button
				variant="ghost"
				onclick={onClear}
				disabled={activeCount === 0}
				data-testid="brand-filter-clear"
			>
				Clear
			</Button>
		</div>
	</div>
</div>

<style>
	.brand-list-filters {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.brand-list-filters__mobile-trigger {
		display: block;
	}
	.brand-list-filters__badge {
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
	.brand-list-filters__row {
		display: none;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.brand-list-filters__row--open {
		display: flex;
	}
	.brand-list-filters__select,
	.brand-list-filters__clear {
		width: 100%;
	}
	@media (min-width: 768px) {
		.brand-list-filters__mobile-trigger { display: none; }
		.brand-list-filters__row {
			display: flex;
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			padding: 0;
			background: transparent;
			border: none;
		}
		.brand-list-filters__select { flex: 0 1 200px; min-width: 160px; width: auto; }
		.brand-list-filters__clear { flex: 0 0 auto; width: auto; margin-left: auto; }
	}
</style>
