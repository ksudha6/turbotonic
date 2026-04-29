<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import {
		canSubmitInvoice,
		canApproveInvoice,
		canPayInvoice,
		canDisputeInvoice,
		canResolveInvoice
	} from '$lib/permissions';
	import type { Invoice, UserRole } from '$lib/types';

	type ActionId = 'submit' | 'approve' | 'pay' | 'dispute' | 'resolve' | 'download-pdf';
	type Mode = 'inline' | 'sticky-bottom';

	let {
		invoice,
		role,
		mode,
		onSubmit,
		onApprove,
		onPay,
		onDispute,
		onResolve,
		onDownloadPdf,
		'data-testid': testid
	}: {
		invoice: Invoice;
		role: UserRole;
		mode: Mode;
		onSubmit: () => void;
		onApprove: () => void;
		onPay: () => void;
		onDispute: () => void;
		onResolve: () => void;
		onDownloadPdf: () => void;
		'data-testid'?: string;
	} = $props();

	const ACTION_LABEL: Readonly<Record<ActionId, string>> = {
		submit: 'Submit',
		approve: 'Approve',
		pay: 'Pay',
		dispute: 'Dispute',
		resolve: 'Resolve',
		'download-pdf': 'Download PDF'
	};

	function readOnlyRole(r: UserRole): boolean {
		return r === 'PROCUREMENT_MANAGER' || r === 'FREIGHT_MANAGER' || r === 'QUALITY_LAB';
	}

	function computePrimary(): ActionId[] {
		if (readOnlyRole(role)) return [];
		const status = invoice.status;
		const out: ActionId[] = [];
		if (status === 'DRAFT' && canSubmitInvoice(role)) {
			out.push('submit');
			return out;
		}
		if (status === 'SUBMITTED') {
			if (canApproveInvoice(role)) out.push('approve');
			if (canDisputeInvoice(role)) out.push('dispute');
			return out;
		}
		if (status === 'APPROVED' && canPayInvoice(role)) {
			out.push('pay');
			return out;
		}
		if (status === 'DISPUTED' && canResolveInvoice(role)) {
			out.push('resolve');
			return out;
		}
		return out;
	}

	const primary = $derived(computePrimary());
	const overflow = $derived<ActionId[]>(
		primary.length > 0 ? (['download-pdf'] as ActionId[]) : []
	);
	const solo = $derived<ActionId[]>(
		primary.length === 0 ? (['download-pdf'] as ActionId[]) : []
	);

	function trigger(action: ActionId): void {
		switch (action) {
			case 'submit':
				onSubmit();
				break;
			case 'approve':
				onApprove();
				break;
			case 'pay':
				onPay();
				break;
			case 'dispute':
				onDispute();
				break;
			case 'resolve':
				onResolve();
				break;
			case 'download-pdf':
				onDownloadPdf();
				break;
		}
	}

	function variantFor(action: ActionId, index: number): 'primary' | 'secondary' {
		if (action === 'dispute') return 'secondary';
		return index === 0 ? 'primary' : 'secondary';
	}
</script>

{#if mode === 'inline'}
	<div class="invoice-action-rail invoice-action-rail--inline" data-testid={testid ?? 'invoice-action-rail'}>
		{#each primary as action, i (action)}
			<Button
				variant={variantFor(action, i)}
				onclick={() => trigger(action)}
				data-testid="invoice-action-{action}"
			>
				{ACTION_LABEL[action]}
			</Button>
		{/each}
		{#each solo as action (action)}
			<Button
				variant="secondary"
				onclick={() => trigger(action)}
				data-testid="invoice-action-{action}"
			>
				{ACTION_LABEL[action]}
			</Button>
		{/each}
		{#if overflow.length > 0}
			<details class="invoice-action-rail__overflow">
				<summary data-testid="invoice-action-overflow" aria-label="More actions">…</summary>
				<div class="invoice-action-rail__menu">
					{#each overflow as action (action)}
						<button
							type="button"
							class="invoice-action-rail__menu-item"
							onclick={() => trigger(action)}
							data-testid="invoice-action-{action}"
						>
							{ACTION_LABEL[action]}
						</button>
					{/each}
				</div>
			</details>
		{/if}
	</div>
{:else}
	<div class="invoice-action-rail invoice-action-rail--sticky" data-testid={testid ?? 'invoice-action-rail'}>
		{#if primary.length > 0}
			<Button
				variant="primary"
				onclick={() => trigger(primary[0])}
				data-testid="invoice-action-{primary[0]}"
			>
				{ACTION_LABEL[primary[0]]}
			</Button>
			<details class="invoice-action-rail__overflow">
				<summary data-testid="invoice-action-overflow" aria-label="More actions">…</summary>
				<div class="invoice-action-rail__menu invoice-action-rail__menu--up">
					{#each primary.slice(1) as action (action)}
						<button
							type="button"
							class="invoice-action-rail__menu-item"
							onclick={() => trigger(action)}
							data-testid="invoice-action-{action}"
						>
							{ACTION_LABEL[action]}
						</button>
					{/each}
					{#each overflow as action (action)}
						<button
							type="button"
							class="invoice-action-rail__menu-item"
							onclick={() => trigger(action)}
							data-testid="invoice-action-{action}"
						>
							{ACTION_LABEL[action]}
						</button>
					{/each}
				</div>
			</details>
		{:else}
			{#each solo as action (action)}
				<Button
					variant="secondary"
					onclick={() => trigger(action)}
					data-testid="invoice-action-{action}"
				>
					{ACTION_LABEL[action]}
				</Button>
			{/each}
		{/if}
	</div>
{/if}

<style>
	.invoice-action-rail {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}
	.invoice-action-rail--sticky {
		position: sticky;
		bottom: 0;
		left: 0;
		right: 0;
		padding: var(--space-3) var(--space-4);
		padding-bottom: calc(var(--space-3) + env(safe-area-inset-bottom, 0px));
		background-color: var(--surface-card);
		border-top: 1px solid var(--gray-200);
		box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
		z-index: 5;
	}
	.invoice-action-rail--sticky :global(.ui-btn) {
		flex: 1 1 auto;
	}
	.invoice-action-rail__overflow {
		position: relative;
	}
	.invoice-action-rail__overflow summary {
		list-style: none;
		cursor: pointer;
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		user-select: none;
	}
	.invoice-action-rail__overflow summary::-webkit-details-marker {
		display: none;
	}
	.invoice-action-rail__overflow summary:hover {
		background-color: var(--gray-50);
	}
	.invoice-action-rail__menu {
		position: absolute;
		top: calc(100% + var(--space-1));
		right: 0;
		min-width: 12rem;
		display: flex;
		flex-direction: column;
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
		padding: var(--space-1);
		z-index: 6;
	}
	.invoice-action-rail__menu--up {
		top: auto;
		bottom: calc(100% + var(--space-1));
	}
	.invoice-action-rail__menu-item {
		text-align: left;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		color: var(--gray-900);
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
	}
	.invoice-action-rail__menu-item:hover {
		background-color: var(--gray-100);
	}
</style>
