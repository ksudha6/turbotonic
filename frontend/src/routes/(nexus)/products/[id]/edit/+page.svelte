<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as appPage } from '$app/state';
	import {
		getProduct,
		updateProduct,
		listVendors,
		listQualificationTypes,
		assignQualification,
		removeQualification,
		listPackagingSpecs,
		createPackagingSpec,
		deletePackagingSpec
	} from '$lib/api';
	import { canManageProducts } from '$lib/permissions';
	import type {
		Product,
		VendorListItem,
		QualificationTypeListItem,
		PackagingSpec,
		UserRole
	} from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import ProductEditForm from '$lib/product/ProductEditForm.svelte';
	import ProductQualificationsPanel from '$lib/product/ProductQualificationsPanel.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let product: Product | null = $state(null);
	let vendors: VendorListItem[] = $state([]);
	let description: string = $state('');
	let manufacturingAddress: string = $state('');
	let submitting: boolean = $state(false);
	let error: string = $state('');
	let loading: boolean = $state(true);

	let allQualificationTypes: QualificationTypeListItem[] = $state([]);
	let currentQualifications: QualificationTypeListItem[] = $state([]);
	let qualificationError: string = $state('');

	// Iter 093 will replace this with `ProductPackagingSpecsPanel`. For iter 092
	// the legacy markup stays inline so the edit page is fully functional under
	// the new shell. State + handlers carry over verbatim from the legacy page.
	let specs: PackagingSpec[] = $state([]);
	let specsError: string = $state('');
	let showAddSpec: boolean = $state(false);
	let newMarketplace: string = $state('');
	let newSpecName: string = $state('');
	let newDescription: string = $state('');
	let newRequirementsText: string = $state('');
	let addingSpec: boolean = $state(false);
	let addSpecError: string = $state('');

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);
	const canManage = $derived(canManageProducts(role));

	const specsByMarketplace = $derived(() => {
		const groups: Record<string, PackagingSpec[]> = {};
		for (const spec of specs) {
			if (!groups[spec.marketplace]) groups[spec.marketplace] = [];
			groups[spec.marketplace].push(spec);
		}
		return groups;
	});

	function vendorName(vendor_id: string): string {
		return vendors.find((v) => v.id === vendor_id)?.name ?? vendor_id;
	}

	onMount(async () => {
		const id = appPage.params.id ?? '';
		try {
			const [fetched, fetchedVendors, allQts] = await Promise.all([
				getProduct(id),
				listVendors(),
				listQualificationTypes()
			]);
			product = fetched;
			vendors = fetchedVendors;
			allQualificationTypes = allQts;
			description = fetched.description;
			manufacturingAddress = fetched.manufacturing_address;
			currentQualifications = fetched.qualifications ?? [];
			await loadSpecs(id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load product';
		} finally {
			loading = false;
		}
	});

	async function loadSpecs(productId: string) {
		try {
			specs = await listPackagingSpecs(productId);
		} catch (err) {
			specsError = err instanceof Error ? err.message : 'Failed to load packaging specs';
		}
	}

	async function handleSubmit() {
		if (!product) return;
		error = '';
		submitting = true;
		try {
			await updateProduct(product.id, {
				description: description.trim(),
				manufacturing_address: manufacturingAddress
			});
			goto('/products');
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred.';
		} finally {
			submitting = false;
		}
	}

	function handleCancel() {
		goto('/products');
	}

	async function handleAddQualification(qtId: string) {
		if (!product) return;
		qualificationError = '';
		try {
			await assignQualification(product.id, qtId);
			const added = allQualificationTypes.find((qt) => qt.id === qtId);
			if (added) currentQualifications = [...currentQualifications, added];
		} catch (err) {
			qualificationError =
				err instanceof Error ? err.message : 'Failed to assign qualification.';
		}
	}

	async function handleRemoveQualification(qtId: string) {
		if (!product) return;
		qualificationError = '';
		try {
			await removeQualification(product.id, qtId);
			currentQualifications = currentQualifications.filter((q) => q.id !== qtId);
		} catch (err) {
			qualificationError =
				err instanceof Error ? err.message : 'Failed to remove qualification.';
		}
	}

	// ----- Legacy packaging-specs handlers (replaced in iter 093) -----

	async function handleAddSpec(e: SubmitEvent) {
		e.preventDefault();
		if (!product) return;
		addSpecError = '';
		addingSpec = true;
		try {
			const spec = await createPackagingSpec({
				product_id: product.id,
				marketplace: newMarketplace.trim(),
				spec_name: newSpecName.trim(),
				description: newDescription.trim(),
				requirements_text: newRequirementsText.trim()
			});
			specs = [...specs, spec];
			showAddSpec = false;
			newMarketplace = '';
			newSpecName = '';
			newDescription = '';
			newRequirementsText = '';
		} catch (err) {
			addSpecError = err instanceof Error ? err.message : 'Failed to add spec.';
		} finally {
			addingSpec = false;
		}
	}

	async function handleDeleteSpec(specId: string) {
		if (!confirm('Delete this packaging spec?')) return;
		try {
			await deletePackagingSpec(specId);
			specs = specs.filter((s) => s.id !== specId);
		} catch (err) {
			specsError = err instanceof Error ? err.message : 'Failed to delete spec.';
		}
	}
</script>

<svelte:head>
	<title>Edit Product</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Products">
	{#snippet userMenu()}
		<UserMenu name={userName} {role} />
	{/snippet}

	<PageHeader title="Edit Product" />

	{#if loading}
		<LoadingState label="Loading product" data-testid="product-edit-loading" />
	{:else if product}
		<div class="product-edit-page">
			<ProductEditForm
				vendorName={vendorName(product.vendor_id)}
				partNumber={product.part_number}
				bind:description
				bind:manufacturingAddress
				canEdit={canManage}
				{error}
				{submitting}
				on_submit={handleSubmit}
				on_cancel={handleCancel}
			/>

			<ProductQualificationsPanel
				current={currentQualifications}
				all={allQualificationTypes}
				{canManage}
				error={qualificationError}
				on_add={handleAddQualification}
				on_remove={handleRemoveQualification}
			/>

			<!--
				Iter 093 retires this block in favor of `ProductPackagingSpecsPanel`.
				Markup matches the legacy page so behavior is unchanged.
			-->
			<div class="section card" data-testid="product-edit-packaging-legacy">
				<div class="section-header">
					<h2>Packaging Specs</h2>
					{#if canManage}
						<button
							type="button"
							class="btn btn-secondary"
							onclick={() => {
								showAddSpec = !showAddSpec;
								addSpecError = '';
							}}
						>
							{showAddSpec ? 'Cancel' : 'Add Spec'}
						</button>
					{/if}
				</div>

				{#if specsError}
					<p class="error-message">{specsError}</p>
				{/if}

				{#if canManage && showAddSpec}
					<form class="add-spec-form card-inner" onsubmit={handleAddSpec}>
						<h3>New Packaging Spec</h3>
						<div class="form-grid">
							<div class="form-group">
								<label for="new-marketplace">Marketplace</label>
								<input
									id="new-marketplace"
									class="input"
									type="text"
									bind:value={newMarketplace}
									required
									placeholder="e.g. AMAZON"
								/>
							</div>
							<div class="form-group">
								<label for="new-spec-name">Spec Name</label>
								<input
									id="new-spec-name"
									class="input"
									type="text"
									bind:value={newSpecName}
									required
									placeholder="e.g. FNSKU Label"
								/>
							</div>
							<div class="form-group span-2">
								<label for="new-description">Description</label>
								<input
									id="new-description"
									class="input"
									type="text"
									bind:value={newDescription}
									placeholder="Short description"
								/>
							</div>
							<div class="form-group span-2">
								<label for="new-requirements">Requirements</label>
								<textarea
									id="new-requirements"
									class="textarea"
									bind:value={newRequirementsText}
									placeholder="Detailed requirements for the vendor"
								></textarea>
							</div>
						</div>
						{#if addSpecError}
							<p class="error-message">{addSpecError}</p>
						{/if}
						<div class="action-buttons">
							<button type="submit" class="btn btn-primary" disabled={addingSpec}>
								{addingSpec ? 'Adding...' : 'Add Spec'}
							</button>
						</div>
					</form>
				{/if}

				{#if specs.length === 0}
					<p class="empty-message">No packaging specs defined yet.</p>
				{:else}
					{#each Object.entries(specsByMarketplace()) as [marketplace, group]}
						<div class="marketplace-group">
							<h3 class="marketplace-heading">{marketplace}</h3>
							<div class="spec-list">
								{#each group as spec (spec.id)}
									<div class="spec-row">
										<div class="spec-info">
											<span class="spec-name">{spec.spec_name}</span>
											{#if spec.description}
												<span class="spec-description">{spec.description}</span>
											{/if}
										</div>
										<div class="spec-meta">
											<span class="status-pill status-{spec.status.toLowerCase()}">{spec.status}</span>
											{#if canManage && spec.status === 'PENDING'}
												<button
													type="button"
													class="btn btn-danger btn-sm"
													onclick={() => handleDeleteSpec(spec.id)}
												>
													Delete
												</button>
											{/if}
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</AppShell>

<style>
	.product-edit-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	/* Legacy packaging-specs styles inlined for iter 092; iter 093 retires them. */
	.section {
		padding: var(--space-4);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-4);
	}
	.section h2 { margin: 0 0 var(--space-3); font-size: var(--font-size-lg); }
	.empty-message { font-size: var(--font-size-sm); color: var(--gray-500); margin: 0; }
	.error-message { color: var(--red-700); font-size: var(--font-size-sm); margin: 0 0 var(--space-3); }
	.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); }
	.form-grid .span-2 { grid-column: span 2; }
	.action-buttons { display: flex; gap: var(--space-3); justify-content: flex-end; margin-top: var(--space-3); }
	.spec-list { display: flex; flex-direction: column; gap: var(--space-2); }
	.spec-row { display: flex; justify-content: space-between; align-items: center; padding: var(--space-2) 0; border-bottom: 1px solid var(--gray-100); }
	.spec-row:last-child { border-bottom: none; }
	.spec-info { display: flex; flex-direction: column; gap: var(--space-1); }
	.spec-name { font-weight: 500; color: var(--gray-900); }
	.spec-description { font-size: var(--font-size-sm); color: var(--gray-700); }
	.spec-meta { display: flex; align-items: center; gap: var(--space-3); }
	.status-pill { padding: var(--space-1) var(--space-2); border-radius: 999px; font-size: var(--font-size-xs); font-weight: 500; }
	.status-pending { background-color: var(--gray-100); color: var(--gray-700); }
	.status-collected { background-color: var(--green-50); color: var(--green-700); }
	.marketplace-heading { font-size: var(--font-size-base); font-weight: 600; margin: var(--space-3) 0 var(--space-2); }
</style>
