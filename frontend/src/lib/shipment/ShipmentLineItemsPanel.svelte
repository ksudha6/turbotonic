<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Button from '$lib/ui/Button.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Input from '$lib/ui/Input.svelte';
	import type { ShipmentLineItem, ShipmentLineItemUpdate } from '$lib/types';

	let {
		lineItems,
		canEdit,
		saving,
		error,
		success,
		on_save
	}: {
		lineItems: ShipmentLineItem[];
		canEdit: boolean;
		saving: boolean;
		error: string;
		success: boolean;
		on_save: (drafts: ShipmentLineItemUpdate[]) => Promise<void>;
	} = $props();

	type Draft = {
		part_number: string;
		net_weight: string;
		gross_weight: string;
		package_count: number | null;
		dimensions: string;
		country_of_origin: string;
	};

	let drafts: Record<string, Draft> = $state({});

	// Re-init drafts whenever the parent reassigns the line_items array (after a
	// successful save). Tracking `lineItems` reference is enough — the parent
	// replaces the whole array.
	$effect(() => {
		const next: Record<string, Draft> = {};
		for (const li of lineItems) {
			next[li.part_number] = {
				part_number: li.part_number,
				net_weight: li.net_weight ?? '',
				gross_weight: li.gross_weight ?? '',
				package_count: li.package_count,
				dimensions: li.dimensions ?? '',
				country_of_origin: li.country_of_origin ?? ''
			};
		}
		drafts = next;
	});

	function trimToNull(v: string): string | null {
		const t = v.trim();
		return t.length === 0 ? null : t;
	}

	function buildPayload(): ShipmentLineItemUpdate[] {
		return Object.values(drafts).map((d) => ({
			part_number: d.part_number,
			net_weight: d.net_weight && String(d.net_weight).trim() ? String(d.net_weight).trim() : null,
			gross_weight: d.gross_weight && String(d.gross_weight).trim() ? String(d.gross_weight).trim() : null,
			package_count:
				d.package_count !== null && d.package_count !== undefined ? Number(d.package_count) : null,
			dimensions: d.dimensions && String(d.dimensions).trim() ? String(d.dimensions).trim() : null,
			country_of_origin:
				d.country_of_origin && String(d.country_of_origin).trim()
					? String(d.country_of_origin).trim()
					: null
		}));
	}

	async function handleSave() {
		await on_save(buildPayload());
	}

	function dash(v: string | number | null | undefined): string {
		if (v === null || v === undefined || v === '') return '—';
		return String(v);
	}
</script>

