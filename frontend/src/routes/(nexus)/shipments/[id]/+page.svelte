<script lang="ts">
	import { onMount } from 'svelte';
	import { page as appPage } from '$app/state';
	import {
		getShipment,
		updateShipmentLineItems,
		downloadPackingListPdf,
		downloadCommercialInvoicePdf
	} from '$lib/api';
	import { canEditShipment } from '$lib/permissions';
	import type { Shipment, ShipmentLineItemUpdate, UserRole } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import Button from '$lib/ui/Button.svelte';
	import ShipmentDetailHeader from '$lib/shipment/ShipmentDetailHeader.svelte';
	import ShipmentMetaPanel from '$lib/shipment/ShipmentMetaPanel.svelte';
	import ShipmentLineItemsPanel from '$lib/shipment/ShipmentLineItemsPanel.svelte';

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

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);
	const canEdit = $derived(shipment ? canEditShipment(role, shipment.status) : false);

	onMount(async () => {
		try {
			shipment = await getShipment(shipmentId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load shipment';
		} finally {
			loading = false;
		}
	});

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
