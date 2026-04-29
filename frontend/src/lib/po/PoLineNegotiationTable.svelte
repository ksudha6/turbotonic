<script lang="ts">
	import type { LineItem } from '$lib/types';
	import type { ModifyLineFields } from '$lib/api';
	import PoLineNegotiationRow from './PoLineNegotiationRow.svelte';

	type NegotiationRole = 'VENDOR' | 'SM';

	let {
		lines,
		role,
		round_count,
		errors = new Map(),
		on_modify,
		on_accept,
		on_remove,
		on_force_accept,
		on_force_remove,
		label = 'Line items under negotiation',
		'data-testid': testid
	}: {
		lines: LineItem[];
		role: NegotiationRole;
		round_count: number;
		errors?: Map<string, string>;
		on_modify: (partNumber: string, fields: ModifyLineFields) => void;
		on_accept: (partNumber: string) => void;
		on_remove: (partNumber: string) => void;
		on_force_accept: (partNumber: string) => void;
		on_force_remove: (partNumber: string) => void;
		label?: string;
		'data-testid'?: string;
	} = $props();
</script>

<section
	class="po-line-table"
	aria-label={label}
	data-testid={testid ?? 'po-line-negotiation-table'}
>
	{#each lines as line (line.part_number)}
		<PoLineNegotiationRow
			{line}
			{role}
			{round_count}
			error={errors.get(line.part_number)}
			{on_modify}
			{on_accept}
			{on_remove}
			{on_force_accept}
			{on_force_remove}
		/>
	{/each}
</section>

<style>
	.po-line-table {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
</style>
