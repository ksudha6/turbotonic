<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Button from '$lib/ui/Button.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import type { PackagingSpec } from '$lib/types';

	export type PackagingSpecAddFields = {
		marketplace: string;
		spec_name: string;
		description: string;
		requirements_text: string;
	};

	let {
		specs,
		canManage,
		error = '',
		addError = '',
		adding = false,
		on_add_spec,
		on_delete_spec
	}: {
		specs: PackagingSpec[];
		canManage: boolean;
		error?: string;
		addError?: string;
		adding?: boolean;
		on_add_spec: (fields: PackagingSpecAddFields) => Promise<void> | void;
		on_delete_spec: (id: string) => void;
	} = $props();

	let showAddForm: boolean = $state(false);
	let marketplace: string = $state('');
	let spec_name: string = $state('');
	let description: string = $state('');
	let requirements_text: string = $state('');

	let marketplaceError: string = $state('');
	let specNameError: string = $state('');

	const specsByMarketplace = $derived(() => {
		const groups: Record<string, PackagingSpec[]> = {};
		for (const spec of specs) {
			if (!groups[spec.marketplace]) groups[spec.marketplace] = [];
			groups[spec.marketplace].push(spec);
		}
		return groups;
	});

	type Tone = 'green' | 'gray' | 'blue' | 'orange' | 'red';
	function statusTone(status: string): Tone {
		if (status === 'COLLECTED') return 'green';
		return 'gray';
	}

	function isBlank(v: string): boolean {
		return v.trim().length === 0;
	}

	function validate(): boolean {
		marketplaceError = '';
		specNameError = '';
		let ok = true;
		if (isBlank(marketplace)) {
			marketplaceError = 'Marketplace is required.';
			ok = false;
		}
		if (isBlank(spec_name)) {
			specNameError = 'Spec name is required.';
			ok = false;
		}
		return ok;
	}

	function resetForm() {
		marketplace = '';
		spec_name = '';
		description = '';
		requirements_text = '';
		marketplaceError = '';
		specNameError = '';
	}

	function toggleAddForm() {
		showAddForm = !showAddForm;
		if (!showAddForm) resetForm();
	}

	async function handleAddSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!validate()) return;
		await on_add_spec({
			marketplace: marketplace.trim(),
			spec_name: spec_name.trim(),
			description: description.trim(),
			requirements_text: requirements_text.trim()
		});
	}

	// Parent closes the form by setting `adding` back to false after a successful
	// add; since we don't get a success signal directly, the parent must clear
	// addError + the panel hides the form when the panel detects a new spec
	// matching the just-submitted (marketplace, spec_name) pair. Simpler: expose
	// a `close_after_add` derived signal — when adding flips false AND addError
	// is empty AND the just-submitted name shows up in the list, we hide the form.
	// In practice, parent flips adding=false after a successful POST; we hide the
	// form when adding goes false-after-true with no error.
	let wasAdding = $state(false);
	$effect(() => {
		if (adding) wasAdding = true;
		else if (wasAdding && !addError) {
			wasAdding = false;
			showAddForm = false;
			resetForm();
		} else if (wasAdding && addError) {
			wasAdding = false;
		}
	});
</script>

