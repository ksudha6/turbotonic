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
		// Iter 058: per-line negotiation events. The timeline surfaces one row per
		// triggering action; the detail field carries the part_number and, for
		// modify events, the sorted list of changed field names.
		PO_LINE_MODIFIED: 'Line modified',
		PO_LINE_ACCEPTED: 'Line accepted',
		PO_LINE_REMOVED: 'Line removed',
		PO_FORCE_ACCEPTED: 'Override: line force-accepted',
		PO_FORCE_REMOVED: 'Override: line force-removed',
		PO_MODIFIED: 'Round submitted',
		PO_CONVERGED: 'Negotiation converged',
		INVOICE_CREATED: 'Invoice created',
		INVOICE_SUBMITTED: 'Invoice submitted',
		INVOICE_APPROVED: 'Invoice approved',
		INVOICE_PAID: 'Invoice paid',
		INVOICE_DISPUTED: 'Invoice disputed',
		MILESTONE_POSTED: 'Milestone posted',
		MILESTONE_OVERDUE: 'Milestone overdue'
	};

	// Iter 058: per-event icon glyph for the negotiation events. Icons stay minimal
	// so the timeline does not require an icon library.
	const EVENT_ICONS: Record<string, string> = {
		PO_LINE_MODIFIED: 'pencil',
		PO_LINE_ACCEPTED: 'check',
		PO_LINE_REMOVED: 'x',
		PO_FORCE_ACCEPTED: 'shield-check',
		PO_FORCE_REMOVED: 'shield-x',
		PO_MODIFIED: 'arrow-right',
		PO_CONVERGED: 'flag'
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
					<span class="entry-label">
						{#if EVENT_ICONS[entry.event]}
							<span class="entry-icon" data-icon={EVENT_ICONS[entry.event]} aria-hidden="true"></span>
						{/if}
						{EVENT_LABELS[entry.event] ?? entry.event}
					</span>
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
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}

	/* Iter 058: small glyph marker per event type. data-icon carries the name so
	   the icon is observable in markup without pulling in an icon library. */
	.entry-icon {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 2px;
		background-color: var(--gray-400);
	}

	.entry-icon[data-icon='check'] { background-color: #10b981; }
	.entry-icon[data-icon='x'] { background-color: #ef4444; }
	.entry-icon[data-icon='pencil'] { background-color: #3b82f6; }
	.entry-icon[data-icon='arrow-right'] { background-color: #f59e0b; }
	.entry-icon[data-icon='flag'] { background-color: #6366f1; }
	.entry-icon[data-icon='shield-check'] { background-color: #059669; }
	.entry-icon[data-icon='shield-x'] { background-color: #b91c1c; }

	.entry-detail {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}

	.entry-time {
		font-size: 11px;
		color: var(--gray-400);
	}
</style>
