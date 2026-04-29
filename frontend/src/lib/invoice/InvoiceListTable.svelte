<script lang="ts">
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import type { InvoiceListItemWithContext, InvoiceStatus } from '$lib/types';

	let {
		rows,
		selectedIds = $bindable(new Set<string>()),
		onRowClick,
		'data-testid': testid
	}: {
		rows: InvoiceListItemWithContext[];
		selectedIds?: Set<string>;
		onRowClick: (id: string) => void;
		'data-testid'?: string;
	} = $props();

	type Tone = 'green' | 'blue' | 'orange' | 'red' | 'gray';

	const STATUS_TONE: Readonly<Record<InvoiceStatus, Tone>> = {
		DRAFT: 'gray',
		SUBMITTED: 'blue',
		APPROVED: 'green',
		PAID: 'green',
		DISPUTED: 'red'
	};

	function statusLabel(status: string): string {
		return status.charAt(0) + status.slice(1).toLowerCase();
	}

	const allOnPageSelected = $derived(
		rows.length > 0 && rows.every((r) => selectedIds.has(r.id))
	);

	function toggleRow(id: string) {
		const next = new Set(selectedIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		selectedIds = next;
	}

	function toggleAllOnPage() {
		if (allOnPageSelected) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(rows.map((r) => r.id));
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatSubtotal(value: string): string {
		return parseFloat(value).toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}
</script>

{#if rows.length > 0}
	<div class="invoice-list-table" data-testid={testid ?? 'invoice-table'}>
		<table class="invoice-list-table__desktop" data-testid="invoice-table-desktop">
			<thead>
				<tr>
					<th class="invoice-list-table__checkbox-col">
						<input
							type="checkbox"
							checked={allOnPageSelected}
							onchange={toggleAllOnPage}
							aria-label="Select all invoices on this page"
							data-testid="invoice-table-checkbox-all"
						/>
					</th>
					<th>Invoice #</th>
					<th>PO #</th>
					<th>Vendor</th>
					<th>Status</th>
					<th>Subtotal</th>
					<th>Created</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as row (row.id)}
					<tr
						class="invoice-list-table__row"
						onclick={() => onRowClick(row.id)}
						data-testid="invoice-row-{row.id}"
					>
						<td
							class="invoice-list-table__checkbox-col"
							onclick={(e) => e.stopPropagation()}
						>
							<input
								type="checkbox"
								checked={selectedIds.has(row.id)}
								onchange={() => toggleRow(row.id)}
								aria-label="Select invoice {row.invoice_number}"
								data-testid="invoice-row-checkbox-{row.id}"
							/>
						</td>
						<td>
							<a
								href="/invoice/{row.id}"
								onclick={(e) => e.stopPropagation()}
								data-testid="invoice-row-link-{row.id}"
							>
								{row.invoice_number}
							</a>
						</td>
						<td>
							<a
								href="/po/{row.po_id}"
								onclick={(e) => e.stopPropagation()}
								data-testid="invoice-row-po-link-{row.id}"
							>
								{row.po_number}
							</a>
						</td>
						<td>{row.vendor_name}</td>
						<td>
							<StatusPill
								tone={STATUS_TONE[row.status]}
								label={statusLabel(row.status)}
								data-testid="invoice-row-status-{row.id}"
							/>
						</td>
						<td>{formatSubtotal(row.subtotal)}</td>
						<td>{formatDate(row.created_at)}</td>
					</tr>
				{/each}
			</tbody>
		</table>

		<div class="invoice-list-table__mobile" role="list" data-testid="invoice-table-mobile">
			{#each rows as row (row.id)}
				<div
					role="listitem"
					class="invoice-row-card"
					onclick={() => onRowClick(row.id)}
					onkeydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							onRowClick(row.id);
						}
					}}
					tabindex="0"
					data-testid="invoice-row-{row.id}"
				>
					<div class="invoice-row-card__header">
						<span
							class="invoice-row-card__check"
							onclick={(e) => e.stopPropagation()}
							role="presentation"
						>
							<input
								type="checkbox"
								checked={selectedIds.has(row.id)}
								onchange={() => toggleRow(row.id)}
								aria-label="Select invoice {row.invoice_number}"
								data-testid="invoice-row-checkbox-{row.id}"
							/>
						</span>
						<span class="invoice-row-card__invoice-number">{row.invoice_number}</span>
						<span class="invoice-row-card__subtotal">{formatSubtotal(row.subtotal)}</span>
					</div>
					<div class="invoice-row-card__vendor">{row.vendor_name}</div>
					<div class="invoice-row-card__po">PO {row.po_number}</div>
					<div class="invoice-row-card__status">
						<StatusPill
							tone={STATUS_TONE[row.status]}
							label={statusLabel(row.status)}
							data-testid="invoice-row-status-{row.id}"
						/>
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.invoice-list-table {
		display: block;
	}
	.invoice-list-table__desktop {
		display: none;
	}
	.invoice-list-table__mobile {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.invoice-row-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		cursor: pointer;
	}
	.invoice-row-card:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: -2px;
	}
	.invoice-row-card:hover {
		background-color: var(--gray-50);
	}
	.invoice-row-card__header {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	.invoice-row-card__check {
		display: inline-flex;
	}
	.invoice-row-card__invoice-number {
		font-weight: 600;
		font-size: var(--font-size-base);
	}
	.invoice-row-card__subtotal {
		margin-left: auto;
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.invoice-row-card__vendor {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.invoice-row-card__po {
		font-size: var(--font-size-xs);
		color: var(--gray-600);
	}
	@media (min-width: 768px) {
		.invoice-list-table__mobile {
			display: none;
		}
		.invoice-list-table__desktop {
			display: table;
			width: 100%;
			border-collapse: collapse;
			font-size: var(--font-size-sm);
		}
		.invoice-list-table__desktop th {
			text-align: left;
			padding: var(--space-3) var(--space-4);
			font-weight: 600;
			color: var(--gray-600);
			border-bottom: 1px solid var(--gray-200);
			background-color: var(--gray-50);
			white-space: nowrap;
		}
		.invoice-list-table__desktop td {
			padding: var(--space-3) var(--space-4);
			border-bottom: 1px solid var(--gray-100);
		}
		.invoice-list-table__row {
			cursor: pointer;
		}
		.invoice-list-table__row:hover {
			background-color: var(--gray-50);
		}
		.invoice-list-table__checkbox-col {
			width: 40px;
			text-align: center;
		}
		.invoice-list-table__desktop a {
			color: var(--blue-600);
			text-decoration: none;
		}
		.invoice-list-table__desktop a:hover {
			text-decoration: underline;
		}
	}
</style>
