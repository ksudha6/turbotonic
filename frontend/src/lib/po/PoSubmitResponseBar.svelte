<script lang="ts">
	import type { LineItem, LineItemStatus } from '$lib/types';
	import Button from '$lib/ui/Button.svelte';

	type NegotiationRole = 'VENDOR' | 'SM';

	const ROUND_CAP = 2;

	let {
		lines,
		role,
		round_count,
		error,
		on_submit,
		'data-testid': testid
	}: {
		lines: LineItem[];
		role: NegotiationRole;
		round_count: number;
		error?: string;
		on_submit: () => void;
		'data-testid'?: string;
	} = $props();

	let showConfirm: boolean = $state(false);

	function isUnaddressed(status: LineItemStatus, currentRole: NegotiationRole): boolean {
		if (status === 'PENDING') return true;
		if (currentRole === 'VENDOR' && status === 'MODIFIED_BY_SM') return true;
		if (currentRole === 'SM' && status === 'MODIFIED_BY_VENDOR') return true;
		return false;
	}

	type Summary = {
		readonly accepted: number;
		readonly removed: number;
		readonly modified: number;
		readonly pending: number;
	};

	function buildSummary(items: LineItem[]): Summary {
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

	const unaddressed = $derived(lines.filter((l) => isUnaddressed(l.status, role)));
	const canSubmit = $derived(unaddressed.length === 0 && lines.length > 0);
	const nextRound = $derived(Math.min(round_count + 1, ROUND_CAP));
	const roundLabel = $derived(`Round ${nextRound} of ${ROUND_CAP}`);
	const summary = $derived(buildSummary(lines));
	const lastRoundWarning = $derived(round_count === 1);

	const titleId = crypto.randomUUID();
</script>

<div
	class="po-submit-bar"
	role="region"
	aria-labelledby={titleId}
	data-testid={testid ?? 'po-submit-response-bar'}
>
	<div class="po-submit-bar__inner">
		<div class="po-submit-bar__meta">
			<span id={titleId} class="po-submit-bar__round" data-testid="po-submit-response-round">
				{roundLabel}
			</span>
			{#if unaddressed.length > 0}
				<span class="po-submit-bar__hint" data-testid="po-submit-response-hint">
					{unaddressed.length} line{unaddressed.length === 1 ? '' : 's'} still need a decision
				</span>
			{:else if lastRoundWarning}
				<span class="po-submit-bar__hint po-submit-bar__hint--warn" data-testid="po-submit-response-hint">
					Next hand-off is force-override only
				</span>
			{/if}
		</div>
		<Button
			disabled={!canSubmit}
			onclick={() => (showConfirm = true)}
			data-testid="po-submit-response-btn"
		>
			Submit response
		</Button>
	</div>
	{#if error}
		<p class="po-submit-bar__error" role="alert" data-testid="po-submit-response-error">
			{error}
		</p>
	{/if}
</div>

{#if showConfirm}
	<div
		class="po-submit-bar__overlay"
		role="dialog"
		aria-modal="true"
		aria-labelledby="po-submit-confirm-title"
		data-testid="po-submit-response-confirm"
	>
		<div class="po-submit-bar__dialog">
			<h3 id="po-submit-confirm-title" class="po-submit-bar__dialog-title">
				Submit response
			</h3>
			<p class="po-submit-bar__dialog-body">Sending {roundLabel}. Delta:</p>
			<ul class="po-submit-bar__delta">
				<li>
					Accepted:
					<strong data-testid="po-submit-response-delta-accepted">{summary.accepted}</strong>
				</li>
				<li>
					Modified:
					<strong data-testid="po-submit-response-delta-modified">{summary.modified}</strong>
				</li>
				<li>
					Removed:
					<strong data-testid="po-submit-response-delta-removed">{summary.removed}</strong>
				</li>
			</ul>
			<div class="po-submit-bar__dialog-footer">
				<Button variant="secondary" onclick={() => (showConfirm = false)}>Cancel</Button>
				<Button
					onclick={() => {
						showConfirm = false;
						on_submit();
					}}
					data-testid="po-submit-response-confirm-btn"
				>
					Confirm
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	.po-submit-bar {
		position: sticky;
		bottom: 0;
		background-color: var(--surface-card);
		border-top: 1px solid var(--gray-200);
		box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.04);
		padding: var(--space-3) var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		z-index: 5;
	}
	.po-submit-bar__inner {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		flex-wrap: wrap;
	}
	.po-submit-bar__meta {
		display: flex;
		flex-direction: column;
		gap: 2px;
		flex: 1 1 auto;
		min-width: 0;
	}
	.po-submit-bar__round {
		font-weight: 600;
		color: var(--gray-900);
		font-size: var(--font-size-sm);
	}
	.po-submit-bar__hint {
		color: var(--gray-600);
		font-size: var(--font-size-xs);
	}
	.po-submit-bar__hint--warn {
		color: #92400e;
	}
	.po-submit-bar__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		margin: 0;
	}
	.po-submit-bar__overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: var(--space-4);
	}
	.po-submit-bar__dialog {
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
	.po-submit-bar__dialog-title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.po-submit-bar__dialog-body {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0;
	}
	.po-submit-bar__delta {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		font-size: var(--font-size-sm);
	}
	.po-submit-bar__dialog-footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}
	@media (max-width: 640px) {
		.po-submit-bar {
			padding-bottom: calc(var(--space-3) + env(safe-area-inset-bottom, 0px));
		}
	}
</style>
