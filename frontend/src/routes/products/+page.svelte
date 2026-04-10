<script lang="ts">
	import { onMount } from 'svelte';
	import { listProducts, listVendors } from '$lib/api';
	import type { ProductListItem, VendorListItem } from '$lib/types';

	let products: ProductListItem[] = $state([]);
	let vendors: VendorListItem[] = $state([]);
	let selectedVendorId: string = $state('');
	let loading: boolean = $state(true);

	async function fetchProducts() {
		loading = true;
		try {
			products = await listProducts(selectedVendorId ? { vendor_id: selectedVendorId } : undefined);
		} finally {
			loading = false;
		}
	}

	onMount(async () => {
		vendors = await listVendors();
		await fetchProducts();
	});

	$effect(() => {
		selectedVendorId;
		fetchProducts();
	});

	function vendorName(vendor_id: string): string {
		return vendors.find((v) => v.id === vendor_id)?.name ?? vendor_id;
	}
</script>

<div class="page-header">
	<h1>Products</h1>
	<a href="/products/new" class="btn btn-primary">New Product</a>
</div>

<div class="filter-bar">
	<select class="select" bind:value={selectedVendorId}>
		<option value="">All Vendors</option>
		{#each vendors as v}
			<option value={v.id}>{v.name}</option>
		{/each}
	</select>
</div>

{#if loading}
	<p>Loading...</p>
{:else if products.length === 0}
	<p>No products found.</p>
{:else}
	<div class="card">
		<table class="table">
			<thead>
				<tr>
					<th>Part Number</th>
					<th>Description</th>
					<th>Vendor</th>
					<th>Requires Cert</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				{#each products as product}
					<tr>
						<td class="part-number">{product.part_number}</td>
						<td>{product.description}</td>
						<td>{vendorName(product.vendor_id)}</td>
						<td>
							{#if product.requires_certification}
								<span class="badge badge-cert">Yes</span>
							{:else}
								<span class="badge badge-no-cert">No</span>
							{/if}
						</td>
						<td>
							<a href="/products/{product.id}/edit" class="btn btn-secondary btn-sm">Edit</a>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<style>
	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-6);
	}

	.filter-bar {
		display: flex;
		gap: var(--space-3);
		margin-bottom: var(--space-4);
	}

	.badge {
		display: inline-block;
		padding: var(--space-1) var(--space-3);
		border-radius: 9999px;
		font-size: var(--font-size-sm);
		font-weight: 500;
	}

	.badge-cert {
		background-color: var(--green-50);
		color: var(--green-700);
	}

	.badge-no-cert {
		background-color: var(--gray-100);
		color: var(--gray-600);
	}

	.btn-sm {
		font-size: var(--font-size-sm);
		padding: var(--space-1) var(--space-3);
	}

	.part-number {
		font-family: monospace;
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}
</style>
