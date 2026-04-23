<script lang="ts">
	import type { LineItem } from '$lib/types';

	let { line }: { line: LineItem } = $props();

	// Converged = line has reached a terminal status (ACCEPTED or REMOVED).
	// Converged lines default to collapsed; in-flight lines default to expanded.
	const isConverged = $derived(line.status === 'ACCEPTED' || line.status === 'REMOVED');
	let expanded: boolean = $state(!isConverged);

	// When the line transitions between converged and in-flight, realign the
	// default. Do not overwrite an explicit user toggle in the opposite direction.
	$effect(() => {
		expanded = !isConverged;
	});

	const entries = $derived(line.history ?? []);
	const roundCount = $derived(new Set(entries.map((e) => e.round)).size);

	function toggle() {
		expanded = !expanded;
	}

	function formatTs(iso: string): string {
		return new Date(iso).toLocaleString();
	}
</script>

<div class="edit-history" data-testid="edit-history-timeline">
	<button
		type="button"
		class="history-toggle"
		onclick={toggle}
		data-testid="edit-history-toggle"
		data-expanded={expanded ? 'true' : 'false'}
	>
		{#if expanded}
			Hide edit history
		{:else if isConverged && entries.length > 0}
			Modified {entries.length} time{entries.length === 1 ? '' : 's'} across {roundCount} round{roundCount === 1 ? '' : 's'}, final values above
		{:else if entries.length > 0}
			Show edit history ({entries.length})
		{:else}
			No edits yet
		{/if}
	</button>

	{#if expanded && entries.length > 0}
		<ol class="history-list" data-testid="edit-history-list">
			{#each entries as entry}
				<li class="history-entry">
					<span class="entry-round">R{entry.round}</span>
					<span class="entry-actor">{entry.actor_role}</span>
					<span class="entry-field">{entry.field}</span>:
					<span class="entry-old">{entry.old_value}</span>
					<span class="entry-arrow">→</span>
					<span class="entry-new">{entry.new_value}</span>
					<span class="entry-time">{formatTs(entry.edited_at)}</span>
				</li>
			{/each}
		</ol>
	{/if}
</div>

<style>
	.edit-history {
		margin-top: var(--space-2);
	}

	.history-toggle {
		background: none;
		border: none;
		color: var(--blue-700, #1d4ed8);
		cursor: pointer;
		font-size: var(--font-size-sm);
		padding: var(--space-1) 0;
	}

	.history-toggle:hover {
		text-decoration: underline;
	}

	.history-list {
		margin: var(--space-2) 0 0;
		padding-left: var(--space-4);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}

	.history-entry {
		margin-bottom: var(--space-1);
	}

	.entry-round {
		display: inline-block;
		background-color: var(--gray-200);
		color: var(--gray-800);
		border-radius: var(--radius);
		padding: 0 6px;
		font-weight: 600;
		margin-right: var(--space-1);
	}

	.entry-actor {
		color: var(--gray-600);
		margin-right: var(--space-1);
	}

	.entry-field {
		font-weight: 500;
	}

	.entry-old {
		text-decoration: line-through;
		color: var(--gray-500);
	}

	.entry-arrow {
		margin: 0 4px;
	}

	.entry-new {
		color: var(--gray-900);
		font-weight: 500;
	}

	.entry-time {
		margin-left: var(--space-2);
		color: var(--gray-400);
		font-size: 11px;
	}
</style>
