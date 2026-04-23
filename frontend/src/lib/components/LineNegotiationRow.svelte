<script lang="ts">
	import type { LineItem, UserRole, LineItemStatus } from '$lib/types';
	import type { ModifyLineFields } from '$lib/api';
	import ModifyLineModal from './ModifyLineModal.svelte';
	import LineDiff from './LineDiff.svelte';
	import EditHistoryTimeline from './EditHistoryTimeline.svelte';

	// LineNegotiationRow renders one line under negotiation. The five callback
	// props are the actions the row can surface; the consumer hooks them up to
	// the API client and handles errors/refreshes.
	let {
		line,
		role,
		round_count,
		on_modify,
		on_accept,
		on_remove,
		on_force_accept,
		on_force_remove
	}: {
		line: LineItem;
		role: UserRole;
		round_count: number;
		on_modify: (partNumber: string, fields: ModifyLineFields) => void;
		on_accept: (partNumber: string) => void;
		on_remove: (partNumber: string) => void;
		on_force_accept: (partNumber: string) => void;
		on_force_remove: (partNumber: string) => void;
	} = $props();

	let showModifyModal: boolean = $state(false);
	let showForceAcceptConfirm: boolean = $state(false);
	let showForceRemoveConfirm: boolean = $state(false);

	// A line is terminal once either party accepts it or it is removed. No more
	// actions are offered.
	const isTerminal = $derived(line.status === 'ACCEPTED' || line.status === 'REMOVED');

	// VENDOR acts when SM just moved; SM acts when VENDOR just moved. Accept is
	// only offered when the counterparty is the last editor.
	const canAccept = $derived(
		!isTerminal &&
			((role === 'VENDOR' && line.status === 'MODIFIED_BY_SM') ||
				(role === 'SM' && line.status === 'MODIFIED_BY_VENDOR'))
	);

	// Modify and (pre-acceptance) remove are offered on PENDING and on any
	// MODIFIED_BY_* state regardless of last editor. This lets an actor fall
	// back to a counter-propose or a removal even if the counterparty hasn't
	// moved yet.
	const canModify = $derived(
		!isTerminal && (line.status === 'PENDING' || line.status === 'MODIFIED_BY_VENDOR' || line.status === 'MODIFIED_BY_SM')
	);
	const canRemove = $derived(canModify);

	// Force actions are terminal overrides available only to SM at round 2 on
	// lines still in a MODIFIED_BY_* state. PENDING lines at round 2 still need
	// a regular accept/remove before force becomes relevant.
	const canForce = $derived(
		role === 'SM' &&
			round_count === 2 &&
			(line.status === 'MODIFIED_BY_VENDOR' || line.status === 'MODIFIED_BY_SM')
	);

	function statusLabel(s: LineItemStatus): string {
		switch (s) {
			case 'PENDING':
				return 'Pending';
			case 'ACCEPTED':
				return 'Accepted';
			case 'MODIFIED_BY_VENDOR':
				return 'Modified by vendor';
			case 'MODIFIED_BY_SM':
				return 'Modified by SM';
			case 'REMOVED':
				return 'Removed';
			case 'REJECTED':
				return 'Rejected';
			default:
				return s;
		}
	}

	function statusClass(s: LineItemStatus): string {
		return `line-status line-status-${s.toLowerCase()}`;
	}

	function onModifySubmit(fields: ModifyLineFields) {
		showModifyModal = false;
		on_modify(line.part_number, fields);
	}
</script>

