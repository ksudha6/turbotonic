<script lang="ts">
	let {
		items,
		'data-testid': testid
	}: {
		items: Array<{ label: string; value: string }>;
		'data-testid'?: string;
	} = $props();
</script>

<dl class="ui-attr-list" data-testid={testid}>
	{#each items as item (item.label)}
		<div class="row">
			<dt>{item.label}</dt>
			<dd>{item.value}</dd>
		</div>
	{/each}
</dl>

<style>
	.ui-attr-list { display: flex; flex-direction: column; gap: var(--space-2); margin: 0; }
	.row {
		display: grid;
		grid-template-columns: minmax(8rem, 1fr) 2fr;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}
	.row:last-child { border-bottom: none; }
	dt { font-size: var(--font-size-sm); color: var(--gray-500); margin: 0; }
	dd { font-size: var(--font-size-sm); color: var(--gray-900); margin: 0; }
</style>