<div data-testid="product-packaging-panel">
	<PanelCard title="Packaging Specs">
		{#snippet action()}
			{#if canManage}
				<Button
					variant="secondary"
					onclick={toggleAddForm}
					data-testid="product-packaging-add-trigger"
				>
					{showAddForm ? 'Cancel' : 'Add Spec'}
				</Button>
			{/if}
		{/snippet}

		{#if error}
			<p
				class="product-packaging-panel__error"
				role="alert"
				data-testid="product-packaging-error"
			>
				{error}
			</p>
		{/if}

		{#if canManage && showAddForm}
			<form
				class="product-packaging-panel__add-form"
				onsubmit={handleAddSubmit}
				data-testid="product-packaging-add-form"
				novalidate
			>
				<div class="product-packaging-panel__add-grid">
					<FormField
						label="Marketplace"
						required
						error={marketplaceError}
					>
						{#snippet children({ invalid })}
							<Input
								bind:value={marketplace}
								{invalid}
								ariaLabel="Marketplace"
								data-testid="product-packaging-add-marketplace"
							/>
						{/snippet}
					</FormField>

					<FormField
						label="Spec Name"
						required
						error={specNameError}
					>
						{#snippet children({ invalid })}
							<Input
								bind:value={spec_name}
								{invalid}
								ariaLabel="Spec name"
								data-testid="product-packaging-add-spec-name"
							/>
						{/snippet}
					</FormField>

					<div class="product-packaging-panel__span-2">
						<FormField label="Description">
							{#snippet children()}
								<Input
									bind:value={description}
									ariaLabel="Description"
									data-testid="product-packaging-add-description"
								/>
							{/snippet}
						</FormField>
					</div>

					<div class="product-packaging-panel__span-2">
						<label
							class="product-packaging-panel__label"
							for="product-packaging-add-requirements"
						>
							Requirements
						</label>
						<textarea
							id="product-packaging-add-requirements"
							class="product-packaging-panel__textarea"
							bind:value={requirements_text}
							data-testid="product-packaging-add-requirements"
						></textarea>
					</div>
				</div>

				{#if addError}
					<p
						class="product-packaging-panel__error"
						role="alert"
						data-testid="product-packaging-add-error"
					>
						{addError}
					</p>
				{/if}

				<div class="product-packaging-panel__add-footer">
					<Button
						variant="secondary"
						onclick={toggleAddForm}
						data-testid="product-packaging-add-cancel"
					>
						Cancel
					</Button>
					<Button
						type="submit"
						variant="primary"
						disabled={adding}
						data-testid="product-packaging-add-submit"
					>
						{adding ? 'Adding…' : 'Add Spec'}
					</Button>
				</div>
			</form>
		{/if}

		{#if specs.length === 0}
			<EmptyState title="No packaging specs defined yet." />
		{:else}
			{#each Object.entries(specsByMarketplace()) as [marketplace, group]}
				<section class="product-packaging-panel__group">
					<h3 class="product-packaging-panel__group-heading">{marketplace}</h3>
					<ul class="product-packaging-panel__list">
						{#each group as spec (spec.id)}
							<li
								class="product-packaging-panel__row"
								data-testid={`product-packaging-row-${spec.id}`}
							>
								<div class="product-packaging-panel__row-info">
									<span class="product-packaging-panel__spec-name">{spec.spec_name}</span>
									{#if spec.description}
										<span class="product-packaging-panel__spec-description">
											{spec.description}
										</span>
									{/if}
								</div>
								<div class="product-packaging-panel__row-meta">
									<StatusPill
										tone={statusTone(spec.status)}
										label={spec.status}
										data-testid={`product-packaging-row-status-${spec.id}`}
									/>
									{#if canManage && spec.status === 'PENDING'}
										<Button
											variant="secondary"
											onclick={() => {
												if (window.confirm('Delete this packaging spec?')) {
													on_delete_spec(spec.id);
												}
											}}
											data-testid={`product-packaging-row-delete-${spec.id}`}
										>
											Delete
										</Button>
									{/if}
								</div>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		{/if}
	</PanelCard>
</div>

<style>
	.product-packaging-panel__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0 0 var(--space-3);
	}
	.product-packaging-panel__add-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		margin-bottom: var(--space-4);
	}
	.product-packaging-panel__add-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-3);
	}
	@media (min-width: 768px) {
		.product-packaging-panel__add-grid {
			grid-template-columns: 1fr 1fr;
		}
		.product-packaging-panel__span-2 { grid-column: span 2; }
	}
	.product-packaging-panel__label {
		display: block;
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
		margin-bottom: var(--space-1);
	}
	.product-packaging-panel__textarea {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-family: var(--font-family);
		font-size: var(--font-size-sm);
		color: var(--gray-900);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		resize: vertical;
		min-height: 4rem;
	}
	.product-packaging-panel__textarea:focus {
		outline: 2px solid var(--brand-accent);
		outline-offset: -2px;
		border-color: var(--brand-accent);
	}
	.product-packaging-panel__add-footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}
	.product-packaging-panel__group {
		margin-top: var(--space-4);
	}
	.product-packaging-panel__group:first-of-type {
		margin-top: 0;
	}
	.product-packaging-panel__group-heading {
		font-size: var(--font-size-base);
		font-weight: 600;
		color: var(--gray-900);
		margin: 0 0 var(--space-2);
	}
	.product-packaging-panel__list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.product-packaging-panel__row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}
	.product-packaging-panel__row:last-child {
		border-bottom: none;
	}
	.product-packaging-panel__row-info {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.product-packaging-panel__spec-name {
		font-weight: 500;
		color: var(--gray-900);
	}
	.product-packaging-panel__spec-description {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.product-packaging-panel__row-meta {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
</style>
