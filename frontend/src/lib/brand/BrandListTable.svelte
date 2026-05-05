<script lang="ts">
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { Brand, BrandStatus } from '$lib/types';

	type Tone = 'green' | 'blue' | 'orange' | 'red' | 'gray';

	const STATUS_TONE: Readonly<Record<BrandStatus, Tone>> = {
		ACTIVE: 'green',
		INACTIVE: 'gray'
	};

	const STATUS_LABEL: Readonly<Record<BrandStatus, string>> = {
		ACTIVE: 'Active',
		INACTIVE: 'Inactive'
	};

	function truncateTaxId(taxId: string): string {
		if (!taxId) return '';
		return taxId.length > 12 ? taxId.slice(0, 12) + '…' : taxId;
	}

	let {
		rows,
		onEdit,
		onDeactivate,
		onReactivate,
		'data-testid': testid
	}: {
		rows: Brand[];
		onEdit: (id: string) => void;
		onDeactivate: (id: string) => void;
		onReactivate: (id: string) => void;
		'data-testid'?: string;
	} = $props();
</script>

<div class="brand-list-table" data-testid={testid ?? 'brand-table'}>
	<table class="brand-list-table__desktop" data-testid="brand-table-desktop">
		<thead>
			<tr>
				<th>Name</th>
				<th>Legal Name</th>
				<th>Country</th>
				<th>Status</th>
				<th>Tax ID</th>
				<th class="brand-list-table__action-col">Actions</th>
			</tr>
		</thead>
		<tbody>
			{#each rows as row (row.id)}
				<tr data-testid={`brand-row-${row.id}`}>
					<td data-testid={`brand-row-name-${row.id}`}>{row.name}</td>
					<td>{row.legal_name}</td>
					<td>{row.country}</td>
					<td>
						<StatusPill
							tone={STATUS_TONE[row.status]}
							label={STATUS_LABEL[row.status]}
							data-testid={`brand-row-status-${row.id}`}
						/>
					</td>
					<td>{truncateTaxId(row.tax_id)}</td>
					<td class="brand-list-table__action-col">
						<div class="brand-list-table__actions">
							<Button
								variant="ghost"
								onclick={() => onEdit(row.id)}
								data-testid={`brand-row-edit-${row.id}`}
							>
								Edit
							</Button>
							{#if row.status === 'ACTIVE'}
								<Button
									variant="secondary"
									onclick={() => onDeactivate(row.id)}
									data-testid={`brand-row-deactivate-${row.id}`}
								>
									Deactivate
								</Button>
							{/if}
							{#if row.status === 'INACTIVE'}
								<Button
									variant="primary"
									onclick={() => onReactivate(row.id)}
									data-testid={`brand-row-reactivate-${row.id}`}
								>
									Reactivate
								</Button>
							{/if}
						</div>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>

	<ul class="brand-list-table__mobile" data-testid="brand-table-mobile">
		{#each rows as row (row.id)}
			<li class="brand-row-card" data-testid={`brand-row-${row.id}`}>
				<div class="brand-row-card__header">
					<span class="brand-row-card__name" data-testid={`brand-row-name-${row.id}`}>
						{row.name}
					</span>
					<StatusPill
						tone={STATUS_TONE[row.status]}
						label={STATUS_LABEL[row.status]}
						data-testid={`brand-row-status-${row.id}`}
					/>
				</div>
				<div class="brand-row-card__meta">
					<span>{row.legal_name}</span>
					<span>·</span>
					<span>{row.country}</span>
					{#if row.tax_id}
						<span>·</span>
						<span>{truncateTaxId(row.tax_id)}</span>
					{/if}
				</div>
				<div class="brand-row-card__actions">
					<Button
						variant="ghost"
						onclick={() => onEdit(row.id)}
						data-testid={`brand-row-edit-${row.id}`}
					>
						Edit
					</Button>
					{#if row.status === 'ACTIVE'}
						<Button
							variant="secondary"
							onclick={() => onDeactivate(row.id)}
							data-testid={`brand-row-deactivate-${row.id}`}
						>
							Deactivate
						</Button>
					{/if}
					{#if row.status === 'INACTIVE'}
						<Button
							variant="primary"
							onclick={() => onReactivate(row.id)}
							data-testid={`brand-row-reactivate-${row.id}`}
						>
							Reactivate
						</Button>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
</div>

<style>
	.brand-list-table {
		display: block;
	}
	.brand-list-table__desktop {
		display: none;
	}
	.brand-list-table__mobile {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.brand-row-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.brand-row-card__header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
	}
	.brand-row-card__name {
		font-weight: 600;
		font-size: var(--font-size-base);
		color: var(--gray-900);
	}
	.brand-row-card__meta {
		display: flex;
		gap: var(--space-2);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		flex-wrap: wrap;
	}
	.brand-row-card__actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		justify-content: flex-end;
	}

	@media (min-width: 768px) {
		.brand-list-table__mobile { display: none; }
		.brand-list-table__desktop {
			display: table;
			width: 100%;
			border-collapse: collapse;
			font-size: var(--font-size-sm);
		}
		.brand-list-table__desktop th {
			text-align: left;
			padding: var(--space-3) var(--space-4);
			font-weight: 600;
			color: var(--gray-600);
			border-bottom: 1px solid var(--gray-200);
			background-color: var(--gray-50);
			white-space: nowrap;
		}
		.brand-list-table__desktop td {
			padding: var(--space-3) var(--space-4);
			border-bottom: 1px solid var(--gray-100);
			vertical-align: middle;
		}
		.brand-list-table__action-col {
			text-align: right;
			white-space: nowrap;
		}
		.brand-list-table__actions {
			display: flex;
			gap: var(--space-2);
			flex-wrap: wrap;
			justify-content: flex-end;
		}
	}
</style>
