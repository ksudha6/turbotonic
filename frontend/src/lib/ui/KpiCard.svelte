<script lang="ts">
	type Delta = { value: string; tone: 'positive' | 'negative' | 'neutral' };

	let {
		label,
		value,
		delta,
		'data-testid': testid
	}: {
		label: string;
		value: string;
		delta?: Delta;
		'data-testid'?: string;
	} = $props();
</script>

<div class="ui-kpi" data-testid={testid}>
	<span class="label">{label}</span>
	<span class="value">{value}</span>
	{#if delta}
		<span class="delta {delta.tone}">{delta.value}</span>
	{/if}
</div>

<style>
	.ui-kpi {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-6);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
	}
	.label {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
		text-transform: uppercase;
		letter-spacing: var(--letter-spacing-wide);
		font-weight: 600;
	}
	.value {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		color: var(--gray-900);
	}
	.delta {
		align-self: flex-start;
		font-size: var(--font-size-xs);
		font-weight: 500;
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
	}
	.positive { background-color: #dcfce7; color: #166534; }
	.negative { background-color: #fee2e2; color: #991b1b; }
	.neutral { background-color: var(--gray-100); color: var(--gray-700); }
</style>
