<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import { canSubmitShipmentForDocuments, canMarkShipmentReady } from '$lib/permissions';
	import type { ShipmentStatus, UserRole, ReadinessResult } from '$lib/types';

	let {
		status,
		role,
		readiness,
		submitting,
		marking,
		error,
		on_submit,
		on_mark_ready
	}: {
		status: ShipmentStatus;
		role: UserRole;
		readiness: ReadinessResult | null;
		submitting: boolean;
		marking: boolean;
		error: string | null;
		on_submit: () => void;
		on_mark_ready: () => void;
	} = $props();

	const showSubmit = $derived(canSubmitShipmentForDocuments(role, status));
	const showMarkReady = $derived(canMarkShipmentReady(role, status));

	const markReadyDisabled = $derived(marking || readiness === null || readiness.is_ready === false);
</script>

{#if showSubmit || showMarkReady}
	<div class="shipment-action-rail" data-testid="shipment-action-rail">
		{#if showSubmit}
			<Button
				variant="primary"
				disabled={submitting}
				onclick={on_submit}
				data-testid="shipment-action-submit"
			>
				{submitting ? 'Submitting…' : 'Submit for documents'}
			</Button>
		{/if}

		{#if showMarkReady}
			<Button
				variant="primary"
				disabled={markReadyDisabled}
				onclick={on_mark_ready}
				data-testid="shipment-action-mark-ready"
			>
				{marking ? 'Marking ready…' : 'Mark Ready to Ship'}
			</Button>
			{#if markReadyDisabled && !marking}
				<p class="shipment-action-rail__hint" data-testid="shipment-action-mark-ready-hint">
					Resolve missing items in the readiness panel before marking ready.
				</p>
			{/if}
		{/if}

		{#if error !== null}
			<p class="shipment-action-rail__error" data-testid="shipment-action-error">{error}</p>
		{/if}
	</div>
{/if}

<style>
	.shipment-action-rail {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-2);
	}

	.shipment-action-rail__hint {
		width: 100%;
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		margin: 0;
	}

	.shipment-action-rail__error {
		width: 100%;
		font-size: var(--font-size-sm);
		color: var(--color-error, #dc2626);
		margin: 0;
	}

	@media (max-width: 767px) {
		.shipment-action-rail {
			flex-direction: column;
			align-items: stretch;
		}
	}
</style>
