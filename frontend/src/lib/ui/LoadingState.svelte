<script lang="ts">
	let { label = 'Loading', 'data-testid': testid }: { label?: string; 'data-testid'?: string } = $props();
</script>

<div class="ui-loading" role="status" aria-live="polite" data-testid={testid}>
	<span class="spinner" aria-hidden="true"></span>
	<span class="sr">{label}</span>
</div>

<style>
	.ui-loading {
		display: flex;
		justify-content: center;
		align-items: center;
		padding: var(--space-8);
	}
	.spinner {
		width: 1.25rem;
		height: 1.25rem;
		border: 2px solid var(--gray-200);
		border-top-color: var(--brand-accent);
		border-radius: 999px;
		animation: spin 0.7s linear infinite;
	}
	.sr {
		position: absolute;
		clip: rect(0 0 0 0);
		width: 1px;
		height: 1px;
		overflow: hidden;
	}
	@keyframes spin { to { transform: rotate(360deg); } }
	@media (prefers-reduced-motion: reduce) {
		.spinner { animation: none; }
	}
</style>
