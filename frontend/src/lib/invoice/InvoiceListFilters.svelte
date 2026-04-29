<script lang="ts">
	import Select from '$lib/ui/Select.svelte';
	import DateInput from '$lib/ui/DateInput.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { VendorListItem } from '$lib/types';

	let {
		status = $bindable(''),
		invoiceNumber = $bindable(''),
		poNumber = $bindable(''),
		vendor = $bindable(''),
		dateFrom = $bindable(''),
		dateTo = $bindable(''),
		vendors,
		invoiceOptions,
		poOptions,
		showVendorFilter = true,
		onClear,
		'data-testid': testid
	}: {
		status?: string;
		invoiceNumber?: string;
		poNumber?: string;
		vendor?: string;
		dateFrom?: string;
		dateTo?: string;
		vendors: VendorListItem[];
		invoiceOptions: string[];
		poOptions: string[];
		showVendorFilter?: boolean;
		onClear: () => void;
		'data-testid'?: string;
	} = $props();

	const STATUS_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: '', label: 'All Statuses' },
		{ value: 'DRAFT', label: 'Draft' },
		{ value: 'SUBMITTED', label: 'Submitted' },
		{ value: 'APPROVED', label: 'Approved' },
		{ value: 'PAID', label: 'Paid' },
		{ value: 'DISPUTED', label: 'Disputed' }
	];

	const invoiceNumberOptions = $derived([
		{ value: '', label: 'All Invoices' },
		...invoiceOptions.map((n) => ({ value: n, label: n }))
	]);

	const poNumberOptions = $derived([
		{ value: '', label: 'All POs' },
		...poOptions.map((n) => ({ value: n, label: n }))
	]);

	const vendorOptions = $derived([
		{ value: '', label: 'All Vendors' },
		...vendors.map((v) => ({ value: v.name, label: v.name }))
	]);

	const activeCount = $derived(
		(status ? 1 : 0) +
			(invoiceNumber ? 1 : 0) +
			(poNumber ? 1 : 0) +
			(showVendorFilter && vendor ? 1 : 0) +
			(dateFrom ? 1 : 0) +
			(dateTo ? 1 : 0)
	);

	let mobilePanelOpen = $state(false);
	function toggleMobilePanel() {
		mobilePanelOpen = !mobilePanelOpen;
	}
</script>

<div class="invoice-list-filters" data-testid={testid ?? 'invoice-filters'}>
	<div class="invoice-list-filters__mobile-trigger">
		<Button variant="secondary" onclick={toggleMobilePanel} data-testid="invoice-filters-toggle">
			Filters{#if activeCount > 0}<span class="invoice-list-filters__badge">{activeCount}</span
				>{/if}
		</Button>
	</div>

	<div
		class="invoice-list-filters__row"
		class:invoice-list-filters__row--open={mobilePanelOpen}
	>
		<div class="invoice-list-filters__select">
			<Select
				bind:value={status}
				options={[...STATUS_OPTIONS]}
				ariaLabel="Status"
				data-testid="invoice-filter-status"
			/>
		</div>
		<div class="invoice-list-filters__select">
			<Select
				bind:value={invoiceNumber}
				options={invoiceNumberOptions}
				ariaLabel="Invoice number"
				data-testid="invoice-filter-invoice-number"
			/>
		</div>
		<div class="invoice-list-filters__select">
			<Select
				bind:value={poNumber}
				options={poNumberOptions}
				ariaLabel="PO number"
				data-testid="invoice-filter-po-number"
			/>
		</div>
		{#if showVendorFilter}
			<div class="invoice-list-filters__select">
				<Select
					bind:value={vendor}
					options={vendorOptions}
					ariaLabel="Vendor"
					data-testid="invoice-filter-vendor"
				/>
			</div>
		{/if}
		<div class="invoice-list-filters__select">
			<DateInput
				bind:value={dateFrom}
				ariaLabel="Date from"
				data-testid="invoice-filter-date-from"
			/>
		</div>
		<div class="invoice-list-filters__select">
			<DateInput
				bind:value={dateTo}
				ariaLabel="Date to"
				data-testid="invoice-filter-date-to"
			/>
		</div>
		{#if activeCount > 0}
			<div class="invoice-list-filters__clear">
				<Button variant="secondary" onclick={onClear} data-testid="invoice-filter-clear">
					Clear
				</Button>
			</div>
		{/if}
	</div>
</div>

<style>
	.invoice-list-filters {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.invoice-list-filters__mobile-trigger {
		display: block;
	}
	.invoice-list-filters__badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 1.25rem;
		height: 1.25rem;
		padding: 0 var(--space-2);
		margin-left: var(--space-2);
		background-color: var(--brand-accent);
		color: var(--white);
		font-size: var(--font-size-xs);
		font-weight: 600;
		border-radius: 999px;
	}
	.invoice-list-filters__row {
		display: none;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.invoice-list-filters__row--open {
		display: flex;
	}
	.invoice-list-filters__select,
	.invoice-list-filters__clear {
		width: 100%;
	}
	@media (min-width: 768px) {
		.invoice-list-filters__mobile-trigger {
			display: none;
		}
		.invoice-list-filters__row {
			display: flex;
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			padding: 0;
			background: transparent;
			border: none;
		}
		.invoice-list-filters__select {
			flex: 0 1 180px;
			min-width: 160px;
			width: auto;
		}
		.invoice-list-filters__clear {
			flex: 0 0 auto;
			width: auto;
		}
	}
</style>
