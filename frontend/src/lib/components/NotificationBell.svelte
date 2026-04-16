<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { fetchUnreadCount, fetchActivity, markActivityRead } from '$lib/api';
	import type { ActivityLogEntry } from '$lib/types';

	const role = $derived(page.data.user?.role);

	let unreadCount: number = $state(0);
	let open: boolean = $state(false);
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

	function relativeTime(dateStr: string): string {
		const diffMs = Date.now() - new Date(dateStr).getTime();
		const diffMin = Math.floor(diffMs / 60000);
		if (diffMin < 1) return 'just now';
		if (diffMin < 60) return `${diffMin}m ago`;
		const diffHr = Math.floor(diffMin / 60);
		if (diffHr < 24) return `${diffHr}h ago`;
		return `${Math.floor(diffHr / 24)}d ago`;
	}

	async function refreshCount() {
		const result = await fetchUnreadCount(role);
		unreadCount = result.count;
	}

	async function toggleDropdown() {
		if (open) {
			open = false;
			return;
		}
		entries = await fetchActivity(10, role);
		open = true;
	}

	async function handleMarkAllRead() {
		await markActivityRead();
		unreadCount = 0;
		entries = [];
		open = false;
	}

	function navigateToEntity(entry: ActivityLogEntry) {
		open = false;
		const path = entry.entity_type === 'PO' ? `/po/${entry.entity_id}` : `/invoice/${entry.entity_id}`;
		goto(path);
	}

	onMount(() => {
		refreshCount();
	});
</script>

<div class="bell-wrapper">
	<button class="bell-btn" onclick={toggleDropdown}>
		<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
			<path d="M10 2a6 6 0 00-6 6v3l-1.5 2H17.5L16 11V8a6 6 0 00-6-6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" fill="none"/>
			<path d="M8.5 16a1.5 1.5 0 003 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
		</svg>
		{#if unreadCount > 0}
			<span class="badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
		{/if}
	</button>

	{#if open}
		<div class="overlay" onclick={() => (open = false)}></div>
		<div class="dropdown">
			{#if entries.length === 0}
				<p class="empty">No recent notifications.</p>
			{:else}
				{#each entries as entry}
					<div class="dropdown-item" onclick={() => navigateToEntity(entry)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && navigateToEntity(entry)}>
						<div class="item-main">
							<span class="item-label">{EVENT_LABELS[entry.event] ?? entry.event}</span>
							<span class="item-time">{relativeTime(entry.created_at)}</span>
						</div>
						{#if entry.detail}
							<p class="item-detail">{entry.detail}</p>
						{/if}
					</div>
				{/each}
			{/if}
			<div class="dropdown-footer">
				<button class="mark-read-btn" onclick={handleMarkAllRead}>Mark all read</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.bell-wrapper {
		position: relative;
	}

	.bell-btn {
		position: relative;
		background: none;
		border: none;
		cursor: pointer;
		color: var(--gray-600);
		padding: var(--space-1);
		display: flex;
		align-items: center;
	}

	.bell-btn:hover {
		color: var(--gray-900);
	}

	.badge {
		position: absolute;
		top: -2px;
		right: -4px;
		background: var(--red-600, #dc2626);
		color: white;
		font-size: 10px;
		min-width: 16px;
		height: 16px;
		border-radius: 9999px;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0 3px;
		line-height: 1;
	}

	.overlay {
		position: fixed;
		inset: 0;
		z-index: 99;
	}

	.dropdown {
		position: absolute;
		top: calc(100% + 8px);
		right: 0;
		width: 320px;
		max-height: 400px;
		overflow-y: auto;
		background: white;
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md, 6px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		z-index: 100;
	}

	.empty {
		padding: var(--space-4);
		color: var(--gray-500);
		font-size: var(--font-size-sm);
		text-align: center;
	}

	.dropdown-item {
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--gray-100);
		cursor: pointer;
	}

	.dropdown-item:hover {
		background: var(--gray-50, #f9fafb);
	}

	.item-main {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--space-2);
	}

	.item-label {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-900);
	}

	.item-time {
		font-size: 11px;
		color: var(--gray-400);
		white-space: nowrap;
	}

	.item-detail {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-top: var(--space-1);
	}

	.dropdown-footer {
		padding: var(--space-2) var(--space-4);
		border-top: 1px solid var(--gray-100);
	}

	.mark-read-btn {
		width: 100%;
		background: none;
		border: none;
		cursor: pointer;
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		padding: var(--space-1) 0;
		text-align: center;
	}

	.mark-read-btn:hover {
		color: var(--gray-700);
	}
</style>
