<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import KpiCard from '$lib/ui/KpiCard.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import { fetchDashboardSummary } from '$lib/api';
	import { canViewPOs, canViewInvoices } from '$lib/permissions';
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

	const isFullLayout = $derived(role === 'ADMIN' || role === 'SM' || role === 'PROCUREMENT_MANAGER');
	const isFmLayout = $derived(role === 'FREIGHT_MANAGER');
	const fetchesSummary = $derived(isFullLayout || isFmLayout);

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

	let summary = $state<DashboardSummary | null>(null);
	let loading = $state<boolean>(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		if (!fetchesSummary) {
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

	type ActivityRow = {
		id: string;
		primary: string;
		secondary: string;
		tone: 'orange' | 'red' | 'blue';
		href: string | null;
	};

	function activityHref(item: DashboardActivityItem, currentRole: UserRole): string | null {
		if (item.entity_type === 'PO' && canViewPOs(currentRole)) return `/po/${item.entity_id}`;
		if (item.entity_type === 'INVOICE' && canViewInvoices(currentRole)) return `/invoice/${item.entity_id}`;
		return null;
	}

	function toActivityRow(item: DashboardActivityItem, currentRole: UserRole): ActivityRow {
		const tone: 'orange' | 'red' | 'blue' =
			item.category === 'ACTION_REQUIRED'
				? 'orange'
				: item.category === 'DELAYED'
					? 'red'
					: 'blue';
		return {
			id: item.id,
			primary: EVENT_LABELS[item.event] ?? item.event,
			secondary: relativeTime(item.created_at),
			tone,
			href: activityHref(item, currentRole)
		};
	}

	const activityRows = $derived<ActivityRow[]>(
		summary === null ? [] : summary.activity.map((item) => toActivityRow(item, role))
	);
</script>

<svelte:head>
	<title>Dashboard</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Dashboard">
	{#snippet userMenu()}
		<UserMenu {name} {role} />
	{/snippet}

	{#if !fetchesSummary}
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
	{:else if summary && isFullLayout}
		<div class="ui-dashboard">
			<div class="ui-dashboard-kpis" data-testid="ui-dashboard-kpis">
				<KpiCard
					label="Pending POs"
					value={String(summary.kpis.pending_pos)}
					delta={{ value: formatUsd(summary.kpis.pending_pos_value_usd), tone: 'neutral' }}
					data-testid="kpi-pending-pos"
				/>
				<KpiCard
					label="Awaiting acceptance"
					value={String(summary.kpis.awaiting_acceptance)}
					delta={{ value: formatUsd(summary.kpis.awaiting_acceptance_value_usd), tone: 'neutral' }}
					data-testid="kpi-awaiting"
				/>
				<KpiCard
					label="In production"
					value={String(summary.kpis.in_production)}
					delta={{ value: formatUsd(summary.kpis.in_production_value_usd), tone: 'neutral' }}
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
						{#if activityRows.length === 0}
							<EmptyState title="No recent activity" />
						{:else}
							<ul class="ui-dashboard-activity-feed" data-testid="activity-feed">
								{#each activityRows as row (row.id)}
									<li>
										{#if row.href}
											<a class="ui-dashboard-activity-row" href={row.href} data-testid="activity-row-{row.id}">
												<span class="ui-dashboard-activity-dot {row.tone}" aria-hidden="true"></span>
												<span class="ui-dashboard-activity-text">
													<span class="ui-dashboard-activity-primary">{row.primary}</span>
													<span class="ui-dashboard-activity-secondary">{row.secondary}</span>
												</span>
											</a>
										{:else}
											<span class="ui-dashboard-activity-row ui-dashboard-activity-static" data-testid="activity-row-{row.id}">
												<span class="ui-dashboard-activity-dot {row.tone}" aria-hidden="true"></span>
												<span class="ui-dashboard-activity-text">
													<span class="ui-dashboard-activity-primary">{row.primary}</span>
													<span class="ui-dashboard-activity-secondary">{row.secondary}</span>
												</span>
											</span>
										{/if}
									</li>
								{/each}
							</ul>
						{/if}
					{/snippet}
				</PanelCard>
			</div>
		</div>
	{:else if summary && isFmLayout && summary.fm_kpis}
		<div class="ui-dashboard">
			<div class="ui-dashboard-kpis" data-testid="ui-dashboard-kpis">
				<KpiCard
					label="Ready batches"
					value={String(summary.fm_kpis.ready_batches)}
					data-testid="kpi-ready-batches"
				/>
				<KpiCard
					label="Shipments in flight"
					value={String(summary.fm_kpis.shipments_in_flight)}
					data-testid="kpi-shipments-in-flight"
				/>
				<KpiCard
					label="Pending invoices"
					value={String(summary.fm_kpis.pending_invoices)}
					delta={{ value: formatUsd(summary.fm_kpis.pending_invoices_value_usd), tone: 'neutral' }}
					data-testid="kpi-pending-invoices"
				/>
				<KpiCard
					label="Docs missing"
					value={String(summary.fm_kpis.docs_missing)}
					data-testid="kpi-docs-missing"
				/>
			</div>

			<div class="ui-dashboard-panels">
				<PanelCard title="Ready batches" data-testid="panel-ready-batches">
					{#snippet children()}
						{#if summary.fm_ready_batches.length === 0}
							<EmptyState title="No batches ready for shipment" />
						{:else}
							<ul class="ui-dashboard-awaiting-list">
								{#each summary.fm_ready_batches as batch (batch.po_id)}
									<li>
										<button
											type="button"
											class="ui-dashboard-awaiting-row"
											onclick={() => goto(`/po/${batch.po_id}`)}
										>
											<span class="ui-dashboard-awaiting-po">{batch.po_number}</span>
											<span class="ui-dashboard-awaiting-vendor">{batch.vendor_name}</span>
											<span class="ui-dashboard-awaiting-value">
												{batch.shipped_qty} / {batch.accepted_qty}
											</span>
										</button>
									</li>
								{/each}
							</ul>
						{/if}
					{/snippet}
				</PanelCard>

				<PanelCard title="Pending invoices" data-testid="panel-pending-invoices">
					{#snippet children()}
						{#if summary.fm_pending_invoices.length === 0}
							<EmptyState title="No pending OpEx or freight invoices" />
						{:else}
							<ul class="ui-dashboard-awaiting-list">
								{#each summary.fm_pending_invoices as inv (inv.id)}
									<li>
										<button
											type="button"
											class="ui-dashboard-awaiting-row"
											onclick={() => goto(`/invoice/${inv.id}`)}
										>
											<span class="ui-dashboard-awaiting-po">{inv.invoice_number}</span>
											<span class="ui-dashboard-awaiting-vendor">{inv.vendor_name} · {inv.vendor_type}</span>
											<span class="ui-dashboard-awaiting-value">{formatUsd(inv.subtotal_usd)}</span>
										</button>
									</li>
								{/each}
							</ul>
						{/if}
					{/snippet}
				</PanelCard>
			</div>

			<PanelCard title="Recent activity" data-testid="panel-activity">
				{#snippet children()}
					{#if activityRows.length === 0}
						<EmptyState title="No recent activity" />
					{:else}
						<ul class="ui-dashboard-activity-feed" data-testid="activity-feed">
							{#each activityRows as row (row.id)}
								<li>
									{#if row.href}
										<a class="ui-dashboard-activity-row" href={row.href} data-testid="activity-row-{row.id}">
											<span class="ui-dashboard-activity-dot {row.tone}" aria-hidden="true"></span>
											<span class="ui-dashboard-activity-text">
												<span class="ui-dashboard-activity-primary">{row.primary}</span>
												<span class="ui-dashboard-activity-secondary">{row.secondary}</span>
											</span>
										</a>
									{:else}
										<span class="ui-dashboard-activity-row ui-dashboard-activity-static" data-testid="activity-row-{row.id}">
											<span class="ui-dashboard-activity-dot {row.tone}" aria-hidden="true"></span>
											<span class="ui-dashboard-activity-text">
												<span class="ui-dashboard-activity-primary">{row.primary}</span>
												<span class="ui-dashboard-activity-secondary">{row.secondary}</span>
											</span>
										</span>
									{/if}
								</li>
							{/each}
						</ul>
					{/if}
				{/snippet}
			</PanelCard>
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

	.ui-dashboard-activity-feed {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.ui-dashboard-activity-row {
		display: flex;
		align-items: flex-start;
		gap: var(--space-3);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-sm);
		text-decoration: none;
		color: inherit;
	}

	a.ui-dashboard-activity-row:hover {
		background-color: var(--gray-50);
	}

	.ui-dashboard-activity-dot {
		flex-shrink: 0;
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 999px;
		margin-top: 0.5rem;
		background-color: var(--dot-gray);
	}
	.ui-dashboard-activity-dot.blue { background-color: var(--dot-blue); }
	.ui-dashboard-activity-dot.orange { background-color: var(--dot-orange); }
	.ui-dashboard-activity-dot.red { background-color: var(--dot-red); }

	.ui-dashboard-activity-text {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.ui-dashboard-activity-primary {
		font-size: var(--font-size-sm);
		color: var(--gray-900);
	}
	.ui-dashboard-activity-secondary {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
	}
</style>
