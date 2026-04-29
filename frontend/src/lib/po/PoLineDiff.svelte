<script lang="ts">
	import type { LineItem, LineEditEntry } from '$lib/types';

	let {
		line,
		'data-testid': testid
	}: {
		line: LineItem;
		'data-testid'?: string;
	} = $props();

	type RoundBlock = { round: number; entries: ReadonlyArray<LineEditEntry> };

	function groupByRound(history: ReadonlyArray<LineEditEntry>): ReadonlyArray<RoundBlock> {
		const map = new Map<number, LineEditEntry[]>();
		for (const entry of history) {
			const bucket = map.get(entry.round) ?? [];
			bucket.push(entry);
			map.set(entry.round, bucket);
		}
		const out: RoundBlock[] = [];
		for (const [round, entries] of map.entries()) {
			out.push({ round, entries });
		}
		out.sort((a, b) => b.round - a.round);
		return out;
	}

	const rounds = $derived(groupByRound(line.history ?? []));
</script>

<div class="po-line-diff" data-testid={testid ?? `po-line-diff-${line.part_number}`}>
	{#if rounds.length === 0}
		<p class="po-line-diff__empty">No modifications yet.</p>
	{:else}
		{#each rounds as block (block.round)}
			<div class="po-line-diff__round">
				<h4 class="po-line-diff__round-title">Round {block.round}</h4>
				<ul class="po-line-diff__list">
					{#each block.entries as entry (entry.field + entry.edited_at)}
						<li class="po-line-diff__row" data-field={entry.field}>
							<span class="po-line-diff__field">{entry.field}</span>
							<span class="po-line-diff__before">{entry.old_value}</span>
							<span class="po-line-diff__arrow" aria-hidden="true">&rarr;</span>
							<span class="po-line-diff__after">{entry.new_value}</span>
							<span class="po-line-diff__actor">by {entry.actor_role}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/each}
	{/if}
</div>

<style>
	.po-line-diff {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.po-line-diff__empty {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
	.po-line-diff__round {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.po-line-diff__round-title {
		font-size: var(--font-size-xs);
		font-weight: 600;
		color: var(--gray-700);
		letter-spacing: var(--letter-spacing-wide);
		text-transform: uppercase;
		margin: 0;
	}
	.po-line-diff__list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.po-line-diff__row {
		display: grid;
		grid-template-columns: minmax(7rem, max-content) 1fr auto 1fr auto;
		gap: var(--space-2);
		align-items: baseline;
		font-size: var(--font-size-sm);
		padding: var(--space-1) var(--space-2);
		background-color: var(--gray-50);
		border-radius: var(--radius-md);
	}
	.po-line-diff__field {
		font-weight: 500;
		color: var(--gray-700);
	}
	.po-line-diff__before {
		color: var(--gray-600);
		text-decoration: line-through;
	}
	.po-line-diff__arrow {
		color: var(--gray-500);
	}
	.po-line-diff__after {
		color: var(--gray-900);
		font-weight: 500;
	}
	.po-line-diff__actor {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
	}
	@media (max-width: 640px) {
		.po-line-diff__row {
			grid-template-columns: 1fr;
			gap: var(--space-1);
		}
		.po-line-diff__arrow {
			display: none;
		}
	}
</style>
