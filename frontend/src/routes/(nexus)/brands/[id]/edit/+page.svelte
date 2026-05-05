<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import {
		getBrand,
		patchBrand,
		deactivateBrand,
		reactivateBrand,
		listBrandVendors,
		listVendors,
		assignVendorToBrand,
		unassignVendorFromBrand,
		fetchReferenceData
	} from '$lib/api';
	import type { Brand, BrandUpdate, ReferenceDataItem, UserRole, Vendor } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import Button from '$lib/ui/Button.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import BrandForm from '$lib/brand/BrandForm.svelte';
	import BrandVendorAssignmentPanel from '$lib/brand/BrandVendorAssignmentPanel.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	const brandId = $derived(appPage.params.id);

	let brand: Brand | null = $state(null);
	let assignedVendors: Vendor[] = $state([]);
	let allActiveVendors: Vendor[] = $state([]);
	let countries: ReferenceDataItem[] = $state([]);
	let loading: boolean = $state(true);
	let loadError: string = $state('');
	let formError: string | null = $state(null);
	let submitting: boolean = $state(false);
	let statusError: string = $state('');

	// Confirm modal state for deactivate
	let confirmDeactivate: boolean = $state(false);

	const sessionUser = $derived(appPage.data.user);
	const sessionRole = $derived<UserRole>((sessionUser?.role as UserRole | undefined) ?? 'ADMIN');
	const sessionName = $derived(sessionUser?.display_name ?? sessionUser?.username ?? 'Guest');
	const sessionRoleLabel = $derived(ROLE_LABEL[sessionRole]);

	onMount(async () => {
		await loadAll();
	});

	async function loadAll() {
		loading = true;
		loadError = '';
		try {
			const [b, bv, av, refData] = await Promise.all([
				getBrand(brandId),
				listBrandVendors(brandId),
				listVendors({ status: 'ACTIVE' }),
				fetchReferenceData()
			]);
			brand = b;
			assignedVendors = bv;
			allActiveVendors = av;
			countries = refData.countries;
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load brand';
		} finally {
			loading = false;
		}
	}

	async function handleFormSubmit(data: BrandUpdate) {
		if (!brand) return;
		formError = null;
		submitting = true;
		try {
			const updated = await patchBrand(brand.id, data);
			brand = updated;
		} catch (e) {
			formError = e instanceof Error ? e.message : 'Save failed';
		} finally {
			submitting = false;
		}
	}

	async function handleDeactivate() {
		if (!brand) return;
		confirmDeactivate = false;
		statusError = '';
		try {
			const updated = await deactivateBrand(brand.id);
			brand = updated;
		} catch (e) {
			statusError = e instanceof Error ? e.message : 'Deactivate failed';
		}
	}

	async function handleReactivate() {
		if (!brand) return;
		statusError = '';
		try {
			const updated = await reactivateBrand(brand.id);
			brand = updated;
		} catch (e) {
			statusError = e instanceof Error ? e.message : 'Reactivate failed';
		}
	}

	async function handleAssign(vendorId: string) {
		await assignVendorToBrand(brandId, vendorId);
		// Refresh assigned vendors
		assignedVendors = await listBrandVendors(brandId);
	}

	async function handleUnassign(vendorId: string) {
		await unassignVendorFromBrand(brandId, vendorId);
		// Remove locally
		assignedVendors = assignedVendors.filter((v) => v.id !== vendorId);
	}
</script>

<svelte:head>
	<title>Edit Brand</title>
</svelte:head>

<AppShell role={sessionRole} roleLabel={sessionRoleLabel} breadcrumb="Brands">
	{#snippet userMenu()}
		<UserMenu name={sessionName} role={sessionRole} />
	{/snippet}

	<PageHeader title={brand ? `Edit: ${brand.name}` : 'Edit Brand'}>
		{#snippet action()}
			<Button variant="secondary" onclick={() => goto('/brands')} data-testid="brand-edit-back">
				Back to Brands
			</Button>
		{/snippet}
	</PageHeader>

	{#if loading}
		<LoadingState label="Loading brand" data-testid="brand-edit-loading" />
	{:else if loadError}
		<ErrorState message={loadError} onRetry={loadAll} />
	{:else if brand}
		<div class="brand-edit-page">
			<!-- Status action row -->
			<div class="brand-edit-page__status-row" data-testid="brand-edit-status-row">
				{#if brand.status === 'ACTIVE'}
					<Button
						variant="secondary"
						onclick={() => (confirmDeactivate = true)}
						data-testid="brand-edit-deactivate"
					>
						Deactivate
					</Button>
				{/if}
				{#if brand.status === 'INACTIVE'}
					<Button
						variant="primary"
						onclick={handleReactivate}
						data-testid="brand-edit-reactivate"
					>
						Reactivate
					</Button>
				{/if}
				{#if statusError}
					<p class="brand-edit-page__status-error" role="alert">{statusError}</p>
				{/if}
			</div>

			<BrandForm
				mode="edit"
				initial={brand}
				{countries}
				{submitting}
				error={formError}
				onSubmit={handleFormSubmit}
				onCancel={() => goto('/brands')}
			/>

			<BrandVendorAssignmentPanel
				{brandId}
				{assignedVendors}
				{allActiveVendors}
				onAssign={handleAssign}
				onUnassign={handleUnassign}
			/>
		</div>
	{/if}
</AppShell>

<!-- Deactivate confirm modal -->
{#if confirmDeactivate}
	<div class="brand-confirm-overlay" role="dialog" aria-modal="true" data-testid="brand-deactivate-modal">
		<div class="brand-confirm-dialog">
			<h2>Deactivate brand</h2>
			<p>This brand will no longer be available when creating new POs. Existing POs are not affected. Reactivating restores it.</p>
			<div class="brand-confirm-dialog__actions">
				<Button variant="secondary" onclick={() => (confirmDeactivate = false)} data-testid="brand-deactivate-cancel">
					Cancel
				</Button>
				<Button variant="primary" onclick={handleDeactivate} data-testid="brand-deactivate-confirm">
					Deactivate
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	.brand-edit-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}
	.brand-edit-page__status-row {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	.brand-edit-page__status-error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		margin: 0;
	}
	.brand-confirm-overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 50;
	}
	.brand-confirm-dialog {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
		max-width: 480px;
		width: calc(100% - var(--space-8));
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.brand-confirm-dialog h2 {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.brand-confirm-dialog p {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0;
	}
	.brand-confirm-dialog__actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}
</style>
