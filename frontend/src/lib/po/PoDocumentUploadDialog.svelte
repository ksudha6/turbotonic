<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Select from '$lib/ui/Select.svelte';
	import { allowedAttachmentTypes, ATTACHMENT_TYPE_LABELS } from '$lib/po/po-attachment-types';
	import type { POAttachmentType } from '$lib/po/po-attachment-types';

	const MAX_SIZE = 10 * 1024 * 1024;

	let {
		po,
		onSubmit,
		onCancel
	}: {
		po: { id: string; po_type: 'PROCUREMENT' | 'OPEX' };
		onSubmit: (file: File, fileType: POAttachmentType) => Promise<void>;
		onCancel: () => void;
	} = $props();

	const allowedTypes = $derived(allowedAttachmentTypes(po.po_type));
	const typeOptions = $derived(
		allowedTypes.map((t) => ({ value: t, label: ATTACHMENT_TYPE_LABELS[t] }))
	);

	let selectedType: string = $state('');
	let fileError: string = $state('');
	let submitting: boolean = $state(false);

	// Reset selectedType when options change (po_type switch).
	$effect(() => {
		if (typeOptions.length > 0 && !typeOptions.find((o) => o.value === selectedType)) {
			selectedType = typeOptions[0].value;
		}
	});

	const titleId = crypto.randomUUID();

	let fileInput: HTMLInputElement | undefined = $state(undefined);

	async function handleSubmit() {
		fileError = '';
		const file = fileInput?.files?.[0];
		if (!file) {
			fileError = 'A PDF file is required.';
			return;
		}
		if (file.size === 0) {
			fileError = 'File must not be empty.';
			return;
		}
		if (file.size > MAX_SIZE) {
			fileError = 'File must be 10 MB or smaller.';
			return;
		}
		if (file.type !== 'application/pdf') {
			fileError = 'Only PDF files are accepted.';
			return;
		}
		submitting = true;
		try {
			await onSubmit(file, selectedType as POAttachmentType);
		} finally {
			submitting = false;
		}
	}
</script>

<div
	class="po-upload-dialog"
	role="dialog"
	aria-modal="true"
	aria-labelledby={titleId}
	data-testid="po-document-upload-dialog"
>
	<div class="po-upload-dialog__card">
		<header class="po-upload-dialog__header">
			<h2 id={titleId} class="po-upload-dialog__title">Upload document</h2>
		</header>

		<div class="po-upload-dialog__body">
			<FormField label="Document type" required data-testid="po-document-type-field">
				{#snippet children()}
					<Select
						bind:value={selectedType}
						options={typeOptions}
						ariaLabel="Document type"
						data-testid="po-document-type-select"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="PDF file"
				required
				error={fileError}
				data-testid="po-document-file-field"
			>
				{#snippet children()}
					<input
						bind:this={fileInput}
						type="file"
						accept="application/pdf"
						aria-label="PDF file to upload"
						data-testid="po-document-file-input"
						class="po-upload-dialog__file-input"
					/>
				{/snippet}
			</FormField>
		</div>

		<footer class="po-upload-dialog__footer">
			<Button
				variant="secondary"
				onclick={onCancel}
				disabled={submitting}
				data-testid="po-document-upload-cancel"
			>
				Cancel
			</Button>
			<Button
				onclick={handleSubmit}
				disabled={submitting}
				data-testid="po-document-upload-submit"
			>
				{submitting ? 'Uploading…' : 'Upload'}
			</Button>
		</footer>
	</div>
</div>

<style>
	.po-upload-dialog {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: var(--space-4);
	}
	.po-upload-dialog__card {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		max-width: 28rem;
		width: 100%;
		display: flex;
		flex-direction: column;
	}
	.po-upload-dialog__header {
		padding: var(--space-6) var(--space-6) var(--space-2);
	}
	.po-upload-dialog__title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.po-upload-dialog__body {
		padding: var(--space-4) var(--space-6);
	}
	.po-upload-dialog__file-input {
		width: 100%;
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		color: var(--gray-900);
	}
	.po-upload-dialog__footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		border-top: 1px solid var(--gray-100);
	}
</style>
