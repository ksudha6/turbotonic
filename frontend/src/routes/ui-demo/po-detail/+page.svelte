<script lang="ts">
	import PoDetailHeader from '$lib/po/PoDetailHeader.svelte';
	import PoActionRail from '$lib/po/PoActionRail.svelte';
	import PoAdvancePaymentPanel from '$lib/po/PoAdvancePaymentPanel.svelte';
	import PoCertWarningsBanner from '$lib/po/PoCertWarningsBanner.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Select from '$lib/ui/Select.svelte';
	import Toggle from '$lib/ui/Toggle.svelte';
	import type {
		PurchaseOrder,
		POStatus,
		POType,
		UserRole,
		CertWarning,
		LineItem
	} from '$lib/types';

	const ROLES: ReadonlyArray<UserRole> = [
		'ADMIN',
		'SM',
		'VENDOR',
		'PROCUREMENT_MANAGER',
		'FREIGHT_MANAGER',
		'QUALITY_LAB'
	];
	const STATUSES: ReadonlyArray<POStatus> = [
		'DRAFT',
		'PENDING',
		'MODIFIED',
		'ACCEPTED',
		'REJECTED',
		'REVISED'
	];
	const PO_TYPES: ReadonlyArray<POType> = ['PROCUREMENT', 'OPEX'];

	let roleValue = $state<string>('SM');
	let statusValue = $state<string>('ACCEPTED');
	let poTypeValue = $state<string>('PROCUREMENT');
	const role = $derived(roleValue as UserRole);
	const status = $derived(statusValue as POStatus);
	const poType = $derived(poTypeValue as POType);
	let advancePaid = $state(false);
	let firstMilestonePosted = $state(false);
	let paymentTermHasAdvance = $state(true);
	let hasCertWarnings = $state(true);
	let hasRemovedLine = $state(false);
	let warningCountValue = $state<string>('3');
	const warningCount = $derived(warningCountValue);
	let certDismissed = $state(false);
	let lastClicked = $state('');

	const LINE_ITEMS: LineItem[] = [
		{
			part_number: 'WIDGET-001',
			description: 'Industrial widget, blue',
			quantity: 100,
			uom: 'EA',
			unit_price: '12.50',
			hs_code: '8473.30',
			country_of_origin: 'CN',
			product_id: 'prod-1',
			status: 'ACCEPTED',
			required_delivery_date: null,
			history: []
		},
		{
			part_number: 'WIDGET-002',
			description: 'Industrial widget, red',
			quantity: 50,
			uom: 'EA',
			unit_price: '14.75',
			hs_code: '8473.30',
			country_of_origin: 'CN',
			product_id: 'prod-2',
			status: 'ACCEPTED',
			required_delivery_date: null,
			history: []
		},
		{
			part_number: 'GASKET-100',
			description: 'Rubber gasket, 50mm',
			quantity: 200,
			uom: 'EA',
			unit_price: '0.85',
			hs_code: '4016.93',
			country_of_origin: 'CN',
			product_id: 'prod-3',
			status: 'ACCEPTED',
			required_delivery_date: null,
			history: []
		}
	];

	const ALL_WARNINGS: CertWarning[] = [
		{ line_item_index: 0, part_number: 'WIDGET-001', product_id: 'prod-1', qualification_name: 'CE marking', reason: 'MISSING' },
		{ line_item_index: 1, part_number: 'WIDGET-002', product_id: 'prod-2', qualification_name: 'RoHS compliance', reason: 'EXPIRED' },
		{ line_item_index: 2, part_number: 'GASKET-100', product_id: 'prod-3', qualification_name: 'REACH SVHC', reason: 'MISSING' },
		{ line_item_index: 0, part_number: 'WIDGET-001', product_id: 'prod-1', qualification_name: 'ISO 9001', reason: 'EXPIRED' },
		{ line_item_index: 1, part_number: 'WIDGET-002', product_id: 'prod-2', qualification_name: 'UL listing', reason: 'MISSING' },
		{ line_item_index: 2, part_number: 'GASKET-100', product_id: 'prod-3', qualification_name: 'FDA food contact', reason: 'MISSING' },
		{ line_item_index: 0, part_number: 'WIDGET-001', product_id: 'prod-1', qualification_name: 'FCC Part 15', reason: 'EXPIRED' },
		{ line_item_index: 1, part_number: 'WIDGET-002', product_id: 'prod-2', qualification_name: 'RCM marking', reason: 'MISSING' }
	];

	const po = $derived<PurchaseOrder>({
		id: 'po-demo-1',
		po_number: 'PO-2026-0142',
		status,
		po_type: poType,
		vendor_id: 'v-1',
		buyer_name: 'Acme Buyer Co',
		buyer_country: 'US',
		vendor_name: 'Acme Manufacturing Ltd',
		vendor_country: 'CN',
		issued_date: '2026-04-01',
		required_delivery_date: '2026-06-15',
		total_value: '4262.50',
		currency: 'USD',
		current_milestone: firstMilestonePosted ? 'PRODUCTION_STARTED' : null,
		marketplace: 'EU',
		has_removed_line: hasRemovedLine,
		round_count: 1,
		ship_to_address: '500 Buyer Way, Springfield, US',
		payment_terms: paymentTermHasAdvance ? 'ADVANCE_30' : 'NET_30',
		terms_and_conditions: 'Standard terms apply.',
		incoterm: 'FOB',
		port_of_loading: 'CNSHA',
		port_of_discharge: 'USLAX',
		country_of_origin: 'CN',
		country_of_destination: 'US',
		line_items: LINE_ITEMS,
		rejection_history: [],
		created_at: '2026-04-01T10:00:00Z',
		updated_at: '2026-04-15T15:30:00Z',
		advance_paid_at: advancePaid ? '2026-04-10T09:00:00Z' : null,
		last_actor_role: 'SM'
	});

	const visibleWarnings = $derived<CertWarning[]>(
		hasCertWarnings ? ALL_WARNINGS.slice(0, parseInt(warningCount, 10)) : []
	);

	function handle(action: string): void {
		lastClicked = `${action} @ ${new Date().toLocaleTimeString()}`;
	}

	const ROLE_OPTIONS = ROLES.map((r) => ({ value: r, label: r }));
	const STATUS_OPTIONS = STATUSES.map((s) => ({ value: s, label: s }));
	const POTYPE_OPTIONS = PO_TYPES.map((p) => ({ value: p, label: p }));
	const WARNING_OPTIONS = [
		{ value: '1', label: '1 warning' },
		{ value: '3', label: '3 warnings' },
		{ value: '8', label: '8 warnings (Show more)' }
	];

	type CellSummary = { actions: string[] };

	function matrixActions(r: UserRole, s: POStatus): string[] {
		const readOnly = r === 'PROCUREMENT_MANAGER' || r === 'FREIGHT_MANAGER' || r === 'QUALITY_LAB';
		if (readOnly) return ['Download PDF'];
		const adminOrSm = r === 'ADMIN' || r === 'SM';
		const out: string[] = [];
		if (s === 'DRAFT') {
			if (adminOrSm) {
				out.push('Edit');
				out.push('Submit');
			}
		} else if (s === 'PENDING') {
			if (r === 'VENDOR') out.push('Accept');
		} else if (s === 'MODIFIED') {
			// per-line only
		} else if (s === 'REJECTED') {
			if (adminOrSm) {
				out.push('Edit');
				out.push('Resubmit');
			}
		} else if (s === 'REVISED') {
			if (adminOrSm) out.push('Resubmit');
		} else if (s === 'ACCEPTED') {
			if (r === 'VENDOR') {
				out.push('Create invoice');
				if (poType === 'PROCUREMENT') out.push('Post milestone');
			}
		}
		out.push('Download PDF');
		return out;
	}

	const matrix = $derived<Array<{ role: UserRole; cells: Array<{ status: POStatus; summary: CellSummary }> }>>(
		ROLES.map((r) => ({
			role: r,
			cells: STATUSES.map((s) => ({ status: s, summary: { actions: matrixActions(r, s) } }))
		}))
	);
