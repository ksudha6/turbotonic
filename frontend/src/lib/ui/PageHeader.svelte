<script lang="ts">
	let {
		title,
		subtitle,
		action,
		'data-testid': testid
	}: {
		title: string;
		subtitle?: string;
		action?: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();

	const titleId = crypto.randomUUID();
</script>

<header class="ui-pageheader" role="banner" aria-labelledby={titleId} data-testid={testid}>
	<div>
		<h1 id={titleId}>{title}</h1>
		{#if subtitle}<p>{subtitle}</p>{/if}
	</div>
	{#if action}<div class="action">{@render action()}</div>{/if}
</header>

<style>
	.ui-pageheader {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-4);
		margin-bottom: var(--space-6);
	}
	h1 {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		margin: 0;
	}
	p {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-top: var(--space-1);
	}
</style>
