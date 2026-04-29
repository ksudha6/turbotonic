<script lang="ts">
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { VendorListItem, VendorStatus, VendorType } from '$lib/types';

	let {
		rows,
		canManage,
		onAction,
		'data-testid': testid
	}: {
		rows: VendorListItem[];
		canManage: boolean;
		onAction: (id: string, action: 'deactivate' | 'reactivate') => void;
		'data-testid'?: string;
	} = $props();

	type Tone = 'green' | 'blue' | 'orange' | 'red' | 'gray';

	const STATUS_TONE: Readonly<Record<VendorStatus, Tone>> = {
		ACTIVE: 'green',
		INACTIVE: 'gray'
	};

	function statusLabel(status: VendorStatus): string {
		return status === 'ACTIVE' ? 'Active' : 'Inactive';
	}

	const VENDOR_TYPE_LABEL: Readonly<Record<VendorType, string>> = {
		PROCUREMENT: 'Procurement',
		OPEX: 'OpEx',
		FREIGHT: 'Freight',
		MISCELLANEOUS: 'Miscellaneous'
	};

	function shortId(id: string): string {
		return id.slice(0, 8);
	}
</script>

<div class="vendor-list-table" data-testid={testid ?? 'vendor-table'}>
	<table class="vendor-list-table__desktop" data-testid="vendor-table-desktop">
		<thead>
			<tr>
				<th>ID</th>
				<th>Name</th>
				<th>Country</th>
				<th>Type</th>
				<th>Status</th>
				{#if canManage}
					<th class="vendor-list-table__action-col"></th>
				{/if}
			</tr>
		</thead>
		<tbody>
			{#each rows as row (row.id)}
				<tr data-testid={`vendor-row-${row.id}`}>
					<td>
						<span
							class="vendor-list-table__id"
							data-testid={`vendor-row-id-${row.id}`}
						>
							{shortId(row.id)}
						</span>
					</td>
					<td>{row.name}</td>
					<td>{row.country}</td>
					<td>{VENDOR_TYPE_LABEL[row.vendor_type] ?? row.vendor_type}</td>
					<td>
						<StatusPill
							tone={STATUS_TONE[row.status]}
							label={statusLabel(row.status)}
							data-testid={`vendor-row-status-${row.id}`}
						/>
					</td>
					{#if canManage}
						<td class="vendor-list-table__action-col">
							{#if row.status === 'ACTIVE'}
								<Button
									variant="secondary"
									onclick={() => onAction(row.id, 'deactivate')}
									data-testid={`vendor-row-action-${row.id}`}
								>
									Deactivate
								</Button>
							{:else}
								<Button
									variant="primary"
									onclick={() => onAction(row.id, 'reactivate')}
									data-testid={`vendor-row-action-${row.id}`}
								>
									Reactivate
								</Button>
							{/if}
						</td>
					{/if}
				</tr>
			{/each}
		</tbody>
	</table>

	<ul class="vendor-list-table__mobile" data-testid="vendor-table-mobile">
		{#each rows as row (row.id)}
			<li class="vendor-row-card" data-testid={`vendor-row-${row.id}`}>
				<div class="vendor-row-card__header">
					<span class="vendor-row-card__name">{row.name}</span>
					<StatusPill
						tone={STATUS_TONE[row.status]}
						label={statusLabel(row.status)}
						data-testid={`vendor-row-status-${row.id}`}
					/>
				</div>
				<div class="vendor-row-card__meta">
					<span data-testid={`vendor-row-id-${row.id}`}>{shortId(row.id)}</span>
					<span>·</span>
					<span>{row.country}</span>
					<span>·</span>
					<span>{VENDOR_TYPE_LABEL[row.vendor_type] ?? row.vendor_type}</span>
				</div>
				{#if canManage}
					<div class="vendor-row-card__action">
						{#if row.status === 'ACTIVE'}
							<Button
								variant="secondary"
								onclick={() => onAction(row.id, 'deactivate')}
								data-testid={`vendor-row-action-${row.id}`}
							>
								Deactivate
							</Button>
						{:else}
							<Button
								variant="primary"
								onclick={() => onAction(row.id, 'reactivate')}
								data-testid={`vendor-row-action-${row.id}`}
							>
								Reactivate
							</Button>
						{/if}
					</div>
				{/if}
			</li>
		{/each}
	</ul>
</div>

<style>
	.vendor-list-table {
		display: block;
	}
	.vendor-list-table__desktop {
		display: none;
	}
	.vendor-list-table__mobile {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.vendor-row-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.vendor-row-card__header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
	}
	.vendor-row-card__name {
		font-weight: 600;
		font-size: var(--font-size-base);
		color: var(--gray-900);
	}
	.vendor-row-card__meta {
		display: flex;
		gap: var(--space-2);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		flex-wrap: wrap;
	}
	.vendor-row-card__action {
		display: flex;
		justify-content: flex-end;
	}
	.vendor-list-table__id {
		font-family: var(--font-family-mono, monospace);
		font-size: var(--font-size-sm);
		color: var(--gray-600);
	}

	@media (min-width: 768px) {
		.vendor-list-table__mobile { display: none; }
		.vendor-list-table__desktop {
			display: table;
			width: 100%;
			border-collapse: collapse;
			font-size: var(--font-size-sm);
		}
		.vendor-list-table__desktop th {
			text-align: left;
			padding: var(--space-3) var(--space-4);
			font-weight: 600;
			color: var(--gray-600);
			border-bottom: 1px solid var(--gray-200);
			background-color: var(--gray-50);
			white-space: nowrap;
		}
		.vendor-list-table__desktop td {
			padding: var(--space-3) var(--space-4);
			border-bottom: 1px solid var(--gray-100);
			vertical-align: middle;
		}
		.vendor-list-table__action-col {
			text-align: right;
			white-space: nowrap;
		}
	}
</style>
