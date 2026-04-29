<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';

	let {
		records,
		formatDate
	}: {
		records: { comment: string; rejected_at: string }[];
		formatDate: (s: string) => string;
	} = $props();

	// Caller provides records in chronological order; render latest-first.
	const reversedRecords = $derived([...records].reverse());
</script>

<PanelCard title="Rejection History" data-testid="po-rejection-history-panel">
	{#snippet children()}
		{#each reversedRecords as record, i}
			<article data-testid="po-rejection-record-{i}" class="rejection-record">
				<p class="rejection-comment">{record.comment}</p>
				<p class="rejection-date">{formatDate(record.rejected_at)}</p>
			</article>
		{/each}
	{/snippet}
</PanelCard>

<style>
	.rejection-record {
		padding: var(--space-3) 0;
		border-bottom: 1px solid var(--gray-100);
	}
	.rejection-record:last-child {
		border-bottom: none;
	}
	.rejection-comment {
		color: var(--gray-800);
		margin-bottom: var(--space-1);
	}
	.rejection-date {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}
</style>
