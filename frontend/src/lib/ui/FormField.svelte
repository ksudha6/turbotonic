<script lang="ts">
	let {
		label,
		error,
		required = false,
		hint,
		'data-testid': testid,
		children
	}: {
		label: string;
		error?: string | null;
		required?: boolean;
		hint?: string;
		'data-testid'?: string;
		children: import('svelte').Snippet<[{ invalid: boolean; 'aria-invalid': boolean }]>;
	} = $props();

	const hasError = $derived(error != null && error.length > 0);
</script>

<div class="ui-field" data-testid={testid}>
	<label>
		<span class="label">
			{label}
			{#if required}<span class="req" aria-hidden="true">*</span>{/if}
		</span>
		{@render children({ invalid: hasError, 'aria-invalid': hasError })}
	</label>
	{#if hasError}
		<span class="error" role="alert" data-testid="{testid}-error">{error}</span>
	{:else if hint}
		<span class="hint">{hint}</span>
	{/if}
</div>

<style>
	.ui-field {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		margin-bottom: var(--space-4);
	}
	.label {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
	}
	.req { color: var(--red-600); margin-left: 2px; }
	.error {
		font-size: var(--font-size-xs);
		color: var(--red-700);
	}
	.hint {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
	}
</style>
