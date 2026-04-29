<script lang="ts">
	type StepState = 'done' | 'current' | 'upcoming' | 'overdue';

	let {
		steps,
		label = 'Timeline',
		'data-testid': testid
	}: {
		steps: Array<{ label: string; state: StepState; detail?: string }>;
		label?: string;
		'data-testid'?: string;
	} = $props();
</script>

<ol class="ui-timeline" aria-label={label} data-testid={testid}>
	{#each steps as step (step.label)}
		<li class={step.state}>
			<span class="marker" aria-hidden="true"></span>
			<div class="content">
				<span class="label">{step.label}</span>
				{#if step.detail}<span class="detail">{step.detail}</span>{/if}
			</div>
		</li>
	{/each}
</ol>

<style>
	.ui-timeline {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	li {
		display: grid;
		grid-template-columns: 1rem 1fr;
		gap: var(--space-3);
		align-items: start;
		position: relative;
	}
	.marker {
		width: 0.75rem;
		height: 0.75rem;
		border-radius: 999px;
		background-color: var(--gray-300);
		margin-top: 0.25rem;
	}
	li.done .marker { background-color: var(--dot-green); }
	li.current .marker { background-color: var(--dot-blue); box-shadow: 0 0 0 3px #dbeafe; }
	li.upcoming .marker { background-color: var(--gray-200); }
	li.overdue .marker { background-color: var(--dot-red); }
	.content { display: flex; flex-direction: column; gap: 2px; }
	.label { font-size: var(--font-size-sm); font-weight: 500; color: var(--gray-900); }
	.detail { font-size: var(--font-size-xs); color: var(--gray-500); }
</style>
