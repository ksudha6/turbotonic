<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';

	let {
		vendorName,
		partNumber,
		description = $bindable(''),
		manufacturingAddress = $bindable(''),
		canEdit,
		error = '',
		submitting = false,
		on_submit,
		on_cancel
	}: {
		vendorName: string;
		partNumber: string;
		description?: string;
		manufacturingAddress?: string;
		canEdit: boolean;
		error?: string;
		submitting?: boolean;
		on_submit: () => void;
		on_cancel: () => void;
	} = $props();

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		on_submit();
	}
</script>

<form
	class="product-edit-form"
	onsubmit={handleSubmit}
	data-testid="product-edit-form"
	novalidate
>
	<PanelCard title="Product Details">
		<div class="product-edit-form__grid">
			<div class="product-edit-form__field">
				<span class="product-edit-form__label">Vendor</span>
				<span class="product-edit-form__readonly" data-testid="product-edit-vendor">
					{vendorName}
				</span>
			</div>
			<div class="product-edit-form__field">
				<span class="product-edit-form__label">Part Number</span>
				<span
					class="product-edit-form__readonly product-edit-form__readonly--mono"
					data-testid="product-edit-part-number"
				>
					{partNumber}
				</span>
			</div>

			{#if canEdit}
				<FormField label="Description" data-testid="product-edit-description-field">
					{#snippet children()}
						<Input
							bind:value={description}
							ariaLabel="Description"
							data-testid="product-edit-description"
						/>
					{/snippet}
				</FormField>

				<div class="product-edit-form__span-2">
					<label
						class="product-edit-form__label"
						for="product-edit-manufacturing-address"
					>
						Manufacturing Address
					</label>
					<textarea
						id="product-edit-manufacturing-address"
						class="product-edit-form__textarea"
						bind:value={manufacturingAddress}
						data-testid="product-edit-manufacturing-address"
					></textarea>
				</div>
			{:else}
				<div class="product-edit-form__field">
					<span class="product-edit-form__label">Description</span>
					<span
						class="product-edit-form__readonly"
						data-testid="product-edit-description"
					>
						{description || '—'}
					</span>
				</div>
				<div class="product-edit-form__field product-edit-form__span-2">
					<span class="product-edit-form__label">Manufacturing Address</span>
					<span
						class="product-edit-form__readonly"
						data-testid="product-edit-manufacturing-address"
					>
						{manufacturingAddress || '—'}
					</span>
				</div>
			{/if}
		</div>
	</PanelCard>

	{#if error}
		<p class="product-edit-form__error" role="alert" data-testid="product-edit-error">{error}</p>
	{/if}

	<footer class="product-edit-form__footer">
		{#if canEdit}
			<Button variant="secondary" onclick={on_cancel} data-testid="product-edit-cancel">
				Cancel
			</Button>
			<Button
				type="submit"
				variant="primary"
				disabled={submitting}
				data-testid="product-edit-save"
			>
				{submitting ? 'Saving…' : 'Save Changes'}
			</Button>
		{:else}
			<Button variant="secondary" onclick={on_cancel} data-testid="product-edit-back">
				Back
			</Button>
		{/if}
	</footer>
</form>

<style>
	.product-edit-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.product-edit-form__grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-4);
	}
	@media (min-width: 768px) {
		.product-edit-form__grid {
			grid-template-columns: 1fr 1fr;
		}
		.product-edit-form__span-2 { grid-column: span 2; }
	}
	.product-edit-form__field {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.product-edit-form__label {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
		margin-bottom: var(--space-1);
	}
	.product-edit-form__readonly {
		font-size: var(--font-size-sm);
		color: var(--gray-900);
		padding: var(--space-2) 0;
	}
	.product-edit-form__readonly--mono {
		font-family: var(--font-family-mono, monospace);
	}
	.product-edit-form__textarea {
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
	.product-edit-form__textarea:focus {
		outline: 2px solid var(--brand-accent);
		outline-offset: -2px;
		border-color: var(--brand-accent);
	}
	.product-edit-form__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}
	.product-edit-form__footer {
		position: sticky;
		bottom: 0;
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-3) 0 calc(var(--space-3) + env(safe-area-inset-bottom, 0px));
		background: linear-gradient(to top, var(--surface-page) 60%, transparent);
	}
	@media (min-width: 768px) {
		.product-edit-form__footer {
			position: static;
			padding: var(--space-3) 0 0;
			background: transparent;
		}
	}
</style>
