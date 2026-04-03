<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getPO, submitPO, acceptPO, rejectPO, resubmitPO, downloadPoPdf, createInvoice, listInvoicesByPO, fetchReferenceData, getRemainingQuantities, listMilestones, postMilestone } from '$lib/api';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import RejectDialog from '$lib/components/RejectDialog.svelte';
	import CreateInvoiceDialog from '$lib/components/CreateInvoiceDialog.svelte';
	import MilestoneTimeline from '$lib/components/MilestoneTimeline.svelte';
	import type { PurchaseOrder, InvoiceListItem, ReferenceData, RemainingLine, InvoiceLineItemCreate, MilestoneUpdate } from '$lib/types';
	import { buildLabelResolver } from '$lib/labels';

	let po: PurchaseOrder | null = $state(null);
	let loading: boolean = $state(true);
	let showRejectDialog: boolean = $state(false);
	let invoices: InvoiceListItem[] = $state([]);
	let refData: ReferenceData | null = $state(null);
	let resolver: ReturnType<typeof buildLabelResolver> | null = $state(null);
	let remainingMap: Map<string, RemainingLine> = $state(new Map());
	let showInvoiceDialog: boolean = $state(false);
	let remainingLines: RemainingLine[] = $state([]);
	let opexError: string = $state('');
	let milestones: MilestoneUpdate[] = $state([]);

	const id: string = $page.params.id ?? '';

	function resolve(category: string, code: string): string {
		if (!resolver) return code;
		return resolver.resolve(category, code);
	}

	async function fetchPO() {
		loading = true;
		try {
			[po, invoices, refData] = await Promise.all([getPO(id), listInvoicesByPO(id), fetchReferenceData()]);
			resolver = buildLabelResolver(refData);
			if (po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT') {
				const resp = await getRemainingQuantities(id);
				remainingMap = new Map(resp.lines.map((l) => [l.part_number, l]));
				milestones = await listMilestones(id);
			}
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchPO();
	});

	async function handleSubmit() {
		await submitPO(id);
		await fetchPO();
	}

	async function handleAccept() {
		await acceptPO(id);
		await fetchPO();
	}

	async function handleReject(comment: string) {
		showRejectDialog = false;
		await rejectPO(id, comment);
		await fetchPO();
	}

	async function handleResubmit() {
		await resubmitPO(id);
		await fetchPO();
	}

	async function handleCreateInvoice() {
		const resp = await getRemainingQuantities(id);
		const allInvoiced = resp.lines.every((l) => l.remaining === 0);
		if (allInvoiced) {
			alert('All quantities already invoiced');
			return;
		}
		remainingLines = resp.lines;
		showInvoiceDialog = true;
	}

	async function handleInvoiceConfirm(lineItems: InvoiceLineItemCreate[]) {
		showInvoiceDialog = false;
		const invoice = await createInvoice(id, lineItems);
		goto(`/invoice/${invoice.id}`);
	}

	async function handlePostMilestone(milestone: string) {
		await postMilestone(id, milestone);
		milestones = await listMilestones(id);
	}

	async function handleCreateOpexInvoice() {
		opexError = '';
		try {
			const invoice = await createInvoice(id);
			goto(`/invoice/${invoice.id}`);
		} catch (err: unknown) {
			const msg = err instanceof Error ? err.message : String(err);
			opexError = msg || 'Failed to create invoice';
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatValue(value: string, currency: string): string {
		return `${parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
	}

	function formatPrice(price: string): string {
		return parseFloat(price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}
</script>

{#if loading}
	<p>Loading...</p>
{:else if po}
	<div class="section card">
		<div class="detail-header">
			<h1>{po.po_number}</h1>
			<StatusPill status={po.status} />
		</div>
		<div class="info-grid">
			<div class="info-item">
				<span class="field-label">Currency</span>
				<span class="value">{resolve('currencies', po.currency)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Issued Date</span>
				<span class="value">{formatDate(po.issued_date)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Delivery Date</span>
				<span class="value">{formatDate(po.required_delivery_date)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Total Value</span>
				<span class="value">{formatValue(po.total_value, po.currency)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Payment Terms</span>
				<span class="value">{resolve('payment_terms', po.payment_terms)}</span>
			</div>
		</div>
	</div>

	<div class="section card">
		<h2>Buyer</h2>
		<div class="info-grid">
			<div class="info-item">
				<span class="field-label">Name</span>
				<span class="value">{po.buyer_name}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Country</span>
				<span class="value">{resolve('countries', po.buyer_country)}</span>
			</div>
		</div>
	</div>

	<div class="section card">
		<h2>Vendor</h2>
		<div class="info-grid">
			<div class="info-item">
				<span class="field-label">Name</span>
				<span class="value">{po.vendor_name}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Country</span>
				<span class="value">{resolve('countries', po.vendor_country)}</span>
			</div>
		</div>
	</div>

	<div class="section card">
		<h2>Trade Details</h2>
		<div class="info-grid">
			<div class="info-item">
				<span class="field-label">Incoterm</span>
				<span class="value">{resolve('incoterms', po.incoterm)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Port of Loading</span>
				<span class="value">{resolve('ports', po.port_of_loading)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Port of Discharge</span>
				<span class="value">{resolve('ports', po.port_of_discharge)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Country of Origin</span>
				<span class="value">{resolve('countries', po.country_of_origin)}</span>
			</div>
			<div class="info-item">
				<span class="field-label">Country of Destination</span>
				<span class="value">{resolve('countries', po.country_of_destination)}</span>
			</div>
		</div>
	</div>

	<div class="section card">
		<h2>Terms &amp; Conditions</h2>
		<p class="terms-text">{po.terms_and_conditions}</p>
	</div>

	<div class="section card">
		<h2>Line Items</h2>
		<table class="table">
			<thead>
				<tr>
					<th>Part Number</th>
					<th>Description</th>
					<th>Qty</th>
					{#if po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT'}
						<th>Invoiced</th>
						<th>Remaining</th>
					{/if}
					<th>UoM</th>
					<th>Unit Price</th>
					<th>HS Code</th>
					<th>Origin</th>
				</tr>
			</thead>
			<tbody>
				{#each po.line_items as item}
					<tr>
						<td>{item.part_number}</td>
						<td>{item.description}</td>
						<td>{item.quantity}</td>
						{#if po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT'}
							{@const r = remainingMap.get(item.part_number)}
							<td>{r ? r.invoiced : 0}</td>
							<td>{r ? r.remaining : 0}</td>
						{/if}
						<td>{item.uom}</td>
						<td>{formatPrice(item.unit_price)}</td>
						<td>{item.hs_code}</td>
						<td>{resolve('countries', item.country_of_origin)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT'}
		<div class="section card">
			<h2>Production Status</h2>
			<MilestoneTimeline milestones={milestones} onPost={handlePostMilestone} />
		</div>
	{/if}

	{#if po.rejection_history.length > 0}
		<div class="section card">
			<h2>Rejection History</h2>
			{#each [...po.rejection_history].reverse() as record}
				<div class="rejection-record">
					<p class="rejection-comment">{record.comment}</p>
					<p class="rejection-date">{formatDate(record.rejected_at)}</p>
				</div>
			{/each}
		</div>
	{/if}

	{#if invoices.length > 0}
		<div class="section card">
			<h2>Invoices</h2>
			<table class="table">
				<thead>
					<tr>
						<th>Invoice #</th>
						<th>Status</th>
						<th>Subtotal</th>
						<th>Created</th>
					</tr>
				</thead>
				<tbody>
					{#each invoices as inv}
						<tr>
							<td><a href="/invoice/{inv.id}">{inv.invoice_number}</a></td>
							<td><StatusPill status={inv.status} /></td>
							<td>{formatValue(inv.subtotal, po.currency)}</td>
							<td>{formatDate(inv.created_at)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

	<div class="actions">
		<button class="btn btn-secondary" onclick={() => downloadPoPdf(id)}>Download PDF</button>
		{#if po.status === 'DRAFT'}
			<a href="/po/{po.id}/edit" class="btn btn-secondary">Edit</a>
			<button class="btn btn-primary" onclick={handleSubmit}>Submit</button>
		{:else if po.status === 'PENDING'}
			<button class="btn btn-success" onclick={handleAccept}>Accept</button>
			<button class="btn btn-danger" onclick={() => (showRejectDialog = true)}>Reject</button>
		{:else if po.status === 'REJECTED'}
			<a href="/po/{po.id}/edit" class="btn btn-secondary">Edit</a>
		{:else if po.status === 'REVISED'}
			<button class="btn btn-primary" onclick={handleResubmit}>Resubmit</button>
		{:else if po.status === 'ACCEPTED'}
			{#if po.po_type === 'PROCUREMENT'}
				<button class="btn btn-primary" onclick={handleCreateInvoice}>Create Invoice</button>
			{:else if po.po_type === 'OPEX'}
				<button class="btn btn-primary" onclick={handleCreateOpexInvoice}>Create Invoice</button>
				{#if opexError}
					<p class="error-message">{opexError}</p>
				{/if}
			{/if}
		{/if}
	</div>

	{#if showRejectDialog}
		<RejectDialog
			onConfirm={handleReject}
			onCancel={() => (showRejectDialog = false)}
		/>
	{/if}

	{#if showInvoiceDialog}
		<CreateInvoiceDialog
			lines={remainingLines}
			onConfirm={handleInvoiceConfirm}
			onCancel={() => (showInvoiceDialog = false)}
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

	.section {
		margin-bottom: var(--space-6);
	}

	.section h2 {
		margin-bottom: var(--space-4);
	}

	.terms-text {
		white-space: pre-wrap;
	}

	.actions {
		display: flex;
		gap: var(--space-3);
		padding-top: var(--space-4);
		border-top: 1px solid var(--gray-200);
		margin-bottom: var(--space-6);
	}

	.accepted-message {
		color: var(--gray-600);
	}

	.error-message {
		color: var(--red-600);
		font-size: var(--font-size-sm);
		margin-top: var(--space-2);
	}

	.rejection-record {
		padding: var(--space-3) 0;
		border-bottom: 1px solid var(--gray-100);
	}

	.rejection-record:last-child {
		border-bottom: none;
	}

	.rejection-comment {
		color: var(--gray-800);
		margin-bottom: var(--space-1);
	}

	.rejection-date {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}
</style>
