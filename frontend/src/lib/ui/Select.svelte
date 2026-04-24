<script lang="ts">
	let {
		value = $bindable(''),
		options,
		disabled = false,
		invalid = false,
		'data-testid': testid
	}: {
		value?: string;
		options: Array<{ value: string; label: string }>;
		disabled?: boolean;
		invalid?: boolean;
		'data-testid'?: string;
	} = $props();
</script>

<select class="ui-select" bind:value {disabled} data-testid={testid} class:invalid>
	{#each options as opt (opt.value)}
		<option value={opt.value}>{opt.label}</option>
	{/each}
</select>

<style>
	.ui-select {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		color: var(--gray-900);
	}
	.ui-select:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 0;
		border-color: var(--brand-accent);
	}
	.ui-select:disabled { opacity: 0.5; cursor: not-allowed; }
	.ui-select.invalid { border-color: var(--red-600); }
</style>
