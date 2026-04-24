<script lang="ts">
	let {
		value,
		label,
		'data-testid': testid
	}: { value: number; label?: string; 'data-testid'?: string } = $props();
	const clamped = $derived(Math.max(0, Math.min(100, value)));
</script>

<div class="ui-progress">
	<div
		class="track"
		role="progressbar"
		aria-valuenow={clamped}
		aria-valuemin="0"
		aria-valuemax="100"
		aria-label={label ?? 'Progress'}
		data-testid={testid}
	>
		<div class="fill" style="width: {clamped}%"></div>
	</div>
	{#if label}<span class="label">{label}</span>{/if}
</div>

<style>
	.ui-progress { display: flex; align-items: center; gap: var(--space-3); }
	.track {
		position: relative;
		flex: 1;
		height: 6px;
		border-radius: 999px;
		background-color: var(--gray-200);
		overflow: hidden;
	}
	.fill {
		height: 100%;
		background-color: var(--button-solid-bg);
		transition: width 0.2s ease;
	}
	.label { font-size: var(--font-size-sm); color: var(--gray-600); min-width: 3ch; text-align: right; }
</style>
