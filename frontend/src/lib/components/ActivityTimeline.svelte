<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchActivityForEntity } from '$lib/api';
	import type { ActivityLogEntry } from '$lib/types';

	let { entityType, entityId }: { entityType: string; entityId: string } = $props();

	let entries: ActivityLogEntry[] = $state([]);

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

	const CATEGORY_COLORS: Record<string, string> = {
		LIVE: '#3b82f6',
		ACTION_REQUIRED: '#f59e0b',
		DELAYED: '#ef4444'
	};

	function formatTimestamp(dateStr: string): string {
		return new Date(dateStr).toLocaleString();
	}

	onMount(async () => {
		entries = await fetchActivityForEntity(entityType, entityId);
	});
</script>

<div class="timeline">
	{#if entries.length === 0}
		<p class="empty">No activity recorded.</p>
	{:else}
		{#each entries as entry}
			<div class="timeline-entry">
				<div class="timeline-dot" style="background: {CATEGORY_COLORS[entry.category] ?? '#6b7280'}"></div>
				<div class="timeline-body">
					<span class="entry-label">{EVENT_LABELS[entry.event] ?? entry.event}</span>
					{#if entry.detail}
						<p class="entry-detail">{entry.detail}</p>
					{/if}
					<p class="entry-time">{formatTimestamp(entry.created_at)}</p>
				</div>
			</div>
		{/each}
	{/if}
</div>

<style>
	.timeline {
		position: relative;
		padding-left: var(--space-6);
		border-left: 2px solid var(--gray-200);
	}

	.empty {
		color: var(--gray-500);
		font-size: var(--font-size-sm);
		padding-left: var(--space-6);
	}

	.timeline-entry {
		position: relative;
		padding: 0 0 var(--space-5) var(--space-4);
	}

	.timeline-dot {
		position: absolute;
		left: -7px;
		top: 4px;
		width: 12px;
		height: 12px;
		border-radius: 50%;
		border: 2px solid white;
		box-shadow: 0 0 0 1px var(--gray-200);
	}

	.timeline-body {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.entry-label {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-900);
	}

	.entry-detail {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}

	.entry-time {
		font-size: 11px;
		color: var(--gray-400);
	}
</style>
