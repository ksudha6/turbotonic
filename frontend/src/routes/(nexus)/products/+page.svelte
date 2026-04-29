<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import { listProducts, listVendors } from '$lib/api';
	import { canManageProducts } from '$lib/permissions';
	import type { ProductListItem, VendorListItem, UserRole } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import Button from '$lib/ui/Button.svelte';
	import ProductListFilters from '$lib/product/ProductListFilters.svelte';
	import ProductListTable from '$lib/product/ProductListTable.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let vendor: string = $state('');

	let products: ProductListItem[] = $state([]);
	let vendors: VendorListItem[] = $state([]);
	let loading: boolean = $state(true);
	let errorMessage: string = $state('');
	let initialFetchComplete: boolean = $state(false);

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);
	const canManage = $derived(canManageProducts(role));
	const hasAnyFilter = $derived(Boolean(vendor));

	let initialized = false;
	$effect(() => {
		vendor;
		if (!initialized) {
			initialized = true;
			return;
		}
		fetchProducts();
	});

	onMount(async () => {
		try {
			vendors = await listVendors();
		} catch {
			// Vendor pre-fetch failure leaves the filter dropdown empty; the main fetch surfaces a real error state.
		}
		await fetchProducts();
	});

	async function fetchProducts() {
		loading = true;
		errorMessage = '';
		try {
			products = await listProducts(vendor ? { vendor_id: vendor } : undefined);
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Failed to load products';
			products = [];
		} finally {
			loading = false;
			initialFetchComplete = true;
		}
	}

	function clearFilters() {
		vendor = '';
	}
</script>

<svelte:head>
	<title>Products</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Products">
	{#snippet userMenu()}
		<UserMenu name={userName} {role} />
	{/snippet}

	<PageHeader title="Products">
		{#snippet action()}
			{#if canManage}
				<Button
					variant="primary"
					onclick={() => goto('/products/new')}
					data-testid="product-page-header-action"
				>
					New Product
				</Button>
			{/if}
		{/snippet}
	</PageHeader>

	<div class="product-list-page">
		<ProductListFilters bind:vendor {vendors} onClear={clearFilters} />

		{#if errorMessage && !loading}
			<ErrorState message={errorMessage} onRetry={fetchProducts} />
		{:else if loading && !initialFetchComplete}
			<LoadingState label="Loading products" data-testid="product-list-loading" />
		{:else if products.length === 0}
			{#if hasAnyFilter}
				<EmptyState title="No matching products" description="Try adjusting filters." />
			{:else}
				<EmptyState
					title="No products yet"
					description="Products appear here once an admin or SM creates one."
				/>
			{/if}
		{:else}
			<div class="product-list-table-region">
				<ProductListTable rows={products} {vendors} {canManage} />
				{#if loading && products.length > 0}
					<div class="product-list-loading-overlay">
						<LoadingState label="Refreshing" data-testid="product-list-loading" />
					</div>
				{/if}
			</div>
		{/if}
	</div>
</AppShell>

<style>
	.product-list-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.product-list-table-region {
		position: relative;
	}
	.product-list-loading-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(255, 255, 255, 0.6);
		z-index: 1;
	}
</style>
