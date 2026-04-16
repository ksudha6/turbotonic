<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { getProduct, updateProduct, listVendors, listQualificationTypes, assignQualification, removeQualification, listPackagingSpecs, createPackagingSpec, deletePackagingSpec } from '$lib/api';
	import { canManageProducts } from '$lib/permissions';
	import type { Product, VendorListItem, QualificationTypeListItem, PackagingSpec } from '$lib/types';

	const role = $derived(page.data.user?.role);
	const isSM = $derived(role === 'SM' || role === 'ADMIN');

	let product: Product | null = $state(null);
	let vendors: VendorListItem[] = $state([]);
	let description: string = $state('');
	let manufacturing_address: string = $state('');
	let submitting: boolean = $state(false);
	let error: string = $state('');
	let loading: boolean = $state(true);

	let allQualificationTypes: QualificationTypeListItem[] = $state([]);
	let currentQualifications: QualificationTypeListItem[] = $state([]);
	let selectedQtId: string = $state('');
	let qualificationError: string = $state('');

	let specs: PackagingSpec[] = $state([]);
	let specsError: string = $state('');
	let showAddSpec: boolean = $state(false);
	let newMarketplace: string = $state('');
	let newSpecName: string = $state('');
	let newDescription: string = $state('');
	let newRequirementsText: string = $state('');
	let addingSpec: boolean = $state(false);
	let addSpecError: string = $state('');

	const specsByMarketplace = $derived(() => {
		const groups: Record<string, PackagingSpec[]> = {};
		for (const spec of specs) {
			if (!groups[spec.marketplace]) groups[spec.marketplace] = [];
			groups[spec.marketplace].push(spec);
		}
		return groups;
	});

	onMount(async () => {
		const id = page.params.id ?? '';
		const [fetched, fetchedVendors, allQts] = await Promise.all([
			getProduct(id),
			listVendors(),
			listQualificationTypes()
		]);
		product = fetched;
		vendors = fetchedVendors;
		allQualificationTypes = allQts;
		description = fetched.description;
		manufacturing_address = fetched.manufacturing_address;
		currentQualifications = fetched.qualifications ?? [];
		await loadSpecs(id);
		loading = false;
	});

	async function loadSpecs(productId: string) {
		try {
			specs = await listPackagingSpecs(productId);
		} catch (err) {
			specsError = err instanceof Error ? err.message : 'Failed to load packaging specs';
		}
	}

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
				requirements_text: newRequirementsText.trim(),
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

	function vendorName(vendor_id: string): string {
		return vendors.find((v) => v.id === vendor_id)?.name ?? vendor_id;
	}

	function availableQualificationTypes(): QualificationTypeListItem[] {
		const assigned = new Set(currentQualifications.map((q) => q.id));
		return allQualificationTypes.filter((qt) => !assigned.has(qt.id));
	}

	async function handleAddQualification() {
		if (!product || !selectedQtId) return;
		qualificationError = '';
		try {
			await assignQualification(product.id, selectedQtId);
			const added = allQualificationTypes.find((qt) => qt.id === selectedQtId);
			if (added) currentQualifications = [...currentQualifications, added];
			selectedQtId = '';
		} catch (err) {
			qualificationError = err instanceof Error ? err.message : 'Failed to assign qualification.';
		}
	}

	async function handleRemoveQualification(qtId: string) {
		if (!product) return;
		qualificationError = '';
		try {
			await removeQualification(product.id, qtId);
			currentQualifications = currentQualifications.filter((q) => q.id !== qtId);
		} catch (err) {
			qualificationError = err instanceof Error ? err.message : 'Failed to remove qualification.';
		}
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!product) return;
		error = '';
		submitting = true;
		try {
			await updateProduct(product.id, { description: description.trim(), manufacturing_address });
			goto('/products');
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred.';
		} finally {
			submitting = false;
		}
	}
</script>

