<script lang="ts">
	import { onMount } from 'svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import ActivityFeed from '$lib/ui/ActivityFeed.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import Button from '$lib/ui/Button.svelte';
	import { fetchActivityForEntity } from '$lib/api';
	import { EVENT_LABELS, categoryToTone } from '$lib/po/event-labels';
	import type { ActivityLogEntry } from '$lib/types';

	let {
		poId,
		mockEntries
	}: {
		poId: string;
		mockEntries?: ActivityLogEntry[];
	} = $props();

	let entries: ActivityLogEntry[] = $state([]);
	let visibleCount: number = $state(10);
	let loading: boolean = $state(true);

	function formatTimestamp(s: string): string {
		return new Date(s).toLocaleString();
	}

	onMount(async () => {
		if (mockEntries !== undefined) {
			entries = mockEntries;
			loading = false;
			return;
		}
		entries = await fetchActivityForEntity('PO', poId);
		loading = false;
	});

	const feedEntries = $derived(
		entries.slice(0, visibleCount).map((entry) => ({
			id: entry.id,
			primary: EVENT_LABELS[entry.event as keyof typeof EVENT_LABELS] ?? entry.event,
			secondary: entry.detail
				? `${formatTimestamp(entry.created_at)} · ${entry.detail}`
				: formatTimestamp(entry.created_at),
			tone: categoryToTone(entry.category)
		}))
	);

	function showMore() {
		visibleCount += 10;
	}
</script>

<PanelCard title="Activity" data-testid="po-activity-panel">
	{#snippet children()}
		{#if loading}
			<LoadingState />
		{:else if entries.length === 0}
			<EmptyState title="No activity yet." />
		{:else}
			<ActivityFeed entries={feedEntries} data-testid="po-activity-feed" />
			{#if visibleCount < entries.length}
				<div class="show-more">
					<Button variant="ghost" onclick={showMore} data-testid="po-activity-show-more-btn">
						Show more
					</Button>
				</div>
			{/if}
		{/if}
	{/snippet}
</PanelCard>

<style>
	.show-more {
		display: flex;
		justify-content: center;
		padding-top: var(--space-3);
	}
</style>
