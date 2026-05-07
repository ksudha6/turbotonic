<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { ShipmentLogisticsPayload } from '$lib/types';

	let {
		pallet_count = null,
		export_reason = '',
		submitting = false,
		error = null,
		on_save
	}: {
		pallet_count?: number | null;
		export_reason?: string;
		submitting?: boolean;
		error?: string | null;
		on_save: (payload: ShipmentLogisticsPayload) => void;
	} = $props();

	// Local editable state seeded from existing values.
	let localPalletCount: string = $state(pallet_count !== null && pallet_count !== undefined ? String(pallet_count) : '');
	let localExportReason: string = $state(export_reason ?? '');

	// Submit is enabled when not already submitting.
	const canSubmit: boolean = $derived(!submitting);

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		const parsedPalletCount = localPalletCount.trim() !== '' ? parseInt(localPalletCount, 10) : null;
		on_save({
			pallet_count: parsedPalletCount,
			export_reason: localExportReason.trim()
		});
	}
</script>

<PanelCard title="Logistics Details" data-testid="shipment-logistics-panel">
	{#snippet children()}
		<form
			class="shipment-logistics-panel__form"
			onsubmit={handleSubmit}
			novalidate
			data-testid="shipment-logistics-form"
		>
			<div class="shipment-logistics-panel__fields">
				<FormField label="Pallet count">
					{#snippet children()}
						<Input
							bind:value={localPalletCount}
							placeholder="e.g. 12"
							ariaLabel="Pallet count"
							disabled={submitting}
							data-testid="shipment-logistics-pallet-count"
						/>
					{/snippet}
				</FormField>

				<FormField label="Reason for export">
					{#snippet children()}
						<Input
							bind:value={localExportReason}
							placeholder="e.g. Sale"
							ariaLabel="Reason for export"
							disabled={submitting}
							data-testid="shipment-logistics-export-reason"
						/>
					{/snippet}
				</FormField>
			</div>

			{#if error !== null}
				<p class="shipment-logistics-panel__error" role="alert" data-testid="shipment-logistics-error">
					{error}
				</p>
			{/if}

			<div class="shipment-logistics-panel__footer">
				<Button
					type="submit"
					variant="primary"
					disabled={!canSubmit}
					data-testid="shipment-logistics-submit"
				>
					{submitting ? 'Saving…' : 'Save logistics details'}
				</Button>
			</div>
		</form>
	{/snippet}
</PanelCard>

<style>
	.shipment-logistics-panel__form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.shipment-logistics-panel__fields {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.shipment-logistics-panel__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}

	.shipment-logistics-panel__footer {
		display: flex;
		justify-content: flex-end;
	}
</style>
