<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import { listBrands, deactivateBrand, reactivateBrand } from '$lib/api';
	import type { Brand, BrandStatus, UserRole } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import Button from '$lib/ui/Button.svelte';
	import BrandListFilters from '$lib/brand/BrandListFilters.svelte';
	import BrandListTable from '$lib/brand/BrandListTable.svelte';
	import { canManageBrands } from '$lib/permissions';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let status: BrandStatus | '' = $state('' as BrandStatus | '');

	let brands: Brand[] = $state([]);
	let loading: boolean = $state(true);
	let errorMessage: string = $state('');
	let initialFetchComplete: boolean = $state(false);

	const sessionUser = $derived(appPage.data.user);
	const sessionRole = $derived<UserRole>((sessionUser?.role as UserRole | undefined) ?? 'ADMIN');
	const sessionName = $derived(
		sessionUser?.display_name ?? sessionUser?.username ?? 'Guest'
	);
	const sessionRoleLabel = $derived(ROLE_LABEL[sessionRole]);
	const canManage = $derived(canManageBrands(sessionRole));
	const hasAnyFilter = $derived(Boolean(status));

	let initialized = false;
	$effect(() => {
		status;
		if (!initialized) {
			initialized = true;
			return;
		}
		fetchBrands();
	});

	onMount(() => {
		fetchBrands();
	});

	async function fetchBrands() {
		loading = true;
		errorMessage = '';
		try {
			brands = await listBrands({ status: status || undefined });
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Failed to load brands';
			brands = [];
		} finally {
			loading = false;
			initialFetchComplete = true;
		}
	}

	function clearFilters() {
		status = '';
	}

	function handleEdit(id: string) {
		goto(`/brands/${id}/edit`);
	}

	async function handleDeactivate(id: string) {
		try {
			const updated = await deactivateBrand(id);
			brands = brands.map((b) => (b.id === updated.id ? updated : b));
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Deactivate failed';
		}
	}

	async function handleReactivate(id: string) {
		try {
			const updated = await reactivateBrand(id);
			brands = brands.map((b) => (b.id === updated.id ? updated : b));
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Reactivate failed';
		}
	}
</script>

<svelte:head>
	<title>Brands</title>
</svelte:head>

<AppShell role={sessionRole} roleLabel={sessionRoleLabel} breadcrumb="Brands">
	{#snippet userMenu()}
		<UserMenu name={sessionName} role={sessionRole} />
	{/snippet}

	<PageHeader title="Brands">
		{#snippet action()}
			{#if canManage}
				<Button
					variant="primary"
					onclick={() => goto('/brands/new')}
					data-testid="brand-page-header-action"
				>
					New brand
				</Button>
			{/if}
		{/snippet}
	</PageHeader>

	<div class="brand-list-page">
		<BrandListFilters bind:status onClear={clearFilters} />

		{#if errorMessage && !loading}
			<ErrorState message={errorMessage} onRetry={fetchBrands} />
		{:else if loading && !initialFetchComplete}
			<LoadingState label="Loading brands" data-testid="brand-list-loading" />
		{:else if brands.length === 0}
			{#if hasAnyFilter}
				<EmptyState title="No matching brands" description="Try adjusting filters." />
			{:else}
				<EmptyState
					title="No brands yet"
					description="Create a brand to get started."
				/>
			{/if}
		{:else}
			<div class="brand-list-table-region">
				<BrandListTable
					rows={brands}
					onEdit={handleEdit}
					onDeactivate={handleDeactivate}
					onReactivate={handleReactivate}
				/>
				{#if loading && brands.length > 0}
					<div class="brand-list-loading-overlay">
						<LoadingState label="Refreshing" data-testid="brand-list-loading" />
					</div>
				{/if}
			</div>
		{/if}
	</div>
</AppShell>

<style>
	.brand-list-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.brand-list-table-region {
		position: relative;
	}
	.brand-list-loading-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(255, 255, 255, 0.6);
		z-index: 1;
	}
</style>
