<script lang="ts">
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Button from '$lib/ui/Button.svelte';
	import { goto } from '$app/navigation';
	import type { ProductListItem, VendorListItem } from '$lib/types';

	let {
		rows,
		vendors,
		canManage,
		'data-testid': testid
	}: {
		rows: ProductListItem[];
		vendors: VendorListItem[];
		canManage: boolean;
		'data-testid'?: string;
	} = $props();

	function vendorName(vendor_id: string): string {
		return vendors.find((v) => v.id === vendor_id)?.name ?? vendor_id;
	}

	function qualSummary(p: ProductListItem): { tone: 'blue' | 'gray'; label: string } {
		const n = p.qualifications.length;
		if (n === 0) {
			return { tone: 'gray', label: 'None' };
		}
		return { tone: 'blue', label: n === 1 ? '1 qualification' : `${n} qualifications` };
	}
</script>

<div class="product-list-table" data-testid={testid ?? 'product-table'}>
	<table class="product-list-table__desktop" data-testid="product-table-desktop">
		<thead>
			<tr>
				<th>Part Number</th>
				<th>Description</th>
				<th>Vendor</th>
				<th>Qualifications</th>
				{#if canManage}
					<th class="product-list-table__action-col"></th>
				{/if}
			</tr>
		</thead>
		<tbody>
			{#each rows as row (row.id)}
				{@const qual = qualSummary(row)}
				<tr data-testid={`product-row-${row.id}`}>
					<td>
						<span class="product-list-table__part">{row.part_number}</span>
					</td>
					<td>{row.description}</td>
					<td>{vendorName(row.vendor_id)}</td>
					<td>
						<StatusPill
							tone={qual.tone}
							label={qual.label}
							data-testid={`product-row-quals-${row.id}`}
						/>
					</td>
					{#if canManage}
						<td class="product-list-table__action-col">
							<Button
								variant="secondary"
								onclick={() => goto(`/products/${row.id}/edit`)}
								data-testid={`product-row-edit-${row.id}`}
							>
								Edit
							</Button>
						</td>
					{/if}
				</tr>
			{/each}
		</tbody>
	</table>

	<ul class="product-list-table__mobile" data-testid="product-table-mobile">
		{#each rows as row (row.id)}
			{@const qual = qualSummary(row)}
			<li class="product-row-card" data-testid={`product-row-${row.id}`}>
				<div class="product-row-card__header">
					<span class="product-row-card__part">{row.part_number}</span>
					<StatusPill
						tone={qual.tone}
						label={qual.label}
						data-testid={`product-row-quals-${row.id}`}
					/>
				</div>
				<p class="product-row-card__description">{row.description}</p>
				<p class="product-row-card__vendor">{vendorName(row.vendor_id)}</p>
				{#if canManage}
					<div class="product-row-card__action">
						<Button
							variant="secondary"
							onclick={() => goto(`/products/${row.id}/edit`)}
							data-testid={`product-row-edit-${row.id}`}
						>
							Edit
						</Button>
					</div>
				{/if}
			</li>
		{/each}
	</ul>
</div>

<style>
	.product-list-table { display: block; }
	.product-list-table__desktop { display: none; }
	.product-list-table__mobile {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.product-row-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.product-row-card__header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
	}
	.product-row-card__part {
		font-weight: 600;
		font-size: var(--font-size-base);
		font-family: var(--font-family-mono, monospace);
		color: var(--gray-900);
	}
	.product-row-card__description {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0;
	}
	.product-row-card__vendor {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		margin: 0;
	}
	.product-row-card__action {
		display: flex;
		justify-content: flex-end;
	}
	.product-list-table__part {
		font-family: var(--font-family-mono, monospace);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	@media (min-width: 768px) {
		.product-list-table__mobile { display: none; }
		.product-list-table__desktop {
			display: table;
			width: 100%;
			border-collapse: collapse;
			font-size: var(--font-size-sm);
		}
		.product-list-table__desktop th {
			text-align: left;
			padding: var(--space-3) var(--space-4);
			font-weight: 600;
			color: var(--gray-600);
			border-bottom: 1px solid var(--gray-200);
			background-color: var(--gray-50);
			white-space: nowrap;
		}
		.product-list-table__desktop td {
			padding: var(--space-3) var(--space-4);
			border-bottom: 1px solid var(--gray-100);
			vertical-align: middle;
		}
		.product-list-table__action-col {
			text-align: right;
			white-space: nowrap;
		}
	}
</style>
