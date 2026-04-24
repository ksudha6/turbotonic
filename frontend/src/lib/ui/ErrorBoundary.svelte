<script lang="ts">
	import ErrorState from './ErrorState.svelte';
	let { children }: { children: import('svelte').Snippet } = $props();
</script>

<svelte:boundary>
	{@render children()}
	{#snippet failed(_error, reset)}
		<ErrorState
			message={'Something went wrong. Please refresh or try again.'}
			onRetry={reset}
			data-testid="app-error-boundary"
		/>
	{/snippet}
</svelte:boundary>
