<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Select from '$lib/ui/Select.svelte';
	import type { Vendor } from '$lib/types';

	let {
		brandId,
		assignedVendors,
		allActiveVendors,
		onAssign,
		onUnassign
	}: {
		brandId: string;
		assignedVendors: Vendor[];
		allActiveVendors: Vendor[];
		onAssign: (vendorId: string) => Promise<void>;
		onUnassign: (vendorId: string) => Promise<void>;
	} = $props();

	// vendorId for the "Add" combobox
	let selectedVendorId: string = $state('');
	let addError: string = $state('');
	let addPending: boolean = $state(false);
	// per-row remove errors keyed by vendor id
	let removeErrors: Record<string, string> = $state({});
	let removePending: Record<string, boolean> = $state({});

	// Vendors not yet assigned
	const unassignedVendors = $derived(
		allActiveVendors.filter((v) => !assignedVendors.some((a) => a.id === v.id))
	);

	const addOptions = $derived([
		{ value: '', label: 'Select a vendor to add' },
		...unassignedVendors.map((v) => ({ value: v.id, label: `${v.name} (${v.country})` }))
	]);

	async function handleAdd() {
		if (!selectedVendorId) return;
		addError = '';
		addPending = true;
		try {
			await onAssign(selectedVendorId);
			selectedVendorId = '';
		} catch (e) {
			addError = e instanceof Error ? e.message : 'Failed to assign vendor';
		} finally {
			addPending = false;
		}
	}

	async function handleRemove(vendorId: string) {
		removeErrors = { ...removeErrors, [vendorId]: '' };
		removePending = { ...removePending, [vendorId]: true };
		try {
			await onUnassign(vendorId);
		} catch (e) {
			removeErrors = {
				...removeErrors,
				[vendorId]: e instanceof Error ? e.message : 'Failed to remove vendor'
			};
		} finally {
			removePending = { ...removePending, [vendorId]: false };
		}
	}
</script>

<PanelCard title="Vendors" data-testid="brand-vendor-panel">
	{#snippet children()}
		<div class="bvap">
			{#if assignedVendors.length === 0}
				<p class="bvap__empty">No vendors assigned yet.</p>
			{:else}
				<ul class="bvap__list">
					{#each assignedVendors as vendor (vendor.id)}
						<li class="bvap__row" data-testid={`brand-vendor-row-${vendor.id}`}>
							<span class="bvap__vendor-name">{vendor.name}</span>
							<span class="bvap__vendor-country">{vendor.country}</span>
							{#if removeErrors[vendor.id]}
								<span class="bvap__row-error" role="alert">{removeErrors[vendor.id]}</span>
							{/if}
							<Button
								variant="secondary"
								onclick={() => handleRemove(vendor.id)}
								disabled={removePending[vendor.id]}
								data-testid={`brand-vendor-remove-${vendor.id}`}
							>
								Remove
							</Button>
						</li>
					{/each}
				</ul>
			{/if}

			<div class="bvap__add-row">
				<Select
					bind:value={selectedVendorId}
					options={addOptions}
					ariaLabel="Vendor to assign"
					data-testid="brand-vendor-add-select"
				/>
				<Button
					variant="primary"
					onclick={handleAdd}
					disabled={!selectedVendorId || addPending}
					data-testid="brand-vendor-add-button"
				>
					Add
				</Button>
			</div>
			{#if addError}
				<p class="bvap__add-error" role="alert" data-testid="brand-vendor-add-error">{addError}</p>
			{/if}
		</div>
	{/snippet}
</PanelCard>

<style>
	.bvap {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.bvap__empty {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
	.bvap__list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.bvap__row {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}
	.bvap__vendor-name {
		font-size: var(--font-size-sm);
		font-weight: 500;
		flex: 1;
	}
	.bvap__vendor-country {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
	}
	.bvap__row-error {
		font-size: var(--font-size-xs);
		color: var(--red-700);
	}
	.bvap__add-row {
		display: flex;
		gap: var(--space-3);
		align-items: center;
		flex-wrap: wrap;
	}
	.bvap__add-error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		margin: 0;
	}
</style>
