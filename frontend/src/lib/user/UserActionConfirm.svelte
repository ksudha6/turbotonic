<script lang="ts">
	import Button from '$lib/ui/Button.svelte';

	let {
		title,
		body,
		confirmLabel,
		onConfirm,
		onCancel
	}: {
		title: string;
		body: string;
		confirmLabel: string;
		// Async callback. Reject with a server message and the modal renders it inline.
		onConfirm: () => Promise<void>;
		onCancel: () => void;
	} = $props();

	const titleId = crypto.randomUUID();

	let serverError: string = $state('');
	let submitting: boolean = $state(false);

	async function handleConfirm() {
		serverError = '';
		submitting = true;
		try {
			await onConfirm();
		} catch (e) {
			serverError = e instanceof Error ? e.message : 'Action failed.';
		} finally {
			submitting = false;
		}
	}
</script>

<div
	class="user-modal"
	role="dialog"
	aria-modal="true"
	aria-labelledby={titleId}
	data-testid="user-action-confirm"
>
	<div class="user-modal__card">
		<header class="user-modal__header">
			<h2 id={titleId} class="user-modal__title">{title}</h2>
		</header>

		<div class="user-modal__body">
			{#if serverError}
				<div class="user-modal__error" role="alert" data-testid="user-action-error">
					{serverError}
				</div>
			{/if}
			<p class="user-modal__copy" data-testid="user-action-body">{body}</p>
		</div>

		<footer class="user-modal__footer">
			<Button variant="secondary" onclick={onCancel} data-testid="user-action-cancel">
				Cancel
			</Button>
			<Button
				variant="primary"
				disabled={submitting}
				onclick={handleConfirm}
				data-testid="user-action-submit"
			>
				{submitting ? 'Working…' : confirmLabel}
			</Button>
		</footer>
	</div>
</div>

<style>
	.user-modal {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: var(--space-4);
	}
	.user-modal__card {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		max-width: 28rem;
		width: 100%;
		max-height: 90vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
	}
	.user-modal__header {
		padding: var(--space-6) var(--space-6) var(--space-2);
	}
	.user-modal__title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.user-modal__body {
		padding: var(--space-2) var(--space-6) var(--space-4);
	}
	.user-modal__copy {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0;
	}
	.user-modal__error {
		padding: var(--space-3);
		margin-bottom: var(--space-4);
		background-color: #fee2e2;
		color: #991b1b;
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
	}
	.user-modal__footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		border-top: 1px solid var(--gray-100);
	}
</style>
