<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import AttributeList from '$lib/ui/AttributeList.svelte';
	import type { Invoice } from '$lib/types';

	let {
		invoice,
		poNumber
	}: {
		invoice: Invoice;
		poNumber?: string;
	} = $props();

	function formatDate(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleDateString();
	}

	function formatPrice(value: string): string {
		return parseFloat(value).toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	const items = $derived([
		{ label: 'Currency', value: invoice.currency },
		{ label: 'Payment Terms', value: invoice.payment_terms },
		{ label: 'Subtotal', value: `${formatPrice(invoice.subtotal)} ${invoice.currency}` },
		{ label: 'Created', value: formatDate(invoice.created_at) }
	]);
</script>

<PanelCard title="Summary" data-testid="invoice-metadata-panel">
	{#snippet children()}
		<AttributeList {items} label="Invoice summary" />
		<div class="invoice-metadata-panel__po-link">
			<a href="/po/{invoice.po_id}" data-testid="invoice-metadata-po-link">
				View PO {poNumber ?? invoice.po_id}
			</a>
		</div>
	{/snippet}
</PanelCard>

<style>
	.invoice-metadata-panel__po-link {
		margin-top: var(--space-3);
		padding-top: var(--space-3);
		border-top: 1px solid var(--gray-100);
	}
	.invoice-metadata-panel__po-link a {
		color: var(--blue-600);
		text-decoration: none;
		font-size: var(--font-size-sm);
		font-weight: 500;
	}
	.invoice-metadata-panel__po-link a:hover {
		text-decoration: underline;
	}
</style>
