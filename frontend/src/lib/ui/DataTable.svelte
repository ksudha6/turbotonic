<script lang="ts" generics="T extends { id: string }">
	import Button from './Button.svelte';

	type Column<Row> = {
		key: string;
		label: string;
		render: (row: Row) => string | number;
	};

	let {
		columns,
		rows,
		pagination,
		onRowClick,
		label,
		'data-testid': testid
	}: {
		columns: Column<T>[];
		rows: T[];
		pagination?: {
			page: number;
			pageSize: number;
			total: number;
			onPageChange: (page: number) => void;
		};
		onRowClick?: (row: T) => void;
		label?: string;
		'data-testid'?: string;
	} = $props();

	const pageCount = $derived(
		pagination ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize)) : 1
	);
</script>

<div class="ui-table" data-testid={testid}>
	<table aria-label={label || undefined}>
		<thead>
			<tr>
				{#each columns as col (col.key)}
					<th scope="col">{col.label}</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each rows as row (row.id)}
				<tr
					onclick={() => onRowClick?.(row)}
					class:clickable={Boolean(onRowClick)}
					tabindex={onRowClick ? 0 : -1}
					onkeydown={(e) => {
						if (onRowClick && (e.key === 'Enter' || e.key === ' ')) {
							e.preventDefault();
							onRowClick(row);
						}
					}}
				>
					{#each columns as col (col.key)}
						<td>{col.render(row)}</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
	{#if pagination}
		<div class="pagination" data-testid="{testid}-pagination">
			<Button
				variant="secondary"
				disabled={pagination.page <= 1}
				onclick={() => pagination.onPageChange(pagination.page - 1)}
			>
				Prev
			</Button>
			<span>Page {pagination.page} of {pageCount}</span>
			<Button
				variant="secondary"
				disabled={pagination.page >= pageCount}
				onclick={() => pagination.onPageChange(pagination.page + 1)}
			>
				Next
			</Button>
		</div>
	{/if}
</div>

<style>
	.ui-table { display: flex; flex-direction: column; gap: var(--space-3); }
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--font-size-sm);
	}
	th {
		text-align: left;
		padding: var(--space-3) var(--space-4);
		font-weight: 600;
		color: var(--gray-600);
		border-bottom: 1px solid var(--gray-200);
		background-color: var(--gray-50);
	}
	td {
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--gray-100);
	}
	tr.clickable { cursor: pointer; }
	tr.clickable:hover { background-color: var(--gray-50); }
	tr.clickable:focus-visible { outline: 2px solid var(--brand-accent); outline-offset: -2px; }
	.pagination {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: var(--space-3);
		font-size: var(--font-size-sm);
		color: var(--gray-600);
	}
</style>
