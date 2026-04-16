<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { fetchDashboard, fetchActivity } from '$lib/api';
	import { canViewPOs, canViewInvoices, canManageVendors } from '$lib/permissions';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import type { ActivityLogEntry, DashboardData } from '$lib/types';

	const role = $derived(page.data.user?.role);

	const MILESTONE_LABELS: Record<string, string> = {
		RAW_MATERIALS: 'Raw Materials',
		PRODUCTION_STARTED: 'Production Started',
		QC_PASSED: 'QC Passed',
		READY_TO_SHIP: 'Ready to Ship',
		SHIPPED: 'Shipped',
	};

	let data: DashboardData | null = $state(null);
	let activity: ActivityLogEntry[] = $state([]);
	let loading: boolean = $state(true);

	onMount(async () => {
		try {
			[data, activity] = await Promise.all([fetchDashboard(), fetchActivity(20, role)]);
		} finally {
			loading = false;
		}
	});

	const EVENT_LABELS: Record<string, string> = {
		PO_CREATED: 'PO created',
		PO_SUBMITTED: 'PO submitted',
		PO_ACCEPTED: 'PO accepted',
		PO_REJECTED: 'PO rejected',
		PO_REVISED: 'PO revised',
		INVOICE_CREATED: 'Invoice created',
		INVOICE_SUBMITTED: 'Invoice submitted',
		INVOICE_APPROVED: 'Invoice approved',
		INVOICE_PAID: 'Invoice paid',
		INVOICE_DISPUTED: 'Invoice disputed',
		MILESTONE_POSTED: 'Milestone posted',
		MILESTONE_OVERDUE: 'Milestone overdue',
	};

	function relativeTime(dateStr: string): string {
		const diffMs = Date.now() - new Date(dateStr).getTime();
		const diffMin = Math.floor(diffMs / 60000);
		if (diffMin < 1) return 'just now';
		if (diffMin < 60) return `${diffMin}m ago`;
		const diffHr = Math.floor(diffMin / 60);
		if (diffHr < 24) return `${diffHr}h ago`;
		return `${Math.floor(diffHr / 24)}d ago`;
	}

	function entityLink(entry: ActivityLogEntry): string {
		return entry.entity_type === 'PO' ? `/po/${entry.entity_id}` : `/invoice/${entry.entity_id}`;
	}

	function categoryClass(category: string): string {
		if (category === 'ACTION_REQUIRED') return 'cat-action';
		if (category === 'DELAYED') return 'cat-delayed';
		return 'cat-live';
	}

	function formatUsd(value: string): string {
		return parseFloat(value).toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 });
	}
</script>

<h1>Dashboard</h1>

{#if loading}
	<p>Loading...</p>
{:else if data}
	{#if role && canViewPOs(role)}
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
	{/if}

	{#if role && canViewInvoices(role)}
	<section class="section">
		<h2>Invoices</h2>
		<div class="summary-grid">
			{#each data.invoice_summary as s}
				<a href="/invoices?status={s.status}" class="summary-card card">
					<div class="summary-status"><StatusPill status={s.status} /></div>
					<div class="summary-count">{s.count}</div>
					<div class="summary-value">≈ {formatUsd(s.total_usd)}</div>
				</a>
			{/each}
			{#if data.invoice_summary.length === 0}
				<p class="empty-text">No invoices yet.</p>
			{/if}
		</div>
	</section>
	{/if}

	{#if role && canManageVendors(role)}
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
	{/if}

	<section class="section">
		<h2>Recent Activity</h2>
		{#if activity.length === 0}
			<p class="empty-text">No recent activity.</p>
		{:else}
			<div class="card feed">
				{#each activity as entry}
					<div class="feed-item" onclick={() => goto(entityLink(entry))}>
						<span class="cat-dot {categoryClass(entry.category)}"></span>
						<div class="feed-content">
							<span class="feed-event">{EVENT_LABELS[entry.event] ?? entry.event}</span>
							{#if entry.detail}
								<span class="feed-detail">{entry.detail}</span>
							{/if}
						</div>
						<span class="feed-time">{relativeTime(entry.created_at)}</span>
					</div>
				{/each}
			</div>
		{/if}
	</section>

	{#if role && canViewPOs(role)}
	<section class="section">
		<h2>Production Pipeline</h2>
		{#if data.production_summary.length === 0}
			<p class="empty-text">No production activity.</p>
		{:else}
			<div class="card">
				<table class="table">
					<thead>
						<tr>
							<th>Stage</th>
							<th>POs</th>
						</tr>
					</thead>
					<tbody>
						{#each data.production_summary as s}
							<tr onclick={() => goto(`/po?status=ACCEPTED&milestone=${s.milestone}`)}>
								<td>{MILESTONE_LABELS[s.milestone] ?? s.milestone}</td>
								<td>{s.count}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>

	<section class="section">
		<h2>Overdue Production</h2>
		{#if data.overdue_pos.length === 0}
			<p class="empty-text">No overdue production orders.</p>
		{:else}
			<div class="card">
				<table class="table">
					<thead>
						<tr>
							<th>PO #</th>
							<th>Vendor</th>
							<th>Milestone</th>
							<th>Days Overdue</th>
						</tr>
					</thead>
					<tbody>
						{#each data.overdue_pos as o}
							<tr onclick={() => goto(`/po/${o.id}`)}>
								<td><a href="/po/{o.id}" onclick={(e) => e.stopPropagation()}>{o.po_number}</a></td>
								<td>{o.vendor_name}</td>
								<td>{MILESTONE_LABELS[o.milestone] ?? o.milestone}</td>
								<td class="overdue-days">{o.days_since_update}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
	{/if}
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

	.overdue-days {
		color: var(--red-600);
		font-weight: 600;
	}

	.feed {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.feed-item {
		display: flex;
		align-items: flex-start;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-4);
		cursor: pointer;
		border-bottom: 1px solid var(--gray-100);
	}

	.feed-item:last-child {
		border-bottom: none;
	}

	.feed-item:hover {
		background-color: var(--gray-50);
	}

	.cat-dot {
		flex-shrink: 0;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin-top: 5px;
	}

	.cat-live {
		background-color: #3b82f6;
	}

	.cat-action {
		background-color: #f59e0b;
	}

	.cat-delayed {
		background-color: var(--red-600);
	}

	.feed-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.feed-event {
		font-size: var(--font-size-sm);
		font-weight: 500;
	}

	.feed-detail {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
	}

	.feed-time {
		flex-shrink: 0;
		font-size: var(--font-size-xs);
		color: var(--gray-500);
		white-space: nowrap;
	}
</style>
