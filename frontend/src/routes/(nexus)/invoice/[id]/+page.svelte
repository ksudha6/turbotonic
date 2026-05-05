<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import {
		getInvoice,
		getPO,
		submitInvoice,
		approveInvoice,
		payInvoice,
		disputeInvoice,
		resolveInvoice,
		downloadInvoicePdf
	} from '$lib/api';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import InvoiceDetailHeader from '$lib/invoice/InvoiceDetailHeader.svelte';
	import InvoiceActionRail from '$lib/invoice/InvoiceActionRail.svelte';
	import InvoiceDisputeModal from '$lib/invoice/InvoiceDisputeModal.svelte';
	import InvoiceMetadataPanel from '$lib/invoice/InvoiceMetadataPanel.svelte';
	import InvoiceDisputeReasonPanel from '$lib/invoice/InvoiceDisputeReasonPanel.svelte';
	import InvoiceDocumentsPanel from '$lib/invoice/InvoiceDocumentsPanel.svelte';
	import InvoiceLineItemsPanel from '$lib/invoice/InvoiceLineItemsPanel.svelte';
	import InvoiceActivityPanel from '$lib/invoice/InvoiceActivityPanel.svelte';
	import type { Invoice, UserRole } from '$lib/types';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let invoice: Invoice | null = $state(null);
	let poNumber: string | undefined = $state(undefined);
	let vendorName: string | undefined = $state(undefined);
	let vendorId: string | undefined = $state(undefined);
	let loading: boolean = $state(true);
	let errorMessage: string = $state('');
	let showDisputeModal: boolean = $state(false);

	const id: string = page.params.id ?? '';
	const user = $derived(page.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);

	async function fetchInvoice() {
		loading = true;
		errorMessage = '';
		try {
			invoice = await getInvoice(id);
			try {
				const po = await getPO(invoice.po_id);
				poNumber = po.po_number;
				vendorName = po.vendor_name;
				vendorId = po.vendor_id;
			} catch {
				poNumber = undefined;
				vendorName = undefined;
				vendorId = undefined;
			}
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Failed to load invoice';
			invoice = null;
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchInvoice();
	});

	async function handleSubmit() {
		await submitInvoice(id);
		await fetchInvoice();
	}
	async function handleApprove() {
		await approveInvoice(id);
		await fetchInvoice();
	}
	async function handlePay() {
		await payInvoice(id);
		await fetchInvoice();
	}
	function openDispute() {
		showDisputeModal = true;
	}
	async function confirmDispute(reason: string) {
		showDisputeModal = false;
		await disputeInvoice(id, reason);
		await fetchInvoice();
	}
	async function handleResolve() {
		await resolveInvoice(id);
		await fetchInvoice();
	}
	function handleDownloadPdf() {
		downloadInvoicePdf(id);
	}
</script>

<svelte:head>
	<title>{invoice?.invoice_number ?? 'Invoice'}</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Invoice">
	{#snippet userMenu()}
		<UserMenu name={userName} {role} />
	{/snippet}

	<div class="invoice-detail-page">
		{#if loading}
			<LoadingState label="Loading invoice" />
		{:else if errorMessage}
			<ErrorState message={errorMessage} onRetry={fetchInvoice} />
		{:else if invoice}
			<InvoiceDetailHeader {invoice} {poNumber} {vendorName}>
				{#snippet actionRail()}
					<InvoiceActionRail
						{invoice}
						{role}
						mode="inline"
						onSubmit={handleSubmit}
						onApprove={handleApprove}
						onPay={handlePay}
						onDispute={openDispute}
						onResolve={handleResolve}
						onDownloadPdf={handleDownloadPdf}
					/>
				{/snippet}
			</InvoiceDetailHeader>

			{#if invoice.status === 'DISPUTED' && invoice.dispute_reason}
				<InvoiceDisputeReasonPanel reason={invoice.dispute_reason} />
			{/if}

			<InvoiceMetadataPanel {invoice} {poNumber} />

			{#if vendorId && user}
				<InvoiceDocumentsPanel
					invoiceId={invoice.id}
					{vendorId}
					{user}
				/>
			{/if}

			<InvoiceLineItemsPanel lineItems={invoice.line_items} />

			<InvoiceActivityPanel invoiceId={invoice.id} />
		{/if}
	</div>

	{#if invoice && !loading}
		<div class="invoice-detail-page__sticky-rail">
			<InvoiceActionRail
				{invoice}
				{role}
				mode="sticky-bottom"
				onSubmit={handleSubmit}
				onApprove={handleApprove}
				onPay={handlePay}
				onDispute={openDispute}
				onResolve={handleResolve}
				onDownloadPdf={handleDownloadPdf}
			/>
		</div>
	{/if}
</AppShell>

{#if showDisputeModal}
	<InvoiceDisputeModal onConfirm={confirmDispute} onCancel={() => (showDisputeModal = false)} />
{/if}

<style>
	.invoice-detail-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.invoice-detail-page__sticky-rail {
		display: block;
	}
	@media (min-width: 768px) {
		.invoice-detail-page__sticky-rail {
			display: none;
		}
	}
</style>
