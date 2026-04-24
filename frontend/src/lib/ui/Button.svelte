<script lang="ts">
	type Variant = 'primary' | 'secondary' | 'ghost';

	let {
		variant = 'primary',
		type = 'button',
		disabled = false,
		onclick,
		children,
		'data-testid': testid
	}: {
		variant?: Variant;
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		onclick?: (e: MouseEvent) => void;
		children: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();
</script>

<button {type} {disabled} {onclick} data-testid={testid} class="btn {variant}">
	{@render children()}
</button>

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		font-size: var(--font-size-sm);
		font-weight: 500;
		border-radius: var(--radius-md);
		border: 1px solid transparent;
		cursor: pointer;
		font-family: var(--font-family);
		transition: opacity 0.15s, background-color 0.15s, border-color 0.15s;
	}
	.btn:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 2px;
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.primary {
		background-color: var(--button-solid-bg);
		color: var(--button-solid-fg);
	}
	.primary:hover:not(:disabled) {
		opacity: 0.9;
	}
	.secondary {
		background-color: var(--surface-card);
		color: var(--gray-900);
		border-color: var(--gray-300);
	}
	.secondary:hover:not(:disabled) {
		background-color: var(--gray-50);
	}
	.ghost {
		background: transparent;
		color: var(--gray-700);
	}
	.ghost:hover:not(:disabled) {
		background-color: var(--gray-100);
	}
</style>
