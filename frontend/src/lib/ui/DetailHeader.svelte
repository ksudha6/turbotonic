<script lang="ts">
	let {
		backHref,
		backLabel,
		title,
		subtitle,
		statusPill,
		'data-testid': testid
	}: {
		backHref: string;
		backLabel: string;
		title: string;
		subtitle?: string;
		statusPill?: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<header class="ui-detailheader" data-testid={testid}>
	<a href={backHref} class="back">← {backLabel}</a>
	<div class="row">
		<div>
			<h1>{title}</h1>
			{#if subtitle}<p>{subtitle}</p>{/if}
		</div>
		{#if statusPill}<div class="pill">{@render statusPill()}</div>{/if}
	</div>
</header>

<style>
	.ui-detailheader {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin-bottom: var(--space-6);
	}
	.back {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		text-decoration: none;
		width: max-content;
	}
	.back:hover { text-decoration: underline; color: var(--gray-700); }
	.row {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-4);
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
