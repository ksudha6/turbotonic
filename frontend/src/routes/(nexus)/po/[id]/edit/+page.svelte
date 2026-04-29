<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { page as appPage } from '$app/state';
	import { goto } from '$app/navigation';
	import { getPO, updatePO } from '$lib/api';
	import PoForm from '$lib/po/PoForm.svelte';
	import PoRejectionHistoryPanel from '$lib/po/PoRejectionHistoryPanel.svelte';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { PurchaseOrder, PurchaseOrderInput, UserRole } from '$lib/types';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	const id: string = $page.params.id ?? '';

	const user = $derived(appPage.data.user);
	const role = $derived((user?.role as UserRole | undefined) ?? 'ADMIN');
	const name = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);

	let po = $state<PurchaseOrder | null>(null);
	let loading: boolean = $state(true);
	let fetchError: string = $state('');

	const status = $derived(po?.status);
	const editable = $derived(status === 'REJECTED' || status === 'DRAFT');
	const formMode = $derived<'edit-draft' | 'edit-revise'>(status === 'DRAFT' ? 'edit-draft' : 'edit-revise');
	const submitLabel = $derived(status === 'DRAFT' ? 'Save Draft' : 'Save & Revise');

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString();
	}

	onMount(async () => {
		try {
			po = await getPO(id);
		} catch (err) {
			fetchError = err instanceof Error ? err.message : 'Failed to load purchase order.';
		} finally {
			loading = false;
		}
	});

	async function handleSubmit(data: PurchaseOrderInput): Promise<void> {
		await updatePO(id, data);
		goto(`/po/${id}`);
	}

	function backToDetail() {
		goto(`/po/${id}`);
	}
</script>

<svelte:head>
	<title>Edit Purchase Order</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Edit PO">
	{#snippet userMenu()}
		<UserMenu {name} {role} />
	{/snippet}

	{#if loading}
		<LoadingState label="Loading purchase order" />
	{:else if fetchError}
		<ErrorState message={fetchError} onRetry={() => location.reload()} />
	{:else if po && !editable}
		<PageHeader title="Edit Purchase Order" subtitle={po.po_number} />
		<div class="not-editable" data-testid="po-edit-not-editable">
			<p class="not-editable-message">This PO is not editable in its current status.</p>
			<Button variant="secondary" onclick={backToDetail} data-testid="po-edit-back-to-detail">
				Back to detail
			</Button>
		</div>
	{:else if po && editable}
		<PageHeader title="Edit Purchase Order" subtitle={po.po_number} />
		{#if po.status === 'REJECTED' && po.rejection_history && po.rejection_history.length > 0}
			<div class="rejection-history-region">
				<PoRejectionHistoryPanel records={po.rejection_history} {formatDate} />
			</div>
		{/if}
		<PoForm
			mode={formMode}
			initialData={{
				po_type: po.po_type,
				vendor_id: po.vendor_id,
				buyer_name: po.buyer_name,
				buyer_country: po.buyer_country,
				currency: po.currency,
				issued_date: po.issued_date,
				required_delivery_date: po.required_delivery_date,
				ship_to_address: po.ship_to_address,
				payment_terms: po.payment_terms,
				incoterm: po.incoterm,
				port_of_loading: po.port_of_loading,
				port_of_discharge: po.port_of_discharge,
				country_of_origin: po.country_of_origin,
				country_of_destination: po.country_of_destination,
				terms_and_conditions: po.terms_and_conditions,
				marketplace: po.marketplace,
				line_items: po.line_items.map((item) => ({
					part_number: item.part_number,
					description: item.description,
					quantity: item.quantity,
					uom: item.uom,
					unit_price: item.unit_price,
					hs_code: item.hs_code,
					country_of_origin: item.country_of_origin,
					product_id: item.product_id
				}))
			}}
			onSubmit={handleSubmit}
			{submitLabel}
			cancelHref="/po/{id}"
		/>
	{/if}
</AppShell>

<style>
	.rejection-history-region {
		margin-bottom: var(--space-4);
	}

	.not-editable {
		padding: var(--space-6) 0;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
	}

	.not-editable-message {
		color: var(--gray-700);
		font-size: var(--font-size-sm);
		margin: 0;
	}
</style>