<PanelCard title="Line items" data-testid="shipment-line-items-panel">
	{#snippet action()}
		{#if canEdit}
			<div class="shipment-line-items__action">
				{#if success}
					<StatusPill
						tone="green"
						label="Saved"
						data-testid="shipment-line-items-saved-pill"
					/>
				{/if}
				<Button
					variant="primary"
					disabled={saving}
					onclick={handleSave}
					data-testid="shipment-line-items-save"
				>
					{saving ? 'Saving…' : 'Save'}
				</Button>
			</div>
		{/if}
	{/snippet}

	{#snippet children()}
		{#if error}
			<p class="shipment-line-items__error" role="alert" data-testid="shipment-line-items-error">
				{error}
			</p>
		{/if}

		<table class="shipment-line-items__desktop">
			<thead>
				<tr>
					<th>Part Number</th>
					<th>Description</th>
					<th>Qty</th>
					<th>UoM</th>
					<th>Net Weight</th>
					<th>Gross Weight</th>
					<th>Pkg Count</th>
					<th>Dimensions</th>
					<th>Country of Origin</th>
				</tr>
			</thead>
			<tbody>
				{#each lineItems as li (li.part_number)}
					{@const draft = drafts[li.part_number]}
					<tr data-testid="shipment-line-item-row-{li.part_number}">
						<td class="part-number">{li.part_number}</td>
						<td>{li.description}</td>
						<td>{li.quantity}</td>
						<td>{li.uom}</td>
						{#if canEdit && draft}
							<td>
								<Input
									bind:value={draft.net_weight}
									ariaLabel="Net weight for {li.part_number}"
									data-testid="shipment-line-item-net-weight-{li.part_number}"
								/>
							</td>
							<td>
								<Input
									bind:value={draft.gross_weight}
									ariaLabel="Gross weight for {li.part_number}"
									data-testid="shipment-line-item-gross-weight-{li.part_number}"
								/>
							</td>
							<td>
								<input
									class="ui-input shipment-line-items__pkg-input"
									type="number"
									min="0"
									aria-label="Package count for {li.part_number}"
									bind:value={draft.package_count}
									data-testid="shipment-line-item-package-count-{li.part_number}"
								/>
							</td>
							<td>
								<Input
									bind:value={draft.dimensions}
									ariaLabel="Dimensions for {li.part_number}"
									data-testid="shipment-line-item-dimensions-{li.part_number}"
								/>
							</td>
							<td>
								<Input
									bind:value={draft.country_of_origin}
									ariaLabel="Country of origin for {li.part_number}"
									data-testid="shipment-line-item-country-{li.part_number}"
								/>
							</td>
						{:else}
							<td>{dash(li.net_weight)}</td>
							<td>{dash(li.gross_weight)}</td>
							<td>{dash(li.package_count)}</td>
							<td>{dash(li.dimensions)}</td>
							<td>{dash(li.country_of_origin)}</td>
						{/if}
					</tr>
				{/each}
			</tbody>
		</table>

		<div class="shipment-line-items__mobile" role="list">
			{#each lineItems as li (li.part_number)}
				{@const draft = drafts[li.part_number]}
				<article
					class="shipment-line-items__card"
					role="listitem"
					data-testid="shipment-line-item-row-{li.part_number}"
				>
					<header class="shipment-line-items__card-header">
						<span class="shipment-line-items__part">{li.part_number}</span>
						<span class="shipment-line-items__qty">{li.quantity} {li.uom}</span>
					</header>
					<p class="shipment-line-items__desc">{li.description}</p>

					<dl class="shipment-line-items__fields">
						<div>
							<dt>Net weight</dt>
							<dd>
								{#if canEdit && draft}
									<Input
										bind:value={draft.net_weight}
										ariaLabel="Net weight for {li.part_number} (mobile)"
										data-testid="shipment-line-item-net-weight-{li.part_number}-mobile"
									/>
								{:else}
									{dash(li.net_weight)}
								{/if}
							</dd>
						</div>
						<div>
							<dt>Gross weight</dt>
							<dd>
								{#if canEdit && draft}
									<Input
										bind:value={draft.gross_weight}
										ariaLabel="Gross weight for {li.part_number} (mobile)"
										data-testid="shipment-line-item-gross-weight-{li.part_number}-mobile"
									/>
								{:else}
									{dash(li.gross_weight)}
								{/if}
							</dd>
						</div>
						<div>
							<dt>Pkg count</dt>
							<dd>
								{#if canEdit && draft}
									<input
										class="ui-input shipment-line-items__pkg-input"
										type="number"
										min="0"
										aria-label="Package count for {li.part_number} (mobile)"
										bind:value={draft.package_count}
										data-testid="shipment-line-item-package-count-{li.part_number}-mobile"
									/>
								{:else}
									{dash(li.package_count)}
								{/if}
							</dd>
						</div>
						<div>
							<dt>Dimensions</dt>
							<dd>
								{#if canEdit && draft}
									<Input
										bind:value={draft.dimensions}
										ariaLabel="Dimensions for {li.part_number} (mobile)"
										data-testid="shipment-line-item-dimensions-{li.part_number}-mobile"
									/>
								{:else}
									{dash(li.dimensions)}
								{/if}
							</dd>
						</div>
						<div>
							<dt>Country of origin</dt>
							<dd>
								{#if canEdit && draft}
									<Input
										bind:value={draft.country_of_origin}
										ariaLabel="Country of origin for {li.part_number} (mobile)"
										data-testid="shipment-line-item-country-{li.part_number}-mobile"
									/>
								{:else}
									{dash(li.country_of_origin)}
								{/if}
							</dd>
						</div>
					</dl>
				</article>
			{/each}
		</div>
	{/snippet}
</PanelCard>

<style>
	.shipment-line-items__action {
		display: inline-flex;
		align-items: center;
		gap: var(--space-3);
	}
	.shipment-line-items__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0;
	}
	.shipment-line-items__desktop { display: none; }
	.shipment-line-items__mobile {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.shipment-line-items__card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-3);
		background-color: var(--gray-50);
		border: 1px solid var(--gray-100);
		border-radius: var(--radius-md);
	}
	.shipment-line-items__card-header {
		display: flex;
		justify-content: space-between;
		gap: var(--space-2);
	}
	.shipment-line-items__part {
		font-weight: 600;
		font-family: monospace;
		color: var(--gray-900);
	}
	.shipment-line-items__qty {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.shipment-line-items__desc {
		margin: 0;
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.shipment-line-items__fields {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: var(--space-2);
		margin: 0;
	}
	.shipment-line-items__fields dt {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0;
	}
	.shipment-line-items__fields dd {
		font-size: var(--font-size-sm);
		color: var(--gray-900);
		margin: 0;
	}
	.shipment-line-items__pkg-input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-family: var(--font-family);
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		background-color: var(--surface-card);
		color: var(--gray-900);
	}
	.shipment-line-items__pkg-input:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 0;
		border-color: var(--brand-accent);
	}
	@media (min-width: 768px) {
		.shipment-line-items__mobile { display: none; }
		.shipment-line-items__desktop {
			display: table;
			width: 100%;
			border-collapse: collapse;
			font-size: var(--font-size-sm);
		}
		.shipment-line-items__desktop th {
			text-align: left;
			padding: var(--space-3) var(--space-4);
			font-weight: 600;
			color: var(--gray-600);
			border-bottom: 1px solid var(--gray-200);
			background-color: var(--gray-50);
			white-space: nowrap;
		}
		.shipment-line-items__desktop td {
			padding: var(--space-3) var(--space-4);
			border-bottom: 1px solid var(--gray-100);
			vertical-align: middle;
		}
		.part-number {
			font-family: monospace;
			font-size: var(--font-size-sm);
		}
	}
</style>
