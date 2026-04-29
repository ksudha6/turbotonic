<script lang="ts">
	import Button from '$lib/ui/Button.svelte';

	let {
		selectedCount,
		loading = false,
		onDownload,
		onClear,
		'data-testid': testid
	}: {
		selectedCount: number;
		loading?: boolean;
		onDownload: () => void;
		onClear: () => void;
		'data-testid'?: string;
	} = $props();
</script>

{#if selectedCount > 0}
	<div class="invoice-list-bulkbar" data-testid={testid ?? 'invoice-bulk-bar'}>
		<span class="invoice-list-bulkbar__count">{selectedCount} selected</span>
		<div class="invoice-list-bulkbar__actions">
			{#if loading}
				<span class="invoice-list-bulkbar__spinner" aria-hidden="true"></span>
			{/if}
			<Button
				variant="primary"
				disabled={loading}
				onclick={onDownload}
				data-testid="invoice-bulk-action-download"
			>
				Download PDFs
			</Button>
			<button
				type="button"
				class="invoice-list-bulkbar__link"
				onclick={onClear}
				data-testid="invoice-bulk-clear"
			>
				Clear
			</button>
		</div>
	</div>
{/if}

<style>
	.invoice-list-bulkbar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.invoice-list-bulkbar__count {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
	}
	.invoice-list-bulkbar__actions {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin-left: auto;
	}
	.invoice-list-bulkbar__link {
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		font-size: var(--font-size-sm);
		color: var(--blue-600);
		text-decoration: underline;
		cursor: pointer;
	}
	.invoice-list-bulkbar__link:hover {
		color: var(--blue-800);
	}
	.invoice-list-bulkbar__spinner {
		width: 0.875rem;
		height: 0.875rem;
		border: 2px solid var(--gray-200);
		border-top-color: var(--brand-accent);
		border-radius: 999px;
		animation: invoice-list-bulkbar-spin 0.7s linear infinite;
	}
	@keyframes invoice-list-bulkbar-spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.invoice-list-bulkbar__spinner {
			animation: none;
		}
	}
	@media (max-width: 767px) {
		.invoice-list-bulkbar {
			position: sticky;
			bottom: 0;
			z-index: 5;
			border-radius: 0;
			border-left: none;
			border-right: none;
			border-bottom: none;
			margin-inline: calc(-1 * var(--space-4));
			box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
		}
		.invoice-list-bulkbar__actions {
			width: 100%;
			margin-left: 0;
			justify-content: flex-end;
		}
	}
</style>
