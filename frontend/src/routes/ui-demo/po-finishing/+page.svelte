<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Select from '$lib/ui/Select.svelte';
	import PoMetadataPanels from '$lib/po/PoMetadataPanels.svelte';
	import PoRejectionHistoryPanel from '$lib/po/PoRejectionHistoryPanel.svelte';
	import PoInvoicesPanel from '$lib/po/PoInvoicesPanel.svelte';
	import PoActivityPanel from '$lib/po/PoActivityPanel.svelte';
	import type {
		PurchaseOrder,
		InvoiceListItem,
		RemainingLine,
		ActivityLogEntry
	} from '$lib/types';

	type POStatusOption = 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'REVISED';
	type RejectionHistoryOption = '0' | '1' | '3';
	type InvoicesOption = '0' | '1' | '3-procurement' | 'opex-with-1';
	type ActivityOption = 'empty' | '5' | '25';

	const STATUS_OPTIONS: ReadonlyArray<{ value: POStatusOption; label: string }> = [
		{ value: 'PENDING', label: 'PENDING' },
		{ value: 'ACCEPTED', label: 'ACCEPTED' },
		{ value: 'REJECTED', label: 'REJECTED' },
		{ value: 'REVISED', label: 'REVISED' }
	];

	const REJECTION_OPTIONS: ReadonlyArray<{ value: RejectionHistoryOption; label: string }> = [
		{ value: '0', label: '0 records' },
		{ value: '1', label: '1 record' },
		{ value: '3', label: '3 records' }
	];

	const INVOICES_OPTIONS: ReadonlyArray<{ value: InvoicesOption; label: string }> = [
		{ value: '0', label: '0 invoices' },
		{ value: '1', label: '1 invoice' },
		{ value: '3-procurement', label: '3 invoices (PROCUREMENT)' },
		{ value: 'opex-with-1', label: 'OPEX with 1 invoice' }
	];

	const ACTIVITY_OPTIONS: ReadonlyArray<{ value: ActivityOption; label: string }> = [
		{ value: 'empty', label: 'Empty' },
		{ value: '5', label: '5 entries' },
		{ value: '25', label: '25 entries (Show more)' }
	];

	let statusValue: string = $state('ACCEPTED');
	let rejectionValue: string = $state('1');
	let invoicesValue: string = $state('3-procurement');
	let activityValue: string = $state('5');

	const status = $derived(statusValue as POStatusOption);
	const rejectionOption = $derived(rejectionValue as RejectionHistoryOption);
	const invoicesOption = $derived(invoicesValue as InvoicesOption);
	const activityOption = $derived(activityValue as ActivityOption);

	const BASE_DATE = '2026-04-01T00:00:00+00:00';
	const ISSUED_DATE = '2026-01-15T00:00:00+00:00';
	const DELIVERY_DATE = '2026-06-30T00:00:00+00:00';

	const po = $derived<PurchaseOrder>({
		id: 'demo-po-1',
		po_number: 'PO-2026-DEMO',
		status,
		po_type: invoicesOption === 'opex-with-1' ? 'OPEX' : 'PROCUREMENT',
		vendor_id: 'vendor-demo',
		vendor_name: 'Acme Manufacturing',
		vendor_country: 'CN',
		buyer_name: 'TurboTonic Ltd',
		buyer_country: 'US',
		ship_to_address: '123 Commerce St, New York, NY',
		payment_terms: 'NET30',
		currency: 'USD',
		issued_date: ISSUED_DATE,
		required_delivery_date: DELIVERY_DATE,
		terms_and_conditions:
			'All goods must comply with applicable import regulations.\nPayment is due within 30 days of invoice.\nAny disputes must be raised within 14 days of delivery.',
		incoterm: 'FOB',
		port_of_loading: 'CNSHA',
		port_of_discharge: 'USLAX',
		country_of_origin: 'CN',
		country_of_destination: 'US',
		marketplace: status === 'ACCEPTED' ? 'AMZ' : null,
		line_items: [],
		rejection_history: buildRejectionHistory(rejectionOption),
		total_value: '48500.00',
		created_at: BASE_DATE,
		updated_at: BASE_DATE,
		round_count: 0,
		last_actor_role: null,
		advance_paid_at: null,
		has_removed_line: false,
		current_milestone: null
	} as unknown as PurchaseOrder);

	function buildRejectionHistory(
		opt: RejectionHistoryOption
	): { comment: string; rejected_at: string }[] {
		if (opt === '0') return [];
		if (opt === '1') {
			return [{ comment: 'Unit price exceeds budget. Please revise.', rejected_at: '2026-02-10T08:00:00+00:00' }];
		}
		return [
			{ comment: 'Initial rejection: missing certifications.', rejected_at: '2026-01-20T09:00:00+00:00' },
			{ comment: 'Second rejection: delivery date too late.', rejected_at: '2026-02-05T11:00:00+00:00' },
			{ comment: 'Third rejection: unit price still too high.', rejected_at: '2026-02-10T08:00:00+00:00' }
		];
	}

	const invoices = $derived<InvoiceListItem[]>(buildInvoices(invoicesOption));

	function buildInvoices(opt: InvoicesOption): InvoiceListItem[] {
		if (opt === '0') return [];
		if (opt === '1') {
			return [
				{
					id: 'inv-001',
					invoice_number: 'INV-2026-001',
					status: 'APPROVED',
					subtotal: '12000.00',
					created_at: '2026-03-01T00:00:00+00:00'
				}
			];
		}
		if (opt === '3-procurement') {
			return [
				{
					id: 'inv-001',
					invoice_number: 'INV-2026-001',
					status: 'APPROVED',
					subtotal: '12000.00',
					created_at: '2026-03-01T00:00:00+00:00'
				},
				{
					id: 'inv-002',
					invoice_number: 'INV-2026-002',
					status: 'SUBMITTED',
					subtotal: '18000.00',
					created_at: '2026-03-15T00:00:00+00:00'
				},
				{
					id: 'inv-003',
					invoice_number: 'INV-2026-003',
					status: 'DRAFT',
					subtotal: '5500.00',
					created_at: '2026-04-01T00:00:00+00:00'
				}
			];
		}
		// opex-with-1
		return [
			{
				id: 'inv-opex-001',
				invoice_number: 'INV-2026-OPEX-001',
				status: 'SUBMITTED',
				subtotal: '48500.00',
				created_at: '2026-03-10T00:00:00+00:00'
			}
		];
	}

	const remainingMap = $derived<Map<string, RemainingLine>>(buildRemainingMap(invoicesOption));

	function buildRemainingMap(opt: InvoicesOption): Map<string, RemainingLine> {
		if (opt === '3-procurement') {
			return new Map([
				['PART-001', { part_number: 'PART-001', description: 'Steel bolt', ordered: 200, invoiced: 150, remaining: 50 }],
				['PART-002', { part_number: 'PART-002', description: 'Brass washer', ordered: 100, invoiced: 100, remaining: 0 }]
			]);
		}
		if (opt === '1') {
			return new Map([
				['PART-001', { part_number: 'PART-001', description: 'Steel bolt', ordered: 200, invoiced: 80, remaining: 120 }]
			]);
		}
		return new Map();
	}

	const mockActivityEntries = $derived<ActivityLogEntry[]>(buildActivity(activityOption));

	function buildActivity(opt: ActivityOption): ActivityLogEntry[] {
		if (opt === 'empty') return [];
		const count = opt === '5' ? 5 : 25;
		const events = [
			{ event: 'PO_CREATED', category: 'LIVE' },
			{ event: 'PO_SUBMITTED', category: 'ACTION_REQUIRED' },
			{ event: 'PO_LINE_MODIFIED', category: 'ACTION_REQUIRED' },
			{ event: 'PO_MODIFIED', category: 'LIVE' },
			{ event: 'PO_ACCEPTED', category: 'LIVE' },
			{ event: 'INVOICE_CREATED', category: 'LIVE' },
			{ event: 'INVOICE_SUBMITTED', category: 'ACTION_REQUIRED' },
			{ event: 'INVOICE_APPROVED', category: 'LIVE' },
			{ event: 'MILESTONE_POSTED', category: 'LIVE' },
			{ event: 'MILESTONE_OVERDUE', category: 'DELAYED' }
		];
		return Array.from({ length: count }, (_, i) => {
			const src = events[i % events.length];
			const daysAgo = count - i;
			const dt = new Date('2026-04-29T12:00:00Z');
			dt.setUTCDate(dt.getUTCDate() - daysAgo);
			return {
				id: `act-${i}`,
				entity_type: 'PO',
				entity_id: 'demo-po-1',
				event: src.event,
				category: src.category as 'LIVE' | 'ACTION_REQUIRED' | 'DELAYED',
				target_role: 'SM',
				detail: i % 3 === 0 ? `Detail note for event ${i}` : '',
				read_at: null,
				created_at: dt.toISOString()
			};
		});
	}

	function formatDate(s: string): string {
		return new Date(s).toLocaleDateString();
	}

	function formatValue(n: string, code: string): string {
		return `${parseFloat(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${code}`;
	}

	const LABELS: Readonly<Record<string, string>> = {
		'currencies:USD': 'US Dollar',
		'countries:US': 'United States',
		'countries:CN': 'China',
		'incoterms:FOB': 'FOB',
		'ports:CNSHA': 'Shanghai',
		'ports:USLAX': 'Los Angeles',
		'payment_terms:NET30': 'Net 30'
	};

	function resolve(kind: string, code: string): string {
		return LABELS[`${kind}:${code}`] ?? code;
	}
