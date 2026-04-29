<script lang="ts">
	import type { LineItem, LineItemStatus } from '$lib/types';
	import type { ModifyLineFields } from '$lib/api';
	import Button from '$lib/ui/Button.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import PoLineModifyModal from './PoLineModifyModal.svelte';
	import PoLineDiff from './PoLineDiff.svelte';
	import PoLineEditHistoryTimeline from './PoLineEditHistoryTimeline.svelte';

	type NegotiationRole = 'VENDOR' | 'SM';

	type StatusToneEntry = {
		readonly tone: 'gray' | 'green' | 'blue' | 'orange' | 'red';
		readonly label: string;
	};

	const STATUS_DISPLAY: Readonly<Record<LineItemStatus, StatusToneEntry>> = {
		PENDING: { tone: 'gray', label: 'Pending' },
		MODIFIED_BY_VENDOR: { tone: 'blue', label: 'Modified by vendor' },
		MODIFIED_BY_SM: { tone: 'orange', label: 'Modified by SM' },
		ACCEPTED: { tone: 'green', label: 'Accepted' },
		REMOVED: { tone: 'red', label: 'Removed' },
		REJECTED: { tone: 'red', label: 'Rejected' }
	};

	let {
		line,
		role,
		round_count,
		error,
		on_modify,
		on_accept,
		on_remove,
		on_force_accept,
		on_force_remove,
		'data-testid': testid
	}: {
		line: LineItem;
		role: NegotiationRole;
		round_count: number;
		error?: string;
		on_modify: (partNumber: string, fields: ModifyLineFields) => void;
		on_accept: (partNumber: string) => void;
		on_remove: (partNumber: string) => void;
		on_force_accept: (partNumber: string) => void;
		on_force_remove: (partNumber: string) => void;
		'data-testid'?: string;
	} = $props();

	let showModifyModal: boolean = $state(false);
	let showForceAcceptConfirm: boolean = $state(false);
	let showForceRemoveConfirm: boolean = $state(false);
	let detailsExpanded: boolean = $state(false);

	const isTerminal = $derived(line.status === 'ACCEPTED' || line.status === 'REMOVED');

	const canAccept = $derived(
		!isTerminal &&
			((role === 'VENDOR' && line.status === 'MODIFIED_BY_SM') ||
				(role === 'SM' && line.status === 'MODIFIED_BY_VENDOR'))
	);

	const canModify = $derived(
		!isTerminal &&
			(line.status === 'PENDING' ||
				line.status === 'MODIFIED_BY_VENDOR' ||
				line.status === 'MODIFIED_BY_SM')
	);
	const canRemove = $derived(canModify);

	const canForce = $derived(
		role === 'SM' &&
			round_count === 2 &&
			(line.status === 'MODIFIED_BY_VENDOR' || line.status === 'MODIFIED_BY_SM')
	);

	const hasHistory = $derived((line.history ?? []).length > 0);
	const display = $derived(STATUS_DISPLAY[line.status]);

	function onModifySubmit(fields: ModifyLineFields): void {
		showModifyModal = false;
		on_modify(line.part_number, fields);
	}

	function formatPrice(value: string): string {
		const n = parseFloat(value);
		if (Number.isNaN(n)) return value;
		return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}
</script>

<article
	class="po-line-row"
	data-status={line.status}
	data-testid={testid ?? `po-line-${line.part_number}`}