</script>

<svelte:head>
	<title>PO Detail Mock — Phase 4.2 gaps</title>
</svelte:head>

<div class="page">
	<header class="page__intro">
		<h1>PO Detail mock — gaps G-13, G-14, G-17, G-20, G-23</h1>
		<p>
			Resize to 390px to verify the sticky bottom action rail. Toggle role / status /
			payment-terms / advance / cert-warnings to drive each gap.
		</p>
		<p class="page__last">Last action: <code>{lastClicked || '—'}</code></p>
	</header>

	<section class="page__controls">
		<h2>Controls</h2>
		<div class="controls-grid">
			<label>
				<span>Role</span>
				<Select bind:value={roleValue} options={ROLE_OPTIONS} data-testid="ctl-role" />
			</label>
			<label>
				<span>Status</span>
				<Select bind:value={statusValue} options={STATUS_OPTIONS} data-testid="ctl-status" />
			</label>
			<label>
				<span>PO type</span>
				<Select bind:value={poTypeValue} options={POTYPE_OPTIONS} data-testid="ctl-potype" />
			</label>
			<label>
				<span>Warnings</span>
				<Select bind:value={warningCountValue} options={WARNING_OPTIONS} data-testid="ctl-warning-count" />
			</label>
		</div>
		<div class="controls-toggles">
			<label class="toggle-row">
				<Toggle bind:pressed={paymentTermHasAdvance} label="Payment term has advance" />
				<span>Payment term has advance</span>
			</label>
			<label class="toggle-row">
				<Toggle bind:pressed={advancePaid} label="Advance paid" />
				<span>Advance paid</span>
			</label>
			<label class="toggle-row">
				<Toggle bind:pressed={firstMilestonePosted} label="First milestone posted" />
				<span>First milestone posted</span>
			</label>
			<label class="toggle-row">
				<Toggle bind:pressed={hasCertWarnings} label="Has cert warnings" />
				<span>Has cert warnings</span>
			</label>
			<label class="toggle-row">
				<Toggle bind:pressed={hasRemovedLine} label="Has removed line (Partial pill)" />
				<span>Has removed line (Partial pill)</span>
			</label>
		</div>
	</section>

	<section class="page__section">
		<h2>G-13 — Detail header, status pill, back nav</h2>
		<PoDetailHeader {po}>
			{#snippet actionRail()}
				<PoActionRail
					{po}
					{role}
					mode="inline"
					onEdit={() => handle('edit')}
					onSubmit={() => handle('submit')}
					onResubmit={() => handle('resubmit')}
					onAccept={() => handle('accept')}
					onMarkAdvancePaid={() => handle('mark-advance-paid')}
					onCreateInvoice={() => handle('create-invoice')}
					onPostMilestone={() => handle('post-milestone')}
					onDownloadPdf={() => handle('download-pdf')}
				/>
			{/snippet}
		</PoDetailHeader>
		<PoCertWarningsBanner warnings={visibleWarnings} bind:dismissed={certDismissed} />
		<PanelCard title="First detail panel">
			Reference position. The cert-warnings banner sits between the header and this card per
			G-13 #4.
		</PanelCard>
	</section>

	<section class="page__section">
		<h2>G-14 — Action rail by role × status</h2>
		<p class="page__hint">
			The standalone rail below reflects the current role and status from the controls. The matrix
			previews all 36 cells.
		</p>
		<div class="standalone-rail">
			<PoActionRail
				{po}
				{role}
				mode="inline"
				onEdit={() => handle('edit')}
				onSubmit={() => handle('submit')}
				onResubmit={() => handle('resubmit')}
				onAccept={() => handle('accept')}
				onMarkAdvancePaid={() => handle('mark-advance-paid')}
				onCreateInvoice={() => handle('create-invoice')}
				onPostMilestone={() => handle('post-milestone')}
				onDownloadPdf={() => handle('download-pdf')}
			/>
		</div>
		<div class="matrix-wrap">
			<table class="matrix">
				<thead>
					<tr>
						<th scope="col">Role \\ Status</th>
						{#each STATUSES as s (s)}
							<th scope="col">{s}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each matrix as row (row.role)}
						<tr>
							<th scope="row">{row.role}</th>
							{#each row.cells as c (c.status)}
								<td class:matrix__cell--current={c.status === status && row.role === role}>
									{#if c.summary.actions.length === 1 && c.summary.actions[0] === 'Download PDF'}
										<span class="matrix__solo">PDF only</span>
									{:else}
										{c.summary.actions.join(' · ')}
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>

	<section class="page__section">
		<h2>G-17 — Advance payment gate banner</h2>
		<p class="page__hint">
			Toggle "Payment term has advance" off to confirm the panel does not render. Toggle "Advance
			paid" and "First milestone posted" to switch between open/closed gate copy.
		</p>
		<PoAdvancePaymentPanel
			{po}
			{role}
			{paymentTermHasAdvance}
			{firstMilestonePosted}
			onMarkAdvancePaid={() => handle('mark-advance-paid')}
		/>
		{#if !paymentTermHasAdvance}
			<p class="page__muted">(Panel hidden — payment term has no advance.)</p>
		{/if}
	</section>

	<section class="page__section">
		<h2>G-20 — Cert warnings banner + dismissal</h2>
		<p class="page__hint">
			Pick 1, 3, or 8 warnings to test the "Show n more" toggle. Dismissal is per-page-load only
			— per the inventory the in-memory dismissal does not persist across PO opens.
		</p>
		<button
			type="button"
			class="link-button"
			onclick={() => {
				certDismissed = false;
			}}
		>
			Reset dismissal
		</button>
		<PoCertWarningsBanner warnings={visibleWarnings} bind:dismissed={certDismissed} />
		{#if visibleWarnings.length === 0}
			<p class="page__muted">(Banner hidden — no warnings.)</p>
		{:else if certDismissed}
			<p class="page__muted">(Dismissed for this session.)</p>
		{/if}
	</section>

	<section class="page__section">
		<h2>G-23 — Download PDF placement</h2>
		<p class="page__hint">
			Download PDF stays visible at every status, including DRAFT (per G-23 #2). When primary
			actions exist, it lives in the overflow menu; when the role is read-only or the rail is
			otherwise empty, it renders solo.
		</p>
		<div class="g23-grid">
			<div>
				<h3>Inline mode</h3>
				<PoActionRail
					{po}
					{role}
					mode="inline"
					onEdit={() => handle('edit')}
					onSubmit={() => handle('submit')}
					onResubmit={() => handle('resubmit')}
					onAccept={() => handle('accept')}
					onMarkAdvancePaid={() => handle('mark-advance-paid')}
					onCreateInvoice={() => handle('create-invoice')}
					onPostMilestone={() => handle('post-milestone')}
					onDownloadPdf={() => handle('download-pdf')}
				/>
			</div>
			<div>
				<h3>Sticky-bottom mode (preview)</h3>
				<div class="sticky-preview">
					<PoActionRail
						{po}
						{role}
						mode="sticky-bottom"
						onEdit={() => handle('edit')}
						onSubmit={() => handle('submit')}
						onResubmit={() => handle('resubmit')}
						onAccept={() => handle('accept')}
						onMarkAdvancePaid={() => handle('mark-advance-paid')}
						onCreateInvoice={() => handle('create-invoice')}
						onPostMilestone={() => handle('post-milestone')}
						onDownloadPdf={() => handle('download-pdf')}
					/>
				</div>
			</div>
		</div>
	</section>

	<section class="page__section">
		<h2>Sticky bar preview (mobile only)</h2>
		<p class="page__hint">
			Below 768px this bar pins to the bottom of the viewport. On desktop it renders inline so the
			page scrolls past it.
		</p>
	</section>
</div>

<div class="mobile-sticky">
	<PoActionRail
		{po}
		{role}
		mode="sticky-bottom"
		onEdit={() => handle('edit')}
		onSubmit={() => handle('submit')}
		onResubmit={() => handle('resubmit')}
		onAccept={() => handle('accept')}
		onMarkAdvancePaid={() => handle('mark-advance-paid')}
		onCreateInvoice={() => handle('create-invoice')}
		onPostMilestone={() => handle('post-milestone')}
		onDownloadPdf={() => handle('download-pdf')}
	/>
</div>

<style>
	.page {
		max-width: 80rem;
		margin: 0 auto;
		padding: var(--space-6) var(--space-4) calc(var(--space-6) * 2);
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
		margin: 0 0 var(--space-2);
	}
	.page__last code {
		font-family: var(--font-family-mono, monospace);
		background: var(--gray-100);
		padding: 0 var(--space-2);
		border-radius: var(--radius-sm);
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
	.controls-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--space-3);
	}
	@media (min-width: 768px) {
		.controls-grid {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}
	.controls-grid label {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.controls-toggles {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
	}
	.toggle-row {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
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
		color: var(--gray-600);
		margin: 0;
	}
	.page__muted {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		font-style: italic;
		margin: 0;
	}
	.link-button {
		align-self: flex-start;
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		font-size: var(--font-size-sm);
		color: var(--blue-600, #2563eb);
		text-decoration: underline;
		cursor: pointer;
	}
	.standalone-rail {
		display: flex;
		justify-content: flex-end;
		padding: var(--space-3);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		background: var(--surface-card);
	}
	.matrix-wrap {
		overflow-x: auto;
	}
	.matrix {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--font-size-xs);
	}
	.matrix th,
	.matrix td {
		border: 1px solid var(--gray-200);
		padding: var(--space-2);
		text-align: left;
		vertical-align: top;
	}
	.matrix thead th {
		background: var(--gray-50);
		font-weight: 600;
	}
	.matrix tbody th {
		background: var(--gray-50);
		font-weight: 600;
		white-space: nowrap;
	}
	.matrix__cell--current {
		background: #fff7ed;
		outline: 2px solid var(--amber-700);
	}
	.matrix__solo {
		color: var(--gray-500);
		font-style: italic;
	}
	.g23-grid {
		display: grid;
		gap: var(--space-3);
	}
	.g23-grid h3 {
		font-size: var(--font-size-sm);
		margin: 0 0 var(--space-2);
		color: var(--gray-700);
	}
	@media (min-width: 768px) {
		.g23-grid {
			grid-template-columns: 1fr 1fr;
		}
	}
	.sticky-preview {
		position: relative;
		height: 6rem;
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		background: var(--gray-50);
		display: flex;
		align-items: flex-end;
	}
	.sticky-preview :global(.po-action-rail--sticky) {
		position: absolute;
		bottom: 0;
	}
	.mobile-sticky {
		display: none;
	}
	@media (max-width: 767px) {
		.mobile-sticky {
			display: block;
			position: fixed;
			bottom: 0;
			left: 0;
			right: 0;
			z-index: 10;
		}
		.page {
			padding-bottom: 6rem;
		}
	}
</style>
