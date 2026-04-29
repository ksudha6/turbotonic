<script lang="ts">
	import Select from '$lib/ui/Select.svelte';
	import Button from '$lib/ui/Button.svelte';

	let {
		page = $bindable(1),
		pageSize = $bindable(20),
		total,
		'data-testid': testid
	}: {
		page?: number;
		pageSize?: number;
		total: number;
		'data-testid'?: string;
	} = $props();

	const PAGE_SIZE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: '10', label: '10 / page' },
		{ value: '20', label: '20 / page' },
		{ value: '50', label: '50 / page' }
	];

	let pageSizeStr = $state(String(pageSize));
	$effect(() => {
		pageSizeStr = String(pageSize);
	});
	$effect(() => {
		const next = parseInt(pageSizeStr, 10);
		if (!Number.isNaN(next) && next !== pageSize) {
			pageSize = next;
			page = 1;
		}
	});

	const totalPages = $derived(Math.max(1, Math.ceil(total / pageSize)));
	const startItem = $derived((page - 1) * pageSize + 1);
	const endItem = $derived(Math.min(page * pageSize, total));

	function prev() {
		if (page > 1) page = page - 1;
	}
	function next() {
		if (page < totalPages) page = page + 1;
	}
</script>

{#if total > 0}
	<div class="invoice-list-pagination" data-testid={testid ?? 'invoice-pagination'}>
		<span class="invoice-list-pagination__info"
			>Showing {startItem}-{endItem} of {total}</span
		>
		<div class="invoice-list-pagination__size">
			<Select
				bind:value={pageSizeStr}
				options={[...PAGE_SIZE_OPTIONS]}
				ariaLabel="Page size"
				data-testid="invoice-pagination-size"
			/>
		</div>
		<div class="invoice-list-pagination__nav">
			<Button
				variant="secondary"
				disabled={page <= 1}
				onclick={prev}
				data-testid="invoice-pagination-prev"
			>
				<span class="invoice-list-pagination__label-full">Prev</span>
				<span class="invoice-list-pagination__label-icon" aria-hidden="true">&lt;</span>
			</Button>
			<Button
				variant="secondary"
				disabled={page >= totalPages}
				onclick={next}
				data-testid="invoice-pagination-next"
			>
				<span class="invoice-list-pagination__label-full">Next</span>
				<span class="invoice-list-pagination__label-icon" aria-hidden="true">&gt;</span>
			</Button>
		</div>
	</div>
{/if}

<style>
	.invoice-list-pagination {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3);
		margin-top: var(--space-4);
		font-size: var(--font-size-sm);
		color: var(--gray-600);
	}
	.invoice-list-pagination__info {
		flex: 1 1 auto;
	}
	.invoice-list-pagination__size {
		flex: 0 0 auto;
		min-width: 8rem;
	}
	.invoice-list-pagination__nav {
		display: flex;
		gap: var(--space-2);
	}
	.invoice-list-pagination__label-icon {
		display: none;
	}
	@media (max-width: 480px) {
		.invoice-list-pagination__label-full {
			display: none;
		}
		.invoice-list-pagination__label-icon {
			display: inline;
		}
	}
</style>
