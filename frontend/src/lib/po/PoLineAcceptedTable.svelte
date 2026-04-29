<script lang="ts">
	import type { LineItem, LineItemStatus, POType, UserRole } from '$lib/types';
	import Button from '$lib/ui/Button.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';

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
		lines,
		role,
		po_type,
		cert_required,
		remaining_map,
		gate_closed,
		errors = new Map(),
		on_remove = null,
		resolve_country = (code: string) => code,
		label = 'Accepted line items',
		'data-testid': testid
	}: {
		lines: LineItem[];
		role: UserRole | null;
		po_type: POType;
		cert_required: Set<string>;
		remaining_map: Map<string, { invoiced: number; remaining: number }>;
		gate_closed: boolean;
		errors?: Map<string, string>;
		on_remove?: ((part_number: string) => Promise<void>) | null;
		resolve_country?: (code: string) => string;
		label?: string;
		'data-testid'?: string;
	} = $props();

	const showRemainingColumns = $derived(po_type === 'PROCUREMENT');

	function formatPrice(value: string): string {
		const n = parseFloat(value);
		if (Number.isNaN(n)) return value;
		return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}

	function canRemove(line: LineItem): boolean {
		return on_remove != null && !gate_closed && line.status !== 'REMOVED';
	}
</script>

<section
	class="ui-po-accepted-table"
	aria-label={label}
	data-testid={testid ?? 'po-accepted-table'}
>
	{#each lines as line (line.part_number)}
		{@const display = STATUS_DISPLAY[line.status]}
		{@const remaining = remaining_map.get(line.part_number)}
		<article
			class="ui-po-accepted-table__row"
			data-status={line.status}
			data-testid="po-accepted-line-{line.part_number}"
		>
			<header class="ui-po-accepted-table__head">
				<div class="ui-po-accepted-table__title">
					<span class="ui-po-accepted-table__part">{line.part_number}</span>
					<span class="ui-po-accepted-table__desc">{line.description}</span>
				</div>
				<div class="ui-po-accepted-table__badges">
					{#if cert_required.has(line.part_number)}
						<span class="ui-po-accepted-table__cert-badge" data-testid="po-accepted-cert-{line.part_number}">
							Cert required
						</span>
					{/if}
					<StatusPill
						tone={display.tone}
						label={display.label}
						data-testid="po-accepted-status-{line.part_number}"
					/>
				</div>
			</header>

			<dl class="ui-po-accepted-table__fields">
				<div class="ui-po-accepted-table__field">
					<dt>Qty</dt>
					<dd>{line.quantity}</dd>
				</div>
				<div class="ui-po-accepted-table__field">
					<dt>UoM</dt>
					<dd>{line.uom}</dd>
				</div>
				<div class="ui-po-accepted-table__field">
					<dt>Unit price</dt>
					<dd>{formatPrice(line.unit_price)}</dd>
				</div>
				<div class="ui-po-accepted-table__field">
					<dt>HS code</dt>
					<dd>{line.hs_code}</dd>
				</div>
				<div class="ui-po-accepted-table__field">
					<dt>Origin</dt>
					<dd>{resolve_country(line.country_of_origin)}</dd>
				</div>
				{#if showRemainingColumns}
					<div class="ui-po-accepted-table__field" data-testid="po-accepted-invoiced-{line.part_number}">
						<dt>Invoiced</dt>
						<dd>{remaining ? remaining.invoiced : 0}</dd>
					</div>
					<div class="ui-po-accepted-table__field" data-testid="po-accepted-remaining-{line.part_number}">
						<dt>Remaining</dt>
						<dd>{remaining ? remaining.remaining : 0}</dd>
					</div>
				{/if}
			</dl>

			{#if canRemove(line)}
				<div class="ui-po-accepted-table__actions">
					<Button
						variant="ghost"
						onclick={() => on_remove && on_remove(line.part_number)}
						data-testid="po-accepted-remove-{line.part_number}"
					>
						Remove
					</Button>
				</div>
			{/if}

			{#if errors.get(line.part_number)}
				<p
					class="ui-po-accepted-table__error"
					role="alert"
					data-testid="po-accepted-error-{line.part_number}"
				>
					{errors.get(line.part_number)}
				</p>
			{/if}
		</article>
	{/each}

	{#if lines.length === 0}
		<p class="ui-po-accepted-table__empty">No line items.</p>
	{/if}
</section>

<style>
	.ui-po-accepted-table {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.ui-po-accepted-table__row {
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.ui-po-accepted-table__row[data-status='ACCEPTED'] {
		border-color: var(--dot-green);
	}
	.ui-po-accepted-table__row[data-status='REMOVED'] {
		opacity: 0.7;
	}
	.ui-po-accepted-table__head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-3);
	}
	.ui-po-accepted-table__title {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		min-width: 0;
	}
	.ui-po-accepted-table__part {
		font-weight: 600;
		font-size: var(--font-size-base);
		color: var(--gray-900);
	}
	.ui-po-accepted-table__desc {
		color: var(--gray-600);
		font-size: var(--font-size-sm);
	}
	.ui-po-accepted-table__badges {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: var(--space-2);
	}
	.ui-po-accepted-table__cert-badge {
		display: inline-flex;
		align-items: center;
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-xs);
		font-weight: 500;
		border-radius: 999px;
		background-color: #fef3c7;
		color: #92400e;
	}
	.ui-po-accepted-table__fields {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: var(--space-3);
		margin: 0;
	}
	.ui-po-accepted-table__field {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.ui-po-accepted-table__field dt {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
		letter-spacing: var(--letter-spacing-wide);
		text-transform: uppercase;
		margin: 0;
	}
	.ui-po-accepted-table__field dd {
		font-size: var(--font-size-sm);
		color: var(--gray-900);
		font-weight: 500;
		margin: 0;
	}
	.ui-po-accepted-table__actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}
	.ui-po-accepted-table__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		margin: 0;
	}
	.ui-po-accepted-table__empty {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
	@media (max-width: 640px) {
		.ui-po-accepted-table__head {
			flex-direction: column;
			align-items: flex-start;
		}
		.ui-po-accepted-table__badges {
			align-items: flex-start;
		}
	}
</style>
