<script lang="ts">
	type Entry = {
		id: string;
		primary: string;
		secondary?: string;
		tone: 'green' | 'blue' | 'orange' | 'red' | 'gray';
	};

	let {
		entries,
		label = 'Activity',
		'data-testid': testid
	}: { entries: Entry[]; label?: string; 'data-testid'?: string } = $props();
</script>

<ul class="ui-feed" aria-label={label} data-testid={testid}>
	{#each entries as e (e.id)}
		<li>
			<span class="dot {e.tone}" aria-hidden="true"></span>
			<div class="content">
				<span class="primary">{e.primary}</span>
				{#if e.secondary}<span class="secondary">{e.secondary}</span>{/if}
			</div>
		</li>
	{/each}
</ul>

<style>
	.ui-feed {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	li {
		display: grid;
		grid-template-columns: 0.5rem 1fr;
		gap: var(--space-3);
		align-items: start;
	}
	.dot {
		width: 0.375rem;
		height: 0.375rem;
		border-radius: 999px;
		margin-top: 0.5rem;
		background-color: var(--dot-gray);
	}
	.dot.green { background-color: var(--dot-green); }
	.dot.blue { background-color: var(--dot-blue); }
	.dot.orange { background-color: var(--dot-orange); }
	.dot.red { background-color: var(--dot-red); }
	.content { display: flex; flex-direction: column; gap: 2px; }
	.primary { font-size: var(--font-size-sm); color: var(--gray-900); }
	.secondary { font-size: var(--font-size-xs); color: var(--gray-500); }
</style>
