<script lang="ts">
	import PoLineAcceptedTable from '$lib/po/PoLineAcceptedTable.svelte';
	import PoMilestoneTimelinePanel from '$lib/po/PoMilestoneTimelinePanel.svelte';
	import PoAddLineDialog from '$lib/po/PoAddLineDialog.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Select from '$lib/ui/Select.svelte';
	import type {
		LineItem,
		MilestoneResponse,
		POType,
		ProductionMilestone,
		ReferenceData,
		UserRole
	} from '$lib/types';

	type DemoRole = 'VENDOR' | 'SM' | 'PROCUREMENT_MANAGER';
	type GateMode = 'open' | 'closed-by-advance' | 'closed-by-milestone';
	type MilestoneState =
		| 'none'
		| 'two-posted'
		| 'four-posted'
		| 'overdue'
		| 'shipped';

	const ROLE_OPTIONS: ReadonlyArray<{ value: DemoRole; label: string }> = [
		{ value: 'VENDOR', label: 'VENDOR' },
		{ value: 'SM', label: 'SM' },
		{ value: 'PROCUREMENT_MANAGER', label: 'PROCUREMENT_MANAGER' }
	];

	const GATE_OPTIONS: ReadonlyArray<{ value: GateMode; label: string }> = [
		{ value: 'open', label: 'Open' },
		{ value: 'closed-by-advance', label: 'Closed by advance paid' },
		{ value: 'closed-by-milestone', label: 'Closed by first milestone' }
	];

	const MILESTONE_OPTIONS: ReadonlyArray<{ value: MilestoneState; label: string }> = [
		{ value: 'none', label: '0 milestones posted' },
		{ value: 'two-posted', label: '2 milestones posted' },
		{ value: 'four-posted', label: '4 milestones posted' },
		{ value: 'overdue', label: 'RAW_MATERIALS overdue' },
		{ value: 'shipped', label: 'SHIPPED (terminal)' }
	];

	const PO_TYPE_OPTIONS: ReadonlyArray<{ value: POType; label: string }> = [
		{ value: 'PROCUREMENT', label: 'PROCUREMENT' },
		{ value: 'OPEX', label: 'OPEX' }
	];

	let roleValue: string = $state('SM');
	let gateValue: string = $state('open');
	let milestoneValue: string = $state('two-posted');
	let poTypeValue: string = $state('PROCUREMENT');

	const role = $derived(roleValue as DemoRole);
	const gate = $derived(gateValue as GateMode);
	const milestoneState = $derived(milestoneValue as MilestoneState);
	const po_type = $derived(poTypeValue as POType);

	const gate_closed = $derived(gate !== 'open');

	let lastClicked: string = $state('');
	function record(action: string): void {
		lastClicked = `${action} @ ${new Date().toLocaleTimeString()}`;
	}

	const LINES: ReadonlyArray<LineItem> = [
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
			part_number: 'GASKET-100',
			description: 'Rubber gasket, 50mm',
			quantity: 200,
			uom: 'EA',
			unit_price: '0.95',
			hs_code: '4016.93',
			country_of_origin: 'IN',
			product_id: 'prod-3',
			status: 'ACCEPTED',
			required_delivery_date: null,
			history: []
		},
		{
			part_number: 'CABLE-X9',
			description: 'Power cable, 3m',
			quantity: 0,
			uom: 'EA',
			unit_price: '4.50',
			hs_code: '8544.42',
			country_of_origin: 'CN',
			product_id: 'prod-5',
			status: 'REMOVED',
			required_delivery_date: null,
			history: []
		}
	];

	const lines = LINES.map((l) => ({ ...l }));

	const cert_required = new Set<string>(['WIDGET-001']);

	const remaining_map = new Map<string, { invoiced: number; remaining: number }>([
		['WIDGET-001', { invoiced: 25, remaining: 75 }],
		['GASKET-100', { invoiced: 0, remaining: 200 }],
		['CABLE-X9', { invoiced: 0, remaining: 0 }]
	]);

	const COUNTRY_LABELS: Readonly<Record<string, string>> = {
		CN: 'China',
		IN: 'India',
		US: 'United States',
		DE: 'Germany',
		VN: 'Vietnam'
	};

	function resolve_country(code: string): string {
		return COUNTRY_LABELS[code] ?? code;
	}

	const REFERENCE_DATA: ReferenceData = {
		currencies: [{ code: 'USD', label: 'USD' }],
		incoterms: [{ code: 'FOB', label: 'FOB' }],
		payment_terms: [
			{ code: 'NET30', label: 'Net 30', has_advance: false },
			{ code: 'ADVANCE_50', label: '50% advance', has_advance: true }
		],
		countries: [
			{ code: 'CN', label: 'China' },
			{ code: 'IN', label: 'India' },
			{ code: 'US', label: 'United States' },
			{ code: 'DE', label: 'Germany' },
			{ code: 'VN', label: 'Vietnam' }
		],
		ports: [{ code: 'USNYC', label: 'New York' }],
		vendor_types: [{ code: 'PROCUREMENT', label: 'Procurement' }],
		po_types: [
			{ code: 'PROCUREMENT', label: 'Procurement' },
			{ code: 'OPEX', label: 'OPEX' }
		]
	};

	function buildMilestones(state: MilestoneState): MilestoneResponse[] {
		const today = new Date('2026-04-29T12:00:00Z');
		function daysAgo(d: number): string {
			const dt = new Date(today);
			dt.setUTCDate(dt.getUTCDate() - d);
			return dt.toISOString();
		}
		switch (state) {
			case 'none':
				return [];
			case 'two-posted':
				return [
					{
						milestone: 'RAW_MATERIALS',
						posted_at: daysAgo(12),
						is_overdue: false,
						days_overdue: null
					},
					{
						milestone: 'PRODUCTION_STARTED',
						posted_at: daysAgo(3),
						is_overdue: false,
						days_overdue: null
					}
				];
			case 'four-posted':
				return [
					{
						milestone: 'RAW_MATERIALS',
						posted_at: daysAgo(24),
						is_overdue: false,
						days_overdue: null
					},
					{
						milestone: 'PRODUCTION_STARTED',
						posted_at: daysAgo(18),
						is_overdue: false,
						days_overdue: null
					},
					{
						milestone: 'QC_PASSED',
						posted_at: daysAgo(6),
						is_overdue: false,
						days_overdue: null
					},
					{
						milestone: 'READY_FOR_SHIPMENT',
						posted_at: daysAgo(1),
						is_overdue: false,
						days_overdue: null
					}
				];
			case 'overdue':
				return [
					{
						milestone: 'RAW_MATERIALS',
						posted_at: daysAgo(11),
						is_overdue: true,
						days_overdue: 4
					}
				];
			case 'shipped':
				return [
					{
						milestone: 'RAW_MATERIALS',
						posted_at: daysAgo(40),
						is_overdue: false,
						days_overdue: null
					},
					{
						milestone: 'PRODUCTION_STARTED',
						posted_at: daysAgo(32),
						is_overdue: false,
						days_overdue: null
					},
					{
						milestone: 'QC_PASSED',
						posted_at: daysAgo(20),
						is_overdue: false,
						days_overdue: null
					},
					{
						milestone: 'READY_FOR_SHIPMENT',
						posted_at: daysAgo(10),
						is_overdue: false,
						days_overdue: null
					},
					{
						milestone: 'SHIPPED',
						posted_at: daysAgo(2),
						is_overdue: false,
						days_overdue: null
					}
				];
		}
	}

	const milestones = $derived(buildMilestones(milestoneState));

	const showMilestonePanel = $derived(po_type === 'PROCUREMENT');

	// Only SM has the post-acceptance affordance; vendor/PROCUREMENT_MANAGER never
	// see Add Line or Remove. Match (nexus)/po/[id]/+page.svelte's canModifyPostAccept.
	const canModifyPostAccept = $derived(role === 'SM');
	const showGateClosedNote = $derived(canModifyPostAccept && gate_closed);
	const showAddLineButton = $derived(canModifyPostAccept && !gate_closed);

	const onRemoveProp = $derived<((part_number: string) => Promise<void>) | null>(
		canModifyPostAccept ? async (pn: string) => record(`remove ${pn}`) : null
	);

	const onPostMilestoneProp = $derived<
		((m: ProductionMilestone) => Promise<void>) | null
	>(role === 'VENDOR' ? async (m: ProductionMilestone) => record(`post ${m}`) : null);

	let showAddDialog: boolean = $state(false);
	let addError: string = $state('');

	async function handleAddSubmit(fields: {
		part_number: string;
		description: string;
		quantity: number;
		uom: string;
		unit_price: string;
		hs_code: string;
		country_of_origin: string;
	}): Promise<void> {
		record(`add-line ${fields.part_number}`);
		addError = '';
		showAddDialog = false;
	}

	function injectAddError(): void {
		addError = 'Server rejected: part number already exists on this PO.';
	}

	const lineErrors = $state<Map<string, string>>(new Map());

	function injectRemoveError(): void {
		const next = new Map(lineErrors);
		next.set('GASKET-100', 'Cannot remove: invoice INV-1 references this line.');
		// $state.raw not available on Map; reassign
		lineErrors.clear();
		next.forEach((v, k) => lineErrors.set(k, v));
	}

	function clearErrors(): void {
		addError = '';
		lineErrors.clear();
	}

	const roleAsUserRole = $derived(role as UserRole);
