<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import { createVendor, fetchReferenceData } from '$lib/api';
	import type { ReferenceDataItem, UserRole } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import VendorForm, { type VendorFormFields } from '$lib/vendor/VendorForm.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let countries: ReferenceDataItem[] = $state([]);
	let error: string = $state('');
	let submitting: boolean = $state(false);

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);

	onMount(async () => {
		try {
			const refData = await fetchReferenceData();
			countries = refData.countries;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load reference data';
		}
	});

	async function handleSubmit(fields: VendorFormFields) {
		error = '';
		submitting = true;
		try {
			await createVendor(fields);
			goto('/vendors');
		} catch (e) {
			error = e instanceof Error ? e.message : 'An error occurred.';
		} finally {
			submitting = false;
		}
	}

	function handleCancel() {
		goto('/vendors');
	}
</script>

<svelte:head>
	<title>Create Vendor</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Vendors">
	{#snippet userMenu()}
		<UserMenu name={userName} {role} />
	{/snippet}

	<PageHeader title="Create Vendor" />

	<VendorForm
		{countries}
		{error}
		{submitting}
		on_submit={handleSubmit}
		on_cancel={handleCancel}
	/>
</AppShell>
