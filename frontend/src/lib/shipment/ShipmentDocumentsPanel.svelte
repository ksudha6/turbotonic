<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Button from '$lib/ui/Button.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import { canManageShipmentRequirements, canUploadShipmentDocument } from '$lib/permissions';
	import { labelForDocumentType } from './document-type-labels';
	import type { ShipmentDocumentRequirement, UserRole, ShipmentStatus } from '$lib/types';

	const MAX_FILE_SIZE = 10 * 1024 * 1024;

	let {
		requirements,
		role,
		status,
		uploading_id = null,
		adding = false,
		error = null,
		add_error = null,
		on_upload,
		on_add
	}: {
		requirements: ShipmentDocumentRequirement[];
		role: UserRole;
		status: ShipmentStatus;
		uploading_id?: string | null;
		adding?: boolean;
		error?: string | null;
		add_error?: string | null;
		on_upload: (requirementId: string, file: File) => void;
		on_add: (documentType: string) => void;
	} = $props();

	let addInput: string = $state('');

	// wasAdding tracks the adding true→false transition to clear input on success.
	let wasAdding = $state(false);
	$effect(() => {
		if (adding) {
			wasAdding = true;
		} else if (wasAdding && !add_error) {
			wasAdding = false;
			addInput = '';
		} else if (wasAdding && add_error) {
			wasAdding = false;
		}
	});

	function handleFileChange(reqId: string, ev: Event) {
		const input = ev.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		input.value = '';
		if (!file) return;
		if (file.type !== 'application/pdf') return;
		if (file.size > MAX_FILE_SIZE) return;
		on_upload(reqId, file);
	}

	function triggerUpload(reqId: string) {
		const el = document.querySelector<HTMLInputElement>(
			`[data-testid="shipment-document-upload-input-${reqId}"]`
		);
		el?.click();
	}

	function handleAddSubmit(e: SubmitEvent) {
		e.preventDefault();
		const trimmed = addInput.trim();
		if (!trimmed) return;
		on_add(trimmed);
	}

	const showAddForm = $derived(canManageShipmentRequirements(role, status));
	const showUpload = $derived(canUploadShipmentDocument(role, status));
</script>

<PanelCard title="Documents" data-testid="shipment-documents-panel">
	{#if requirements.length === 0}
		<EmptyState
			title="No documents yet"
			description="Submit the shipment for documents to seed the checklist."
			data-testid="shipment-documents-empty"
		/>
	{:else}
		<ul class="shipment-documents-panel__list">
			{#each requirements as req (req.id)}
				<li
					class="shipment-documents-panel__row"
					data-testid={`shipment-document-row-${req.id}`}
				>
					<div class="shipment-documents-panel__row-info">
						<span class="shipment-documents-panel__row-label">
							{labelForDocumentType(req.document_type)}
							{#if req.is_auto_generated}
								<span class="shipment-documents-panel__auto-hint">(auto-generated)</span>
							{/if}
						</span>
					</div>

					<div class="shipment-documents-panel__row-meta">
						<StatusPill
							tone={req.status === 'COLLECTED' ? 'green' : 'gray'}
							label={req.status}
							data-testid={`shipment-document-status-${req.id}`}
						/>

						{#if req.is_auto_generated}
							<span class="shipment-documents-panel__hint-text">Generated on download</span>
						{:else if req.status === 'PENDING' && showUpload}
							<Button
								variant="secondary"
								onclick={() => triggerUpload(req.id)}
								disabled={uploading_id === req.id}
								data-testid={`shipment-document-upload-${req.id}`}
							>
								{uploading_id === req.id ? 'Uploading…' : 'Upload PDF'}
							</Button>
							<input
								type="file"
								accept="application/pdf"
								class="shipment-documents-panel__file-input"
								onchange={(ev) => handleFileChange(req.id, ev)}
								data-testid={`shipment-document-upload-input-${req.id}`}
							/>
						{:else if req.status === 'COLLECTED' && req.document_id !== null}
							<span class="shipment-documents-panel__hint-text">Uploaded</span>
							<a
								href={`/api/v1/files/${req.document_id}/download`}
								target="_blank"
								rel="noopener"
								class="shipment-documents-panel__download-link"
							>
								Download
							</a>
						{:else if req.status === 'COLLECTED' && req.document_id === null}
							<span class="shipment-documents-panel__hint-text">Uploaded</span>
						{/if}
					</div>
				</li>

				{#if error !== null && uploading_id === req.id}
					<p
						class="shipment-documents-panel__error"
						role="alert"
						data-testid={`shipment-document-error-${req.id}`}
					>
						{error}
					</p>
				{/if}
			{/each}
		</ul>

		{#if showAddForm}
			<form
				class="shipment-documents-panel__add-form"
				onsubmit={handleAddSubmit}
				data-testid="shipment-documents-add-form"
				novalidate
			>
				<FormField label="Document type">
					{#snippet children()}
						<Input
							bind:value={addInput}
							placeholder="BILL_OF_LADING"
							ariaLabel="Document type"
							data-testid="shipment-documents-add-input"
						/>
					{/snippet}
				</FormField>

				{#if add_error !== null}
					<p
						class="shipment-documents-panel__error"
						role="alert"
						data-testid="shipment-documents-add-error"
					>
						{add_error}
					</p>
				{/if}

				<div class="shipment-documents-panel__add-footer">
					<Button
						type="submit"
						variant="primary"
						disabled={adding || addInput.trim().length === 0}
						data-testid="shipment-documents-add-submit"
					>
						{adding ? 'Adding…' : 'Add Requirement'}
					</Button>
				</div>
			</form>
		{/if}
	{/if}
</PanelCard>

<style>
	.shipment-documents-panel__list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0;
	}
	.shipment-documents-panel__row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}
	.shipment-documents-panel__row:last-of-type {
		border-bottom: none;
	}
	.shipment-documents-panel__row-info {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.shipment-documents-panel__row-label {
		font-weight: 500;
		color: var(--gray-900);
	}
	.shipment-documents-panel__auto-hint {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		font-weight: 400;
	}
	.shipment-documents-panel__row-meta {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex-shrink: 0;
	}
	.shipment-documents-panel__hint-text {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}
	.shipment-documents-panel__download-link {
		font-size: var(--font-size-sm);
		color: var(--blue-600, #2563eb);
		text-decoration: underline;
	}
	.shipment-documents-panel__file-input {
		display: none;
	}
	.shipment-documents-panel__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}
	.shipment-documents-panel__add-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		margin-top: var(--space-4);
	}
	.shipment-documents-panel__add-footer {
		display: flex;
		justify-content: flex-end;
	}
</style>