</script>

<svelte:head>
	<title>PO finishing mock — iter 083</title>
</svelte:head>

<div class="page">
	<header class="page__intro">
		<h1>PO finishing mock — iter 083</h1>
		<p>
			Toggleable matrix for the four finishing panels: metadata, rejection history, invoices, and
			activity. Auth-free visual verification surface.
		</p>
	</header>

	<section class="page__controls" aria-label="Mock controls">
		<h2>Controls</h2>
		<div class="page__grid">
			<label class="page__field">
				<span>PO Status</span>
				<Select
					bind:value={statusValue}
					options={STATUS_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="PO Status"
					data-testid="ctl-status"
				/>
			</label>
			<label class="page__field">
				<span>Rejection History</span>
				<Select
					bind:value={rejectionValue}
					options={REJECTION_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Rejection History"
					data-testid="ctl-rejection"
				/>
			</label>
			<label class="page__field">
				<span>Invoices</span>
				<Select
					bind:value={invoicesValue}
					options={INVOICES_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Invoices"
					data-testid="ctl-invoices"
				/>
			</label>
			<label class="page__field">
				<span>Activity</span>
				<Select
					bind:value={activityValue}
					options={ACTIVITY_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Activity"
					data-testid="ctl-activity"
				/>
			</label>
		</div>
	</section>

	<section class="page__section">
		<h2>Metadata Panels</h2>
		<div class="panels-stack">
			<PoMetadataPanels {po} {resolve} {formatDate} {formatValue} />
		</div>
	</section>

	{#if po.rejection_history.length > 0}
		<section class="page__section">
			<h2>Rejection History Panel</h2>
			<PoRejectionHistoryPanel records={po.rejection_history} {formatDate} />
		</section>
	{/if}

	<section class="page__section">
		<h2>Invoices Panel</h2>
		<PoInvoicesPanel {invoices} {po} {remainingMap} {formatDate} {formatValue} />
		{#if invoices.length === 0 && po.po_type !== 'OPEX'}
			<p class="page__hint">Panel hidden (no invoices, PROCUREMENT).</p>
		{/if}
	</section>

	<section class="page__section">
		<h2>Activity Panel</h2>
		<PoActivityPanel poId={po.id} mockEntries={mockActivityEntries} />
	</section>
</div>

<style>
	.page {
		max-width: 80rem;
		margin: 0 auto;
		padding: var(--space-6) var(--space-4) var(--space-20);
		display: flex;
		flex-direction: column;
		gap: var(--space-8);
	}
	.page__intro h1 {
		font-size: var(--font-size-2xl);
		margin: 0 0 var(--space-2);
	}
	.page__intro p {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		margin: 0;
	}
	.page__controls {
		background: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.page__controls h2 {
		font-size: var(--font-size-lg);
		margin: 0;
	}
	.page__grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--space-3);
	}
	.page__field {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.page__section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-4);
		border: 1px dashed var(--gray-300);
		border-radius: var(--radius-lg);
	}
	.page__section h2 {
		font-size: var(--font-size-lg);
		margin: 0;
	}
	.page__hint {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
	.panels-stack {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
</style>
