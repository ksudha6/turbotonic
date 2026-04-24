<script lang="ts">
	import Button from './Button.svelte';
	let {
		message,
		onRetry,
		'data-testid': testid
	}: { message: string; onRetry?: () => void; 'data-testid'?: string } = $props();
</script>

<div class="ui-error" role="alert" data-testid={testid}>
	<p>{message}</p>
	{#if onRetry}
		<Button variant="secondary" onclick={onRetry} data-testid="{testid}-retry">Retry</Button>
	{/if}
</div>

<style>
	.ui-error {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-8);
		border-radius: var(--radius-md);
		background-color: #fef2f2;
		color: var(--red-700);
	}
	p { font-size: var(--font-size-sm); margin: 0; }
</style>
