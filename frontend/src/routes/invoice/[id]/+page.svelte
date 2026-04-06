<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getInvoice, submitInvoice, approveInvoice, payInvoice, disputeInvoice, resolveInvoice, downloadInvoicePdf } from '$lib/api';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import DisputeDialog from '$lib/components/DisputeDialog.svelte';
	import ActivityTimeline from '$lib/components/ActivityTimeline.svelte';
	import type { Invoice } from '$lib/types';

	let invoice: Invoice | null = $state(null);
	let loading: boolean = $state(true);
	let showDisputeDialog: boolean = $state(false);

	const id: string = $page.params.id ?? '';

	async function fetchInvoice() {
		loading = true;
		try {
			invoice = await getInvoice(id);
		} finally {
			loading = false;
		}
	}

	onMount(() => { fetchInvoice(); });

	async function handleSubmit() { await submitInvoice(id); await fetchInvoice(); }
	async function handleApprove() { await approveInvoice(id); await fetchInvoice(); }
	async function handlePay() { await payInvoice(id); await fetchInvoice(); }
	async function handleDispute(reason: string) {
		showDisputeDialog = false;
		await disputeInvoice(id, reason);
		await fetchInvoice();
	}
	async function handleResolve() { await resolveInvoice(id); await fetchInvoice(); }

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatPrice(price: string): string {
		return parseFloat(price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}

	function formatValue(value: string, currency: string): string {
		return `${formatPrice(value)} ${currency}`;
	}
</script>

{#if loading}
	<p>Loading...</p>
{:else if invoice}
	<div class="section card">
		<div class="detail-header">
			<h1>{invoice.invoice_number}</h1>
			<StatusPill status={invoice.status} />
		</div>
		<div class="info-grid">
			<div class="info-item">
				<span class="field-label">Currency</span>
				<span class="value">{invoice.currency}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Payment Terms</span>
				<span class="value">{invoice.payment_terms}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Subtotal</span>
				<span class="value">{formatValue(invoice.subtotal, invoice.currency)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Created</span>
				<span class="value">{formatDate(invoice.created_at)}</span>
			</div>
		</div>
		<div class="po-link">
			<a href="/po/{invoice.po_id}">View Purchase Order</a>
		</div>
	</div>

	{#if invoice.dispute_reason}
		<div class="section card">
			<h2>Dispute Reason</h2>
			<p class="dispute-text">{invoice.dispute_reason}</p>
		</div>
	{/if}

	<div class="section card">
		<h2>Line Items</h2>
		<table class="table">
			<thead>
				<tr>
					<th>Part Number</th>
					<th>Description</th>
					<th>Qty</th>
					<th>UoM</th>
					<th>Unit Price</th>
				</tr>
			</thead>
			<tbody>
				{#each invoice.line_items as item}
					<tr>
						<td>{item.part_number}</td>
						<td>{item.description}</td>
						<td>{item.quantity}</td>
						<td>{item.uom}</td>
						<td>{formatPrice(item.unit_price)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class="section card">
		<h2>Activity</h2>
		<ActivityTimeline entityType="INVOICE" entityId={invoice.id} />
	</div>

	<div class="actions">
		<button class="btn btn-secondary" onclick={() => downloadInvoicePdf(id)}>Download PDF</button>
		{#if invoice.status === 'DRAFT'}
			<button class="btn btn-primary" onclick={handleSubmit}>Submit</button>
		{:else if invoice.status === 'SUBMITTED'}
			<button class="btn btn-success" onclick={handleApprove}>Approve</button>
			<button class="btn btn-danger" onclick={() => (showDisputeDialog = true)}>Dispute</button>
		{:else if invoice.status === 'APPROVED'}
			<button class="btn btn-primary" onclick={handlePay}>Pay</button>
		{:else if invoice.status === 'DISPUTED'}
			<button class="btn btn-secondary" onclick={handleResolve}>Resolve</button>
		{:else if invoice.status === 'PAID'}
			<p class="paid-message">This invoice has been paid.</p>
		{/if}
	</div>

	{#if showDisputeDialog}
		<DisputeDialog
			onConfirm={handleDispute}
			onCancel={() => (showDisputeDialog = false)}
		/>
	{/if}
{/if}

<style>
	.detail-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-4);
	}

	.info-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
	}

	.info-item .field-label {
		display: block;
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-bottom: var(--space-1);
	}

	.info-item .value {
		font-size: var(--font-size-base);
		color: var(--gray-900);
	}

	.po-link {
		margin-top: var(--space-4);
	}

	.section {
		margin-bottom: var(--space-6);
	}

	.section h2 {
		margin-bottom: var(--space-4);
	}

	.dispute-text {
		color: var(--gray-800);
		white-space: pre-wrap;
	}

	.actions {
		display: flex;
		gap: var(--space-3);
		padding-top: var(--space-4);
		border-top: 1px solid var(--gray-200);
		margin-bottom: var(--space-6);
	}

	.paid-message {
		color: var(--gray-600);
	}
</style>
