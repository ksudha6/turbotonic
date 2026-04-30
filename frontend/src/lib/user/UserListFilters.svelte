<script lang="ts">
	import Select from '$lib/ui/Select.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { UserRole, UserStatus } from '$lib/types';

	let {
		status = $bindable(''),
		role = $bindable(''),
		onClear,
		'data-testid': testid
	}: {
		status?: UserStatus | '';
		role?: UserRole | '';
		onClear: () => void;
		'data-testid'?: string;
	} = $props();

	const STATUS_OPTIONS: ReadonlyArray<{ value: '' | UserStatus; label: string }> = [
		{ value: '', label: 'All Statuses' },
		{ value: 'ACTIVE', label: 'Active' },
		{ value: 'INACTIVE', label: 'Inactive' },
		{ value: 'PENDING', label: 'Pending' }
	];

	const ROLE_OPTIONS: ReadonlyArray<{ value: '' | UserRole; label: string }> = [
		{ value: '', label: 'All Roles' },
		{ value: 'ADMIN', label: 'Administrator' },
		{ value: 'SM', label: 'Supply Manager' },
		{ value: 'VENDOR', label: 'Vendor' },
		{ value: 'FREIGHT_MANAGER', label: 'Freight Manager' },
		{ value: 'QUALITY_LAB', label: 'Quality Lab' },
		{ value: 'PROCUREMENT_MANAGER', label: 'Procurement Manager' }
	];

	const activeCount = $derived((status ? 1 : 0) + (role ? 1 : 0));

	let mobilePanelOpen = $state(false);
	function toggleMobilePanel() {
		mobilePanelOpen = !mobilePanelOpen;
	}
</script>

<div class="user-list-filters" data-testid={testid ?? 'user-filters'}>
	<div class="user-list-filters__mobile-trigger">
		<Button variant="secondary" onclick={toggleMobilePanel} data-testid="user-filters-toggle">
			Filters{#if activeCount > 0}<span class="user-list-filters__badge">{activeCount}</span>{/if}
		</Button>
	</div>

	<div class="user-list-filters__row" class:user-list-filters__row--open={mobilePanelOpen}>
		<div class="user-list-filters__select">
			<Select
				bind:value={status}
				options={[...STATUS_OPTIONS]}
				ariaLabel="User status filter"
				data-testid="user-filter-status"
			/>
		</div>
		<div class="user-list-filters__select">
			<Select
				bind:value={role}
				options={[...ROLE_OPTIONS]}
				ariaLabel="User role filter"
				data-testid="user-filter-role"
			/>
		</div>
		<div class="user-list-filters__clear">
			<Button
				variant="ghost"
				onclick={onClear}
				disabled={activeCount === 0}
				data-testid="user-filter-clear"
			>
				Clear
			</Button>
		</div>
	</div>
</div>

<style>
	.user-list-filters {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.user-list-filters__mobile-trigger {
		display: block;
	}
	.user-list-filters__badge {
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
	.user-list-filters__row {
		display: none;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.user-list-filters__row--open {
		display: flex;
	}
	.user-list-filters__select,
	.user-list-filters__clear {
		width: 100%;
	}
	@media (min-width: 768px) {
		.user-list-filters__mobile-trigger { display: none; }
		.user-list-filters__row {
			display: flex;
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			padding: 0;
			background: transparent;
			border: none;
		}
		.user-list-filters__select { flex: 0 1 200px; min-width: 160px; width: auto; }
		.user-list-filters__clear { flex: 0 0 auto; width: auto; margin-left: auto; }
	}
</style>
