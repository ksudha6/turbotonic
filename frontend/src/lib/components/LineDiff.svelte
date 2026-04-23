<script lang="ts">
	import type { LineItem, LineEditEntry } from '$lib/types';

	let { line }: { line: LineItem } = $props();

	// Group history entries by round, latest round first. Each round contains one
	// row per changed field with its pre/post values.
	const rounds = $derived(groupByRound(line.history ?? []));

	function groupByRound(history: LineEditEntry[]): Array<{ round: number; entries: LineEditEntry[] }> {
		const map = new Map<number, LineEditEntry[]>();
		for (const entry of history) {
			const bucket = map.get(entry.round) ?? [];
			bucket.push(entry);
			map.set(entry.round, bucket);
		}
		const out: Array<{ round: number; entries: LineEditEntry[] }> = [];
		for (const [round, entries] of map.entries()) {
			out.push({ round, entries });
		}
		out.sort((a, b) => b.round - a.round);
		return out;
	}
</script>

<div class="line-diff" data-testid="line-diff">
	{#if rounds.length === 0}
		<p class="empty">No modifications yet.</p>
	{:else}
		{#each rounds as round (round.round)}
			<div class="round-block">
				<h4 class="round-title">Round {round.round}</h4>
				<table class="diff-table">
					<thead>
						<tr>
							<th>Field</th>
							<th>Before</th>
							<th>After</th>
							<th>By</th>
						</tr>
					</thead>
					<tbody>
						{#each round.entries as entry}
							<tr class="changed-row" data-field={entry.field}>
								<td class="field-name">{entry.field}</td>
								<td class="before">{entry.old_value}</td>
								<td class="after">{entry.new_value}</td>
								<td class="actor">{entry.actor_role}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/each}
	{/if}
</div>

<style>
	.line-diff {
		margin-top: var(--space-3);
	}

	.empty {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}

	.round-block {
		margin-bottom: var(--space-3);
	}

	.round-title {
		font-size: var(--font-size-sm);
		font-weight: 600;
		color: var(--gray-700);
		margin-bottom: var(--space-1);
	}

	.diff-table {
		width: 100%;
		font-size: var(--font-size-sm);
		border-collapse: collapse;
	}

	.diff-table th,
	.diff-table td {
		border: 1px solid var(--gray-200);
		padding: var(--space-1) var(--space-2);
		text-align: left;
	}

	.diff-table th {
		background-color: var(--gray-50);
		font-weight: 500;
	}

	.changed-row .before {
		background-color: #fee2e2;
		text-decoration: line-through;
		color: var(--gray-700);
	}

	.changed-row .after {
		background-color: #d1fae5;
		color: var(--gray-900);
	}

	.field-name {
		font-weight: 500;
	}
</style>
