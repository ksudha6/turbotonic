<script lang="ts">
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import type { POStatus } from '$lib/types';

	let {
		status,
		partial = false,
		'data-testid': testid
	}: { status: POStatus; partial?: boolean; 'data-testid'?: string } = $props();

	const STATUS_TONE: Readonly<Record<POStatus, 'gray' | 'orange' | 'green' | 'red' | 'blue'>> = {
		DRAFT: 'gray',
		PENDING: 'orange',
		MODIFIED: 'orange',
		ACCEPTED: 'green',
		REJECTED: 'red',
		REVISED: 'blue'
	};

	const STATUS_LABEL: Readonly<Record<POStatus, string>> = {
		DRAFT: 'Draft',
		PENDING: 'Pending',
		MODIFIED: 'Modified',
		ACCEPTED: 'Accepted',
		REJECTED: 'Rejected',
		REVISED: 'Revised'
	};

	const showPartial = $derived(status === 'ACCEPTED' && partial);
</script>

<span class="po-status-pills" data-testid={testid}>
	<StatusPill tone={STATUS_TONE[status]} label={STATUS_LABEL[status]} />
	{#if showPartial}
		<span data-testid="po-status-partial">
			<StatusPill tone="orange" label="Partial" />
		</span>
	{/if}
</span>

<style>
	.po-status-pills {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
	}
</style>
