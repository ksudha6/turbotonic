<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import { createProduct, listVendors } from '$lib/api';
	import type { VendorListItem, UserRole } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import ProductCreateForm, {
		type ProductCreateFields
	} from '$lib/product/ProductCreateForm.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let vendors: VendorListItem[] = $state([]);
	let error: string = $state('');
	let submitting: boolean = $state(false);

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);

	onMount(async () => {
		try {
			vendors = await listVendors({ status: 'ACTIVE' });
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load vendors';
		}
	});

	async function handleSubmit(fields: ProductCreateFields) {
		error = '';
		submitting = true;
		try {
			await createProduct(fields);
			goto('/products');
		} catch (err) {
			if (err instanceof Error && err.message.includes('409')) {
				error = 'A product with this part number already exists for this vendor.';
			} else {
				error = err instanceof Error ? err.message : 'An error occurred.';
			}
		} finally {
			submitting = false;
		}
	}

	function handleCancel() {
		goto('/products');
	}
</script>

<svelte:head>
	<title>Create Product</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Products">
	{#snippet userMenu()}
		<UserMenu name={userName} {role} />
	{/snippet}

	<PageHeader title="Create Product" />

	<ProductCreateForm
		{vendors}
		{error}
		{submitting}
		on_submit={handleSubmit}
		on_cancel={handleCancel}
	/>
</AppShell>
