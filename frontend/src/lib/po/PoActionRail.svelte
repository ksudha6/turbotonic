<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import {
		canEditPO,
		canSubmitPO,
		canAcceptRejectPO,
		canCreateInvoice,
		canPostMilestone
	} from '$lib/permissions';
	import type { PurchaseOrder, UserRole } from '$lib/types';

	type ActionId =
		| 'edit'
		| 'submit'
		| 'resubmit'
		| 'accept'
		| 'create-invoice'
		| 'post-milestone'
		| 'download-pdf';

	type Mode = 'inline' | 'sticky-bottom';

	let {
		po,
		role,
		mode,
		onEdit,
		onSubmit,
		onResubmit,
		onAccept,
		onMarkAdvancePaid: _onMarkAdvancePaid,
		onCreateInvoice,
		onPostMilestone,
		onDownloadPdf,
		'data-testid': testid
	}: {
		po: PurchaseOrder;
		role: UserRole;
		mode: Mode;
		onEdit: () => void;
		onSubmit: () => void;
		onResubmit: () => void;
		onAccept: () => void;
		onMarkAdvancePaid: () => void;
		onCreateInvoice: () => void;
		onPostMilestone: () => void;
		onDownloadPdf: () => void;
		'data-testid'?: string;
	} = $props();

	const ACTION_LABEL: Readonly<Record<ActionId, string>> = {
		edit: 'Edit',
		submit: 'Submit',
		resubmit: 'Resubmit',
		accept: 'Accept',
		'create-invoice': 'Create invoice',
		'post-milestone': 'Post milestone',
		'download-pdf': 'Download PDF'
	};

	function pdfLabel(): string {
		const base = ACTION_LABEL['download-pdf'];
		return (po.round_count ?? 0) > 0 ? `${base} (Modified)` : base;
	}

	function readOnlyRole(r: UserRole): boolean {
		return r === 'PROCUREMENT_MANAGER' || r === 'FREIGHT_MANAGER' || r === 'QUALITY_LAB';
	}

	function computePrimary(): ActionId[] {
		if (readOnlyRole(role)) return [];
		const status = po.status;
		const out: ActionId[] = [];
		if (status === 'DRAFT' && canEditPO(role)) {
			out.push('edit');
			if (canSubmitPO(role)) out.push('submit');
			return out;
		}
		if (status === 'PENDING') {
			if (role === 'VENDOR' && canAcceptRejectPO(role)) out.push('accept');
			return out;
		}
		if (status === 'MODIFIED') {
			return out;
		}
		if (status === 'REJECTED' && canEditPO(role)) {
			out.push('edit');
			return out;
		}
		if (status === 'REVISED' && canSubmitPO(role)) {
			out.push('resubmit');
			return out;
		}
		if (status === 'ACCEPTED') {
			if (role === 'VENDOR' && canCreateInvoice(role)) {
				out.push('create-invoice');
				if (po.po_type === 'PROCUREMENT' && canPostMilestone(role)) out.push('post-milestone');
			}
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
			case 'edit':
				onEdit();
				break;
			case 'submit':
				onSubmit();
				break;
			case 'resubmit':
				onResubmit();
				break;
			case 'accept':
				onAccept();
				break;
			case 'create-invoice':
				onCreateInvoice();
				break;
			case 'post-milestone':
				onPostMilestone();
				break;
			case 'download-pdf':
				onDownloadPdf();
				break;
		}
	}

	function labelFor(action: ActionId): string {
		return action === 'download-pdf' ? pdfLabel() : ACTION_LABEL[action];
	}

	function variantFor(action: ActionId, index: number): 'primary' | 'secondary' {
		if (action === 'edit') return 'secondary';
		return index === 0 ? 'primary' : 'secondary';
	}
</script>

{#if mode === 'inline'}
	<div class="po-action-rail po-action-rail--inline" data-testid={testid ?? 'po-action-rail'}>
		{#each primary as action, i (action)}
			<Button
				variant={variantFor(action, i)}
				onclick={() => trigger(action)}
				data-testid="po-action-{action}"
			>
				{labelFor(action)}
			</Button>
		{/each}
		{#each solo as action (action)}
			<Button
				variant="secondary"
				onclick={() => trigger(action)}
				data-testid="po-action-{action}"
			>
				{labelFor(action)}
			</Button>
		{/each}
		{#if overflow.length > 0}
			<details class="po-action-rail__overflow">
				<summary data-testid="po-action-overflow" aria-label="More actions">…</summary>
				<div class="po-action-rail__menu">
					{#each overflow as action (action)}
						<button
							type="button"
							class="po-action-rail__menu-item"
							onclick={() => trigger(action)}
							data-testid="po-action-{action}"
						>
							{labelFor(action)}
						</button>
					{/each}
				</div>
			</details>
		{/if}
	</div>
{:else}
	<div class="po-action-rail po-action-rail--sticky" data-testid={testid ?? 'po-action-rail'}>
		{#if primary.length > 0}
			<Button
				variant="primary"
				onclick={() => trigger(primary[0])}
				data-testid="po-action-{primary[0]}"
			>
				{labelFor(primary[0])}
			</Button>
			<details class="po-action-rail__overflow">
				<summary data-testid="po-action-overflow" aria-label="More actions">…</summary>
				<div class="po-action-rail__menu po-action-rail__menu--up">
					{#each primary.slice(1) as action (action)}
						<button
							type="button"
							class="po-action-rail__menu-item"
							onclick={() => trigger(action)}
							data-testid="po-action-{action}"
						>
							{labelFor(action)}
						</button>
					{/each}
					{#each overflow as action (action)}
						<button
							type="button"
							class="po-action-rail__menu-item"
							onclick={() => trigger(action)}
							data-testid="po-action-{action}"
						>
							{labelFor(action)}
						</button>
					{/each}
				</div>
			</details>
		{:else}
			{#each solo as action (action)}
				<Button
					variant="secondary"
					onclick={() => trigger(action)}
					data-testid="po-action-{action}"
				>
					{labelFor(action)}
				</Button>
			{/each}
		{/if}
	</div>
{/if}

<style>
	.po-action-rail {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}
	.po-action-rail--sticky {
		position: sticky;
		bottom: 0;
		left: 0;
		right: 0;
		padding: var(--space-3) var(--space-4);
		background-color: var(--surface-card);
		border-top: 1px solid var(--gray-200);
		box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
		z-index: 5;
	}
	.po-action-rail--sticky :global(.ui-btn) {
		flex: 1 1 auto;
	}
	.po-action-rail__overflow {
		position: relative;
	}
	.po-action-rail__overflow summary {
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
	.po-action-rail__overflow summary::-webkit-details-marker {
		display: none;
	}
	.po-action-rail__overflow summary:hover {
		background-color: var(--gray-50);
	}
	.po-action-rail__menu {
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
	.po-action-rail__menu--up {
		top: auto;
		bottom: calc(100% + var(--space-1));
	}
	.po-action-rail__menu-item {
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
	.po-action-rail__menu-item:hover {
		background-color: var(--gray-100);
	}
</style>
