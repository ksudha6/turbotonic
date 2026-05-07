<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Select from '$lib/ui/Select.svelte';
	import type { ReferenceDataItem, VendorType } from '$lib/types';

	export type VendorFormFields = {
		name: string;
		country: string;
		vendor_type: VendorType;
		address: string;
		account_details: string;
		tax_id: string;
	};

	let {
		countries,
		error = '',
		submitting = false,
		on_submit,
		on_cancel
	}: {
		countries: ReferenceDataItem[];
		error?: string;
		submitting?: boolean;
		on_submit: (fields: VendorFormFields) => void;
		on_cancel: () => void;
	} = $props();

	let name: string = $state('');
	let country: string = $state('');
	let vendor_type: VendorType = $state('PROCUREMENT');
	let address: string = $state('');
	let account_details: string = $state('');
	let tax_id: string = $state('');

	let nameError: string = $state('');
	let countryError: string = $state('');

	const COUNTRY_OPTIONS = $derived([
		{ value: '', label: 'Select country' },
		...countries.map((c) => ({ value: c.code, label: c.label }))
	]);

	const VENDOR_TYPE_OPTIONS: ReadonlyArray<{ value: VendorType; label: string }> = [
		{ value: 'PROCUREMENT', label: 'Procurement' },
		{ value: 'OPEX', label: 'OpEx' },
		{ value: 'FREIGHT', label: 'Freight' },
		{ value: 'MISCELLANEOUS', label: 'Miscellaneous' }
	];

	function isBlank(v: string): boolean {
		return v.trim().length === 0;
	}

	function validate(): boolean {
		nameError = '';
		countryError = '';
		let ok = true;
		if (isBlank(name)) {
			nameError = 'Name is required.';
			ok = false;
		}
		if (isBlank(country)) {
			countryError = 'Country is required.';
			ok = false;
		}
		return ok;
	}

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!validate()) return;
		on_submit({
			name: name.trim(),
			country,
			vendor_type,
			address,
			account_details,
			tax_id
		});
	}
</script>

<form
	class="vendor-form"
	onsubmit={handleSubmit}
	data-testid="vendor-form"
	novalidate
>
	<PanelCard title="Vendor Details">
		<div class="vendor-form__grid">
			<FormField
				label="Name"
				required
				error={nameError}
				data-testid="vendor-form-name-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={name}
						{invalid}
						ariaLabel="Vendor name"
						data-testid="vendor-form-name"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Country"
				required
				error={countryError}
				data-testid="vendor-form-country-field"
			>
				{#snippet children({ invalid })}
					<Select
						bind:value={country}
						options={COUNTRY_OPTIONS}
						{invalid}
						ariaLabel="Country"
						data-testid="vendor-form-country"
					/>
				{/snippet}
			</FormField>

			<FormField label="Tax ID" data-testid="vendor-form-tax-id-field">
				{#snippet children()}
					<Input
						bind:value={tax_id}
						placeholder="e.g. EIN-12-3456789"
						ariaLabel="Tax ID"
						data-testid="vendor-form-tax-id"
					/>
				{/snippet}
			</FormField>

			<FormField label="Vendor Type" required data-testid="vendor-form-vendor-type-field">
				{#snippet children()}
					<Select
						bind:value={vendor_type}
						options={[...VENDOR_TYPE_OPTIONS] as Array<{ value: string; label: string }>}
						ariaLabel="Vendor type"
						data-testid="vendor-form-vendor-type"
					/>
				{/snippet}
			</FormField>

			<div class="vendor-form__span-2">
				<label class="vendor-form__label" for="vendor-form-address">Address</label>
				<textarea
					id="vendor-form-address"
					class="vendor-form__textarea"
					bind:value={address}
					data-testid="vendor-form-address"
				></textarea>
			</div>

			<div class="vendor-form__span-2">
				<label class="vendor-form__label" for="vendor-form-account-details">Account Details</label>
				<textarea
					id="vendor-form-account-details"
					class="vendor-form__textarea"
					bind:value={account_details}
					data-testid="vendor-form-account-details"
				></textarea>
			</div>
		</div>
	</PanelCard>

	{#if error}
		<p class="vendor-form__error" role="alert" data-testid="vendor-form-error">{error}</p>
	{/if}

	<footer class="vendor-form__footer">
		<Button variant="secondary" onclick={on_cancel} data-testid="vendor-form-cancel">
			Cancel
		</Button>
		<Button
			type="submit"
			variant="primary"
			disabled={submitting}
			data-testid="vendor-form-submit"
		>
			{submitting ? 'Creating…' : 'Create Vendor'}
		</Button>
	</footer>
</form>

<style>
	.vendor-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.vendor-form__grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-4);
	}
	@media (min-width: 768px) {
		.vendor-form__grid {
			grid-template-columns: 1fr 1fr;
		}
		.vendor-form__span-2 { grid-column: span 2; }
	}
	.vendor-form__label {
		display: block;
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
		margin-bottom: var(--space-1);
	}
	.vendor-form__textarea {
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
	.vendor-form__textarea:focus {
		outline: 2px solid var(--brand-accent);
		outline-offset: -2px;
		border-color: var(--brand-accent);
	}
	.vendor-form__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}
	.vendor-form__footer {
		position: sticky;
		bottom: 0;
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-3) 0 calc(var(--space-3) + env(safe-area-inset-bottom, 0px));
		background: linear-gradient(to top, var(--surface-page) 60%, transparent);
	}
	@media (min-width: 768px) {
		.vendor-form__footer {
			position: static;
			padding: var(--space-3) 0 0;
			background: transparent;
		}
	}
</style>
