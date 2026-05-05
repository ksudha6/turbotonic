<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Select from '$lib/ui/Select.svelte';
	import type { Brand, BrandCreate, BrandUpdate, ReferenceDataItem } from '$lib/types';

	type Mode = 'create' | 'edit';

	let {
		mode,
		initial,
		countries,
		submitting = false,
		error = null,
		onSubmit,
		onCancel
	}: {
		mode: Mode;
		initial?: Brand;
		countries: ReferenceDataItem[];
		submitting?: boolean;
		error?: string | null;
		onSubmit: (data: BrandCreate | BrandUpdate) => void;
		onCancel: () => void;
	} = $props();

	let name: string = $state(initial?.name ?? '');
	let legal_name: string = $state(initial?.legal_name ?? '');
	let address: string = $state(initial?.address ?? '');
	let country: string = $state(initial?.country ?? '');
	let tax_id: string = $state(initial?.tax_id ?? '');

	let nameError: string = $state('');
	let legalNameError: string = $state('');
	let addressError: string = $state('');
	let countryError: string = $state('');

	const COUNTRY_OPTIONS = $derived([
		{ value: '', label: 'Select country' },
		...countries.map((c) => ({ value: c.code, label: c.label }))
	]);

	function isBlank(v: string): boolean {
		return v.trim().length === 0;
	}

	function validate(): boolean {
		nameError = '';
		legalNameError = '';
		addressError = '';
		countryError = '';
		let ok = true;
		if (mode === 'create' && isBlank(name)) {
			nameError = 'Name is required.';
			ok = false;
		}
		if (isBlank(legal_name)) {
			legalNameError = 'Legal name is required.';
			ok = false;
		}
		if (isBlank(address)) {
			addressError = 'Address is required.';
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
		if (mode === 'create') {
			onSubmit({
				name: name.trim(),
				legal_name: legal_name.trim(),
				address: address.trim(),
				country,
				tax_id: tax_id.trim() || undefined
			} satisfies BrandCreate);
		} else {
			onSubmit({
				legal_name: legal_name.trim(),
				address: address.trim(),
				country,
				tax_id: tax_id.trim() || undefined
			} satisfies BrandUpdate);
		}
	}
</script>

<form class="brand-form" onsubmit={handleSubmit} data-testid="brand-form" novalidate>
	<PanelCard title="Brand Details">
		<div class="brand-form__grid">
			<FormField
				label="Name"
				required={mode === 'create'}
				error={nameError}
				data-testid="brand-form-name-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={name}
						{invalid}
						disabled={mode === 'edit'}
						ariaLabel="Brand name"
						data-testid="brand-form-name"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Legal Name"
				required
				error={legalNameError}
				data-testid="brand-form-legal-name-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={legal_name}
						{invalid}
						ariaLabel="Legal name"
						data-testid="brand-form-legal-name"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Country"
				required
				error={countryError}
				data-testid="brand-form-country-field"
			>
				{#snippet children({ invalid })}
					<Select
						bind:value={country}
						options={COUNTRY_OPTIONS}
						{invalid}
						ariaLabel="Country"
						data-testid="brand-form-country"
					/>
				{/snippet}
			</FormField>

			<FormField label="Tax ID" data-testid="brand-form-tax-id-field">
				{#snippet children({ invalid })}
					<Input
						bind:value={tax_id}
						{invalid}
						ariaLabel="Tax ID"
						data-testid="brand-form-tax-id"
					/>
				{/snippet}
			</FormField>

			<div class="brand-form__span-2">
				<label class="brand-form__label" for="brand-form-address">Address</label>
				{#if addressError}
					<p class="brand-form__field-error" role="alert">{addressError}</p>
				{/if}
				<textarea
					id="brand-form-address"
					class="brand-form__textarea"
					class:brand-form__textarea--invalid={!!addressError}
					bind:value={address}
					data-testid="brand-form-address"
				></textarea>
			</div>
		</div>
	</PanelCard>

	{#if error}
		<p class="brand-form__error" role="alert" data-testid="brand-form-error">{error}</p>
	{/if}

	<footer class="brand-form__footer">
		<Button variant="secondary" onclick={onCancel} data-testid="brand-form-cancel">
			Cancel
		</Button>
		<Button
			type="submit"
			variant="primary"
			disabled={submitting}
			data-testid="brand-form-submit"
		>
			{submitting ? 'Saving…' : mode === 'create' ? 'Create Brand' : 'Save Changes'}
		</Button>
	</footer>
</form>

<style>
	.brand-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.brand-form__grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-4);
	}
	@media (min-width: 768px) {
		.brand-form__grid {
			grid-template-columns: 1fr 1fr;
		}
		.brand-form__span-2 { grid-column: span 2; }
	}
	.brand-form__label {
		display: block;
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
		margin-bottom: var(--space-1);
	}
	.brand-form__field-error {
		font-size: var(--font-size-xs);
		color: var(--red-700);
		margin: 0 0 var(--space-1);
	}
	.brand-form__textarea {
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
		box-sizing: border-box;
	}
	.brand-form__textarea--invalid {
		border-color: var(--red-500);
	}
	.brand-form__textarea:focus {
		outline: 2px solid var(--brand-accent);
		outline-offset: -2px;
		border-color: var(--brand-accent);
	}
	.brand-form__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}
	.brand-form__footer {
		position: sticky;
		bottom: 0;
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-3) 0 calc(var(--space-3) + env(safe-area-inset-bottom, 0px));
		background: linear-gradient(to top, var(--surface-page) 60%, transparent);
	}
	@media (min-width: 768px) {
		.brand-form__footer {
			position: static;
			padding: var(--space-3) 0 0;
			background: transparent;
		}
	}
</style>
