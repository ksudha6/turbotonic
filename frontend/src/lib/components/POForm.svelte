<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { LineItemInput, PurchaseOrderInput, ReferenceData } from '$lib/types';
	import type { VendorListItem } from '$lib/types';
	import { listVendors, fetchReferenceData } from '$lib/api';

	const DEFAULT_BUYER_NAME = 'TurboTonic Ltd';
	const DEFAULT_BUYER_COUNTRY = 'US';

	interface InitialData {
		po_type?: string;
		vendor_id?: string;
		buyer_name?: string;
		buyer_country?: string;
		ship_to_address?: string;
		payment_terms?: string;
		currency?: string;
		issued_date?: string;
		required_delivery_date?: string;
		terms_and_conditions?: string;
		incoterm?: string;
		port_of_loading?: string;
		port_of_discharge?: string;
		country_of_origin?: string;
		country_of_destination?: string;
		marketplace?: string | null;
		line_items?: LineItemInput[];
	}

	interface Props {
		initialData?: InitialData;
		onSubmit: (data: PurchaseOrderInput) => Promise<void>;
		submitLabel: string;
	}

	let { initialData = {}, onSubmit, submitLabel }: Props = $props();

	function emptyLineItem(): LineItemInput {
		return {
			part_number: '',
			description: '',
			quantity: 1,
			uom: '',
			unit_price: '0',
			hs_code: '',
			country_of_origin: '',
			product_id: null
		};
	}

	function extractDate(iso: string | undefined): string {
		if (!iso) return '';
		return iso.split('T')[0];
	}

	let vendors: VendorListItem[] = $state([]);
	let refData: ReferenceData | null = $state(null);
	let vendor_id: string = $state(initialData.vendor_id ?? '');
	let buyer_name: string = $state(initialData.buyer_name ?? DEFAULT_BUYER_NAME);
	let buyer_country: string = $state(initialData.buyer_country ?? DEFAULT_BUYER_COUNTRY);
	let currency: string = $state(initialData.currency ?? '');
	let issued_date: string = $state(extractDate(initialData.issued_date));
	let required_delivery_date: string = $state(extractDate(initialData.required_delivery_date));
	let ship_to_address: string = $state(initialData.ship_to_address ?? '');
	let payment_terms: string = $state(initialData.payment_terms ?? '');
	let incoterm: string = $state(initialData.incoterm ?? '');
	let port_of_loading: string = $state(initialData.port_of_loading ?? '');
	let port_of_discharge: string = $state(initialData.port_of_discharge ?? '');
	let country_of_origin: string = $state(initialData.country_of_origin ?? '');
	let country_of_destination: string = $state(initialData.country_of_destination ?? '');
	let terms_and_conditions: string = $state(initialData.terms_and_conditions ?? '');
	let marketplace: string = $state(initialData.marketplace ?? '');
	let lineItems: LineItemInput[] = $state(
		initialData.line_items && initialData.line_items.length > 0
			? initialData.line_items.map((item) => ({ ...item }))
			: [emptyLineItem()]
	);
	let submitting: boolean = $state(false);
	let error: string = $state('');

	const HS_CODE_PATTERN = /^[\d.]{4,}$/;

	function hsCodeError(code: string): string {
		if (!code || code.trim().length === 0) return '';
		return HS_CODE_PATTERN.test(code) ? '' : 'HS code must be at least 4 characters and contain only digits and dots';
	}

	let hsCodeErrors = $derived(lineItems.map((item) => hsCodeError(item.hs_code)));
	let hasHsCodeErrors = $derived(hsCodeErrors.some((e) => e !== ''));

	let po_type: string = $state(initialData.po_type ?? 'PROCUREMENT');

	let filteredVendors = $derived(vendors.filter(v => v.vendor_type === po_type));

	$effect(() => {
		if (vendor_id && !filteredVendors.some(v => v.id === vendor_id)) {
			vendor_id = '';
		}
	});

	onMount(async () => {
		[vendors, refData] = await Promise.all([listVendors({ status: 'ACTIVE' }), fetchReferenceData()]);
	});

	function addLineItem() {
		lineItems = [...lineItems, emptyLineItem()];
	}

	function removeLineItem(index: number) {
		lineItems = lineItems.filter((_, i) => i !== index);
	}

	function toISODateTime(dateStr: string): string {
		return dateStr ? `${dateStr}T00:00:00Z` : '';
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';

		if (lineItems.length === 0) {
			error = 'At least one line item is required.';
			return;
		}

		for (let i = 0; i < lineItems.length; i++) {
			const item = lineItems[i];
			if (!item.part_number.trim()) {
				error = `Line item ${i + 1}: Part Number is required.`;
				return;
			}
			if (item.quantity <= 0) {
				error = `Line item ${i + 1}: Quantity must be greater than 0.`;
				return;
			}
			if (parseFloat(item.unit_price) < 0) {
				error = `Line item ${i + 1}: Unit Price must be 0 or greater.`;
				return;
			}
		}

		const data: PurchaseOrderInput = {
			po_number: '',
			po_type: po_type as import('$lib/types').POType,
			total_value: '',
			vendor_id,
			buyer_name,
			buyer_country,
			currency,
			issued_date: toISODateTime(issued_date),
			required_delivery_date: toISODateTime(required_delivery_date),
			ship_to_address,
			payment_terms,
			incoterm,
			port_of_loading,
			port_of_discharge,
			country_of_origin,
			country_of_destination,
			terms_and_conditions,
			marketplace: marketplace || null,
			line_items: lineItems.map((item) => ({
				...item,
				unit_price: String(parseFloat(item.unit_price) || 0),
				product_id: item.product_id || null
			}))
		};

		submitting = true;
		try {
			await onSubmit(data);
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred.';
		} finally {
			submitting = false;
		}
	}
