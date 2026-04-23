<script lang="ts">
	import type { LineItem, UserRole, LineItemStatus } from '$lib/types';

	// SubmitResponseBar is the sticky footer on the Line Items tab. It is
	// visible only when the current actor can submit (PO is PENDING or MODIFIED
	// and the current actor is on the clock). The Submit button stays disabled
	// until every line has been addressed by the current actor.
	let {
		lines,
		role,
		round_count,
		on_submit
	}: {
		lines: LineItem[];
		role: UserRole;
		round_count: number;
		on_submit: () => void;
	} = $props();

	let showConfirm: boolean = $state(false);

	// A line is unaddressed by the current actor if it is PENDING, or if the
	// counterparty just moved and we have not responded. A line the current
	// actor just modified is already addressed from their perspective.
	function isUnaddressed(status: LineItemStatus, currentRole: UserRole): boolean {
		if (status === 'PENDING') return true;
		if (currentRole === 'VENDOR' && status === 'MODIFIED_BY_SM') return true;
		if (currentRole === 'SM' && status === 'MODIFIED_BY_VENDOR') return true;
		return false;
	}

	const unaddressed = $derived(lines.filter((l) => isUnaddressed(l.status, role)));
	const canSubmit = $derived(unaddressed.length === 0 && lines.length > 0);

	const roundLabel = $derived(`Round ${Math.min(round_count + 1, 2)} of 2`);

	// Delta summary: count lines per bucket so the confirm dialog shows what
	// is actually being submitted.
	const summary = $derived(buildSummary(lines));

	function buildSummary(items: LineItem[]): { accepted: number; removed: number; modified: number; pending: number } {
		let accepted = 0;
		let removed = 0;
		let modified = 0;
		let pending = 0;
		for (const l of items) {
			if (l.status === 'ACCEPTED') accepted += 1;
			else if (l.status === 'REMOVED') removed += 1;
			else if (l.status === 'MODIFIED_BY_VENDOR' || l.status === 'MODIFIED_BY_SM') modified += 1;
			else pending += 1;
		}
		return { accepted, removed, modified, pending };
	}
</script>

<div class="submit-response-bar" data-testid="submit-response-bar">
	<span class="round-indicator" data-testid="round-indicator">{roundLabel}</span>
	{#if unaddressed.length > 0}
		<span class="hint" data-testid="unaddressed-hint">
			{unaddressed.length} line{unaddressed.length === 1 ? '' : 's'} still need a decision.
		</span>
	{/if}
	<button
		class="btn btn-primary"
		data-testid="submit-response-btn"
		disabled={!canSubmit}
		onclick={() => (showConfirm = true)}
	>Submit Response</button>
</div>

{#if showConfirm}
	<div class="overlay" data-testid="submit-confirm-dialog">
		<div class="dialog">
			<h3>Submit Response</h3>
			<p>Sending {roundLabel}. Delta:</p>
			<ul class="delta-summary" data-testid="delta-summary">
				<li>Accepted: <strong data-testid="delta-accepted">{summary.accepted}</strong></li>
				<li>Modified: <strong data-testid="delta-modified">{summary.modified}</strong></li>
				<li>Removed: <strong data-testid="delta-removed">{summary.removed}</strong></li>
			</ul>
			<div class="dialog-actions">
				<button class="btn btn-secondary" onclick={() => (showConfirm = false)}>Cancel</button>
				<button
					class="btn btn-primary"
					data-testid="submit-confirm-btn"
					onclick={() => {
						showConfirm = false;
						on_submit();
					}}
				>Confirm</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.submit-response-bar {
		position: sticky;
		bottom: 0;
		background-color: white;
		border-top: 1px solid var(--gray-200);
		padding: var(--space-3);
		display: flex;
		align-items: center;
		gap: var(--space-4);
		box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.04);
	}

	.round-indicator {
		font-weight: 600;
		color: var(--gray-800);
	}

	.hint {
		color: var(--amber-800, #92400e);
		font-size: var(--font-size-sm);
		flex: 1;
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
		max-width: 440px;
		width: 100%;
	}

	.delta-summary {
		list-style: none;
		padding: 0;
		margin: var(--space-3) 0;
	}

	.delta-summary li {
		padding: var(--space-1) 0;
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		margin-top: var(--space-4);
	}
</style>
