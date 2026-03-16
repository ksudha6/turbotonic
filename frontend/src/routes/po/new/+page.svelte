<script lang="ts">
	import { goto } from '$app/navigation';
	import { createPO } from '$lib/api';
	import POForm from '$lib/components/POForm.svelte';
	import type { PurchaseOrderInput } from '$lib/types';

	async function handleSubmit(data: PurchaseOrderInput): Promise<void> {
		const result = await createPO(data);
		goto(`/po/${result.id}`);
	}
</script>

<h1>Create Purchase Order</h1>

<POForm onSubmit={handleSubmit} submitLabel="Create PO" />