{#if loading}
	<p>Loading...</p>
{:else if product}
	<h1>Edit Product</h1>

	<form onsubmit={handleSubmit}>
		<div class="section card">
			<h2>Product Details</h2>
			<div class="form-grid">
				<div class="form-group">
					<label>Vendor</label>
					<p class="readonly-value">{vendorName(product.vendor_id)}</p>
				</div>
				<div class="form-group">
					<label>Part Number</label>
					<p class="readonly-value">{product.part_number}</p>
				</div>
				{#if role && canManageProducts(role)}
					<div class="form-group">
						<label for="description">Description</label>
						<input id="description" class="input" type="text" bind:value={description} />
					</div>
					<div class="form-group span-2">
						<label for="manufacturing_address">Manufacturing Address</label>
						<textarea id="manufacturing_address" class="textarea" bind:value={manufacturing_address}></textarea>
					</div>
				{:else}
					<div class="form-group">
						<label>Description</label>
						<p class="readonly-value">{description}</p>
					</div>
					<div class="form-group span-2">
						<label>Manufacturing Address</label>
						<p class="readonly-value">{manufacturing_address || '—'}</p>
					</div>
				{/if}
			</div>
		</div>

		<div class="section card">
			<h2>Qualifications</h2>
			{#if currentQualifications.length === 0}
				<p class="empty-message">No qualifications assigned.</p>
			{:else}
				<ul class="qualification-list">
					{#each currentQualifications as qt}
						<li class="qualification-item">
							<span class="qt-name">{qt.name}</span>
							<span class="qt-market">{qt.target_market}</span>
							{#if role && canManageProducts(role)}
								<button
									type="button"
									class="btn btn-danger btn-sm"
									onclick={() => handleRemoveQualification(qt.id)}
								>Remove</button>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}

			{#if role && canManageProducts(role)}
				<div class="add-qualification">
					<select class="select" bind:value={selectedQtId}>
						<option value="">Add qualification...</option>
						{#each availableQualificationTypes() as qt}
							<option value={qt.id}>{qt.name} ({qt.target_market})</option>
						{/each}
					</select>
					<button
						type="button"
						class="btn btn-secondary"
						disabled={!selectedQtId}
						onclick={handleAddQualification}
					>Add</button>
				</div>
			{/if}

			{#if qualificationError}
				<p class="error-message">{qualificationError}</p>
			{/if}
		</div>

		{#if role && canManageProducts(role)}
			<div class="form-actions">
				{#if error}
					<p class="error-message">{error}</p>
				{/if}
				<div class="action-buttons">
					<a href="/products" class="btn btn-secondary">Cancel</a>
					<button type="submit" class="btn btn-primary" disabled={submitting}>
						{submitting ? 'Saving...' : 'Save Changes'}
					</button>
				</div>
			</div>
		{:else}
			<div class="form-actions">
				<div class="action-buttons">
					<a href="/products" class="btn btn-secondary">Back</a>
				</div>
			</div>
		{/if}
	</form>

	<div class="section card">
		<div class="section-header">
			<h2>Packaging Specs</h2>
			{#if isSM}
				<button type="button" class="btn btn-secondary" onclick={() => { showAddSpec = !showAddSpec; addSpecError = ''; }}>
					{showAddSpec ? 'Cancel' : 'Add Spec'}
				</button>
			{/if}
		</div>

		{#if specsError}
			<p class="error-message">{specsError}</p>
		{/if}

		{#if isSM && showAddSpec}
			<form class="add-spec-form card-inner" onsubmit={handleAddSpec}>
				<h3>New Packaging Spec</h3>
				<div class="form-grid">
					<div class="form-group">
						<label for="new-marketplace">Marketplace</label>
						<input id="new-marketplace" class="input" type="text" bind:value={newMarketplace} required placeholder="e.g. AMAZON" />
					</div>
					<div class="form-group">
						<label for="new-spec-name">Spec Name</label>
						<input id="new-spec-name" class="input" type="text" bind:value={newSpecName} required placeholder="e.g. FNSKU Label" />
					</div>
					<div class="form-group span-2">
						<label for="new-description">Description</label>
						<input id="new-description" class="input" type="text" bind:value={newDescription} placeholder="Short description" />
					</div>
					<div class="form-group span-2">
						<label for="new-requirements">Requirements</label>
						<textarea id="new-requirements" class="textarea" bind:value={newRequirementsText} placeholder="Detailed requirements for the vendor"></textarea>
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
									{#if isSM && spec.status === 'PENDING'}
										<button type="button" class="btn btn-danger btn-sm" onclick={() => handleDeleteSpec(spec.id)}>Delete</button>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		{/if}
	</div>
{/if}

<style>
	.section {
		margin-bottom: var(--space-6);
	}

	.section h2 {
		margin-bottom: var(--space-4);
	}

	.form-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
	}

	.form-grid .span-2 {
		grid-column: span 2;
	}

	.readonly-value {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0;
		padding: var(--space-2) 0;
	}

	.empty-message {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-bottom: var(--space-4);
	}

	.qualification-list {
		list-style: none;
		padding: 0;
		margin: 0 0 var(--space-4) 0;
	}

	.qualification-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}

	.qualification-item:last-child {
		border-bottom: none;
	}

	.qt-name {
		font-weight: 500;
		flex: 1;
	}

	.qt-market {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}

	.add-qualification {
		display: flex;
		gap: var(--space-3);
		align-items: center;
		margin-top: var(--space-4);
	}

	.add-qualification .select {
		flex: 1;
	}

	.btn-danger {
		background-color: var(--red-50);
		color: var(--red-700);
		border: 1px solid var(--red-200);
	}

	.btn-danger:hover {
		background-color: var(--red-100);
	}

	.btn-sm {
		font-size: var(--font-size-sm);
		padding: var(--space-1) var(--space-3);
	}

	.form-actions {
		padding-top: var(--space-4);
		border-top: 1px solid var(--gray-200);
		margin-bottom: var(--space-6);
	}

	.error-message {
		color: var(--red-600);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-3);
	}

	.action-buttons {
		display: flex;
		gap: var(--space-3);
	}
</style>
