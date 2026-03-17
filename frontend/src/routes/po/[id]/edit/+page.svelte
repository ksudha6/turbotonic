<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getPO, updatePO } from '$lib/api';
	import POForm from '$lib/components/POForm.svelte';
	import type { PurchaseOrder, PurchaseOrderInput } from '$lib/types';

	const id: string = $page.params.id ?? '';

	let po: PurchaseOrder | null = $state(null);
	let loading: boolean = $state(true);
	let fetchError: string = $state('');

	onMount(async () => {
		try {
			po = await getPO(id);
		} catch (err) {
			fetchError = err instanceof Error ? err.message : 'Failed to load purchase order.';
		} finally {
			loading = false;
		}
	});

	async function handleSubmit(data: PurchaseOrderInput): Promise<void> {
		await updatePO(id, data);
		goto(`/po/${id}`);
	}
</script>

{#if loading}
	<p>Loading...</p>
{:else if fetchError}
	<p class="error-message">{fetchError}</p>
{:else if po && po.status !== 'REJECTED'}
	<p class="error-message">Only rejected POs can be edited.</p>
{:else if po}
	<h1>Edit Purchase Order</h1>
	<POForm
		initialData={{
			vendor_id: po.vendor_id,
			buyer_name: po.buyer_name,
			buyer_country: po.buyer_country,
			currency: po.currency,
			issued_date: po.issued_date,
			required_delivery_date: po.required_delivery_date,
			ship_to_address: po.ship_to_address,
			payment_terms: po.payment_terms,
			incoterm: po.incoterm,
			port_of_loading: po.port_of_loading,
			port_of_discharge: po.port_of_discharge,
			country_of_origin: po.country_of_origin,
			country_of_destination: po.country_of_destination,
			terms_and_conditions: po.terms_and_conditions,
			line_items: po.line_items.map((item) => ({
				part_number: item.part_number,
				description: item.description,
				quantity: item.quantity,
				uom: item.uom,
				unit_price: item.unit_price,
				hs_code: item.hs_code,
				country_of_origin: item.country_of_origin
			}))
		}}
		onSubmit={handleSubmit}
		submitLabel="Save & Revise"
	/>
{/if}

<style>
	.error-message {
		color: var(--red-600);
		font-size: var(--font-size-base);
		padding: var(--space-4) 0;
	}
</style>
