<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { createProduct, listVendors } from '$lib/api';
	import type { VendorListItem } from '$lib/types';

	let vendor_id: string = $state('');
	let part_number: string = $state('');
	let description: string = $state('');
	let requires_certification: boolean = $state(false);
	let manufacturing_address: string = $state('');
	let submitting: boolean = $state(false);
	let error: string = $state('');
	let vendors: VendorListItem[] = $state([]);

	onMount(async () => {
		vendors = await listVendors({ status: 'ACTIVE' });
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';

		if (!vendor_id) {
			error = 'Vendor is required.';
			return;
		}
		if (!part_number.trim()) {
			error = 'Part Number is required.';
			return;
		}

		submitting = true;
		try {
			await createProduct({
				vendor_id,
				part_number: part_number.trim(),
				description: description.trim(),
				requires_certification,
				manufacturing_address
			});
			goto('/products');
		} catch (err) {
			if (err instanceof Error && err.message.includes('409')) {
				error = 'A product with this part number already exists for this vendor.';
			} else {
				error = err instanceof Error ? err.message : 'An error occurred.';
			}
		} finally {
			submitting = false;
		}
	}
</script>

<h1>Create Product</h1>

<form onsubmit={handleSubmit}>
	<div class="section card">
		<h2>Product Details</h2>
		<div class="form-grid">
			<div class="form-group">
				<label for="vendor_id">Vendor *</label>
				<select id="vendor_id" class="select" required bind:value={vendor_id}>
					<option value="">Select vendor</option>
					{#each vendors as v}
						<option value={v.id}>{v.name}</option>
					{/each}
				</select>
			</div>
			<div class="form-group">
				<label for="part_number">Part Number *</label>
				<input id="part_number" class="input" type="text" required bind:value={part_number} />
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
			<div class="form-group span-2">
				<label for="manufacturing_address">Manufacturing Address</label>
				<textarea id="manufacturing_address" class="textarea" bind:value={manufacturing_address}></textarea>
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
				{submitting ? 'Creating...' : 'Create Product'}
			</button>
		</div>
	</div>
</form>

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
