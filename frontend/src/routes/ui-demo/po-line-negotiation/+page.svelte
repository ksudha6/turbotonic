<script lang="ts">
	import PoLineNegotiationTable from '$lib/po/PoLineNegotiationTable.svelte';
	import PoSubmitResponseBar from '$lib/po/PoSubmitResponseBar.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Select from '$lib/ui/Select.svelte';
	import type { LineItem, LineEditEntry } from '$lib/types';
	import type { ModifyLineFields } from '$lib/api';

	type NegotiationRole = 'VENDOR' | 'SM';

	const ROLE_OPTIONS: ReadonlyArray<{ value: NegotiationRole; label: string }> = [
		{ value: 'VENDOR', label: 'VENDOR' },
		{ value: 'SM', label: 'SM' }
	];

	const ROUND_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
		{ value: '0', label: 'Round 0 (Pending, fresh PO)' },
		{ value: '1', label: 'Round 1 (mid-negotiation)' },
		{ value: '2', label: 'Round 2 (force-override available to SM)' }
	];

	let roleValue = $state<string>('SM');
	let roundValue = $state<string>('1');
	const role = $derived(roleValue as NegotiationRole);
	const round_count = $derived(parseInt(roundValue, 10));

	let lastClicked = $state<string>('');

	function record(action: string): void {
		lastClicked = `${action} @ ${new Date().toLocaleTimeString()}`;
	}

	function makeHistoryEntry(
		part_number: string,
		round: number,
		actor_role: 'VENDOR' | 'SM',
		field: string,
		old_value: string,
		new_value: string,
		hour: number
	): LineEditEntry {
		return {
			part_number,
			round,
			actor_role,
			field,
			old_value,
			new_value,
			edited_at: `2026-04-28T${hour.toString().padStart(2, '0')}:00:00Z`
		};
	}

	// Five rows cover the LineItemStatus matrix at round-1 mid-negotiation.
	// Use the mock controls to flip role / round; per-row status stays fixed
	// so visual assertions on each state are stable.
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
			status: 'PENDING',
			required_delivery_date: null,
			history: []
		},
		{
			part_number: 'WIDGET-002',
			description: 'Industrial widget, red',
			quantity: 80,
			uom: 'EA',
			unit_price: '14.00',
			hs_code: '8473.30',
			country_of_origin: 'CN',
			product_id: 'prod-2',
			status: 'MODIFIED_BY_VENDOR',
			required_delivery_date: null,
			history: [
				makeHistoryEntry('WIDGET-002', 1, 'VENDOR', 'quantity', '100', '80', 9),
				makeHistoryEntry('WIDGET-002', 1, 'VENDOR', 'unit_price', '14.75', '14.00', 9)
			]
		},
		{
			part_number: 'GASKET-100',
			description: 'Rubber gasket, 50mm',
			quantity: 200,
			uom: 'EA',
			unit_price: '0.95',
			hs_code: '4016.93',
			country_of_origin: 'CN',
			product_id: 'prod-3',
			status: 'MODIFIED_BY_SM',
			required_delivery_date: null,
			history: [
				makeHistoryEntry('GASKET-100', 1, 'VENDOR', 'unit_price', '0.85', '1.05', 10),
				makeHistoryEntry('GASKET-100', 1, 'SM', 'unit_price', '1.05', '0.95', 11)
			]
		},
		{
			part_number: 'BOLT-440',
			description: 'M4 bolt, stainless',
			quantity: 500,
			uom: 'EA',
			unit_price: '0.10',
			hs_code: '7318.15',
			country_of_origin: 'IN',
			product_id: 'prod-4',
			status: 'ACCEPTED',
			required_delivery_date: null,
			history: [
				makeHistoryEntry('BOLT-440', 1, 'VENDOR', 'country_of_origin', 'CN', 'IN', 9)
			]
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
			history: [
				makeHistoryEntry('CABLE-X9', 1, 'VENDOR', 'quantity', '50', '0', 9)
			]
		}
	];

	let lines = $state<LineItem[]>(LINES.map((l) => ({ ...l, history: [...(l.history ?? [])] })));

	let lineErrors = $state<Map<string, string>>(new Map());
	let submitError = $state<string>('');

	function setLineError(part_number: string, msg: string): void {
		const next = new Map(lineErrors);
		if (msg) next.set(part_number, msg);
		else next.delete(part_number);
		lineErrors = next;
	}

	function handleModify(part_number: string, fields: ModifyLineFields): void {
		setLineError(part_number, '');
		record(`modify ${part_number} ${JSON.stringify(fields)}`);
	}

	function handleAccept(part_number: string): void {
		setLineError(part_number, '');
		record(`accept ${part_number}`);
	}

	function handleRemove(part_number: string): void {
		setLineError(part_number, '');
		record(`remove ${part_number}`);
	}

	function handleForceAccept(part_number: string): void {
		setLineError(part_number, '');
		record(`force-accept ${part_number}`);
	}

	function handleForceRemove(part_number: string): void {
		setLineError(part_number, '');
		record(`force-remove ${part_number}`);
	}

	function handleSubmit(): void {
		submitError = '';
		record('submit-response');
	}

	function injectError(): void {
		setLineError('WIDGET-002', 'Server rejected: round cap exceeded.');
		submitError = '';
	}

	function clearErrors(): void {
		lineErrors = new Map();
		submitError = '';
	}
