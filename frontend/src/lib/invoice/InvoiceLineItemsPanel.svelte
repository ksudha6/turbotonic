<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import type { InvoiceLineItem } from '$lib/types';

	let {
		lineItems
	}: {
		lineItems: InvoiceLineItem[];
	} = $props();

	function formatPrice(value: string): string {
		return parseFloat(value).toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}
</script>

<PanelCard title="Line Items" data-testid="invoice-line-items-panel">
	{#snippet children()}
		{#if lineItems.length === 0}
			<EmptyState title="No line items." />
		{:else}
			<table class="invoice-line-items__desktop" data-testid="invoice-line-items-table">
				<thead>
					<tr>
						<th>Part Number</th>
						<th>Description</th>
						<th>Qty</th>
						<th>UoM</th>
						<th>Unit Price</th>
					</tr>
				</thead>
				<tbody>
					{#each lineItems as item, i (`${item.part_number}-${i}`)}
						<tr data-testid="invoice-line-row-{i}">
							<td>{item.part_number}</td>
							<td>{item.description}</td>
							<td>{item.quantity}</td>
							<td>{item.uom}</td>
							<td>{formatPrice(item.unit_price)}</td>
						</tr>
					{/each}
				</tbody>
			</table>

			<div class="invoice-line-items__mobile" role="list">
				{#each lineItems as item, i (`${item.part_number}-${i}`)}
					<div class="invoice-line-items-card" role="listitem" data-testid="invoice-line-card-{i}">
						<div class="invoice-line-items-card__header">
							<span class="invoice-line-items-card__part">{item.part_number}</span>
							<span class="invoice-line-items-card__qty">{item.quantity} {item.uom}</span>
						</div>
						<p class="invoice-line-items-card__description">{item.description}</p>
						<div class="invoice-line-items-card__price">
							Unit price: {formatPrice(item.unit_price)}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{/snippet}
</PanelCard>

<style>
	.invoice-line-items__desktop {
		display: none;
	}
	.invoice-line-items__mobile {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.invoice-line-items-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		padding: var(--space-3);
		background-color: var(--gray-50);
		border: 1px solid var(--gray-100);
		border-radius: var(--radius-md);
	}
	.invoice-line-items-card__header {
		display: flex;
		justify-content: space-between;
		gap: var(--space-2);
	}
	.invoice-line-items-card__part {
		font-weight: 600;
		font-size: var(--font-size-base);
		color: var(--gray-900);
	}
	.invoice-line-items-card__qty {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.invoice-line-items-card__description {
		margin: 0;
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.invoice-line-items-card__price {
		font-size: var(--font-size-xs);
		color: var(--gray-600);
	}
	@media (min-width: 768px) {
		.invoice-line-items__mobile {
			display: none;
		}
		.invoice-line-items__desktop {
			display: table;
			width: 100%;
			border-collapse: collapse;
			font-size: var(--font-size-sm);
		}
		.invoice-line-items__desktop th {
			text-align: left;
			padding: var(--space-3) var(--space-4);
			font-weight: 600;
			color: var(--gray-600);
			border-bottom: 1px solid var(--gray-200);
			background-color: var(--gray-50);
			white-space: nowrap;
		}
		.invoice-line-items__desktop td {
			padding: var(--space-3) var(--space-4);
			border-bottom: 1px solid var(--gray-100);
		}
	}
</style>
