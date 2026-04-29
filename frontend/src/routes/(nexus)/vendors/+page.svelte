<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import { listVendors, deactivateVendor, reactivateVendor } from '$lib/api';
	import type { VendorListItem, UserRole } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import Button from '$lib/ui/Button.svelte';
	import VendorListFilters from '$lib/vendor/VendorListFilters.svelte';
	import VendorListTable from '$lib/vendor/VendorListTable.svelte';
	import { canManageVendors } from '$lib/permissions';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let status: string = $state('');
	let vendorType: string = $state('');

	let vendors: VendorListItem[] = $state([]);
	let loading: boolean = $state(true);
	let errorMessage: string = $state('');
	let initialFetchComplete: boolean = $state(false);

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);
	const canManage = $derived(canManageVendors(role));
	const hasAnyFilter = $derived(Boolean(status || vendorType));

	let initialized = false;
	$effect(() => {
		status;
		vendorType;
		if (!initialized) {
			initialized = true;
			return;
		}
		fetchVendors();
	});

	onMount(() => {
		fetchVendors();
	});

	async function fetchVendors() {
		loading = true;
		errorMessage = '';
		try {
			vendors = await listVendors({
				status: status || undefined,
				vendor_type: vendorType || undefined
			});
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Failed to load vendors';
			vendors = [];
		} finally {
			loading = false;
			initialFetchComplete = true;
		}
	}

	function clearFilters() {
		status = '';
		vendorType = '';
	}

	async function handleAction(id: string, action: 'deactivate' | 'reactivate') {
		try {
			if (action === 'deactivate') {
				await deactivateVendor(id);
			} else {
				await reactivateVendor(id);
			}
			await fetchVendors();
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : `Failed to ${action} vendor`;
		}
	}
</script>

<svelte:head>
	<title>Vendors</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Vendors">
	{#snippet userMenu()}
		<UserMenu name={userName} {role} />
	{/snippet}

	<PageHeader title="Vendors">
		{#snippet action()}
			{#if canManage}
				<Button
					variant="primary"
					onclick={() => goto('/vendors/new')}
					data-testid="vendor-page-header-action"
				>
					New Vendor
				</Button>
			{/if}
		{/snippet}
	</PageHeader>

	<div class="vendor-list-page">
		<VendorListFilters bind:status bind:vendorType onClear={clearFilters} />

		{#if errorMessage && !loading}
			<ErrorState message={errorMessage} onRetry={fetchVendors} />
		{:else if loading && !initialFetchComplete}
			<LoadingState label="Loading vendors" data-testid="vendor-list-loading" />
		{:else if vendors.length === 0}
			{#if hasAnyFilter}
				<EmptyState title="No matching vendors" description="Try adjusting filters." />
			{:else}
				<EmptyState
					title="No vendors yet"
					description="Vendors appear here once an admin or SM creates one."
				/>
			{/if}
		{:else}
			<div class="vendor-list-table-region">
				<VendorListTable rows={vendors} {canManage} onAction={handleAction} />
				{#if loading && vendors.length > 0}
					<div class="vendor-list-loading-overlay">
						<LoadingState label="Refreshing" data-testid="vendor-list-loading" />
					</div>
				{/if}
			</div>
		{/if}
	</div>
</AppShell>

<style>
	.vendor-list-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.vendor-list-table-region {
		position: relative;
	}
	.vendor-list-loading-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(255, 255, 255, 0.6);
		z-index: 1;
	}
</style>
