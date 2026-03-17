<script lang="ts">
	import { onMount } from 'svelte';
	import { listVendors, deactivateVendor } from '$lib/api';
	import type { VendorListItem } from '$lib/types';

	let vendors: VendorListItem[] = $state([]);
	let selectedStatus: string = $state('');
	let loading: boolean = $state(true);

	async function fetchVendors() {
		loading = true;
		try {
			vendors = await listVendors(selectedStatus || undefined);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchVendors();
	});

	$effect(() => {
		selectedStatus;
		fetchVendors();
	});

	async function handleDeactivate(id: string) {
		await deactivateVendor(id);
		await fetchVendors();
	}
</script>

<div class="page-header">
	<h1>Vendors</h1>
	<a href="/vendors/new" class="btn btn-primary">New Vendor</a>
</div>

<div class="filter-bar">
	<select class="select" bind:value={selectedStatus}>
		<option value="">All</option>
		<option value="ACTIVE">Active</option>
		<option value="INACTIVE">Inactive</option>
	</select>
</div>

{#if loading}
	<p>Loading...</p>
{:else if vendors.length === 0}
	<p>No vendors found.</p>
{:else}
	<div class="card">
		<table class="table">
			<thead>
				<tr>
					<th>Name</th>
					<th>Country</th>
					<th>Status</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				{#each vendors as vendor}
					<tr>
						<td>{vendor.name}</td>
						<td>{vendor.country}</td>
						<td>
							<span class="badge {vendor.status === 'ACTIVE' ? 'badge-active' : 'badge-inactive'}">
								{vendor.status === 'ACTIVE' ? 'Active' : 'Inactive'}
							</span>
						</td>
						<td>
							{#if vendor.status === 'ACTIVE'}
								<button class="btn btn-danger btn-sm" onclick={() => handleDeactivate(vendor.id)}>
									Deactivate
								</button>
							{/if}
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
		margin-bottom: var(--space-4);
	}

	.badge {
		display: inline-block;
		padding: var(--space-1) var(--space-3);
		border-radius: 9999px;
		font-size: var(--font-size-sm);
		font-weight: 500;
	}

	.badge-active {
		background-color: var(--green-50);
		color: var(--green-700);
	}

	.badge-inactive {
		background-color: var(--gray-100);
		color: var(--gray-600);
	}

	.btn-sm {
		font-size: var(--font-size-sm);
		padding: var(--space-1) var(--space-3);
	}
</style>
