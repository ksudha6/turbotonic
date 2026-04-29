<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import AttributeList from '$lib/ui/AttributeList.svelte';
	import type { Shipment } from '$lib/types';

	let { shipment }: { shipment: Shipment } = $props();

	function formatDate(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	const items = $derived([
		{ label: 'Marketplace', value: shipment.marketplace },
		{ label: 'Created', value: formatDate(shipment.created_at) },
		{ label: 'Updated', value: formatDate(shipment.updated_at) }
	]);
</script>

<PanelCard title="Shipment" data-testid="shipment-meta-panel">
	{#snippet children()}
		<AttributeList {items} />
	{/snippet}
</PanelCard>
