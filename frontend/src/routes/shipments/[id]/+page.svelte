<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { getShipment, updateShipmentLineItems, downloadPackingListPdf } from '$lib/api';
	import type { Shipment, ShipmentLineItemUpdate } from '$lib/types';

	const shipmentId: string = page.params.id ?? '';

	let shipment: Shipment | null = $state(null);
	let loading: boolean = $state(true);
	let error: string = $state('');
	let saving: boolean = $state(false);
	let saveError: string = $state('');
	let saveSuccess: boolean = $state(false);
	let downloading: boolean = $state(false);

	// Editable drafts indexed by part_number
	let drafts: Record<string, ShipmentLineItemUpdate> = $state({});

	function initDrafts(s: Shipment) {
		const next: Record<string, ShipmentLineItemUpdate> = {};
		for (const li of s.line_items) {
			next[li.part_number] = {
				part_number: li.part_number,
				net_weight: li.net_weight ?? '',
				gross_weight: li.gross_weight ?? '',
				package_count: li.package_count ?? null,
				dimensions: li.dimensions ?? '',
				country_of_origin: li.country_of_origin ?? '',
			};
		}
		drafts = next;
	}

	async function load() {
		loading = true;
		error = '';
		try {
			shipment = await getShipment(shipmentId);
			initDrafts(shipment);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load shipment';
		} finally {
			loading = false;
		}
	}

	onMount(() => load());

	// editable when DRAFT or DOCUMENTS_PENDING
	const isEditable = $derived(
		shipment?.status === 'DRAFT' || shipment?.status === 'DOCUMENTS_PENDING'
	);

	async function save() {
		if (!shipment) return;
		saving = true;
		saveError = '';
		saveSuccess = false;
		try {
			const lineItems: ShipmentLineItemUpdate[] = Object.values(drafts).map((d) => ({
				part_number: d.part_number,
				net_weight: d.net_weight && String(d.net_weight).trim() ? String(d.net_weight).trim() : null,
				gross_weight: d.gross_weight && String(d.gross_weight).trim() ? String(d.gross_weight).trim() : null,
				package_count: d.package_count !== null && d.package_count !== undefined ? Number(d.package_count) : null,
				dimensions: d.dimensions && String(d.dimensions).trim() ? String(d.dimensions).trim() : null,
				country_of_origin: d.country_of_origin && String(d.country_of_origin).trim() ? String(d.country_of_origin).trim() : null,
			}));
			shipment = await updateShipmentLineItems(shipment.id, { line_items: lineItems });
			initDrafts(shipment);
			saveSuccess = true;
			setTimeout(() => { saveSuccess = false; }, 3000);
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Save failed';
		} finally {
			saving = false;
		}
	}

	async function handleDownload() {
		if (!shipment) return;
		downloading = true;
		try {
			await downloadPackingListPdf(shipment.id, shipment.shipment_number);
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Download failed';
		} finally {
			downloading = false;
		}
	}

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString();
	}
</script>

{#if loading}
	<p>Loading...</p>
{:else if error}
	<p class="error">{error}</p>
{:else if shipment}
	<div class="page-header">
		<div>
			<h1>{shipment.shipment_number}</h1>
			<span class="status-badge status-{shipment.status.toLowerCase()}">{shipment.status.replace(/_/g, ' ')}</span>
		</div>
		<button
			class="btn btn-secondary"
			disabled={downloading}
			onclick={handleDownload}
		>
			{downloading ? 'Downloading...' : 'Download Packing List'}
		</button>
	</div>

	<div class="card meta-card">
		<div class="meta-grid">
			<div><span class="label">Marketplace</span><span>{shipment.marketplace}</span></div>
			<div><span class="label">Created</span><span>{formatDate(shipment.created_at)}</span></div>
			<div><span class="label">Updated</span><span>{formatDate(shipment.updated_at)}</span></div>
		</div>
	</div>

	<div class="section-header">
		<h2>Line Items</h2>
		{#if isEditable}
			<div class="actions">
				{#if saveSuccess}
					<span class="save-ok">Saved</span>
				{/if}
				{#if saveError}
					<span class="save-err">{saveError}</span>
				{/if}
				<button class="btn btn-primary" disabled={saving} onclick={save}>
					{saving ? 'Saving...' : 'Save'}
				</button>
			</div>
		{/if}
	</div>

	<div class="card">
		<table class="table line-items-table">
			<thead>
				<tr>
					<th>Part Number</th>
					<th>Description</th>
					<th>Qty</th>
					<th>UOM</th>
					<th>Net Weight</th>
					<th>Gross Weight</th>
					<th>Pkg Count</th>
					<th>Dimensions</th>
					<th>Country of Origin</th>
				</tr>
			</thead>
			<tbody>
				{#each shipment.line_items as li}
					{@const draft = drafts[li.part_number]}
					<tr>
						<td class="part-number">{li.part_number}</td>
						<td>{li.description}</td>
						<td>{li.quantity}</td>
						<td>{li.uom}</td>
						{#if isEditable && draft}
							<td><input class="inline-input" type="text" bind:value={draft.net_weight} placeholder="-" /></td>
							<td><input class="inline-input" type="text" bind:value={draft.gross_weight} placeholder="-" /></td>
							<td><input class="inline-input narrow" type="number" min="0" bind:value={draft.package_count} placeholder="-" /></td>
							<td><input class="inline-input wide" type="text" bind:value={draft.dimensions} placeholder="e.g. 40x30x20 cm" /></td>
							<td><input class="inline-input" type="text" bind:value={draft.country_of_origin} placeholder="e.g. CN" /></td>
						{:else}
							<td>{li.net_weight ?? '-'}</td>
							<td>{li.gross_weight ?? '-'}</td>
							<td>{li.package_count ?? '-'}</td>
							<td>{li.dimensions ?? '-'}</td>
							<td>{li.country_of_origin ?? '-'}</td>
						{/if}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<style>
	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: var(--space-6);
	}

	.page-header h1 {
		margin: 0 0 var(--space-2) 0;
	}

	.status-badge {
		display: inline-block;
		padding: 2px 10px;
		border-radius: 9999px;
		font-size: var(--font-size-sm);
		font-weight: 600;
		background-color: var(--gray-200);
		color: var(--gray-700);
	}

	.status-badge.status-draft { background-color: #dbeafe; color: #1e40af; }
	.status-badge.status-documents_pending { background-color: #fef9c3; color: #854d0e; }
	.status-badge.status-ready_to_ship { background-color: #dcfce7; color: #166534; }

	.meta-card {
		margin-bottom: var(--space-4);
		padding: var(--space-4);
	}

	.meta-grid {
		display: flex;
		gap: var(--space-6);
	}

	.label {
		display: block;
		font-size: var(--font-size-xs, 0.75rem);
		color: var(--gray-500);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 2px;
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-3);
	}

	.section-header h2 {
		margin: 0;
	}

	.actions {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.save-ok {
		color: #166534;
		font-size: var(--font-size-sm);
		font-weight: 600;
	}

	.save-err {
		color: #dc2626;
		font-size: var(--font-size-sm);
	}

	.error {
		color: #dc2626;
	}

	.line-items-table th,
	.line-items-table td {
		white-space: nowrap;
	}

	.part-number {
		font-family: monospace;
		font-size: var(--font-size-sm);
	}

	.inline-input {
		width: 80px;
		font-size: var(--font-size-sm);
		padding: 2px 4px;
		border: 1px solid var(--gray-300, #d1d5db);
		border-radius: 4px;
	}

	.inline-input.narrow {
		width: 60px;
	}

	.inline-input.wide {
		width: 120px;
	}
</style>
