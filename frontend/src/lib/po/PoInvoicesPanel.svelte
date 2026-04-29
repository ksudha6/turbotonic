<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import type { InvoiceListItem, PurchaseOrder, RemainingLine } from '$lib/types';

	let {
		invoices,
		po,
		remainingMap,
		formatDate,
		formatValue
	}: {
		invoices: InvoiceListItem[];
		po: PurchaseOrder;
		remainingMap: Map<string, RemainingLine>;
		formatDate: (s: string) => string;
		formatValue: (n: string, code: string) => string;
	} = $props();

	// Sum of remaining across all lines for PROCUREMENT POs.
	const remainingTotal = $derived(
		po.po_type === 'PROCUREMENT'
			? [...remainingMap.values()].reduce((sum, line) => sum + line.remaining, 0)
			: 0
	);

	const subtitle = $derived.by((): string | undefined => {
		if (po.po_type === 'PROCUREMENT' && remainingTotal > 0) {
			return `${remainingTotal} unit${remainingTotal === 1 ? '' : 's'} remaining to invoice`;
		}
		if (po.po_type === 'OPEX' && invoices.length === 0) {
			return 'OPEX — single invoice';
		}
		return undefined;
	});

	// The panel renders only when there is something to show.
	// Caller controls visibility; this internal guard prevents
	// an empty panel from appearing before the caller's condition kicks in.
	const shouldRender = $derived(
		invoices.length > 0 ||
		(po.po_type === 'OPEX')
	);
</script>

{#if shouldRender}
	<PanelCard title="Invoices" subtitle={subtitle} data-testid="po-invoices-panel">
		{#snippet children()}
			<table class="invoices-table">
				<thead>
					<tr>
						<th>Invoice #</th>
						<th>Status</th>
						<th>Subtotal</th>
						<th>Created</th>
					</tr>
				</thead>
				<tbody>
					{#each invoices as inv}
						<tr data-testid="po-invoices-row-{inv.id}">
							<td><a href="/invoice/{inv.id}">{inv.invoice_number}</a></td>
							<td><StatusPill status={inv.status} /></td>
							<td>{formatValue(inv.subtotal, po.currency)}</td>
							<td>{formatDate(inv.created_at)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/snippet}
	</PanelCard>
{/if}

<style>
	.invoices-table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--font-size-sm);
	}
	thead {
		background-color: var(--gray-50);
		border-bottom: 1px solid var(--gray-200);
	}
	thead th {
		padding: var(--space-3) var(--space-4);
		text-align: left;
		font-weight: 500;
		color: var(--gray-700);
	}
	tbody tr {
		border-bottom: 1px solid var(--gray-100);
	}
	tbody tr:last-child {
		border-bottom: none;
	}
	tbody td {
		padding: var(--space-3) var(--space-4);
		color: var(--gray-900);
	}
	tbody td a {
		color: var(--brand-accent);
		text-decoration: none;
	}
	tbody td a:hover {
		text-decoration: underline;
	}
</style>
