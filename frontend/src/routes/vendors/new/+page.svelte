<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { createVendor, fetchReferenceData } from '$lib/api';
	import type { ReferenceDataItem, VendorType } from '$lib/types';

	let name: string = $state('');
	let country: string = $state('');
	let vendor_type: VendorType = $state('PROCUREMENT');
	let submitting: boolean = $state(false);
	let error: string = $state('');
	let countries: ReferenceDataItem[] = $state([]);

	onMount(async () => {
		const refData = await fetchReferenceData();
		countries = refData.countries;
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';

		if (!name.trim()) {
			error = 'Name is required.';
			return;
		}
		if (!country) {
			error = 'Country is required.';
			return;
		}

		submitting = true;
		try {
			await createVendor({ name: name.trim(), country, vendor_type });
			goto('/vendors');
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred.';
		} finally {
			submitting = false;
		}
	}
</script>

<h1>Create Vendor</h1>

<form onsubmit={handleSubmit}>
	<div class="section card">
		<h2>Vendor Details</h2>
		<div class="form-grid">
			<div class="form-group">
				<label for="name">Name *</label>
				<input id="name" class="input" type="text" required bind:value={name} />
			</div>
			<div class="form-group">
				<label for="country">Country *</label>
				<select id="country" class="select" required bind:value={country}>
					<option value="">Select country</option>
					{#each countries as c}
						<option value={c.code}>{c.label}</option>
					{/each}
				</select>
			</div>
			<div class="form-group">
				<label for="vendor_type">Vendor Type *</label>
				<select id="vendor_type" class="select" required bind:value={vendor_type}>
					<option value="PROCUREMENT">Procurement</option>
					<option value="OPEX">OpEx</option>
					<option value="FREIGHT">Freight</option>
					<option value="MISCELLANEOUS">Miscellaneous</option>
				</select>
			</div>
		</div>
	</div>

	<div class="form-actions">
		{#if error}
			<p class="error-message">{error}</p>
		{/if}
		<div class="action-buttons">
			<a href="/vendors" class="btn btn-secondary">Cancel</a>
			<button type="submit" class="btn btn-primary" disabled={submitting}>
				{submitting ? 'Creating...' : 'Create Vendor'}
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
