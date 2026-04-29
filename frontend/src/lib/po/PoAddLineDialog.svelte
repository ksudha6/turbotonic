<script lang="ts">
	import type { ReferenceData } from '$lib/types';
	import Button from '$lib/ui/Button.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Select from '$lib/ui/Select.svelte';

	export type AddLineFields = {
		part_number: string;
		description: string;
		quantity: number;
		uom: string;
		unit_price: string;
		hs_code: string;
		country_of_origin: string;
	};

	let {
		reference_data,
		error = '',
		on_submit,
		on_close,
		'data-testid': testid
	}: {
		reference_data: ReferenceData;
		error?: string;
		on_submit: (fields: AddLineFields) => Promise<void>;
		on_close: () => void;
		'data-testid'?: string;
	} = $props();

	// Snapshot the initial country code at component init. The dialog is short-
	// lived (mounted on open, unmounted on close) so reading reference_data once
	// here is intentional — see Svelte's state_referenced_locally note.
	const initialCountry = reference_data.countries[0]?.code ?? '';

	let part_number: string = $state('');
	let description: string = $state('');
	let quantity: string = $state('1');
	let unit_price: string = $state('0.00');
	let uom: string = $state('EA');
	let hs_code: string = $state('');
	let country_of_origin: string = $state(initialCountry);

	let partNumberError: string = $state('');
	let descriptionError: string = $state('');
	let uomError: string = $state('');
	let countryError: string = $state('');

	let submitting: boolean = $state(false);

	const titleId = crypto.randomUUID();

	// UoM and HS code are not in ReferenceData (free-form per iter 020), so the
	// dialog uses Input for both. Country of origin uses the reference list.
	const COUNTRY_OPTIONS = $derived(
		reference_data.countries.map((c) => ({ value: c.code, label: c.label }))
	);

	function isBlank(v: string): boolean {
		return v.trim().length === 0;
	}

	function validate(): boolean {
		partNumberError = '';
		descriptionError = '';
		uomError = '';
		countryError = '';
		let ok = true;
		if (isBlank(part_number)) {
			partNumberError = 'Part number is required.';
			ok = false;
		}
		if (isBlank(description)) {
			descriptionError = 'Description is required.';
			ok = false;
		}
		if (isBlank(uom)) {
			uomError = 'UoM is required.';
			ok = false;
		}
		if (isBlank(country_of_origin)) {
			countryError = 'Country of origin is required.';
			ok = false;
		}
		return ok;
	}

	async function handleSubmit(): Promise<void> {
		if (!validate()) return;
		const qtyParsed = Number.parseInt(quantity, 10);
		const fields: AddLineFields = {
			part_number: part_number.trim(),
			description: description.trim(),
			quantity: Number.isFinite(qtyParsed) ? qtyParsed : 0,
			uom: uom.trim(),
			unit_price: unit_price.trim(),
			hs_code: hs_code.trim(),
			country_of_origin: country_of_origin.trim()
		};
		submitting = true;
		try {
			await on_submit(fields);
		} finally {
			submitting = false;
		}
	}
</script>

<div
	class="ui-po-add-line-dialog"
	role="dialog"
	aria-modal="true"
	aria-labelledby={titleId}
	data-testid={testid ?? 'po-add-line-dialog'}
>
	<div class="ui-po-add-line-dialog__card">
		<header class="ui-po-add-line-dialog__header">
			<h2 id={titleId} class="ui-po-add-line-dialog__title">Add line</h2>
		</header>

		<div class="ui-po-add-line-dialog__body">
			{#if error}
				<p
					class="ui-po-add-line-dialog__error"
					role="alert"
					data-testid="po-add-line-error"
				>
					{error}
				</p>
			{/if}

			<FormField
				label="Part number"
				required
				error={partNumberError}
				data-testid="po-add-line-part-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={part_number}
						{invalid}
						ariaLabel="Part number"
						data-testid="po-add-line-part"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Description"
				required
				error={descriptionError}
				data-testid="po-add-line-description-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={description}
						{invalid}
						ariaLabel="Description"
						data-testid="po-add-line-description"
					/>
				{/snippet}
			</FormField>

			<FormField label="Quantity" data-testid="po-add-line-quantity-field">
				{#snippet children()}
					<Input
						type="number"
						bind:value={quantity}
						ariaLabel="Quantity"
						data-testid="po-add-line-quantity"
					/>
				{/snippet}
			</FormField>

			<FormField label="Unit price" data-testid="po-add-line-unit-price-field">
				{#snippet children()}
					<Input
						bind:value={unit_price}
						ariaLabel="Unit price"
						data-testid="po-add-line-unit-price"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="UoM"
				required
				error={uomError}
				hint="Free-form unit of measure code (e.g. EA, KG)."
				data-testid="po-add-line-uom-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={uom}
						{invalid}
						ariaLabel="Unit of measure"
						data-testid="po-add-line-uom"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="HS code"
				hint="Digits and dots, 4+ characters."
				data-testid="po-add-line-hs-code-field"
			>
				{#snippet children()}
					<Input
						bind:value={hs_code}
						ariaLabel="HS code"
						data-testid="po-add-line-hs-code"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Country of origin"
				required
				error={countryError}
				data-testid="po-add-line-country-field"
			>
				{#snippet children({ invalid })}
					<Select
						bind:value={country_of_origin}
						options={COUNTRY_OPTIONS}
						{invalid}
						ariaLabel="Country of origin"
						data-testid="po-add-line-country"
					/>
				{/snippet}
			</FormField>
		</div>

		<footer class="ui-po-add-line-dialog__footer">
			<Button
				variant="secondary"
				onclick={on_close}
				data-testid="po-add-line-cancel"
			>
				Cancel
			</Button>
			<Button
				onclick={handleSubmit}
				disabled={submitting}
				data-testid="po-add-line-submit"
			>
				{submitting ? 'Adding…' : 'Add'}
			</Button>
		</footer>
	</div>
</div>

<style>
	.ui-po-add-line-dialog {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: var(--space-4);
	}
	.ui-po-add-line-dialog__card {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		max-width: 32rem;
		width: 100%;
		max-height: 90vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
	}
	.ui-po-add-line-dialog__header {
		padding: var(--space-6) var(--space-6) var(--space-2);
	}
	.ui-po-add-line-dialog__title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.ui-po-add-line-dialog__body {
		padding: var(--space-2) var(--space-6) var(--space-4);
	}
	.ui-po-add-line-dialog__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0 0 var(--space-3);
	}
	.ui-po-add-line-dialog__footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		border-top: 1px solid var(--gray-100);
	}
</style>
