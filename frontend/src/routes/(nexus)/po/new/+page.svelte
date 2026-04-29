<script lang="ts">
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import { createPO } from '$lib/api';
	import PoForm from '$lib/po/PoForm.svelte';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import type { PurchaseOrderInput, UserRole } from '$lib/types';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	const user = $derived(appPage.data.user);
	const role = $derived((user?.role as UserRole | undefined) ?? 'ADMIN');
	const name = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);

	async function handleSubmit(data: PurchaseOrderInput): Promise<void> {
		const result = await createPO(data);
		goto(`/po/${result.id}`);
	}
</script>

<svelte:head>
	<title>Create Purchase Order</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="New PO">
	{#snippet userMenu()}
		<UserMenu {name} {role} />
	{/snippet}

	<PageHeader title="Create Purchase Order" subtitle="Draft a new purchase order." />

	<PoForm
		mode="create"
		onSubmit={handleSubmit}
		submitLabel="Create PO"
		cancelHref="/po"
	/>
</AppShell>
