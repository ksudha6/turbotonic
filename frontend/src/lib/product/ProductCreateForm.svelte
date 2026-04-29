<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Select from '$lib/ui/Select.svelte';
	import type { VendorListItem } from '$lib/types';

	export type ProductCreateFields = {
		vendor_id: string;
		part_number: string;
		description: string;
		manufacturing_address: string;
	};

	let {
		vendors,
		error = '',
		submitting = false,
		on_submit,
		on_cancel
	}: {
		vendors: VendorListItem[];
		error?: string;
		submitting?: boolean;
		on_submit: (fields: ProductCreateFields) => void;
		on_cancel: () => void;
	} = $props();

	let vendor_id: string = $state('');
	let part_number: string = $state('');
	let description: string = $state('');
	let manufacturing_address: string = $state('');

	let vendorError: string = $state('');
	let partNumberError: string = $state('');

	const VENDOR_OPTIONS = $derived([
		{ value: '', label: 'Select vendor' },
		...vendors.map((v) => ({ value: v.id, label: v.name }))
	]);

	function isBlank(v: string): boolean {
		return v.trim().length === 0;
	}

	function validate(): boolean {
		vendorError = '';
		partNumberError = '';
		let ok = true;
		if (isBlank(vendor_id)) {
			vendorError = 'Vendor is required.';
			ok = false;
		}
		if (isBlank(part_number)) {
			partNumberError = 'Part Number is required.';
			ok = false;
		}
		return ok;
	}

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!validate()) return;
		on_submit({
			vendor_id,
			part_number: part_number.trim(),
			description: description.trim(),
			manufacturing_address
		});
	}
</script>

<form
	class="product-create-form"
	onsubmit={handleSubmit}
	data-testid="product-create-form"
	novalidate
>
	<PanelCard title="Product Details">
		<div class="product-create-form__grid">
			<FormField
				label="Vendor"
				required
				error={vendorError}
				data-testid="product-form-vendor-field"
			>
				{#snippet children({ invalid })}
					<Select
						bind:value={vendor_id}
						options={VENDOR_OPTIONS}
						{invalid}
						ariaLabel="Vendor"
						data-testid="product-form-vendor"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Part Number"
				required
				error={partNumberError}
				data-testid="product-form-part-number-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={part_number}
						{invalid}
						ariaLabel="Part Number"
						data-testid="product-form-part-number"
					/>
				{/snippet}
			</FormField>

			<FormField label="Description" data-testid="product-form-description-field">
				{#snippet children()}
					<Input
						bind:value={description}
						ariaLabel="Description"
						data-testid="product-form-description"
					/>
				{/snippet}
			</FormField>

			<div class="product-create-form__span-2">
				<label class="product-create-form__label" for="product-form-manufacturing-address">
					Manufacturing Address
				</label>
				<textarea
					id="product-form-manufacturing-address"
					class="product-create-form__textarea"
					bind:value={manufacturing_address}
					data-testid="product-form-manufacturing-address"
				></textarea>
			</div>
		</div>
	</PanelCard>

	{#if error}
		<p class="product-create-form__error" role="alert" data-testid="product-form-error">{error}</p>
	{/if}

	<footer class="product-create-form__footer">
		<Button variant="secondary" onclick={on_cancel} data-testid="product-form-cancel">
			Cancel
		</Button>
		<Button
			type="submit"
			variant="primary"
			disabled={submitting}
			data-testid="product-form-submit"
		>
			{submitting ? 'Creating…' : 'Create Product'}
		</Button>
	</footer>
</form>

<style>
	.product-create-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.product-create-form__grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-4);
	}
	@media (min-width: 768px) {
		.product-create-form__grid {
			grid-template-columns: 1fr 1fr;
		}
		.product-create-form__span-2 { grid-column: span 2; }
	}
	.product-create-form__label {
		display: block;
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
		margin-bottom: var(--space-1);
	}
	.product-create-form__textarea {
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
	.product-create-form__textarea:focus {
		outline: 2px solid var(--brand-accent);
		outline-offset: -2px;
		border-color: var(--brand-accent);
	}
	.product-create-form__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}
	.product-create-form__footer {
		position: sticky;
		bottom: 0;
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-3) 0 calc(var(--space-3) + env(safe-area-inset-bottom, 0px));
		background: linear-gradient(to top, var(--surface-page) 60%, transparent);
	}
	@media (min-width: 768px) {
		.product-create-form__footer {
			position: static;
			padding: var(--space-3) 0 0;
			background: transparent;
		}
	}
</style>
