<script lang="ts">
	import DetailHeader from '$lib/ui/DetailHeader.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import type { Shipment, ShipmentStatus } from '$lib/types';
	import type { Snippet } from 'svelte';

	let {
		shipment,
		actionRail,
		'data-testid': testid
	}: {
		shipment: Shipment;
		actionRail?: Snippet;
		'data-testid'?: string;
	} = $props();

	type Tone = 'green' | 'blue' | 'orange' | 'red' | 'gray';

	const STATUS_TONE: Readonly<Record<ShipmentStatus, Tone>> = {
		DRAFT: 'gray',
		DOCUMENTS_PENDING: 'orange',
		READY_TO_SHIP: 'blue',
		BOOKED: 'blue',
		SHIPPED: 'green'
	};

	function statusLabel(status: ShipmentStatus): string {
		return status
			.split('_')
			.map((part) => part.charAt(0) + part.slice(1).toLowerCase())
			.join(' ');
	}

	function formatDate(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	const subtitle = $derived(
		`${shipment.marketplace} · Created ${formatDate(shipment.created_at)}`
	);
</script>

<div class="shipment-detail-header" data-testid={testid ?? 'shipment-detail-header'}>
	<div class="shipment-detail-header__main">
		<DetailHeader
			backHref="/po"
			backLabel="Purchase Orders"
			title={shipment.shipment_number}
			{subtitle}
		>
			{#snippet statusPill()}
				<StatusPill
					tone={STATUS_TONE[shipment.status]}
					label={statusLabel(shipment.status)}
					data-testid="shipment-detail-status"
				/>
			{/snippet}
		</DetailHeader>
	</div>
	{#if actionRail}
		<div class="shipment-detail-header__rail">{@render actionRail()}</div>
	{/if}
</div>

<style>
	.shipment-detail-header {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.shipment-detail-header__main {
		flex: 1 1 auto;
		min-width: 0;
	}
	.shipment-detail-header__rail {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}
	@media (min-width: 768px) {
		.shipment-detail-header {
			flex-direction: row;
			align-items: flex-start;
			justify-content: space-between;
			gap: var(--space-4);
		}
		.shipment-detail-header__rail {
			margin-top: var(--space-6);
		}
	}
</style>