>
	<header class="po-line-row__head">
		<div class="po-line-row__title">
			<span class="po-line-row__part">{line.part_number}</span>
			<span class="po-line-row__desc">{line.description}</span>
		</div>
		<StatusPill
			tone={display.tone}
			label={display.label}
			data-testid="po-line-status-{line.part_number}"
		/>
	</header>

	<dl class="po-line-row__fields">
		<div class="po-line-row__field">
			<dt>Qty</dt>
			<dd>{line.quantity}</dd>
		</div>
		<div class="po-line-row__field">
			<dt>UoM</dt>
			<dd>{line.uom}</dd>
		</div>
		<div class="po-line-row__field">
			<dt>Unit price</dt>
			<dd>{formatPrice(line.unit_price)}</dd>
		</div>
		<div class="po-line-row__field">
			<dt>HS code</dt>
			<dd>{line.hs_code}</dd>
		</div>
		<div class="po-line-row__field">
			<dt>Origin</dt>
			<dd>{line.country_of_origin}</dd>
		</div>
	</dl>

	<div class="po-line-row__actions" data-testid="po-line-actions-{line.part_number}">
		{#if canAccept}
			<Button
				onclick={() => on_accept(line.part_number)}
				data-testid="po-line-action-accept-{line.part_number}"
			>
				Accept
			</Button>
		{/if}
		{#if canModify}
			<Button
				variant="secondary"
				onclick={() => (showModifyModal = true)}
				data-testid="po-line-action-modify-{line.part_number}"
			>
				Modify
			</Button>
		{/if}
		{#if canRemove}
			<Button
				variant="ghost"
				onclick={() => on_remove(line.part_number)}
				data-testid="po-line-action-remove-{line.part_number}"
			>
				Remove
			</Button>
		{/if}
		{#if canForce}
			<Button
				variant="secondary"
				onclick={() => (showForceAcceptConfirm = true)}
				data-testid="po-line-action-force-accept-{line.part_number}"
			>
				Force Accept
			</Button>
			<Button
				variant="secondary"
				onclick={() => (showForceRemoveConfirm = true)}
				data-testid="po-line-action-force-remove-{line.part_number}"
			>
				Force Remove
			</Button>
		{/if}
	</div>

	{#if error}
		<p
			class="po-line-row__error"
			role="alert"
			data-testid="po-line-error-{line.part_number}"
		>
			{error}
		</p>
	{/if}

	{#if hasHistory}
		<div class="po-line-row__details">
			<button
				type="button"
				class="po-line-row__toggle"
				aria-expanded={detailsExpanded}
				onclick={() => (detailsExpanded = !detailsExpanded)}
				data-testid="po-line-details-toggle-{line.part_number}"
			>
				{detailsExpanded ? 'Hide changes' : 'View changes'}
			</button>
			{#if detailsExpanded}
				<div class="po-line-row__details-body">
					<PoLineDiff {line} />
					<PoLineEditHistoryTimeline {line} />
				</div>
			{/if}
		</div>
	{/if}
</article>

{#if showModifyModal}
	<PoLineModifyModal
		{line}
		onSubmit={onModifySubmit}
		onCancel={() => (showModifyModal = false)}
	/>
{/if}

{#if showForceAcceptConfirm}
	<div
		class="po-line-confirm"
		role="dialog"
		aria-modal="true"
		aria-labelledby="po-line-force-accept-title-{line.part_number}"
		data-testid="po-line-force-accept-confirm-{line.part_number}"
	>
		<div class="po-line-confirm__card">
			<h3 id="po-line-force-accept-title-{line.part_number}" class="po-line-confirm__title">
				Force accept {line.part_number}
			</h3>
			<p class="po-line-confirm__body">
				This locks the line at the latest values and ends negotiation for it.
			</p>
			<div class="po-line-confirm__footer">
				<Button variant="secondary" onclick={() => (showForceAcceptConfirm = false)}>
					Cancel
				</Button>
				<Button
					onclick={() => {
						showForceAcceptConfirm = false;
						on_force_accept(line.part_number);
					}}
					data-testid="po-line-action-force-accept-confirm-{line.part_number}"
				>
					Force Accept
				</Button>
			</div>
		</div>
	</div>
{/if}

{#if showForceRemoveConfirm}
	<div
		class="po-line-confirm"
		role="dialog"
		aria-modal="true"
		aria-labelledby="po-line-force-remove-title-{line.part_number}"
		data-testid="po-line-force-remove-confirm-{line.part_number}"
	>
		<div class="po-line-confirm__card">
			<h3 id="po-line-force-remove-title-{line.part_number}" class="po-line-confirm__title">
				Force remove {line.part_number}
			</h3>
			<p class="po-line-confirm__body">
				This drops the line from the PO and ends negotiation for it.
			</p>
			<div class="po-line-confirm__footer">
				<Button variant="secondary" onclick={() => (showForceRemoveConfirm = false)}>
					Cancel
				</Button>
				<Button
					onclick={() => {
						showForceRemoveConfirm = false;
						on_force_remove(line.part_number);
					}}
					data-testid="po-line-action-force-remove-confirm-{line.part_number}"
				>
					Force Remove
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	.po-line-row {
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.po-line-row[data-status='ACCEPTED'] {
		border-color: var(--dot-green);
	}
	.po-line-row[data-status='REMOVED'] {
		opacity: 0.7;
	}
	.po-line-row__head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-3);
	}
	.po-line-row__title {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		min-width: 0;
	}
	.po-line-row__part {
		font-weight: 600;
		font-size: var(--font-size-base);
		color: var(--gray-900);
	}
	.po-line-row__desc {
		color: var(--gray-600);
		font-size: var(--font-size-sm);
	}
	.po-line-row__fields {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: var(--space-3);
		margin: 0;
	}
	.po-line-row__field {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.po-line-row__field dt {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
		letter-spacing: var(--letter-spacing-wide);
		text-transform: uppercase;
		margin: 0;
	}
	.po-line-row__field dd {
		font-size: var(--font-size-sm);
		color: var(--gray-900);
		font-weight: 500;
		margin: 0;
	}
	.po-line-row__actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}
	.po-line-row__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		margin: 0;
	}
	.po-line-row__toggle {
		align-self: flex-start;
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		font-size: var(--font-size-sm);
		color: var(--brand-accent);
		cursor: pointer;
	}
	.po-line-row__toggle:hover {
		text-decoration: underline;
	}
	.po-line-row__details {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		border-top: 1px solid var(--gray-100);
		padding-top: var(--space-3);
	}
	.po-line-row__details-body {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.po-line-confirm {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 110;
		padding: var(--space-4);
	}
	.po-line-confirm__card {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		padding: var(--space-6);
		max-width: 28rem;
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.po-line-confirm__title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.po-line-confirm__body {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0;
	}
	.po-line-confirm__footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}
	@media (max-width: 640px) {
		.po-line-row__head {
			flex-direction: column;
			align-items: flex-start;
		}
		.po-line-row__actions :global(.ui-btn) {
			flex: 1 1 calc(50% - var(--space-2));
		}
	}
</style>
