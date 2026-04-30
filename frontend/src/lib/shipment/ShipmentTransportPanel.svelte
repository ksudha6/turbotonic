<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { ShipmentTransportPayload } from '$lib/types';

	let {
		vessel_name = '',
		voyage_number = '',
		submitting = false,
		error = null,
		on_save
	}: {
		vessel_name?: string;
		voyage_number?: string;
		submitting?: boolean;
		error?: string | null;
		on_save: (payload: ShipmentTransportPayload) => void;
	} = $props();

	// Local editable state seeded from existing values (allows pre-populating on re-render).
	let localVessel: string = $state(vessel_name ?? '');
	let localVoyage: string = $state(voyage_number ?? '');

	// Both fields are optional; submit is enabled when not already submitting.
	const canSubmit: boolean = $derived(!submitting);

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		on_save({
			vessel_name: localVessel.trim() || null,
			voyage_number: localVoyage.trim() || null
		});
	}
</script>

<PanelCard title="Transport Details" data-testid="shipment-transport-panel">
	{#snippet children()}
		<form
			class="shipment-transport-panel__form"
			onsubmit={handleSubmit}
			novalidate
			data-testid="shipment-transport-form"
		>
			<div class="shipment-transport-panel__fields">
				<FormField label="Vessel name">
					{#snippet children()}
						<Input
							bind:value={localVessel}
							placeholder="e.g. MSC GULSUN"
							ariaLabel="Vessel name"
							disabled={submitting}
							data-testid="shipment-transport-vessel"
						/>
					{/snippet}
				</FormField>

				<FormField label="Voyage number">
					{#snippet children()}
						<Input
							bind:value={localVoyage}
							placeholder="e.g. 031W"
							ariaLabel="Voyage number"
							disabled={submitting}
							data-testid="shipment-transport-voyage"
						/>
					{/snippet}
				</FormField>
			</div>

			{#if error !== null}
				<p class="shipment-transport-panel__error" role="alert" data-testid="shipment-transport-error">
					{error}
				</p>
			{/if}

			<div class="shipment-transport-panel__footer">
				<Button
					type="submit"
					variant="primary"
					disabled={!canSubmit}
					data-testid="shipment-transport-submit"
				>
					{submitting ? 'Saving…' : 'Save transport details'}
				</Button>
			</div>
		</form>
	{/snippet}
</PanelCard>

<style>
	.shipment-transport-panel__form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.shipment-transport-panel__fields {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.shipment-transport-panel__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}

	.shipment-transport-panel__footer {
		display: flex;
		justify-content: flex-end;
	}
</style>
