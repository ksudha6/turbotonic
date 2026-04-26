<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import KpiCard from '$lib/ui/KpiCard.svelte';
	import ActivityFeed from '$lib/ui/ActivityFeed.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import { fetchDashboardSummary } from '$lib/api';
	import type { DashboardActivityItem, DashboardSummary, UserRole } from '$lib/types';

	const user = $derived(page.data.user);
	const role = $derived((user?.role as UserRole | undefined) ?? 'ADMIN');
	const name = $derived(user?.display_name ?? user?.username ?? 'Guest');

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};
	const roleLabel = $derived(ROLE_LABEL[role]);

	const isFullLayout = $derived(role === 'ADMIN' || role === 'SM');

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
		MILESTONE_OVERDUE: 'Milestone overdue'
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

	function formatUsd(value: string): string {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		}).format(parseFloat(value));
	}

	let summary: DashboardSummary | null = $state(null);
	let loading: boolean = $state(true);
	let error: string | null = $state(null);

	onMount(async () => {
		if (!isFullLayout) {
			loading = false;
			return;
		}
		try {
			summary = await fetchDashboardSummary();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load dashboard';
		} finally {
			loading = false;
		}
	});

	const activityEntries = $derived(
		(summary !== null ? summary.activity : [] as DashboardActivityItem[]).map((item: DashboardActivityItem) => ({
			id: item.id,
			primary: EVENT_LABELS[item.event] ?? item.event,
			secondary: relativeTime(item.created_at),
			tone: (item.category === 'ACTION_REQUIRED'
				? 'orange'
				: item.category === 'DELAYED'
					? 'red'
					: 'blue') as 'orange' | 'red' | 'blue'
		}))
	);
</script>

<svelte:head>
	<title>Dashboard</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Dashboard">
	{#snippet userMenu()}
		<UserMenu {name} {role} />
	{/snippet}

	{#if !isFullLayout}
		<div class="ui-dashboard-placeholder">
			<PanelCard title="Dashboard" data-testid="panel-placeholder">
				{#snippet children()}
					<p class="ui-dashboard-coming-soon">
						Your role-specific dashboard is coming in a later iteration.
					</p>
				{/snippet}
			</PanelCard>
		</div>
	{:else if loading}
		<LoadingState label="Loading dashboard" />
	{:else if error}
		<ErrorState message={error} onRetry={() => { error = null; loading = true; fetchDashboardSummary().then(s => { summary = s; }).catch(e => { error = e instanceof Error ? e.message : 'Failed to load dashboard'; }).finally(() => { loading = false; }); }} />
	{:else if summary}
		<div class="ui-dashboard">
			<div class="ui-dashboard-kpis" data-testid="ui-dashboard-kpis">
				<KpiCard
					label="Pending POs"
					value={String(summary.kpis.pending_pos)}
					data-testid="kpi-pending-pos"
				/>
				<KpiCard
					label="Awaiting acceptance"
					value={String(summary.kpis.awaiting_acceptance)}
					data-testid="kpi-awaiting"
				/>
				<KpiCard
					label="In production"
					value={String(summary.kpis.in_production)}
					data-testid="kpi-in-production"
				/>
				<KpiCard
					label="Outstanding A/P"
					value={formatUsd(summary.kpis.outstanding_ap_usd)}
					data-testid="kpi-outstanding-ap"
				/>
			</div>

			<div class="ui-dashboard-panels">
				<PanelCard title="Awaiting acceptance" data-testid="panel-awaiting">
					{#snippet children()}
						{#if summary.awaiting_acceptance.length === 0}
							<EmptyState title="No POs awaiting acceptance" />
						{:else}
							<ul class="ui-dashboard-awaiting-list">
								{#each summary.awaiting_acceptance as item (item.id)}
									<li>
										<button
											type="button"
											class="ui-dashboard-awaiting-row"
											onclick={() => goto(`/po/${item.id}`)}
										>
											<span class="ui-dashboard-awaiting-po">{item.po_number}</span>
											<span class="ui-dashboard-awaiting-vendor">{item.vendor_name}</span>
											<span class="ui-dashboard-awaiting-value">{formatUsd(item.total_value_usd)}</span>
										</button>
									</li>
								{/each}
							</ul>
						{/if}
					{/snippet}
				</PanelCard>

				<PanelCard title="Recent activity" data-testid="panel-activity">
					{#snippet children()}
						{#if activityEntries.length === 0}
							<EmptyState title="No recent activity" />
						{:else}
							<ActivityFeed entries={activityEntries} data-testid="activity-feed" />
						{/if}
					{/snippet}
				</PanelCard>
			</div>
		</div>
	{/if}
</AppShell>

<style>
	.ui-dashboard {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.ui-dashboard-kpis {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: var(--space-4);
	}

	.ui-dashboard-panels {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
	}

	@media (max-width: 768px) {
		.ui-dashboard-panels {
			grid-template-columns: 1fr;
		}
	}

	.ui-dashboard-awaiting-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.ui-dashboard-awaiting-row {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		width: 100%;
		padding: var(--space-2) var(--space-3);
		border: none;
		background: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		text-align: left;
		font-size: var(--font-size-sm);
		color: var(--gray-900);
	}

	.ui-dashboard-awaiting-row:hover {
		background-color: var(--gray-50);
	}

	.ui-dashboard-awaiting-po {
		font-weight: 600;
		min-width: 6rem;
	}

	.ui-dashboard-awaiting-vendor {
		flex: 1;
		color: var(--gray-600);
	}

	.ui-dashboard-awaiting-value {
		font-weight: 500;
		white-space: nowrap;
	}

	.ui-dashboard-placeholder {
		max-width: 40rem;
	}

	.ui-dashboard-coming-soon {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
</style>
