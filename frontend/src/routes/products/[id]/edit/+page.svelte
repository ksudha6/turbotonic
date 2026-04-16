<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { getProduct, updateProduct, listVendors, listQualificationTypes, assignQualification, removeQualification } from '$lib/api';
	import { canManageProducts } from '$lib/permissions';
	import type { Product, VendorListItem, QualificationTypeListItem } from '$lib/types';

	const role = $derived(page.data.user?.role);

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
		loading = false;
	});

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
