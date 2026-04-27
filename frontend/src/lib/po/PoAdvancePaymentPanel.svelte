<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Button from '$lib/ui/Button.svelte';
	import { canMarkAdvancePaid } from '$lib/permissions';
	import type { PurchaseOrder, UserRole } from '$lib/types';

	let {
		po,
		role,
		paymentTermHasAdvance,
		firstMilestonePosted,
		onMarkAdvancePaid,
		'data-testid': testid
	}: {
		po: PurchaseOrder;
		role: UserRole;
		paymentTermHasAdvance: boolean;
		firstMilestonePosted: boolean;
		onMarkAdvancePaid: () => void;
		'data-testid'?: string;
	} = $props();

	function formatDate(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
	}

	const paid = $derived(!!po.advance_paid_at);
	const gateOpen = $derived(!paid && !firstMilestonePosted);
	const showMarkButton = $derived(
		!paid &&
			canMarkAdvancePaid(role) &&
			(po.status === 'ACCEPTED' || po.status === 'MODIFIED')
	);
</script>

{#if paymentTermHasAdvance}
	<div data-testid={testid ?? 'po-advance-panel'}>
		<PanelCard title="Advance payment">
			{#if paid}
				<p class="po-advance-panel__status po-advance-panel__status--paid">
					Paid on {formatDate(po.advance_paid_at!)}
				</p>
				<p class="po-advance-panel__note">Add/remove window closed (advance paid)</p>
			{:else if firstMilestonePosted}
				<p class="po-advance-panel__status">Pending</p>
				<p class="po-advance-panel__note">Add/remove window closed (production started)</p>
			{:else}
				<p class="po-advance-panel__status">Pending</p>
				<p class="po-advance-panel__note">
					Add/remove window open until advance paid or first milestone
				</p>
			{/if}
			{#if showMarkButton && gateOpen}
				<div class="po-advance-panel__action">
					<Button
						variant="primary"
						onclick={onMarkAdvancePaid}
						data-testid="po-action-mark-advance-paid"
					>
						Mark advance paid
					</Button>
				</div>
			{/if}
		</PanelCard>
	</div>
{/if}

<style>
	.po-advance-panel__status {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-900);
		margin: 0;
	}
	.po-advance-panel__status--paid {
		color: var(--green-700, #166534);
	}
	.po-advance-panel__note {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
	.po-advance-panel__action {
		margin-top: var(--space-2);
	}
</style>
