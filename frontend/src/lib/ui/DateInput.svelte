<script lang="ts">
	let {
		value = $bindable(''),
		disabled = false,
		invalid = false,
		'data-testid': testid
	}: {
		value?: string;
		disabled?: boolean;
		invalid?: boolean;
		'data-testid'?: string;
	} = $props();
</script>

<input class="ui-date" type="date" bind:value {disabled} data-testid={testid} class:invalid />

<style>
	.ui-date {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		color: var(--gray-900);
	}
	.ui-date:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 0;
		border-color: var(--brand-accent);
	}
	.ui-date:disabled { opacity: 0.5; cursor: not-allowed; }
	.ui-date.invalid { border-color: var(--red-600); }
</style>
