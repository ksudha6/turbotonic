<script lang="ts">
	import Button from '$lib/ui/Button.svelte';

	let {
		onConfirm,
		onCancel
	}: {
		onConfirm: (reason: string) => void;
		onCancel: () => void;
	} = $props();

	let reason: string = $state('');

	const canConfirm = $derived(reason.trim().length > 0);
</script>

<div
	class="invoice-dispute-modal__overlay"
	data-testid="invoice-dispute-modal"
	role="dialog"
	aria-modal="true"
	aria-labelledby="invoice-dispute-modal-title"
>
	<div class="invoice-dispute-modal">
		<h2 id="invoice-dispute-modal-title" class="invoice-dispute-modal__title">Dispute Invoice</h2>
		<div class="invoice-dispute-modal__body">
			<label for="invoice-dispute-reason" class="invoice-dispute-modal__label">
				Dispute reason
			</label>
			<textarea
				id="invoice-dispute-reason"
				class="invoice-dispute-modal__textarea"
				bind:value={reason}
				placeholder="Describe what's wrong with this invoice…"
				rows="4"
				data-testid="invoice-dispute-reason-input"
			></textarea>
		</div>
		<div class="invoice-dispute-modal__actions">
			<Button variant="secondary" onclick={onCancel} data-testid="invoice-dispute-cancel">
				Cancel
			</Button>
			<Button
				variant="primary"
				onclick={() => onConfirm(reason)}
				disabled={!canConfirm}
				data-testid="invoice-dispute-confirm"
			>
				Dispute
			</Button>
		</div>
	</div>
</div>

<style>
	.invoice-dispute-modal__overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4);
		z-index: 100;
	}
	.invoice-dispute-modal {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		padding: var(--space-6);
		max-width: 32rem;
		width: 100%;
	}
	.invoice-dispute-modal__title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0 0 var(--space-4);
		color: var(--gray-900);
	}
	.invoice-dispute-modal__body {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin-bottom: var(--space-4);
	}
	.invoice-dispute-modal__label {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-700);
	}
	.invoice-dispute-modal__textarea {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-family: var(--font-family);
		font-size: var(--font-size-sm);
		color: var(--gray-900);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		resize: vertical;
		min-height: 6rem;
	}
	.invoice-dispute-modal__textarea:focus {
		outline: 2px solid var(--brand-accent);
		outline-offset: -2px;
		border-color: var(--brand-accent);
	}
	.invoice-dispute-modal__actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}
</style>
