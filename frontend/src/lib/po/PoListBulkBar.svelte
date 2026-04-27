<script lang="ts">
	import Button from '$lib/ui/Button.svelte';

	type BulkAction = 'submit' | 'accept' | 'reject' | 'resubmit';
	type BulkBannerTone = 'success' | 'partial' | 'error';

	let {
		selectedCount,
		totalMatching,
		validActions,
		crossPagePromotable,
		crossPageActive,
		bulkLoading,
		bulkBanner,
		onAction,
		onPromoteCrossPage,
		onClear,
		'data-testid': testid
	}: {
		selectedCount: number;
		totalMatching: number;
		validActions: string[];
		crossPagePromotable: boolean;
		crossPageActive: boolean;
		bulkLoading: boolean;
		bulkBanner: { tone: BulkBannerTone; text: string } | null;
		onAction: (action: string) => void;
		onPromoteCrossPage: () => void;
		onClear: () => void;
		'data-testid'?: string;
	} = $props();

	const ACTION_LABEL: Readonly<Record<BulkAction, string>> = {
		submit: 'Submit',
		accept: 'Accept',
		reject: 'Reject',
		resubmit: 'Resubmit'
	};

	function variantFor(action: string): 'primary' | 'secondary' {
		if (action === 'submit' || action === 'accept') return 'primary';
		return 'secondary';
	}
</script>

{#if selectedCount > 0}
	<div class="po-list-bulkbar" data-testid={testid ?? 'po-bulk-bar'}>
		{#if bulkBanner}
			<div
				class="po-list-bulkbar__banner po-list-bulkbar__banner--{bulkBanner.tone}"
				data-testid="po-bulk-banner"
			>
				{bulkBanner.text}
			</div>
		{/if}
		<div class="po-list-bulkbar__row">
			<span class="po-list-bulkbar__count">{selectedCount} selected</span>
			{#if crossPagePromotable && !crossPageActive}
				<button
					type="button"
					class="po-list-bulkbar__link"
					onclick={onPromoteCrossPage}
					data-testid="po-bulk-cross-page"
				>
					Select all {totalMatching} matching
				</button>
			{:else if crossPageActive}
				<span class="po-list-bulkbar__crosspage">
					All {totalMatching} matching selected.
					<button
						type="button"
						class="po-list-bulkbar__link"
						onclick={onClear}
						data-testid="po-bulk-cross-page-clear"
					>
						Clear
					</button>
				</span>
			{/if}
			<div class="po-list-bulkbar__actions">
				{#if validActions.length === 0}
					<span class="po-list-bulkbar__hint"
						>No common action across the selected POs.</span
					>
				{:else}
					{#if bulkLoading}
						<span class="po-list-bulkbar__spinner" aria-hidden="true"></span>
					{/if}
					{#each validActions as action (action)}
						<Button
							variant={variantFor(action)}
							disabled={bulkLoading}
							onclick={() => onAction(action)}
							data-testid="po-bulk-action-{action}"
						>
							<span class:po-list-bulkbar__reject-text={action === 'reject'}>
								{ACTION_LABEL[action as BulkAction] ?? action}
							</span>
						</Button>
					{/each}
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.po-list-bulkbar {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-3);
		background-color: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.po-list-bulkbar__row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3);
	}
	.po-list-bulkbar__count {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
	}
	.po-list-bulkbar__crosspage {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.po-list-bulkbar__link {
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		font-size: var(--font-size-sm);
		color: var(--blue-600);
		text-decoration: underline;
		cursor: pointer;
	}
	.po-list-bulkbar__link:hover {
		color: var(--blue-800);
	}
	.po-list-bulkbar__actions {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin-left: auto;
	}
	.po-list-bulkbar__hint {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		font-style: italic;
	}
	.po-list-bulkbar__reject-text {
		color: var(--red-600);
	}
	.po-list-bulkbar__spinner {
		width: 0.875rem;
		height: 0.875rem;
		border: 2px solid var(--gray-200);
		border-top-color: var(--brand-accent);
		border-radius: 999px;
		animation: po-list-bulkbar-spin 0.7s linear infinite;
	}
	@keyframes po-list-bulkbar-spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.po-list-bulkbar__spinner {
			animation: none;
		}
	}
	.po-list-bulkbar__banner {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		border-radius: var(--radius-sm);
	}
	.po-list-bulkbar__banner--success {
		background-color: var(--green-100);
		color: var(--green-700);
	}
	.po-list-bulkbar__banner--partial {
		background-color: var(--amber-100);
		color: var(--amber-700);
	}
	.po-list-bulkbar__banner--error {
		background-color: var(--red-100);
		color: var(--red-700);
	}
	@media (max-width: 767px) {
		.po-list-bulkbar {
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
		.po-list-bulkbar__actions {
			width: 100%;
			margin-left: 0;
			justify-content: flex-end;
		}
	}
</style>
