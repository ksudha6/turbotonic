<script lang="ts">
	import type { LineItem } from '$lib/types';
	import type { ModifyLineFields } from '$lib/api';

	let {
		line,
		onSubmit,
		onCancel
	}: {
		line: LineItem;
		onSubmit: (fields: ModifyLineFields) => void;
		onCancel: () => void;
	} = $props();

	// Editable fields mirror the backend EDITABLE_LINE_FIELDS tuple. part_number
	// is rendered read-only; attempting to edit it would be rejected server-side.
	let quantity: number = $state(line.quantity);
	let unit_price: string = $state(line.unit_price);
	let uom: string = $state(line.uom);
	let description: string = $state(line.description);
	let hs_code: string = $state(line.hs_code);
	let country_of_origin: string = $state(line.country_of_origin);
	// required_delivery_date is a per-line override. Empty string means "inherit".
	let required_delivery_date: string = $state(line.required_delivery_date ? line.required_delivery_date.slice(0, 10) : '');

	let quantityError: string = $state('');
	let unitPriceError: string = $state('');
	let hsCodeError: string = $state('');

	// Backend HS-code pattern: digits and dots, at least 4 characters.
	const HS_CODE_PATTERN = /^[0-9.]{4,}$/;

	function validate(): boolean {
		quantityError = '';
		unitPriceError = '';
		hsCodeError = '';
		let ok = true;
		if (!Number.isInteger(quantity) || quantity < 0) {
			quantityError = 'Quantity must be a non-negative integer.';
			ok = false;
		}
		// Unit price must be > 0 unless quantity is 0 (which routes to REMOVED).
		const price = parseFloat(unit_price);
		if (quantity > 0) {
			if (Number.isNaN(price) || price <= 0) {
				unitPriceError = 'Unit price must be greater than 0.';
				ok = false;
			}
		}
		if (!HS_CODE_PATTERN.test(hs_code)) {
			hsCodeError = 'HS code must be digits and dots, 4+ characters.';
			ok = false;
		}
		return ok;
	}

	function buildChangedFields(): ModifyLineFields {
		const out: ModifyLineFields = {};
		if (quantity !== line.quantity) out.quantity = quantity;
		if (unit_price.trim() !== line.unit_price) out.unit_price = unit_price.trim();
		if (uom !== line.uom) out.uom = uom;
		if (description !== line.description) out.description = description;
		if (hs_code !== line.hs_code) out.hs_code = hs_code;
		if (country_of_origin !== line.country_of_origin) out.country_of_origin = country_of_origin;
		// Compare against the existing per-line override. Empty string in the input
		// means "inherit from PO" (null on the wire).
		const currentOverride = line.required_delivery_date ? line.required_delivery_date.slice(0, 10) : '';
		if (required_delivery_date !== currentOverride) {
			out.required_delivery_date = required_delivery_date || null;
		}
		return out;
	}

	function handleSubmit() {
		if (!validate()) return;
		const changed = buildChangedFields();
		if (Object.keys(changed).length === 0) {
			// Nothing changed; cancel silently rather than firing an empty modify.
			onCancel();
			return;
		}
		onSubmit(changed);
	}
</script>

<div class="overlay" data-testid="modify-line-modal">
	<div class="dialog">
		<h2 class="dialog-title">Modify line {line.part_number}</h2>

		<div class="form-group">
			<label for="mod-part">Part Number</label>
			<input
				id="mod-part"
				type="text"
				value={line.part_number}
				readonly
				title="Part number is immutable"
				data-testid="modify-part-number"
			/>
		</div>

		<div class="form-group">
			<label for="mod-qty">Quantity</label>
			<input
				id="mod-qty"
				type="number"
				min="0"
				step="1"
				bind:value={quantity}
				data-testid="modify-quantity"
			/>
			{#if quantity === 0}
				<p class="qty-zero-hint" data-testid="qty-zero-hint">This will remove the line from the PO.</p>
			{/if}
			{#if quantityError}
				<p class="error-message">{quantityError}</p>
			{/if}
		</div>

		<div class="form-group">
			<label for="mod-price">Unit Price</label>
			<input
				id="mod-price"
				type="text"
				bind:value={unit_price}
				data-testid="modify-unit-price"
			/>
			{#if unitPriceError}
				<p class="error-message">{unitPriceError}</p>
			{/if}
		</div>

		<div class="form-group">
			<label for="mod-uom">UoM</label>
			<input id="mod-uom" type="text" bind:value={uom} data-testid="modify-uom" />
		</div>

		<div class="form-group">
			<label for="mod-desc">Description</label>
			<input id="mod-desc" type="text" bind:value={description} data-testid="modify-description" />
		</div>

		<div class="form-group">
			<label for="mod-hs">HS Code</label>
			<input id="mod-hs" type="text" bind:value={hs_code} data-testid="modify-hs-code" />
			{#if hsCodeError}
				<p class="error-message">{hsCodeError}</p>
			{/if}
		</div>

		<div class="form-group">
			<label for="mod-coo">Country of Origin</label>
			<input id="mod-coo" type="text" bind:value={country_of_origin} data-testid="modify-country" />
		</div>

		<div class="form-group">
			<label for="mod-rdd">Required Delivery Date (override)</label>
			<input
				id="mod-rdd"
				type="date"
				bind:value={required_delivery_date}
				data-testid="modify-rdd"
			/>
		</div>

		<div class="dialog-actions">
			<button class="btn btn-secondary" onclick={onCancel}>Cancel</button>
			<button class="btn btn-primary" onclick={handleSubmit} data-testid="modify-submit">
				Save
			</button>
		</div>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.dialog {
		background-color: white;
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		padding: var(--space-6);
		max-width: 520px;
		width: 100%;
		max-height: 90vh;
		overflow-y: auto;
	}

	.dialog-title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin-bottom: var(--space-4);
	}

	.form-group {
		margin-bottom: var(--space-3);
	}

	.form-group label {
		display: block;
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		margin-bottom: var(--space-1);
	}

	.form-group input {
		width: 100%;
		padding: var(--space-2);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius);
	}

	.form-group input[readonly] {
		background-color: var(--gray-100);
		color: var(--gray-700);
	}

	.qty-zero-hint {
		font-size: var(--font-size-sm);
		color: var(--amber-800, #92400e);
		margin-top: var(--space-1);
	}

	.error-message {
		color: var(--red-600);
		font-size: var(--font-size-sm);
		margin-top: var(--space-1);
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		margin-top: var(--space-4);
	}
</style>
