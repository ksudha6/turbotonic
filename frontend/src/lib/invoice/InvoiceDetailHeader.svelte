<script lang="ts">
	import DetailHeader from '$lib/ui/DetailHeader.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import type { Invoice, InvoiceStatus } from '$lib/types';
	import type { Snippet } from 'svelte';

	let {
		invoice,
		vendorName,
		poNumber,
		actionRail,
		'data-testid': testid
	}: {
		invoice: Invoice;
		vendorName?: string;
		poNumber?: string;
		actionRail?: Snippet;
		'data-testid'?: string;
	} = $props();

	type Tone = 'green' | 'blue' | 'orange' | 'red' | 'gray';

	const STATUS_TONE: Readonly<Record<InvoiceStatus, Tone>> = {
		DRAFT: 'gray',
		SUBMITTED: 'blue',
		APPROVED: 'green',
		PAID: 'green',
		DISPUTED: 'red'
	};

	function statusLabel(status: string): string {
		return status.charAt(0) + status.slice(1).toLowerCase();
	}

	function formatDate(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	const subtitle = $derived(
		`${vendorName ?? '—'} · PO ${poNumber ?? invoice.po_id} · Created ${formatDate(invoice.created_at)}`
	);
</script>

<div class="invoice-detail-header" data-testid={testid ?? 'invoice-detail-header'}>
	<div class="invoice-detail-header__main">
		<DetailHeader
			backHref="/invoices"
			backLabel="Invoices"
			title={invoice.invoice_number}
			{subtitle}
		>
			{#snippet statusPill()}
				<StatusPill
					tone={STATUS_TONE[invoice.status]}
					label={statusLabel(invoice.status)}
					data-testid="invoice-detail-status"
				/>
			{/snippet}
		</DetailHeader>
	</div>
	{#if actionRail}
		<div class="invoice-detail-header__rail">{@render actionRail()}</div>
	{/if}
</div>

<style>
	.invoice-detail-header {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.invoice-detail-header__main {
		flex: 1 1 auto;
		min-width: 0;
	}
	.invoice-detail-header__rail {
		display: none;
	}
	@media (min-width: 768px) {
		.invoice-detail-header {
			flex-direction: row;
			align-items: flex-start;
			justify-content: space-between;
			gap: var(--space-4);
		}
		.invoice-detail-header__rail {
			display: flex;
			align-items: center;
			margin-top: var(--space-6);
		}
	}
</style>
