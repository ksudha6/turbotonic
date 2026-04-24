<script lang="ts">
	let {
		title,
		description,
		action,
		'data-testid': testid
	}: {
		title: string;
		description?: string;
		action?: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<div class="ui-empty" data-testid={testid}>
	<h3>{title}</h3>
	{#if description}<p>{description}</p>{/if}
	{#if action}<div class="action">{@render action()}</div>{/if}
</div>

<style>
	.ui-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: var(--space-3);
		padding: var(--space-12) var(--space-4);
		color: var(--gray-600);
	}
	h3 { font-size: var(--font-size-lg); font-weight: 600; color: var(--gray-900); margin: 0; }
	p { font-size: var(--font-size-sm); margin: 0; }
</style>
