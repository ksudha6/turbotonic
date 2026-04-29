<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Select from '$lib/ui/Select.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import type { QualificationTypeListItem } from '$lib/types';

	let {
		current,
		all,
		canManage,
		error = '',
		on_add,
		on_remove
	}: {
		current: QualificationTypeListItem[];
		all: QualificationTypeListItem[];
		canManage: boolean;
		error?: string;
		on_add: (qualificationTypeId: string) => void;
		on_remove: (qualificationTypeId: string) => void;
	} = $props();

	let selectedQtId: string = $state('');

	const available = $derived(() => {
		const assigned = new Set(current.map((q) => q.id));
		return all.filter((qt) => !assigned.has(qt.id));
	});

	const addOptions = $derived([
		{ value: '', label: 'Add qualification…' },
		...available().map((qt) => ({ value: qt.id, label: `${qt.name} (${qt.target_market})` }))
	]);

	function handleAdd() {
		if (!selectedQtId) return;
		const id = selectedQtId;
		selectedQtId = '';
		on_add(id);
	}
</script>

<div data-testid="product-qualifications-panel">
	<PanelCard title="Qualifications">
		{#if current.length === 0}
			<EmptyState title="No qualifications assigned." />
		{:else}
			<ul class="product-qualifications-panel__list">
				{#each current as qt (qt.id)}
					<li
						class="product-qualifications-panel__row"
						data-testid={`product-qualification-row-${qt.id}`}
					>
						<span class="product-qualifications-panel__name">{qt.name}</span>
						<StatusPill tone="blue" label={qt.target_market} />
						{#if canManage}
							<Button
								variant="secondary"
								onclick={() => on_remove(qt.id)}
								data-testid={`product-qualification-remove-${qt.id}`}
							>
								Remove
							</Button>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}

		{#if canManage}
			<div class="product-qualifications-panel__add-row">
				<div class="product-qualifications-panel__add-select">
					<Select
						bind:value={selectedQtId}
						options={addOptions}
						ariaLabel="Add qualification"
						data-testid="product-qualification-add-select"
					/>
				</div>
				<Button
					variant="primary"
					onclick={handleAdd}
					disabled={!selectedQtId}
					data-testid="product-qualification-add-button"
				>
					Add
				</Button>
			</div>
		{/if}

		{#if error}
			<p
				class="product-qualifications-panel__error"
				role="alert"
				data-testid="product-qualifications-error"
			>
				{error}
			</p>
		{/if}
	</PanelCard>
</div>

<style>
	.product-qualifications-panel__list {
		list-style: none;
		padding: 0;
		margin: 0 0 var(--space-3);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.product-qualifications-panel__row {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}
	.product-qualifications-panel__row:last-child {
		border-bottom: none;
	}
	.product-qualifications-panel__name {
		font-weight: 500;
		color: var(--gray-900);
		flex: 1;
	}
	.product-qualifications-panel__add-row {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-top: var(--space-3);
	}
	.product-qualifications-panel__add-select {
		flex: 1;
	}
	.product-qualifications-panel__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		margin: var(--space-3) 0 0;
	}
</style>
