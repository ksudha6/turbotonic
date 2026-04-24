<script lang="ts">
	let {
		title,
		subtitle,
		action,
		children,
		'data-testid': testid
	}: {
		title: string;
		subtitle?: string;
		action?: import('svelte').Snippet;
		children: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<section class="ui-panel" data-testid={testid}>
	<header>
		<div>
			<h3>{title}</h3>
			{#if subtitle}<p class="subtitle">{subtitle}</p>{/if}
		</div>
		{#if action}<div class="action">{@render action()}</div>{/if}
	</header>
	<div class="body">{@render children()}</div>
</section>

<style>
	.ui-panel {
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-4);
		margin-bottom: var(--space-4);
	}
	h3 {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.subtitle {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-top: var(--space-1);
	}
	.body { display: flex; flex-direction: column; gap: var(--space-3); }
</style>
