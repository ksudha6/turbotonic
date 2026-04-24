<script lang="ts">
	let {
		value = $bindable(''),
		type = 'text',
		placeholder,
		disabled = false,
		invalid = false,
		'data-testid': testid
	}: {
		value?: string;
		type?: string;
		placeholder?: string;
		disabled?: boolean;
		invalid?: boolean;
		'data-testid'?: string;
	} = $props();
</script>

<input
	class="ui-input"
	{type}
	{placeholder}
	{disabled}
	aria-invalid={invalid || undefined}
	bind:value
	data-testid={testid}
	class:invalid
/>

<style>
	.ui-input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		color: var(--gray-900);
	}
	.ui-input:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 0;
		border-color: var(--brand-accent);
	}
	.ui-input:disabled { opacity: 0.5; cursor: not-allowed; }
	.ui-input.invalid { border-color: var(--red-600); }
</style>
