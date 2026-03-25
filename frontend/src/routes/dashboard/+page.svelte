<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fetchDashboard } from '$lib/api';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import type { DashboardData, POStatusSummary, RecentPO } from '$lib/types';

	let data: DashboardData | null = $state(null);
	let loading: boolean = $state(true);

	onMount(async () => {
		try {
			data = await fetchDashboard();
		} finally {
			loading = false;
		}
	});

	function formatUsd(value: string): string {
		return parseFloat(value).toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 });
	}

	function formatValue(value: string, currency: string): string {
		return `${parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}
</script>

<h1>Dashboard</h1>

{#if loading}
	<p>Loading...</p>
{:else if data}
	<section class="section">
		<h2>Purchase Orders</h2>
		<div class="summary-grid">
			{#each data.po_summary as s}
				<a href="/po?status={s.status}" class="summary-card card">
					<div class="summary-status"><StatusPill status={s.status} /></div>
					<div class="summary-count">{s.count}</div>
					<div class="summary-value">≈ {formatUsd(s.total_usd)}</div>
				</a>
			{/each}
			{#if data.po_summary.length === 0}
				<p class="empty-text">No purchase orders yet.</p>
			{/if}
		</div>
	</section>

	<section class="section">
		<h2>Vendors</h2>
		<div class="vendor-summary">
			<div class="card vendor-card">
				<div class="vendor-count">{data.vendor_summary.active}</div>
				<div class="vendor-label">Active</div>
			</div>
			<div class="card vendor-card">
				<div class="vendor-count">{data.vendor_summary.inactive}</div>
				<div class="vendor-label">Inactive</div>
			</div>
		</div>
	</section>

	<section class="section">
		<h2>Recent Activity</h2>
		{#if data.recent_pos.length === 0}
			<p class="empty-text">No recent activity.</p>
		{:else}
			<div class="card">
				<table class="table">
					<thead>
						<tr>
							<th>PO Number</th>
							<th>Vendor</th>
							<th>Status</th>
							<th>Total Value</th>
							<th>Updated</th>
						</tr>
					</thead>
					<tbody>
						{#each data.recent_pos as po}
							<tr onclick={() => goto(`/po/${po.id}`)}>
								<td>{po.po_number}</td>
								<td>{po.vendor_name}</td>
								<td><StatusPill status={po.status} /></td>
								<td>{formatValue(po.total_value, po.currency)}</td>
								<td>{formatDate(po.updated_at)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
{/if}

<style>
	.section {
		margin-bottom: var(--space-8);
	}

	.summary-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: var(--space-4);
	}

	.summary-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		text-decoration: none;
		color: inherit;
		transition: box-shadow 0.15s;
	}

	.summary-card:hover {
		box-shadow: var(--shadow-md);
		text-decoration: none;
	}

	.summary-count {
		font-size: var(--font-size-2xl);
		font-weight: 700;
	}

	.summary-value {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}

	.vendor-summary {
		display: flex;
		gap: var(--space-4);
	}

	.vendor-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-1);
		min-width: 120px;
	}

	.vendor-count {
		font-size: var(--font-size-2xl);
		font-weight: 700;
	}

	.vendor-label {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}

	.empty-text {
		color: var(--gray-500);
	}

	tbody tr {
		cursor: pointer;
	}

	tbody tr:hover td {
		background-color: var(--gray-50);
	}
</style>
