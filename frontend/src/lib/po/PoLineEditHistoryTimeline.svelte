<script lang="ts">
	import type { LineItem } from '$lib/types';

	let {
		line,
		'data-testid': testid
	}: {
		line: LineItem;
		'data-testid'?: string;
	} = $props();

	const isConverged = $derived(line.status === 'ACCEPTED' || line.status === 'REMOVED');
	let expanded: boolean = $state(!isConverged);

	$effect(() => {
		expanded = !isConverged;
	});

	const entries = $derived(line.history ?? []);
	const roundCount = $derived(new Set(entries.map((e) => e.round)).size);

	function toggle(): void {
		expanded = !expanded;
	}

	function formatTs(iso: string): string {
		return new Date(iso).toLocaleString();
	}

	const summary = $derived(buildSummary());

	function buildSummary(): string {
		if (entries.length === 0) return 'No edits yet';
		if (isConverged) {
			const roundWord = roundCount === 1 ? 'round' : 'rounds';
			const editWord = entries.length === 1 ? 'edit' : 'edits';
			return `${entries.length} ${editWord} across ${roundCount} ${roundWord}`;
		}
		return `${entries.length} edit${entries.length === 1 ? '' : 's'}`;
	}
</script>

<div class="po-line-history" data-testid={testid ?? `po-line-history-${line.part_number}`}>
	<button
		type="button"
		class="po-line-history__toggle"
		aria-expanded={expanded}
		onclick={toggle}
		data-testid="po-line-history-toggle-{line.part_number}"
	>
		{expanded ? 'Hide edit history' : 'Show edit history'}
		<span class="po-line-history__count">({summary})</span>
	</button>

	{#if expanded && entries.length > 0}
		<ol class="po-line-history__list" data-testid="po-line-history-list-{line.part_number}">
			{#each entries as entry (entry.field + entry.edited_at)}
				<li class="po-line-history__entry">
					<span class="po-line-history__round">R{entry.round}</span>
					<span class="po-line-history__actor">{entry.actor_role}</span>
					<span class="po-line-history__field">{entry.field}</span>
					<span class="po-line-history__old">{entry.old_value}</span>
					<span class="po-line-history__arrow" aria-hidden="true">&rarr;</span>
					<span class="po-line-history__new">{entry.new_value}</span>
					<span class="po-line-history__time">{formatTs(entry.edited_at)}</span>
				</li>
			{/each}
		</ol>
	{/if}
</div>

<style>
	.po-line-history {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.po-line-history__toggle {
		align-self: flex-start;
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		font-size: var(--font-size-sm);
		color: var(--brand-accent);
		cursor: pointer;
		display: inline-flex;
		gap: var(--space-2);
		align-items: baseline;
	}
	.po-line-history__toggle:hover {
		text-decoration: underline;
	}
	.po-line-history__count {
		color: var(--gray-500);
		font-size: var(--font-size-xs);
	}
	.po-line-history__list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		font-size: var(--font-size-sm);
	}
	.po-line-history__entry {
		display: grid;
		grid-template-columns: auto auto minmax(6rem, max-content) 1fr auto 1fr auto;
		gap: var(--space-2);
		align-items: baseline;
		padding: var(--space-1) var(--space-2);
		background-color: var(--gray-50);
		border-radius: var(--radius-md);
	}
	.po-line-history__round {
		font-weight: 600;
		color: var(--gray-800);
		background-color: var(--gray-200);
		padding: 0 var(--space-2);
		border-radius: var(--radius-md);
	}
	.po-line-history__actor {
		color: var(--gray-600);
		font-size: var(--font-size-xs);
	}
	.po-line-history__field {
		font-weight: 500;
		color: var(--gray-700);
	}
	.po-line-history__old {
		color: var(--gray-500);
		text-decoration: line-through;
	}
	.po-line-history__arrow {
		color: var(--gray-500);
	}
	.po-line-history__new {
		color: var(--gray-900);
		font-weight: 500;
	}
	.po-line-history__time {
		color: var(--gray-400);
		font-size: var(--font-size-xs);
	}
	@media (max-width: 640px) {
		.po-line-history__entry {
			grid-template-columns: 1fr;
			gap: var(--space-1);
		}
		.po-line-history__arrow {
			display: none;
		}
	}
</style>
