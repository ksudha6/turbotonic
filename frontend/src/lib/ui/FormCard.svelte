<script lang="ts">
	import Button from './Button.svelte';
	let {
		title,
		subtitle,
		onCancel,
		onSubmit,
		submitLabel = 'Save',
		cancelLabel = 'Cancel',
		submitDisabled = false,
		children,
		'data-testid': testid
	}: {
		title: string;
		subtitle?: string;
		onCancel?: () => void;
		onSubmit: () => void;
		submitLabel?: string;
		cancelLabel?: string;
		submitDisabled?: boolean;
		children: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		onSubmit();
	}
</script>

<form class="ui-form-card" onsubmit={handleSubmit} data-testid={testid}>
	<header>
		<h3>{title}</h3>
		{#if subtitle}<p class="subtitle">{subtitle}</p>{/if}
	</header>
	<div class="body">{@render children()}</div>
	<footer>
		{#if onCancel}
			<Button variant="secondary" onclick={onCancel} data-testid="{testid}-cancel">{cancelLabel}</Button>
		{/if}
		<Button type="submit" disabled={submitDisabled} data-testid="{testid}-submit">{submitLabel}</Button>
	</footer>
</form>

<style>
	.ui-form-card {
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	h3 { font-size: var(--font-size-lg); font-weight: 600; margin: 0; }
	.subtitle { font-size: var(--font-size-sm); color: var(--gray-500); margin-top: var(--space-1); }
	footer { display: flex; justify-content: flex-end; gap: var(--space-3); }
</style>
