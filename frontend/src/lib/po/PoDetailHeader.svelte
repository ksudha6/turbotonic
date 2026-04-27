<script lang="ts">
	import DetailHeader from '$lib/ui/DetailHeader.svelte';
	import PoStatusPills from '$lib/po/PoStatusPills.svelte';
	import type { PurchaseOrder } from '$lib/types';
	import type { Snippet } from 'svelte';

	let {
		po,
		actionRail,
		'data-testid': testid
	}: {
		po: PurchaseOrder;
		actionRail?: Snippet;
		'data-testid'?: string;
	} = $props();

	function formatIssued(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	const subtitle = $derived(`${po.vendor_name} · Issued ${formatIssued(po.issued_date)}`);
	const partial = $derived(po.status === 'ACCEPTED' && !!po.has_removed_line);
</script>

<div class="po-detail-header" data-testid={testid ?? 'po-detail-header'}>
	<div class="po-detail-header__main">
		<DetailHeader
			backHref="/po"
			backLabel="Purchase Orders"
			title={po.po_number}
			{subtitle}
		>
			{#snippet statusPill()}
				<PoStatusPills status={po.status} {partial} />
			{/snippet}
		</DetailHeader>
	</div>
	{#if actionRail}
		<div class="po-detail-header__rail">{@render actionRail()}</div>
	{/if}
</div>

<style>
	.po-detail-header {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.po-detail-header__main {
		flex: 1 1 auto;
		min-width: 0;
	}
	.po-detail-header__rail {
		display: none;
	}
	@media (min-width: 768px) {
		.po-detail-header {
			flex-direction: row;
			align-items: flex-start;
			justify-content: space-between;
			gap: var(--space-4);
		}
		.po-detail-header__rail {
			display: flex;
			align-items: center;
			margin-top: var(--space-6);
		}
	}
</style>
