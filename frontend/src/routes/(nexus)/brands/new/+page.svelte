<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import { createBrand, fetchReferenceData } from '$lib/api';
	import type { BrandCreate, ReferenceDataItem, UserRole } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import BrandForm from '$lib/brand/BrandForm.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let countries: ReferenceDataItem[] = $state([]);
	let error: string | null = $state(null);
	let submitting: boolean = $state(false);

	const sessionUser = $derived(appPage.data.user);
	const sessionRole = $derived<UserRole>((sessionUser?.role as UserRole | undefined) ?? 'ADMIN');
	const sessionName = $derived(sessionUser?.display_name ?? sessionUser?.username ?? 'Guest');
	const sessionRoleLabel = $derived(ROLE_LABEL[sessionRole]);

	onMount(async () => {
		try {
			const refData = await fetchReferenceData();
			countries = refData.countries;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load reference data';
		}
	});

	async function handleSubmit(data: BrandCreate) {
		error = null;
		submitting = true;
		try {
			const brand = await createBrand(data as BrandCreate);
			goto(`/brands/${brand.id}/edit`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'An error occurred.';
		} finally {
			submitting = false;
		}
	}

	function handleCancel() {
		goto('/brands');
	}
</script>

<svelte:head>
	<title>Create Brand</title>
</svelte:head>

<AppShell role={sessionRole} roleLabel={sessionRoleLabel} breadcrumb="Brands">
	{#snippet userMenu()}
		<UserMenu name={sessionName} role={sessionRole} />
	{/snippet}

	<PageHeader title="Create Brand" />

	<BrandForm
		mode="create"
		{countries}
		{submitting}
		{error}
		onSubmit={handleSubmit}
		onCancel={handleCancel}
	/>
</AppShell>
