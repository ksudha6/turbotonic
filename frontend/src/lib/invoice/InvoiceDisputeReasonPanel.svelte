<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';

	let {
		reason
	}: {
		reason: string;
	} = $props();
</script>

<PanelCard title="Dispute Reason" data-testid="invoice-dispute-reason-panel">
	{#snippet children()}
		<p class="invoice-dispute-reason-panel__body">{reason}</p>
	{/snippet}
</PanelCard>

<style>
	.invoice-dispute-reason-panel__body {
		margin: 0;
		font-size: var(--font-size-sm);
		color: var(--gray-800);
		white-space: pre-wrap;
	}
</style>
