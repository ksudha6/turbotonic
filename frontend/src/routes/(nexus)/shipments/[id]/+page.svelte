<script lang="ts">
	import { onMount } from 'svelte';
	import { page as appPage } from '$app/state';
	import {
		getShipment,
		updateShipmentLineItems,
		downloadPackingListPdf,
		downloadCommercialInvoicePdf,
		listShipmentRequirements,
		addShipmentRequirement,
		uploadShipmentDocument,
		getShipmentReadiness,
		submitShipmentForDocuments,
		markShipmentReady,
		MarkReadyNotReadyError
	} from '$lib/api';
	import { canEditShipment, canViewShipmentReadiness } from '$lib/permissions';
	import type {
		Shipment,
		ShipmentLineItemUpdate,
		UserRole,
		ShipmentDocumentRequirement,
		ReadinessResult
	} from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import Button from '$lib/ui/Button.svelte';
	import ShipmentDetailHeader from '$lib/shipment/ShipmentDetailHeader.svelte';
	import ShipmentMetaPanel from '$lib/shipment/ShipmentMetaPanel.svelte';
	import ShipmentLineItemsPanel from '$lib/shipment/ShipmentLineItemsPanel.svelte';
	import ShipmentActionRail from '$lib/shipment/ShipmentActionRail.svelte';
	import ShipmentDocumentsPanel from '$lib/shipment/ShipmentDocumentsPanel.svelte';
	import ShipmentReadinessPanel from '$lib/shipment/ShipmentReadinessPanel.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	const shipmentId: string = appPage.params.id ?? '';

	let shipment: Shipment | null = $state(null);
	let loading: boolean = $state(true);
	let error: string = $state('');
	let saving: boolean = $state(false);
	let saveError: string = $state('');
	let saveSuccess: boolean = $state(false);
	let downloading: boolean = $state(false);
	let downloadingCi: boolean = $state(false);

	// Auxiliary state for documents + readiness
	let requirements: ShipmentDocumentRequirement[] = $state([]);
	let readiness: ReadinessResult | null = $state(null);
	let submitting: boolean = $state(false);
	let marking: boolean = $state(false);
	let actionError: string | null = $state(null);
	let uploadingId: string | null = $state(null);
	let addingRequirement: boolean = $state(false);
	let documentsError: string | null = $state(null);
	let addError: string | null = $state(null);

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);
	const canEdit = $derived(shipment ? canEditShipment(role, shipment.status) : false);

	// productLookup maps product_id → { part_number, description } for readiness panel resolution.
	function buildProductLookup(
		s: Shipment | null
	): Map<string, { part_number: string; description: string }> {
		if (!s?.line_items) return new Map();
		return new Map(
			s.line_items
				.filter((li) => li.product_id !== null)
				.map((li) => [li.product_id as string, { part_number: li.part_number, description: li.description }])
		);
	}
	const productLookup = $derived(buildProductLookup(shipment));

	async function fetchAuxiliary(s: Shipment) {
		const [reqs, rdns] = await Promise.all([
			listShipmentRequirements(s.id),
			canViewShipmentReadiness(role) && s.status !== 'DRAFT'
				? getShipmentReadiness(s.id)
				: Promise.resolve(null)
		]);
		requirements = reqs;
		readiness = rdns;
	}

	onMount(async () => {
		try {
			shipment = await getShipment(shipmentId);
			await fetchAuxiliary(shipment);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load shipment';
		} finally {
			loading = false;
		}
	});

	async function handleSubmit() {
		submitting = true;
		actionError = null;
		try {
			shipment = await submitShipmentForDocuments(shipmentId);
			await fetchAuxiliary(shipment);
		} catch (e) {
			actionError = e instanceof Error ? e.message : 'Submit failed';
		} finally {
			submitting = false;
		}
	}

	async function handleMarkReady() {
		marking = true;
		actionError = null;
		try {
			shipment = await markShipmentReady(shipmentId);
			await fetchAuxiliary(shipment);
		} catch (e) {
			if (e instanceof MarkReadyNotReadyError) {
				readiness = e.readiness;
				actionError = 'Some readiness checks failed. See the readiness panel below.';
			} else {
				actionError = e instanceof Error ? e.message : 'Mark ready failed';
			}
		} finally {
			marking = false;
		}
	}

	async function handleUpload(reqId: string, file: File) {
		uploadingId = reqId;
		documentsError = null;
		try {
			await uploadShipmentDocument(shipmentId, reqId, file);
			if (shipment) await fetchAuxiliary(shipment);
		} catch (e) {
			documentsError = e instanceof Error ? e.message : 'Upload failed';
		} finally {
			uploadingId = null;
		}
	}

	async function handleAddRequirement(documentType: string) {
		addingRequirement = true;
		addError = null;
		try {
			await addShipmentRequirement(shipmentId, documentType);
			if (shipment) await fetchAuxiliary(shipment);
		} catch (e) {
			addError = e instanceof Error ? e.message : 'Add requirement failed';
		} finally {
			addingRequirement = false;
		}
	}

	async function handleSave(drafts: ShipmentLineItemUpdate[]) {
		if (!shipment) return;
		saving = true;
		saveError = '';
		saveSuccess = false;
		try {
			shipment = await updateShipmentLineItems(shipment.id, { line_items: drafts });
			saveSuccess = true;
			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Save failed';
		} finally {
			saving = false;
		}
	}

	async function handleDownloadPacking() {
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

	async function handleDownloadCi() {
		if (!shipment) return;
		downloadingCi = true;
		try {
			await downloadCommercialInvoicePdf(shipment.id, shipment.shipment_number);
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Download failed';
		} finally {
			downloadingCi = false;
		}
	}
</script>

<svelte:head>
	<title>{shipment?.shipment_number ?? 'Shipment'}</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Shipment">
	{#snippet userMenu()}
		<UserMenu name={userName} {role} />
	{/snippet}

	<div class="shipment-detail-page">
		{#if loading}
			<LoadingState label="Loading shipment" data-testid="shipment-detail-loading" />
		{:else if error}
			<p class="shipment-detail-page__error" role="alert" data-testid="shipment-detail-error">
				{error}
			</p>
		{:else if shipment}
			<ShipmentDetailHeader {shipment}>
				{#snippet actionRail()}
					<Button
						variant="secondary"
						disabled={downloading}
						onclick={handleDownloadPacking}
						data-testid="shipment-download-packing-list"
					>
						{downloading ? 'Downloading…' : 'Download Packing List'}
					</Button>
					<Button
						variant="secondary"
						disabled={downloadingCi}
						onclick={handleDownloadCi}
						data-testid="shipment-download-commercial-invoice"
					>
						{downloadingCi ? 'Downloading…' : 'Download Commercial Invoice'}
					</Button>
				{/snippet}
			</ShipmentDetailHeader>

			<ShipmentMetaPanel {shipment} />

			<ShipmentActionRail
				status={shipment.status}
				{role}
				{readiness}
				{submitting}
				{marking}
				error={actionError}
				on_submit={handleSubmit}
				on_mark_ready={handleMarkReady}
			/>

			{#if shipment.status !== 'DRAFT' || requirements.length > 0}
				<ShipmentDocumentsPanel
					{requirements}
					{role}
					status={shipment.status}
					uploading_id={uploadingId}
					adding={addingRequirement}
					error={documentsError}
					add_error={addError}
					on_upload={handleUpload}
					on_add={handleAddRequirement}
				/>
			{/if}

			{#if readiness !== null && canViewShipmentReadiness(role)}
				<ShipmentReadinessPanel
					{readiness}
					{productLookup}
					loading={false}
					error={null}
				/>
			{/if}

			<ShipmentLineItemsPanel
				lineItems={shipment.line_items}
				{canEdit}
				{saving}
				error={saveError}
				success={saveSuccess}
				on_save={handleSave}
			/>
		{/if}
	</div>
</AppShell>

<style>
	.shipment-detail-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.shipment-detail-page__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-3) var(--space-4);
		margin: 0;
	}
</style>
