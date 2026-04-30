<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import DateInput from '$lib/ui/DateInput.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { ShipmentBookingPayload } from '$lib/types';

	let {
		submitting = false,
		error = null,
		on_book
	}: {
		submitting?: boolean;
		error?: string | null;
		on_book: (payload: ShipmentBookingPayload) => void;
	} = $props();

	let carrier: string = $state('');
	let booking_reference: string = $state('');
	let pickup_date: string = $state('');

	// Submit is disabled while the required text fields are empty or whitespace-only,
	// or while a submission is in flight.
	const canSubmit: boolean = $derived(
		!submitting &&
		carrier.trim().length > 0 &&
		booking_reference.trim().length > 0 &&
		pickup_date.length > 0
	);

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		const trimmedCarrier = carrier.trim();
		const trimmedRef = booking_reference.trim();
		if (!trimmedCarrier || !trimmedRef || !pickup_date) return;
		on_book({ carrier: trimmedCarrier, booking_reference: trimmedRef, pickup_date });
	}
</script>

<PanelCard title="Book Shipment" data-testid="shipment-booking-panel">
	{#snippet children()}
		<form
			class="shipment-booking-panel__form"
			onsubmit={handleSubmit}
			novalidate
			data-testid="shipment-booking-form"
		>
			<div class="shipment-booking-panel__fields">
				<FormField label="Carrier">
					{#snippet children()}
						<Input
							bind:value={carrier}
							placeholder="e.g. Maersk"
							ariaLabel="Carrier"
							disabled={submitting}
							data-testid="shipment-booking-carrier"
						/>
					{/snippet}
				</FormField>

				<FormField label="Booking reference">
					{#snippet children()}
						<Input
							bind:value={booking_reference}
							placeholder="e.g. MAEU1234567"
							ariaLabel="Booking reference"
							disabled={submitting}
							data-testid="shipment-booking-reference"
						/>
					{/snippet}
				</FormField>

				<FormField label="Pickup date">
					{#snippet children()}
						<DateInput
							bind:value={pickup_date}
							ariaLabel="Pickup date"
							disabled={submitting}
							data-testid="shipment-booking-pickup-date"
						/>
					{/snippet}
				</FormField>
			</div>

			{#if error !== null}
				<p class="shipment-booking-panel__error" role="alert" data-testid="shipment-booking-error">
					{error}
				</p>
			{/if}

			<div class="shipment-booking-panel__footer">
				<Button
					type="submit"
					variant="primary"
					disabled={!canSubmit}
					data-testid="shipment-booking-submit"
				>
					{submitting ? 'Booking…' : 'Book shipment'}
				</Button>
			</div>
		</form>
	{/snippet}
</PanelCard>

<style>
	.shipment-booking-panel__form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.shipment-booking-panel__fields {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.shipment-booking-panel__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}

	.shipment-booking-panel__footer {
		display: flex;
		justify-content: flex-end;
	}
</style>
