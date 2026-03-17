<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { listPOs } from '$lib/api';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import type { PurchaseOrderListItem } from '$lib/types';

	let pos: PurchaseOrderListItem[] = $state([]);
	let selectedStatus: string = $state('');
	let loading: boolean = $state(true);

	async function fetchPOs() {
		loading = true;
		try {
			pos = await listPOs(selectedStatus || undefined);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchPOs();
	});

	$effect(() => {
		// Re-fetch when filter changes; skip the initial mount call (handled by onMount)
		selectedStatus;
		fetchPOs();
	});

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatValue(value: string, currency: string): string {
		return `${parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
	}
</script>

<div class="page-header">
	<h1>Purchase Orders</h1>
	<a href="/po/new" class="btn btn-primary">New PO</a>
</div>

<div class="filter-bar">
	<select class="select" bind:value={selectedStatus}>
		<option value="">All</option>
		<option value="DRAFT">Draft</option>
		<option value="PENDING">Pending</option>
		<option value="ACCEPTED">Accepted</option>
		<option value="REJECTED">Rejected</option>
		<option value="REVISED">Revised</option>
	</select>
</div>

{#if loading}
	<p>Loading...</p>
{:else if pos.length === 0}
	<p>No purchase orders found.</p>
{:else}
	<div class="card">
		<table class="table">
			<thead>
				<tr>
					<th>PO Number</th>
					<th>Vendor</th>
					<th>Issued Date</th>
					<th>Delivery Date</th>
					<th>Total Value</th>
					<th>Status</th>
				</tr>
			</thead>
			<tbody>
				{#each pos as po}
					<tr onclick={() => goto(`/po/${po.id}`)}>
						<td>{po.po_number}</td>
						<td>{po.vendor_name}</td>
						<td>{formatDate(po.issued_date)}</td>
						<td>{formatDate(po.required_delivery_date)}</td>
						<td>{formatValue(po.total_value, po.currency)}</td>
						<td><StatusPill status={po.status} /></td>
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

	tbody tr {
		cursor: pointer;
	}

	tbody tr:hover td {
		background-color: var(--gray-50);
	}
</style>
