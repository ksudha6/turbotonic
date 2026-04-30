<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { ShipmentDeclarePayload } from '$lib/types';

	let {
		submitting = false,
		error = null,
		on_declare
	}: {
		submitting?: boolean;
		error?: string | null;
		on_declare: (payload: ShipmentDeclarePayload) => void;
	} = $props();

	let signatory_name: string = $state('');
	let signatory_title: string = $state('');

	// signatory_name is required; signatory_title is required per backend validation.
	const canSubmit: boolean = $derived(
		!submitting &&
		signatory_name.trim().length > 0 &&
		signatory_title.trim().length > 0
	);

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		const name = signatory_name.trim();
		const title = signatory_title.trim();
		if (!name || !title) return;
		on_declare({ signatory_name: name, signatory_title: title });
	}
</script>

<PanelCard title="Customs Declaration" data-testid="shipment-declare-panel">
	{#snippet children()}
		<form
			class="shipment-declare-panel__form"
			onsubmit={handleSubmit}
			novalidate
			data-testid="shipment-declare-form"
		>
			<p class="shipment-declare-panel__description">
				Record the signatory for the shipper's declaration on the Commercial Invoice.
			</p>

			<div class="shipment-declare-panel__fields">
				<FormField label="Signatory name">
					{#snippet children()}
						<Input
							bind:value={signatory_name}
							placeholder="e.g. Jane Smith"
							ariaLabel="Signatory name"
							disabled={submitting}
							data-testid="shipment-declare-signatory-name"
						/>
					{/snippet}
				</FormField>

				<FormField label="Signatory title">
					{#snippet children()}
						<Input
							bind:value={signatory_title}
							placeholder="e.g. Export Manager"
							ariaLabel="Signatory title"
							disabled={submitting}
							data-testid="shipment-declare-signatory-title"
						/>
					{/snippet}
				</FormField>
			</div>

			{#if error !== null}
				<p class="shipment-declare-panel__error" role="alert" data-testid="shipment-declare-error">
					{error}
				</p>
			{/if}

			<div class="shipment-declare-panel__footer">
				<Button
					type="submit"
					variant="primary"
					disabled={!canSubmit}
					data-testid="shipment-declare-submit"
				>
					{submitting ? 'Declaring…' : 'Record declaration'}
				</Button>
			</div>
		</form>
	{/snippet}
</PanelCard>

<style>
	.shipment-declare-panel__form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.shipment-declare-panel__description {
		font-size: var(--font-size-sm);
		color: var(--text-secondary, #6b7280);
		margin: 0;
	}

	.shipment-declare-panel__fields {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.shipment-declare-panel__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}

	.shipment-declare-panel__footer {
		display: flex;
		justify-content: flex-end;
	}
</style>
