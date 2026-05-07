<script lang="ts">
	import PoStatusPills from './PoStatusPills.svelte';
	import type { PurchaseOrderListItem } from '$lib/types';

	type SortDir = 'asc' | 'desc';

	let {
		rows,
		selectedIds = $bindable(new Set<string>()),
		canBulk,
		sortBy = $bindable('issued_date'),
		sortDir = $bindable<SortDir>('desc'),
		onRowClick,
		'data-testid': testid
	}: {
		rows: PurchaseOrderListItem[];
		selectedIds?: Set<string>;
		canBulk: boolean;
		sortBy?: string;
		sortDir?: SortDir;
		onRowClick: (id: string) => void;
		'data-testid'?: string;
	} = $props();

	const MILESTONE_LABELS: Readonly<Record<string, string>> = {
		RAW_MATERIALS: 'Raw Materials',
		PRODUCTION_STARTED: 'Production Started',
		QC_PASSED: 'QC Passed',
		READY_FOR_SHIPMENT: 'Ready for Shipment',
		SHIPPED: 'Shipped'
	};

	const SORTABLE_COLUMNS: ReadonlyArray<{ key: string; label: string }> = [
		{ key: 'po_number', label: 'PO #' },
		{ key: 'vendor_name', label: 'Vendor' },
		{ key: 'issued_date', label: 'Issued' },
		{ key: 'required_delivery_date', label: 'Required by' },
		{ key: 'total_value', label: 'Value' },
		{ key: 'status', label: 'Status' }
	];

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

	function toggleSort(column: string) {
		if (sortBy === column) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortBy = column;
			sortDir = 'desc';
		}
	}

	function sortGlyph(column: string): string {
		if (sortBy !== column) return '';
		return sortDir === 'asc' ? ' \u25B2' : ' \u25BC';
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatValue(value: string, currency: string): string {
		const num = parseFloat(value).toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
		return `${num} ${currency}`;
	}

	function milestoneLabel(milestone: string | null): string {
		if (!milestone) return '\u2014';
		return MILESTONE_LABELS[milestone] ?? milestone;
	}
</script>

{#if rows.length > 0}
	<div class="po-list-table" data-testid={testid ?? 'po-table'}>
		<table class="po-list-table__desktop">
			<thead>
				<tr>
					{#if canBulk}
						<th class="po-list-table__checkbox-col">
							<input
								type="checkbox"
								checked={allOnPageSelected}
								onchange={toggleAllOnPage}
								data-testid="po-select-all"
							/>
						</th>
					{/if}
					{#each SORTABLE_COLUMNS as col (col.key)}
						<th
							class="po-list-table__sortable"
							onclick={() => toggleSort(col.key)}
							data-testid="po-sort-{col.key}"
						>
							{col.label}{sortGlyph(col.key)}
						</th>
					{/each}
					<th>Brand</th>
					<th>Type</th>
					<th>Current Milestone</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as row (row.id)}
					<tr
						class="po-list-table__row"
						onclick={() => onRowClick(row.id)}
						data-testid="po-row-{row.id}"
					>
						{#if canBulk}
							<td
								class="po-list-table__checkbox-col"
								onclick={(e) => e.stopPropagation()}
							>
								<input
									type="checkbox"
									checked={selectedIds.has(row.id)}
									onchange={() => toggleRow(row.id)}
									data-testid="po-row-select-{row.id}"
								/>
							</td>
						{/if}
						<td>{row.po_number}</td>
						<td>{row.vendor_name}</td>
						<td>
							<PoStatusPills
								status={row.status}
								partial={Boolean(row.has_removed_line)}
							/>
						</td>
						<td>{formatDate(row.issued_date)}</td>
						<td>{formatDate(row.required_delivery_date)}</td>
						<td>{formatValue(row.total_value, row.currency)}</td>
						<td class="po-list-table__brand" title={row.brand_name}>{row.brand_name ? (row.brand_name.length > 18 ? row.brand_name.slice(0, 18) + '…' : row.brand_name) : ''}</td>
						<td>{row.po_type}</td>
						<td class="po-list-table__milestone">{milestoneLabel(row.current_milestone)}</td>
					</tr>
				{/each}
			</tbody>
		</table>

		<div class="po-list-table__mobile" role="list">
			{#each rows as row (row.id)}
				<div
					role="listitem"
					class="po-row-card"
					onclick={() => onRowClick(row.id)}
					onkeydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							onRowClick(row.id);
						}
					}}
					tabindex="0"
					data-testid="po-row-{row.id}"
				>
					<div class="po-row-card__header">
						{#if canBulk}
							<span
								class="po-row-card__check"
								onclick={(e) => e.stopPropagation()}
								role="presentation"
							>
								<input
									type="checkbox"
									checked={selectedIds.has(row.id)}
									onchange={() => toggleRow(row.id)}
									data-testid="po-row-select-{row.id}"
								/>
							</span>
						{/if}
						<span class="po-row-card__po-number">{row.po_number}</span>
						<span class="po-row-card__value"
							>{formatValue(row.total_value, row.currency)}</span
						>
					</div>
					{#if row.brand_name}
						<div class="po-row-card__brand">Brand: {row.brand_name}</div>
					{/if}
					<div class="po-row-card__vendor">{row.vendor_name}</div>
					<div class="po-row-card__status">
						<PoStatusPills
							status={row.status}
							partial={Boolean(row.has_removed_line)}
						/>
					</div>
					{#if row.current_milestone}
						<div class="po-row-card__milestone">
							{milestoneLabel(row.current_milestone)}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.po-list-table {
		display: block;
	}
	.po-list-table__desktop {
		display: none;
	}
	.po-list-table__mobile {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.po-row-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		cursor: pointer;
	}
	.po-row-card:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: -2px;
	}
	.po-row-card:hover {
		background-color: var(--gray-50);
	}
	.po-row-card__header {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	.po-row-card__check {
		display: inline-flex;
	}
	.po-row-card__po-number {
		font-weight: 600;
		font-size: var(--font-size-base);
	}
	.po-row-card__value {
		margin-left: auto;
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.po-row-card__vendor {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.po-row-card__milestone {
		font-size: var(--font-size-xs);
		color: var(--gray-600);
	}
	@media (min-width: 768px) {
		.po-list-table__mobile {
			display: none;
		}
		.po-list-table__desktop {
			display: table;
			width: 100%;
			border-collapse: collapse;
			font-size: var(--font-size-sm);
		}
		.po-list-table__desktop th {
			text-align: left;
			padding: var(--space-3) var(--space-4);
			font-weight: 600;
			color: var(--gray-600);
			border-bottom: 1px solid var(--gray-200);
			background-color: var(--gray-50);
			white-space: nowrap;
		}
		.po-list-table__desktop td {
			padding: var(--space-3) var(--space-4);
			border-bottom: 1px solid var(--gray-100);
		}
		.po-list-table__sortable {
			cursor: pointer;
			user-select: none;
		}
		.po-list-table__sortable:hover {
			color: var(--gray-900);
		}
		.po-list-table__row {
			cursor: pointer;
		}
		.po-list-table__row:hover {
			background-color: var(--gray-50);
		}
		.po-list-table__checkbox-col {
			width: 40px;
			text-align: center;
		}
		.po-list-table__milestone {
			font-size: var(--font-size-sm);
			color: var(--gray-600);
			white-space: nowrap;
		}
		.po-list-table__brand {
			font-size: var(--font-size-sm);
			color: var(--gray-700);
			max-width: 140px;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
		}
	}
	.po-row-card__brand {
		font-size: var(--font-size-xs);
		color: var(--gray-600);
	}
</style>
