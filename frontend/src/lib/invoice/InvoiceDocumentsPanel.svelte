<script lang="ts">
	import { onMount } from 'svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Button from '$lib/ui/Button.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import InvoiceDocumentUploadDialog from '$lib/invoice/InvoiceDocumentUploadDialog.svelte';
	import { canViewInvoiceAttachments, canManageInvoiceAttachments } from '$lib/permissions';
	import { INVOICE_ATTACHMENT_TYPE_LABELS } from '$lib/invoice/invoice-attachment-types';
	import type { InvoiceAttachmentType } from '$lib/invoice/invoice-attachment-types';
	import type { User } from '$lib/types';

	interface InvoiceFileListItem {
		id: string;
		entity_type: string;
		entity_id: string;
		file_type: string;
		original_name: string;
		content_type: string;
		size_bytes: number;
		uploaded_at: string;
		uploaded_by: string | null;
		uploaded_by_username: string | null;
	}

	let {
		invoiceId,
		vendorId,
		user,
		mockFiles
	}: {
		invoiceId: string;
		vendorId: string;
		user: User;
		mockFiles?: InvoiceFileListItem[] | null;
	} = $props();

	let files: InvoiceFileListItem[] = $state([]);
	let loading: boolean = $state(true);
	let fetchError: string = $state('');
	let dialogOpen: boolean = $state(false);

	const canView = $derived(canViewInvoiceAttachments(user, vendorId));
	const canManage = $derived(canManageInvoiceAttachments(user, vendorId));
	const shouldRender = $derived(canView && (files.length > 0 || canManage));

	function formatDate(s: string): string {
		return new Date(s).toLocaleDateString();
	}

	async function loadFiles() {
		loading = true;
		fetchError = '';
		try {
			const res = await fetch(`/api/v1/invoices/${invoiceId}/documents`, {
				credentials: 'include'
			});
			if (!res.ok) throw new Error(`${res.status}`);
			files = (await res.json()) as InvoiceFileListItem[];
		} catch (err) {
			fetchError = err instanceof Error ? err.message : 'Failed to load documents.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		if (mockFiles !== undefined && mockFiles !== null) {
			files = mockFiles;
			loading = false;
			return;
		}
		if (canView) {
			loadFiles();
		} else {
			loading = false;
		}
	});

	async function handleUpload(file: File, fileType: InvoiceAttachmentType): Promise<void> {
		const form = new FormData();
		form.append('file', file);
		form.append('file_type', fileType);
		const res = await fetch(`/api/v1/invoices/${invoiceId}/documents`, {
			method: 'POST',
			body: form,
			credentials: 'include'
		});
		if (!res.ok) {
			const text = await res.text().catch(() => '');
			throw new Error(text || `Upload failed: ${res.status}`);
		}
		const newFile = (await res.json()) as InvoiceFileListItem;
		files = [newFile, ...files];
		dialogOpen = false;
	}

	async function handleDelete(fileId: string) {
		if (!confirm('Delete this document?')) return;
		const res = await fetch(`/api/v1/invoices/${invoiceId}/documents/${fileId}`, {
			method: 'DELETE',
			credentials: 'include'
		});
		if (!res.ok) return;
		files = files.filter((f) => f.id !== fileId);
	}
</script>

{#snippet emptyUploadAction()}
	<Button
		variant="primary"
		onclick={() => (dialogOpen = true)}
		data-testid="invoice-documents-upload-btn"
	>
		Upload document
	</Button>
{/snippet}

{#if canView}
	{#if shouldRender}
		<div data-testid="invoice-documents-panel">
			<PanelCard title="Documents">
				{#snippet action()}
					{#if canManage}
						<Button
							variant="primary"
							onclick={() => (dialogOpen = true)}
							data-testid="invoice-documents-upload-btn"
						>
							Upload document
						</Button>
					{/if}
				{/snippet}
				{#snippet children()}
					{#if loading}
						<LoadingState />
					{:else if fetchError}
						<ErrorState message="Failed to load documents." onRetry={loadFiles} />
					{:else if files.length === 0}
						<EmptyState
							title="No documents attached."
							data-testid="invoice-documents-empty-state"
							action={canManage ? emptyUploadAction : undefined}
						></EmptyState>
					{:else}
						<table class="documents-table">
							<thead>
								<tr>
									<th>File name</th>
									<th>Type</th>
									<th>Uploaded by</th>
									<th>Uploaded</th>
									{#if canManage}<th></th>{/if}
								</tr>
							</thead>
							<tbody>
								{#each files as file (file.id)}
									<tr data-testid="invoice-documents-row-{file.id}">
										<td>
											<a
												href="/api/v1/invoices/{invoiceId}/documents/{file.id}"
												download={file.original_name}
											>
												{file.original_name}
											</a>
										</td>
										<td>{INVOICE_ATTACHMENT_TYPE_LABELS[file.file_type as InvoiceAttachmentType] ?? file.file_type}</td>
										<td>{file.uploaded_by_username ?? '—'}</td>
										<td>{formatDate(file.uploaded_at)}</td>
										{#if canManage}
											<td>
												<Button
													variant="ghost"
													onclick={() => handleDelete(file.id)}
													data-testid="invoice-documents-delete-{file.id}-btn"
												>
													Delete
												</Button>
											</td>
										{/if}
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}
				{/snippet}
			</PanelCard>
		</div>
	{/if}

	{#if dialogOpen}
		<InvoiceDocumentUploadDialog
			onSubmit={handleUpload}
			onCancel={() => (dialogOpen = false)}
		/>
	{/if}
{/if}

<style>
	.documents-table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--font-size-sm);
	}
	thead {
		background-color: var(--gray-50);
		border-bottom: 1px solid var(--gray-200);
	}
	thead th {
		padding: var(--space-3) var(--space-4);
		text-align: left;
		font-weight: 500;
		color: var(--gray-700);
	}
	tbody tr {
		border-bottom: 1px solid var(--gray-100);
	}
	tbody tr:last-child {
		border-bottom: none;
	}
	tbody td {
		padding: var(--space-3) var(--space-4);
		color: var(--gray-900);
	}
	tbody td a {
		color: var(--brand-accent);
		text-decoration: none;
	}
	tbody td a:hover {
		text-decoration: underline;
	}
</style>
