<script lang="ts">
	import type { LineItem } from '$lib/types';
	import type { ModifyLineFields } from '$lib/api';
	import Button from '$lib/ui/Button.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';

	let {
		line,
		onSubmit,
		onCancel,
		'data-testid': testid
	}: {
		line: LineItem;
		onSubmit: (fields: ModifyLineFields) => void;
		onCancel: () => void;
		'data-testid'?: string;
	} = $props();

	// Editable fields mirror the backend EDITABLE_LINE_FIELDS tuple. part_number
	// is rendered read-only; the server rejects part_number changes.
	let quantity: string = $state(String(line.quantity));
	let unit_price: string = $state(line.unit_price);
	let uom: string = $state(line.uom);
	let description: string = $state(line.description);
	let hs_code: string = $state(line.hs_code);
	let country_of_origin: string = $state(line.country_of_origin);
	let required_delivery_date: string = $state(
		line.required_delivery_date ? line.required_delivery_date.slice(0, 10) : ''
	);

	let quantityError: string = $state('');
	let unitPriceError: string = $state('');
	let uomError: string = $state('');
	let descriptionError: string = $state('');
	let hsCodeError: string = $state('');
	let countryError: string = $state('');

	const HS_CODE_PATTERN = /^[0-9.]{4,}$/;

	const titleId = crypto.randomUUID();

	function isBlank(v: string): boolean {
		return v.trim().length === 0;
	}

	function validate(): boolean {
		quantityError = '';
		unitPriceError = '';
		uomError = '';
		descriptionError = '';
		hsCodeError = '';
		countryError = '';
		let ok = true;
		const qtyParsed = Number.parseInt(quantity, 10);
		if (!Number.isInteger(qtyParsed) || qtyParsed < 0) {
			quantityError = 'Quantity must be a non-negative integer.';
			ok = false;
		}
		if (qtyParsed > 0) {
			const price = parseFloat(unit_price);
			if (Number.isNaN(price) || price <= 0) {
				unitPriceError = 'Unit price must be greater than 0.';
				ok = false;
			}
		}
		if (isBlank(uom)) {
			uomError = 'UoM is required.';
			ok = false;
		}
		if (isBlank(description)) {
			descriptionError = 'Description is required.';
			ok = false;
		}
		if (!HS_CODE_PATTERN.test(hs_code)) {
			hsCodeError = 'HS code must be digits and dots, 4+ characters.';
			ok = false;
		}
		if (isBlank(country_of_origin)) {
			countryError = 'Country of origin is required.';
			ok = false;
		}
		return ok;
	}

	function buildChangedFields(): ModifyLineFields {
		const out: ModifyLineFields = {};
		const qtyParsed = Number.parseInt(quantity, 10);
		if (qtyParsed !== line.quantity) out.quantity = qtyParsed;
		if (unit_price.trim() !== line.unit_price) out.unit_price = unit_price.trim();
		if (uom.trim() !== line.uom) out.uom = uom.trim();
		if (description.trim() !== line.description) out.description = description.trim();
		if (hs_code !== line.hs_code) out.hs_code = hs_code;
		if (country_of_origin.trim() !== line.country_of_origin)
			out.country_of_origin = country_of_origin.trim();
		const currentOverride = line.required_delivery_date
			? line.required_delivery_date.slice(0, 10)
			: '';
		if (required_delivery_date !== currentOverride) {
			out.required_delivery_date = required_delivery_date || null;
		}
		return out;
	}

	function handleSubmit(): void {
		if (!validate()) return;
		const changed = buildChangedFields();
		if (Object.keys(changed).length === 0) {
			onCancel();
			return;
		}
		onSubmit(changed);
	}

	const willRemove = $derived(Number.parseInt(quantity, 10) === 0);
</script>

<div
	class="po-line-modal"
	role="dialog"
	aria-modal="true"
	aria-labelledby={titleId}
	data-testid={testid ?? `po-line-modify-modal-${line.part_number}`}
>
	<div class="po-line-modal__card">
		<header class="po-line-modal__header">
			<h2 id={titleId} class="po-line-modal__title">Modify line {line.part_number}</h2>
			<p class="po-line-modal__subtitle">{line.description}</p>
		</header>

		<div class="po-line-modal__body">
			<FormField label="Part number" data-testid="po-line-modify-part">
				{#snippet children()}
					<Input value={line.part_number} disabled ariaLabel="Part number" />
				{/snippet}
			</FormField>

			<FormField
				label="Quantity"
				required
				error={quantityError}
				hint={willRemove ? 'Quantity 0 will remove the line from the PO.' : undefined}
				data-testid="po-line-modify-quantity-field"
			>
				{#snippet children({ invalid })}
					<Input
						type="number"
						bind:value={quantity}
						{invalid}
						ariaLabel="Quantity"
						data-testid="po-line-modify-quantity"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Unit price"
				required
				error={unitPriceError}
				data-testid="po-line-modify-unit-price-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={unit_price}
						{invalid}
						ariaLabel="Unit price"
						data-testid="po-line-modify-unit-price"
					/>
				{/snippet}
			</FormField>

			<FormField label="UoM" required error={uomError} data-testid="po-line-modify-uom-field">
				{#snippet children({ invalid })}
					<Input
						bind:value={uom}
						{invalid}
						ariaLabel="Unit of measure"
						data-testid="po-line-modify-uom"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Description"
				required
				error={descriptionError}
				data-testid="po-line-modify-description-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={description}
						{invalid}
						ariaLabel="Description"
						data-testid="po-line-modify-description"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="HS code"
				required
				error={hsCodeError}
				data-testid="po-line-modify-hs-code-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={hs_code}
						{invalid}
						ariaLabel="HS code"
						data-testid="po-line-modify-hs-code"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Country of origin"
				required
				error={countryError}
				data-testid="po-line-modify-country-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={country_of_origin}
						{invalid}
						ariaLabel="Country of origin"
						data-testid="po-line-modify-country"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Required delivery date (override)"
				hint="Empty inherits PO delivery date."
				data-testid="po-line-modify-rdd-field"
			>
				{#snippet children()}
					<Input
						type="date"
						bind:value={required_delivery_date}
						ariaLabel="Required delivery date override"
						data-testid="po-line-modify-rdd"
					/>
				{/snippet}
			</FormField>
		</div>

		<footer class="po-line-modal__footer">
			<Button variant="secondary" onclick={onCancel} data-testid="po-line-modify-cancel">
				Cancel
			</Button>
			<Button onclick={handleSubmit} data-testid="po-line-modify-submit">
				{willRemove ? 'Remove line' : 'Save'}
			</Button>
		</footer>
	</div>
</div>

<style>
	.po-line-modal {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: var(--space-4);
	}
	.po-line-modal__card {
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
	.po-line-modal__header {
		padding: var(--space-6) var(--space-6) var(--space-2);
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.po-line-modal__title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.po-line-modal__subtitle {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
	.po-line-modal__body {
		padding: var(--space-2) var(--space-6) var(--space-4);
	}
	.po-line-modal__footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		border-top: 1px solid var(--gray-100);
	}
</style>
