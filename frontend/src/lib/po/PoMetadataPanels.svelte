<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import AttributeList from '$lib/ui/AttributeList.svelte';
	import type { PurchaseOrder } from '$lib/types';

	let {
		po,
		resolve,
		formatDate,
		formatValue
	}: {
		po: PurchaseOrder;
		resolve: (kind: string, code: string) => string;
		formatDate: (s: string) => string;
		formatValue: (n: string, code: string) => string;
	} = $props();

	const tradeSummaryItems = $derived.by(() => {
		const items: Array<{ label: string; value: string }> = [
			{ label: 'Currency', value: resolve('currencies', po.currency) },
			{ label: 'Issued Date', value: formatDate(po.issued_date) },
			{ label: 'Delivery Date', value: formatDate(po.required_delivery_date) },
			{ label: 'Total Value', value: formatValue(po.total_value, po.currency) },
			{ label: 'Payment Terms', value: resolve('payment_terms', po.payment_terms) }
		];
		if (po.marketplace) {
			items.push({ label: 'Marketplace', value: po.marketplace });
		}
		return items;
	});

	const buyerItems = $derived([
		{ label: 'Name', value: po.buyer_name },
		{ label: 'Country', value: resolve('countries', po.buyer_country) }
	]);

	const vendorItems = $derived([
		{ label: 'Name', value: po.vendor_name },
		{ label: 'Country', value: resolve('countries', po.vendor_country) }
	]);

	const tradeDetailsItems = $derived([
		{ label: 'Incoterm', value: resolve('incoterms', po.incoterm) },
		{ label: 'Port of Loading', value: resolve('ports', po.port_of_loading) },
		{ label: 'Port of Discharge', value: resolve('ports', po.port_of_discharge) },
		{ label: 'Country of Origin', value: resolve('countries', po.country_of_origin) },
		{ label: 'Country of Destination', value: resolve('countries', po.country_of_destination) }
	]);
</script>

<PanelCard title="Trade Summary" data-testid="po-metadata-trade-summary">
	{#snippet children()}
		<AttributeList items={tradeSummaryItems} />
	{/snippet}
</PanelCard>

<PanelCard title="Buyer" data-testid="po-metadata-buyer">
	{#snippet children()}
		<AttributeList items={buyerItems} />
	{/snippet}
</PanelCard>

<PanelCard title="Vendor" data-testid="po-metadata-vendor">
	{#snippet children()}
		<AttributeList items={vendorItems} />
	{/snippet}
</PanelCard>

<PanelCard title="Trade Details" data-testid="po-metadata-trade-details">
	{#snippet children()}
		<AttributeList items={tradeDetailsItems} />
	{/snippet}
</PanelCard>

<PanelCard title="Terms &amp; Conditions" data-testid="po-metadata-terms">
	{#snippet children()}
		<p style="white-space: pre-wrap">{po.terms_and_conditions}</p>
	{/snippet}
</PanelCard>
