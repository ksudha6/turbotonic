<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getProduct, updateProduct, listVendors } from '$lib/api';
	import type { Product, VendorListItem } from '$lib/types';

	let product: Product | null = $state(null);
	let vendors: VendorListItem[] = $state([]);
	let description: string = $state('');
	let requires_certification: boolean = $state(false);
	let submitting: boolean = $state(false);
	let error: string = $state('');
	let loading: boolean = $state(true);

	onMount(async () => {
		const id = $page.params.id;
		const [fetched, fetchedVendors] = await Promise.all([getProduct(id), listVendors()]);
		product = fetched;
		vendors = fetchedVendors;
		description = fetched.description;
		requires_certification = fetched.requires_certification;
		loading = false;
	});

	function vendorName(vendor_id: string): string {
		return vendors.find((v) => v.id === vendor_id)?.name ?? vendor_id;
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!product) return;
		error = '';
		submitting = true;
		try {
			await updateProduct(product.id, { description: description.trim(), requires_certification });
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
				<div class="form-group">
					<label for="description">Description</label>
					<input id="description" class="input" type="text" bind:value={description} />
				</div>
				<div class="form-group form-group-checkbox">
					<label>
						<input type="checkbox" bind:checked={requires_certification} />
						Requires Certification
					</label>
				</div>
			</div>
		</div>

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

	.readonly-value {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0;
		padding: var(--space-2) 0;
	}

	.form-group-checkbox {
		display: flex;
		align-items: center;
	}

	.form-group-checkbox label {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		cursor: pointer;
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