</script>

<form onsubmit={handleSubmit}>
	<!-- Header section -->
	<div class="section card">
		<h2>Purchase Order Details</h2>
		<div class="form-grid">
			<div class="form-group">
				<label for="po_type">PO Type *</label>
				<select id="po_type" class="select" required bind:value={po_type}>
					<option value="PROCUREMENT">Procurement</option>
					<option value="OPEX">OpEx</option>
				</select>
			</div>
			<div class="form-group">
				<label for="vendor_id">Vendor *</label>
				<select id="vendor_id" class="select" required bind:value={vendor_id}>
					<option value="">Select a vendor</option>
					{#each filteredVendors as v}
						<option value={v.id}>{v.name} ({v.country})</option>
					{/each}
				</select>
			</div>
			<div class="form-group">
				<label for="marketplace">Marketplace</label>
				<select id="marketplace" class="select" bind:value={marketplace}>
					<option value="">None</option>
					<option value="AMZ">AMZ</option>
					<option value="3PL_1">3PL_1</option>
					<option value="3PL_2">3PL_2</option>
					<option value="3PL_3">3PL_3</option>
				</select>
			</div>
			<div class="form-group">
				<label for="buyer_name">Buyer Name *</label>
				<input id="buyer_name" class="input" type="text" required bind:value={buyer_name} />
			</div>
			<div class="form-group">
				<label for="buyer_country">Buyer Country *</label>
				<select id="buyer_country" class="select" required bind:value={buyer_country}>
					<option value="">Select...</option>
					{#if refData}
						{#each refData.countries as item}
							<option value={item.code}>{item.code} — {item.label}</option>
						{/each}
					{/if}
				</select>
			</div>
			<div class="form-group">
				<label for="currency">Currency *</label>
				<select id="currency" class="select" required bind:value={currency}>
					<option value="">Select...</option>
					{#if refData}
						{#each refData.currencies as item}
							<option value={item.code}>{item.code} — {item.label}</option>
						{/each}
					{/if}
				</select>
			</div>
			<div class="form-group">
				<label for="issued_date">Issued Date *</label>
				<input id="issued_date" class="input" type="date" required bind:value={issued_date} />
			</div>
			<div class="form-group">
				<label for="required_delivery_date">Required Delivery Date *</label>
				<input
					id="required_delivery_date"
					class="input"
					type="date"
					required
					bind:value={required_delivery_date}
				/>
			</div>
			<div class="form-group span-2">
				<label for="ship_to_address">Ship-to Address</label>
				<textarea id="ship_to_address" class="textarea" bind:value={ship_to_address}></textarea>
			</div>
			<div class="form-group">
				<label for="payment_terms">Payment Terms</label>
				<select id="payment_terms" class="select" bind:value={payment_terms}>
					<option value="">Select...</option>
					{#if refData}
						{#each refData.payment_terms as item}
							<option value={item.code}>{item.code} — {item.label}</option>
						{/each}
					{/if}
				</select>
			</div>
		</div>
	</div>

	<!-- Trade Details section -->
	<div class="section card">
		<h2>Trade Details</h2>
		<div class="form-grid">
			<div class="form-group">
				<label for="incoterm">Incoterm</label>
				<select id="incoterm" class="select" bind:value={incoterm}>
					<option value="">Select...</option>
					{#if refData}
						{#each refData.incoterms as item}
							<option value={item.code}>{item.code} — {item.label}</option>
						{/each}
					{/if}
				</select>
			</div>
			<div class="form-group">
				<label for="port_of_loading">Port of Loading</label>
				<select id="port_of_loading" class="select" bind:value={port_of_loading}>
					<option value="">Select...</option>
					{#if refData}
						{#each refData.ports as item}
							<option value={item.code}>{item.code} — {item.label}</option>
						{/each}
					{/if}
				</select>
			</div>
			<div class="form-group">
				<label for="port_of_discharge">Port of Discharge</label>
				<select id="port_of_discharge" class="select" bind:value={port_of_discharge}>
					<option value="">Select...</option>
					{#if refData}
						{#each refData.ports as item}
							<option value={item.code}>{item.code} — {item.label}</option>
						{/each}
					{/if}
				</select>
			</div>
			<div class="form-group">
				<label for="country_of_origin">Country of Origin</label>
				<select id="country_of_origin" class="select" bind:value={country_of_origin}>
					<option value="">Select...</option>
					{#if refData}
						{#each refData.countries as item}
							<option value={item.code}>{item.code} — {item.label}</option>
						{/each}
					{/if}
				</select>
			</div>
			<div class="form-group">
				<label for="country_of_destination">Country of Destination</label>
				<select id="country_of_destination" class="select" bind:value={country_of_destination}>
					<option value="">Select...</option>
					{#if refData}
						{#each refData.countries as item}
							<option value={item.code}>{item.code} — {item.label}</option>
						{/each}
					{/if}
				</select>
			</div>
		</div>
	</div>

	<!-- Terms & Conditions section -->
	<div class="section card">
		<h2>Terms &amp; Conditions</h2>
		<div class="form-group">
			<textarea
				id="terms_and_conditions"
				class="textarea"
				rows="6"
				bind:value={terms_and_conditions}
			></textarea>
		</div>
	</div>

	<!-- Line Items section -->
	<div class="section card">
		<div class="line-items-header">
			<h2>Line Items</h2>
			<button type="button" class="btn btn-secondary" onclick={addLineItem}>Add Line Item</button>
		</div>

		<div class="line-items-table">
			<div class="line-item-header-row">
				<span>Part Number *</span>
				<span>Description</span>
				<span>Qty *</span>
				<span>UoM</span>
				<span>Unit Price *</span>
				<span>HS Code</span>
				<span>Country of Origin</span>
				<span>Product ID</span>
				<span></span>
			</div>
			{#each lineItems as item, i}
				<div class="line-item-row">
					<input
						class="input"
						type="text"
						required
						placeholder="Part No."
						bind:value={item.part_number}
					/>
					<input
						class="input"
						type="text"
						placeholder="Description"
						bind:value={item.description}
					/>
					<input
						class="input"
						type="number"
						required
						min="1"
						placeholder="Qty"
						bind:value={item.quantity}
					/>
					<input class="input" type="text" placeholder="UoM" bind:value={item.uom} />
					<input
						class="input"
						type="number"
						required
						min="0"
						step="0.01"
						placeholder="0.00"
						bind:value={item.unit_price}
					/>
					<div class="hs-code-cell">
						<input class="input" type="text" placeholder="HS Code" bind:value={item.hs_code} />
						{#if hsCodeErrors[i]}
							<p class="error-message">{hsCodeErrors[i]}</p>
						{/if}
					</div>
					<input
						class="input"
						type="text"
						placeholder="Origin"
						bind:value={item.country_of_origin}
					/>
					<input
						class="input"
						type="text"
						placeholder="Product ID"
						bind:value={item.product_id}
					/>
					<button
						type="button"
						class="btn btn-danger remove-btn"
						disabled={lineItems.length <= 1}
						onclick={() => removeLineItem(i)}
					>
						Remove
					</button>
				</div>
			{/each}
		</div>
	</div>

	<!-- Form Actions -->
	<div class="form-actions">
		{#if error}
			<p class="error-message">{error}</p>
		{/if}
		<div class="action-buttons">
			<a href="/po" class="btn btn-secondary">Cancel</a>
			<button type="submit" class="btn btn-primary" disabled={submitting || hasHsCodeErrors}>
				{submitting ? 'Saving...' : submitLabel}
			</button>
		</div>
	</div>
</form>

<style>
	.section {
		margin-bottom: var(--space-6);
	}

	.section h2 {
		margin-bottom: var(--space-4);
	}

	.form-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
	}

	.form-grid .span-2 {
		grid-column: span 2;
	}

	.line-items-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-4);
	}

	.line-items-header h2 {
		margin-bottom: 0;
	}

	.line-items-table {
		overflow-x: auto;
	}

	.line-item-header-row,
	.line-item-row {
		display: grid;
		grid-template-columns: 2fr 2fr 1fr 1fr 1.5fr 1.5fr 1.5fr 1.5fr auto;
		gap: var(--space-2);
		align-items: end;
	}

	.line-item-header-row {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-600);
		padding-bottom: var(--space-2);
		border-bottom: 1px solid var(--gray-200);
		margin-bottom: var(--space-2);
	}

	.line-item-row {
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}

	.line-item-row:last-child {
		border-bottom: none;
	}

	.remove-btn {
		font-size: var(--font-size-sm);
		padding: var(--space-2) var(--space-3);
	}

	.hs-code-cell {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.hs-code-cell .error-message {
		margin-bottom: 0;
	}

	.form-actions {
		padding-top: var(--space-4);
		border-top: 1px solid var(--gray-200);
		margin-bottom: var(--space-6);
	}

	.error-message {
		color: var(--red-600);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-3);
	}

	.action-buttons {
		display: flex;
		gap: var(--space-3);
	}
</style>