<div class="line-row" data-testid="line-row-{line.part_number}" data-status={line.status}>
	<div class="line-header">
		<div class="line-title">
			<span class="part-number">{line.part_number}</span>
			<span class="description">{line.description}</span>
		</div>
		<span class={statusClass(line.status)} data-testid="line-status-{line.part_number}">
			{statusLabel(line.status)}
		</span>
	</div>

	<div class="line-fields">
		<div class="field">
			<span class="field-label">Qty</span>
			<span class="field-value">{line.quantity}</span>
		</div>
		<div class="field">
			<span class="field-label">UoM</span>
			<span class="field-value">{line.uom}</span>
		</div>
		<div class="field">
			<span class="field-label">Unit price</span>
			<span class="field-value">{line.unit_price}</span>
		</div>
		<div class="field">
			<span class="field-label">HS code</span>
			<span class="field-value">{line.hs_code}</span>
		</div>
		<div class="field">
			<span class="field-label">Origin</span>
			<span class="field-value">{line.country_of_origin}</span>
		</div>
	</div>

	<div class="line-actions" data-testid="line-actions-{line.part_number}">
		{#if canModify}
			<button
				class="btn btn-secondary btn-sm"
				data-testid="modify-btn-{line.part_number}"
				onclick={() => (showModifyModal = true)}
			>Modify</button>
		{/if}
		{#if canAccept}
			<button
				class="btn btn-success btn-sm"
				data-testid="accept-btn-{line.part_number}"
				onclick={() => on_accept(line.part_number)}
			>Accept</button>
		{/if}
		{#if canRemove}
			<button
				class="btn btn-danger btn-sm"
				data-testid="remove-btn-{line.part_number}"
				onclick={() => on_remove(line.part_number)}
			>Remove</button>
		{/if}
		{#if canForce}
			<button
				class="btn btn-warning btn-sm"
				data-testid="force-accept-btn-{line.part_number}"
				onclick={() => (showForceAcceptConfirm = true)}
			>Force Accept</button>
			<button
				class="btn btn-warning btn-sm"
				data-testid="force-remove-btn-{line.part_number}"
				onclick={() => (showForceRemoveConfirm = true)}
			>Force Remove</button>
		{/if}
	</div>

	{#if (line.history ?? []).length > 0}
		<LineDiff {line} />
	{/if}

	<EditHistoryTimeline {line} />
</div>

{#if showModifyModal}
	<ModifyLineModal
		{line}
		onSubmit={onModifySubmit}
		onCancel={() => (showModifyModal = false)}
	/>
{/if}

{#if showForceAcceptConfirm}
	<div class="overlay" data-testid="force-accept-confirm">
		<div class="dialog">
			<h3>Force accept {line.part_number}</h3>
			<p>This overrides the negotiation for {line.part_number} and is terminal.</p>
			<div class="dialog-actions">
				<button class="btn btn-secondary" onclick={() => (showForceAcceptConfirm = false)}>Cancel</button>
				<button
					class="btn btn-warning"
					data-testid="force-accept-confirm-btn"
					onclick={() => {
						showForceAcceptConfirm = false;
						on_force_accept(line.part_number);
					}}
				>Force Accept</button>
			</div>
		</div>
	</div>
{/if}

{#if showForceRemoveConfirm}
	<div class="overlay" data-testid="force-remove-confirm">
		<div class="dialog">
			<h3>Force remove {line.part_number}</h3>
			<p>This overrides the negotiation for {line.part_number} and is terminal.</p>
			<div class="dialog-actions">
				<button class="btn btn-secondary" onclick={() => (showForceRemoveConfirm = false)}>Cancel</button>
				<button
					class="btn btn-warning"
					data-testid="force-remove-confirm-btn"
					onclick={() => {
						showForceRemoveConfirm = false;
						on_force_remove(line.part_number);
					}}
				>Force Remove</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.line-row {
		border: 1px solid var(--gray-200);
		border-radius: var(--radius);
		padding: var(--space-3);
		margin-bottom: var(--space-3);
		background-color: white;
	}

	.line-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-2);
	}

	.line-title {
		display: flex;
		gap: var(--space-3);
		align-items: baseline;
	}

	.part-number {
		font-weight: 600;
		font-size: var(--font-size-base);
	}

	.description {
		color: var(--gray-600);
		font-size: var(--font-size-sm);
	}

	.line-fields {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-4);
		margin-bottom: var(--space-2);
	}

	.field {
		display: flex;
		flex-direction: column;
		font-size: var(--font-size-sm);
	}

	.field-label {
		color: var(--gray-500);
	}

	.field-value {
		color: var(--gray-900);
		font-weight: 500;
	}

	.line-status {
		display: inline-block;
		font-size: var(--font-size-sm);
		padding: 2px 8px;
		border-radius: var(--radius);
		background-color: var(--gray-100);
		color: var(--gray-700);
	}

	.line-status-pending { background-color: var(--gray-100); color: var(--gray-700); }
	.line-status-accepted { background-color: #d1fae5; color: #065f46; }
	.line-status-modified_by_vendor { background-color: #dbeafe; color: #1e40af; }
	.line-status-modified_by_sm { background-color: #fef3c7; color: #92400e; }
	.line-status-removed { background-color: #fee2e2; color: #991b1b; }
	.line-status-rejected { background-color: #fee2e2; color: #991b1b; }

	.line-actions {
		display: flex;
		gap: var(--space-2);
		flex-wrap: wrap;
		margin-bottom: var(--space-2);
	}

	.btn-sm {
		padding: 4px 10px;
		font-size: var(--font-size-sm);
	}

	.btn-warning {
		background-color: #f59e0b;
		color: white;
		border: none;
		border-radius: var(--radius);
		cursor: pointer;
	}

	.btn-warning:hover {
		background-color: #d97706;
	}

	.overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.dialog {
		background-color: white;
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		padding: var(--space-6);
		max-width: 480px;
		width: 100%;
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		margin-top: var(--space-4);
	}
</style>
