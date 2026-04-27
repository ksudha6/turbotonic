<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import type { CertWarning } from '$lib/types';

	const COLLAPSED_LIMIT = 5;

	let {
		warnings,
		dismissed = $bindable(false),
		'data-testid': testid
	}: {
		warnings: CertWarning[];
		dismissed?: boolean;
		'data-testid'?: string;
	} = $props();

	let expanded = $state(false);

	const visible = $derived(
		expanded ? warnings : warnings.slice(0, COLLAPSED_LIMIT)
	);
	const hidden = $derived(Math.max(0, warnings.length - COLLAPSED_LIMIT));
</script>

{#if warnings.length > 0 && !dismissed}
	<div class="po-cert-warnings" role="status" data-testid={testid ?? 'po-cert-warnings'}>
		<div class="po-cert-warnings__head">
			<strong class="po-cert-warnings__title">Quality warnings</strong>
			<Button
				variant="ghost"
				onclick={() => {
					dismissed = true;
				}}
				data-testid="po-cert-warnings-dismiss"
			>
				Dismiss
			</Button>
		</div>
		<ul class="po-cert-warnings__list">
			{#each visible as w (`${w.line_item_index}-${w.qualification_name}`)}
				<li>{w.part_number}: {w.qualification_name} ({w.reason})</li>
			{/each}
		</ul>
		{#if hidden > 0 && !expanded}
			<button
				type="button"
				class="po-cert-warnings__more"
				onclick={() => {
					expanded = true;
				}}
				data-testid="po-cert-warnings-more"
			>
				Show {hidden} more
			</button>
		{/if}
	</div>
{/if}

<style>
	.po-cert-warnings {
		background-color: var(--amber-100);
		color: var(--amber-700);
		border: 1px solid var(--amber-200, #fde68a);
		border-radius: var(--radius-md);
		padding: var(--space-3) var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.po-cert-warnings__head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
	}
	.po-cert-warnings__title {
		font-size: var(--font-size-sm);
		font-weight: 600;
	}
	.po-cert-warnings__list {
		margin: 0;
		padding-left: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		font-size: var(--font-size-sm);
	}
	.po-cert-warnings__more {
		align-self: flex-start;
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		font-size: var(--font-size-sm);
		color: var(--amber-700);
		text-decoration: underline;
		cursor: pointer;
	}
</style>
