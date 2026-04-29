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
	import ProductPackagingSpecsPanel, {
		type PackagingSpecAddFields
	} from '$lib/product/ProductPackagingSpecsPanel.svelte';

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

	let specs: PackagingSpec[] = $state([]);
	let specsError: string = $state('');
	let addSpecError: string = $state('');
	let addingSpec: boolean = $state(false);

	const user = $derived(appPage.data.user);
	const role = $derived<UserRole>((user?.role as UserRole | undefined) ?? 'ADMIN');
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const roleLabel = $derived(ROLE_LABEL[role]);
	const canManage = $derived(canManageProducts(role));

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

	async function handleAddSpec(fields: PackagingSpecAddFields) {
		if (!product) return;
		addSpecError = '';
		addingSpec = true;
		try {
			const spec = await createPackagingSpec({
				product_id: product.id,
				...fields
			});
			specs = [...specs, spec];
		} catch (err) {
			addSpecError = err instanceof Error ? err.message : 'Failed to add spec.';
		} finally {
			addingSpec = false;
		}
	}

	async function handleDeleteSpec(specId: string) {
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

			<ProductPackagingSpecsPanel
				{specs}
				{canManage}
				error={specsError}
				addError={addSpecError}
				adding={addingSpec}
				on_add_spec={handleAddSpec}
				on_delete_spec={handleDeleteSpec}
			/>
		</div>
	{/if}
</AppShell>

<style>
	.product-edit-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
</style>