</script>

<svelte:head>
	<title>PO line negotiation mock — Phase 4.2 G-15 / G-16</title>
</svelte:head>

<div class="page">
	<header class="page__intro">
		<h1>PO line negotiation mock — gaps G-15, G-16</h1>
		<p>
			Five rows cover every LineItemStatus: PENDING, MODIFIED_BY_VENDOR, MODIFIED_BY_SM, ACCEPTED,
			REMOVED. Toggle role to flip vendor / SM perspective. Toggle round to surface force-override
			at round 2. Resize to 390px to verify mobile stacking and sticky bar safe-area padding.
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
				<span>Round count</span>
				<Select
					bind:value={roundValue}
					options={ROUND_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Round count"
					data-testid="ctl-round"
				/>
			</label>
		</div>
		<div class="page__actions">
			<button type="button" class="page__link" onclick={injectError}>
				Inject server error on WIDGET-002
			</button>
			<button type="button" class="page__link" onclick={clearErrors}>Clear errors</button>
		</div>
	</section>

	<section class="page__section">
		<h2>G-15 &mdash; Line negotiation rows ({role}, round {round_count})</h2>
		<p class="page__hint">
			Modify is offered on PENDING and MODIFIED_BY_* lines. Accept appears only when the
			counterparty was last to move. Force Accept and Force Remove appear only for SM at round 2 on
			lines still in a MODIFIED_BY_* state. Terminal lines (ACCEPTED, REMOVED) show no actions.
		</p>
		<PanelCard title="Line items" subtitle="{lines.length} lines under negotiation">
			{#snippet children()}
				<PoLineNegotiationTable
					{lines}
					{role}
					{round_count}
					errors={lineErrors}
					on_modify={handleModify}
					on_accept={handleAccept}
					on_remove={handleRemove}
					on_force_accept={handleForceAccept}
					on_force_remove={handleForceRemove}
				/>
			{/snippet}
		</PanelCard>
	</section>

	<section class="page__section">
		<h2>G-16 &mdash; Submit response bar</h2>
		<p class="page__hint">
			The bar disables Submit until every line under the current actor's clock has a decision. At
			round 1 it warns that the next hand-off will be force-override only. The confirm dialog shows
			accepted / modified / removed counts.
		</p>
	</section>
</div>

<PoSubmitResponseBar
	{lines}
	{role}
	{round_count}
	error={submitError}
	on_submit={handleSubmit}
/>

<style>
	.page {
		max-width: 80rem;
		margin: 0 auto;
		padding: var(--space-6) var(--space-4) calc(var(--space-20));
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
</style>