</script>

<svelte:head>
	<title>PO accepted mock — Phase 4.2 G-18 / G-19</title>
</svelte:head>

<div class="page">
	<header class="page__intro">
		<h1>PO accepted mock — gaps G-18, G-19</h1>
		<p>
			Toggle role × gate × milestone state × PO type. Gate-closed paths hide Add Line and per-row
			Remove rather than disabling them. The milestone timeline panel uses the Phase 4.0 Timeline
			primitive with the new <code>overdue</code> state.
		</p>
		<p class="page__last">Last action: <code>{lastClicked || '—'}</code></p>
	</header>

	<section class="page__controls" aria-label="Mock controls">
		<h2>Controls</h2>
		<div class="page__grid">
			<label class="page__field">
				<span>Role</span>
				<Select
					bind:value={roleValue}
					options={ROLE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Role"
					data-testid="ctl-role"
				/>
			</label>
			<label class="page__field">
				<span>Gate</span>
				<Select
					bind:value={gateValue}
					options={GATE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Gate"
					data-testid="ctl-gate"
				/>
			</label>
			<label class="page__field">
				<span>Milestone state</span>
				<Select
					bind:value={milestoneValue}
					options={MILESTONE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Milestone state"
					data-testid="ctl-milestone"
				/>
			</label>
			<label class="page__field">
				<span>PO type</span>
				<Select
					bind:value={poTypeValue}
					options={PO_TYPE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="PO type"
					data-testid="ctl-po-type"
				/>
			</label>
		</div>
		<div class="page__actions">
			<button type="button" class="page__link" onclick={injectAddError}>
				Inject add-line server error
			</button>
			<button type="button" class="page__link" onclick={injectRemoveError}>
				Inject remove server error on GASKET-100
			</button>
			<button type="button" class="page__link" onclick={clearErrors}>Clear errors</button>
		</div>
	</section>

	<section class="page__section">
		<h2>G-18 &mdash; Accepted line items ({role}, gate {gate})</h2>
		<p class="page__hint">
			SM sees Add Line + per-row Remove only when the gate is open. When the gate closes, those
			affordances are hidden and SM sees a panel-level note. Vendor and PROCUREMENT_MANAGER never
			see post-acceptance edits.
		</p>
		<PanelCard title="Line items" subtitle="{lines.length} accepted lines">
			{#snippet action()}
				{#if showAddLineButton}
					<Button
						onclick={() => {
							addError = '';
							showAddDialog = true;
						}}
						data-testid="add-line-btn"
					>
						Add line
					</Button>
				{/if}
			{/snippet}
			{#snippet children()}
				{#if showGateClosedNote}
					<p
						class="page__gate-note"
						data-testid="po-post-accept-gate-closed-note"
					>
						Post-acceptance line edits closed: advance paid or first milestone posted.
					</p>
				{/if}
				<PoLineAcceptedTable
					{lines}
					role={roleAsUserRole}
					{po_type}
					{cert_required}
					{remaining_map}
					{gate_closed}
					errors={lineErrors}
					on_remove={onRemoveProp}
					{resolve_country}
				/>
			{/snippet}
		</PanelCard>
	</section>

	{#if showMilestonePanel}
		<section class="page__section">
			<h2>G-19 &mdash; Production status ({role}, {milestoneState})</h2>
			<p class="page__hint">
				Vendor sees the post-next-milestone Button when an unposted milestone remains. Other roles
				see the Timeline only. The overdue state renders a red marker and an
				<code>Overdue {'{n}'}d</code> detail line.
			</p>
			<PoMilestoneTimelinePanel
				{milestones}
				role={roleAsUserRole}
				onPost={onPostMilestoneProp}
			/>
		</section>
	{/if}
</div>

{#if showAddDialog}
	<PoAddLineDialog
		reference_data={REFERENCE_DATA}
		error={addError}
		on_submit={handleAddSubmit}
		on_close={() => (showAddDialog = false)}
	/>
{/if}

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
	.page__actions {
		display: flex;
		gap: var(--space-3);
		flex-wrap: wrap;
	}
	.page__link {
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		font-size: var(--font-size-sm);
		color: var(--brand-accent);
		text-decoration: underline;
		cursor: pointer;
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
	.page__gate-note {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		background: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0 0 var(--space-3);
	}
</style>
