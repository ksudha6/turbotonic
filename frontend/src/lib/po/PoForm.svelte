<script lang="ts">
	import { onMount } from 'svelte';
	import type { LineItemInput, PurchaseOrderInput, ReferenceData, VendorListItem } from '$lib/types';
	import { listVendors, fetchReferenceData } from '$lib/api';
	import { untrack } from 'svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Select from '$lib/ui/Select.svelte';
	import DateInput from '$lib/ui/DateInput.svelte';
	import Button from '$lib/ui/Button.svelte';

	const DEFAULT_BUYER_NAME = 'TurboTonic Ltd';
	const DEFAULT_BUYER_COUNTRY = 'US';

	const MARKETPLACE_OPTIONS = [
		{ value: '', label: 'None' },
		{ value: 'AMZ', label: 'AMZ' },
		{ value: '3PL_1', label: '3PL_1' },
		{ value: '3PL_2', label: '3PL_2' },
		{ value: '3PL_3', label: '3PL_3' }
	] as const;

	const PO_TYPE_OPTIONS = [
		{ value: 'PROCUREMENT', label: 'Procurement' },
		{ value: 'OPEX', label: 'OpEx' }
	] as const;

	const HS_CODE_PATTERN = /^[\d.]{4,}$/;

	type Mode = 'create' | 'edit-draft' | 'edit-revise';

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

	let {
		mode = 'create',
		initialData = {},
		onSubmit,
		submitLabel,
		cancelHref
	}: {
		mode?: Mode;
		initialData?: InitialData;
		onSubmit: (data: PurchaseOrderInput) => Promise<void>;
		submitLabel: string;
		cancelHref: string;
	} = $props();

	// Internal form state binds string-typed numeric fields so the Input
	// primitive (which emits strings) can two-way bind. Converted back to
	// LineItemInput shape on submit.
	interface LineFormState {
		part_number: string;
		description: string;
		quantity: string;
		uom: string;
		unit_price: string;
		hs_code: string;
		country_of_origin: string;
		product_id: string;
	}

	function emptyLineItem(): LineFormState {
		return {
			part_number: '',
			description: '',
			quantity: '1',
			uom: '',
			unit_price: '0',
			hs_code: '',
			country_of_origin: '',
			product_id: ''
		};
	}

	function lineToFormState(line: LineItemInput): LineFormState {
		return {
			part_number: line.part_number,
			description: line.description,
			quantity: String(line.quantity),
			uom: line.uom,
			unit_price: line.unit_price,
			hs_code: line.hs_code,
			country_of_origin: line.country_of_origin,
			product_id: line.product_id ?? ''
		};
	}

	function extractDate(iso: string | undefined): string {
		if (!iso) return '';
		return iso.split('T')[0];
	}

	let vendors = $state<VendorListItem[]>([]);
	let refData = $state<ReferenceData | null>(null);

	let po_type: string = $state(initialData.po_type ?? 'PROCUREMENT');
	let vendor_id: string = $state(initialData.vendor_id ?? '');
	let vendorClearedHint: boolean = $state(false);
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
	let lineItems = $state<LineFormState[]>(
		initialData.line_items && initialData.line_items.length > 0
			? initialData.line_items.map(lineToFormState)
			: [emptyLineItem()]
	);
	let submitting: boolean = $state(false);
	let error: string = $state('');
	let showDiscardModal: boolean = $state(false);

	const initialSnapshot = untrack(() =>
		JSON.stringify({
			po_type,
			vendor_id,
			buyer_name,
			buyer_country,
			currency,
			issued_date,
			required_delivery_date,
			ship_to_address,
			payment_terms,
			incoterm,
			port_of_loading,
			port_of_discharge,
			country_of_origin,
			country_of_destination,
			terms_and_conditions,
			marketplace,
			lineItems
		})
	);

	const currentSnapshot = $derived(
		JSON.stringify({
			po_type,
			vendor_id,
			buyer_name,
			buyer_country,
			currency,
			issued_date,
			required_delivery_date,
			ship_to_address,
			payment_terms,
			incoterm,
			port_of_loading,
			port_of_discharge,
			country_of_origin,
			country_of_destination,
			terms_and_conditions,
			marketplace,
			lineItems
		})
	);

	const dirty = $derived(currentSnapshot !== initialSnapshot);

	function hsCodeError(code: string): string {
		if (!code || code.trim().length === 0) return '';
		return HS_CODE_PATTERN.test(code) ? '' : 'HS code must be at least 4 characters and contain only digits and dots';
	}

	const hsCodeErrors = $derived(lineItems.map((item) => hsCodeError(item.hs_code)));
	const hasHsCodeErrors = $derived(hsCodeErrors.some((e) => e !== ''));

	const filteredVendors = $derived(vendors.filter((v) => v.vendor_type === po_type));
	const vendorOptions = $derived([
		{ value: '', label: 'Select a vendor' },
		...filteredVendors.map((v) => ({ value: v.id, label: `${v.name} (${v.country})` }))
	]);

	$effect(() => {
		if (vendor_id && filteredVendors.length > 0 && !filteredVendors.some((v) => v.id === vendor_id)) {
			vendor_id = '';
			vendorClearedHint = true;
		}
	});

	const countryOptions = $derived([
		{ value: '', label: 'Select...' },
		...(refData?.countries ?? []).map((c) => ({ value: c.code, label: `${c.code} — ${c.label}` }))
	]);
	const currencyOptions = $derived([
		{ value: '', label: 'Select...' },
		...(refData?.currencies ?? []).map((c) => ({ value: c.code, label: `${c.code} — ${c.label}` }))
	]);
	const incotermOptions = $derived([
		{ value: '', label: 'Select...' },
		...(refData?.incoterms ?? []).map((c) => ({ value: c.code, label: `${c.code} — ${c.label}` }))
	]);
	const portOptions = $derived([
		{ value: '', label: 'Select...' },
		...(refData?.ports ?? []).map((c) => ({ value: c.code, label: `${c.code} — ${c.label}` }))
	]);
	const paymentTermOptions = $derived([
		{ value: '', label: 'Select...' },
		...(refData?.payment_terms ?? []).map((c) => ({
			value: c.code,
			label: c.has_advance
				? `${c.code} — ${c.label} — advance required`
				: `${c.code} — ${c.label}`
		}))
	]);

	const showMarketplace = $derived(po_type === 'PROCUREMENT');
	const poTypeDisabled = $derived(mode !== 'create');

	const vendorHint = $derived.by(() => {
		if (vendorClearedHint) {
			return 'Vendor cleared because it does not match the selected PO type.';
		}
		return undefined;
	});

	onMount(async () => {
		[vendors, refData] = await Promise.all([
			listVendors({ status: 'ACTIVE' }),
			fetchReferenceData()
		]);
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
			const qty = Number.parseInt(item.quantity, 10);
			if (!Number.isFinite(qty) || qty <= 0) {
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
			marketplace: showMarketplace ? marketplace || null : null,
			line_items: lineItems.map((item) => ({
				part_number: item.part_number,
				description: item.description,
				quantity: Number.parseInt(item.quantity, 10) || 0,
				uom: item.uom,
				unit_price: String(parseFloat(item.unit_price) || 0),
				hs_code: item.hs_code,
				country_of_origin: item.country_of_origin,
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

	function handleCancel() {
		if (dirty) {
			showDiscardModal = true;
			return;
		}
		window.location.href = cancelHref;
	}

	function confirmDiscard() {
		showDiscardModal = false;
		window.location.href = cancelHref;
	}

	function keepEditing() {
		showDiscardModal = false;
	}
</script>

<form
	class="po-form"
	onsubmit={handleSubmit}
	novalidate
	data-testid="po-form"
>
	<div class="po-form-section" data-testid="po-form-section-details">
		<PanelCard title="Purchase Order Details">
			<div class="form-grid">
				<FormField label="PO Type" required>
					{#snippet children({ invalid })}
						<Select
							bind:value={po_type}
							options={[...PO_TYPE_OPTIONS]}
							disabled={poTypeDisabled}
							{invalid}
							ariaLabel="PO Type"
							data-testid="po-form-po-type"
						/>
					{/snippet}
				</FormField>

				<FormField label="Vendor" required hint={vendorHint}>
					{#snippet children({ invalid })}
						<Select
							bind:value={vendor_id}
							options={vendorOptions}
							disabled={!po_type}
							{invalid}
							ariaLabel="Vendor"
							data-testid="po-form-vendor"
						/>
					{/snippet}
				</FormField>

				{#if showMarketplace}
					<FormField label="Marketplace">
						{#snippet children()}
							<Select
								bind:value={marketplace}
								options={[...MARKETPLACE_OPTIONS]}
								ariaLabel="Marketplace"
								data-testid="po-form-marketplace"
							/>
						{/snippet}
					</FormField>
				{/if}

				<FormField label="Buyer Name" required>
					{#snippet children({ invalid })}
						<Input
							bind:value={buyer_name}
							{invalid}
							ariaLabel="Buyer Name"
							data-testid="po-form-buyer-name"
						/>
					{/snippet}
				</FormField>

				<FormField label="Buyer Country" required>
					{#snippet children({ invalid })}
						<Select
							bind:value={buyer_country}
							options={countryOptions}
							{invalid}
							ariaLabel="Buyer Country"
							data-testid="po-form-buyer-country"
						/>
					{/snippet}
				</FormField>

				<FormField label="Currency" required>
					{#snippet children({ invalid })}
						<Select
							bind:value={currency}
							options={currencyOptions}
							{invalid}
							ariaLabel="Currency"
							data-testid="po-form-currency"
						/>
					{/snippet}
				</FormField>

				<FormField label="Issued Date" required>
					{#snippet children({ invalid })}
						<DateInput
							bind:value={issued_date}
							{invalid}
							ariaLabel="Issued Date"
							data-testid="po-form-issued-date"
						/>
					{/snippet}
				</FormField>

				<FormField label="Required Delivery Date" required>
					{#snippet children({ invalid })}
						<DateInput
							bind:value={required_delivery_date}
							{invalid}
							ariaLabel="Required Delivery Date"
							data-testid="po-form-required-delivery-date"
						/>
					{/snippet}
				</FormField>

				<div class="span-2">
					<FormField label="Ship-to Address">
						{#snippet children()}
							<textarea
								class="form-textarea"
								bind:value={ship_to_address}
								aria-label="Ship-to Address"
								data-testid="po-form-ship-to-address"
							></textarea>
						{/snippet}
					</FormField>
				</div>

				<FormField label="Payment Terms">
					{#snippet children()}
						<Select
							bind:value={payment_terms}
							options={paymentTermOptions}
							ariaLabel="Payment Terms"
							data-testid="po-form-payment-terms"
						/>
					{/snippet}
				</FormField>
			</div>
		</PanelCard>
	</div>

	<div class="po-form-section" data-testid="po-form-section-trade">
		<PanelCard title="Trade Details">
			<div class="form-grid">
				<FormField label="Incoterm">
					{#snippet children()}
						<Select
							bind:value={incoterm}
							options={incotermOptions}
							ariaLabel="Incoterm"
							data-testid="po-form-incoterm"
						/>
					{/snippet}
				</FormField>

				<FormField label="Port of Loading">
					{#snippet children()}
						<Select
							bind:value={port_of_loading}
							options={portOptions}
							ariaLabel="Port of Loading"
							data-testid="po-form-port-loading"
						/>
					{/snippet}
				</FormField>

				<FormField label="Port of Discharge">
					{#snippet children()}
						<Select
							bind:value={port_of_discharge}
							options={portOptions}
							ariaLabel="Port of Discharge"
							data-testid="po-form-port-discharge"
						/>
					{/snippet}
				</FormField>

				<FormField label="Country of Origin">
					{#snippet children()}
						<Select
							bind:value={country_of_origin}
							options={countryOptions}
							ariaLabel="Country of Origin"
							data-testid="po-form-country-origin"
						/>
					{/snippet}
				</FormField>

				<FormField label="Country of Destination">
					{#snippet children()}
						<Select
							bind:value={country_of_destination}
							options={countryOptions}
							ariaLabel="Country of Destination"
							data-testid="po-form-country-destination"
						/>
					{/snippet}
				</FormField>
			</div>
		</PanelCard>
	</div>

	<div class="po-form-section" data-testid="po-form-section-terms">
		<PanelCard title="Terms & Conditions">
			<FormField label="Terms">
				{#snippet children()}
					<textarea
						class="form-textarea"
						rows="6"
						bind:value={terms_and_conditions}
						aria-label="Terms and Conditions"
						data-testid="po-form-terms-and-conditions"
					></textarea>
				{/snippet}
			</FormField>
		</PanelCard>
	</div>

	<div class="po-form-section" data-testid="po-form-section-line-items">
		<PanelCard title="Line Items">
			{#snippet action()}
				<Button variant="secondary" onclick={addLineItem} data-testid="po-form-add-line">
					Add Line Item
				</Button>
			{/snippet}

			<div class="line-items">
				{#each lineItems as item, i (i)}
					<div class="line-item-card" data-testid="po-form-line-{i}">
						<div class="line-item-grid">
							<FormField label="Part Number" required>
								{#snippet children({ invalid })}
									<Input
										bind:value={item.part_number}
										{invalid}
										ariaLabel="Part Number"
										data-testid="po-form-line-{i}-part-number"
									/>
								{/snippet}
							</FormField>

							<FormField label="Description">
								{#snippet children()}
									<Input
										bind:value={item.description}
										ariaLabel="Description"
										data-testid="po-form-line-{i}-description"
									/>
								{/snippet}
							</FormField>

							<FormField label="Quantity" required>
								{#snippet children({ invalid })}
									<Input
										type="number"
										bind:value={item.quantity}
										{invalid}
										ariaLabel="Quantity"
										data-testid="po-form-line-{i}-quantity"
									/>
								{/snippet}
							</FormField>

							<FormField label="UoM">
								{#snippet children()}
									<Input
										bind:value={item.uom}
										ariaLabel="Unit of Measure"
										data-testid="po-form-line-{i}-uom"
									/>
								{/snippet}
							</FormField>

							<FormField label="Unit Price" required>
								{#snippet children({ invalid })}
									<Input
										type="number"
										bind:value={item.unit_price}
										{invalid}
										ariaLabel="Unit Price"
										data-testid="po-form-line-{i}-unit-price"
									/>
								{/snippet}
							</FormField>

							<FormField
								label="HS Code"
								error={hsCodeErrors[i] || undefined}
								data-testid="po-form-line-{i}-hs-code-field"
							>
								{#snippet children({ invalid })}
									<Input
										bind:value={item.hs_code}
										{invalid}
										ariaLabel="HS Code"
										data-testid="po-form-line-{i}-hs-code"
									/>
								{/snippet}
							</FormField>

							<FormField label="Country of Origin">
								{#snippet children()}
									<Input
										bind:value={item.country_of_origin}
										ariaLabel="Line Country of Origin"
										data-testid="po-form-line-{i}-country-origin"
									/>
								{/snippet}
							</FormField>

							<FormField label="Product ID">
								{#snippet children()}
									<Input
										bind:value={item.product_id}
										ariaLabel="Product ID"
										data-testid="po-form-line-{i}-product-id"
									/>
								{/snippet}
							</FormField>
						</div>

						<div class="line-item-actions">
							<Button
								variant="ghost"
								disabled={lineItems.length <= 1}
								onclick={() => removeLineItem(i)}
								data-testid="po-form-line-{i}-remove"
							>
								Remove
							</Button>
						</div>
					</div>
				{/each}
			</div>
		</PanelCard>
	</div>

	<div class="po-form-footer">
		{#if error}
			<p class="po-form-error" role="alert" data-testid="po-form-error-banner">{error}</p>
		{/if}
		<div class="po-form-footer-actions">
			<Button
				variant="secondary"
				onclick={handleCancel}
				data-testid="po-form-cancel"
			>
				Cancel
			</Button>
			<Button
				type="submit"
				disabled={submitting || hasHsCodeErrors}
				data-testid="po-form-submit"
			>
				{submitting ? 'Saving...' : submitLabel}
			</Button>
		</div>
	</div>
</form>

{#if showDiscardModal}
	<div
		class="discard-modal-backdrop"
		role="dialog"
		aria-modal="true"
		aria-labelledby="discard-modal-title"
		data-testid="po-form-discard-modal"
	>
		<div class="discard-modal-card">
			<h2 id="discard-modal-title" class="discard-modal-title">Discard changes?</h2>
			<p class="discard-modal-body">You have unsaved changes. Leaving this page will discard them.</p>
			<div class="discard-modal-actions">
				<Button variant="secondary" onclick={keepEditing} data-testid="po-form-discard-keep">
					Keep editing
				</Button>
				<Button onclick={confirmDiscard} data-testid="po-form-discard-confirm">
					Discard
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	.po-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.po-form-section {
		display: block;
	}

	.form-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
	}

	.form-grid .span-2 {
		grid-column: span 2;
	}

	@media (max-width: 767px) {
		.form-grid {
			grid-template-columns: 1fr;
		}
		.form-grid .span-2 {
			grid-column: span 1;
		}
	}

	.form-textarea {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		color: var(--gray-900);
		min-height: 4rem;
		resize: vertical;
	}

	.form-textarea:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 0;
		border-color: var(--brand-accent);
	}

	.line-items {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.line-item-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		background-color: var(--surface-page);
	}

	.line-item-grid {
		display: grid;
		grid-template-columns: 2fr 2fr 1fr 1fr 1.5fr 1.5fr 1.5fr 1.5fr;
		gap: var(--space-3);
		align-items: start;
	}

	.line-item-actions {
		display: flex;
		justify-content: flex-end;
	}

	@media (max-width: 1023px) {
		.line-item-grid {
			grid-template-columns: 1fr 1fr;
		}
	}

	@media (max-width: 600px) {
		.line-item-grid {
			grid-template-columns: 1fr;
		}
	}

	.po-form-footer {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-4);
		background-color: var(--surface-card);
		border-top: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}

	.po-form-error {
		color: var(--red-700);
		font-size: var(--font-size-sm);
		margin: 0;
	}

	.po-form-footer-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}

	@media (max-width: 767px) {
		.po-form-footer {
			position: sticky;
			bottom: 0;
			padding-bottom: calc(var(--space-4) + env(safe-area-inset-bottom));
			z-index: 10;
		}
	}

	.discard-modal-backdrop {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: var(--space-4);
	}

	.discard-modal-card {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		max-width: 24rem;
		width: 100%;
		padding: var(--space-6);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.discard-modal-title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}

	.discard-modal-body {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0;
	}

	.discard-modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}
</style>
