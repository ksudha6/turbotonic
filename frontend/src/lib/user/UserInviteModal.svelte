<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Select from '$lib/ui/Select.svelte';
	import { listVendors, listBrands, inviteUser } from '$lib/api';
	import type { Brand, InviteUserInput, InviteUserResponse, UserRole, VendorListItem } from '$lib/types';

	let {
		onSuccess,
		onCancel
	}: {
		onSuccess: (response: InviteUserResponse) => void;
		onCancel: () => void;
	} = $props();

	const titleId = crypto.randomUUID();

	const ROLE_OPTIONS: ReadonlyArray<{ value: UserRole; label: string }> = [
		{ value: 'ADMIN', label: 'Administrator' },
		{ value: 'SM', label: 'Supply Manager' },
		{ value: 'VENDOR', label: 'Vendor' },
		{ value: 'FREIGHT_MANAGER', label: 'Freight Manager' },
		{ value: 'QUALITY_LAB', label: 'Quality Lab' },
		{ value: 'PROCUREMENT_MANAGER', label: 'Procurement Manager' }
	];

	const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

	let username: string = $state('');
	let role: UserRole | '' = $state('' as UserRole | '');
	let display_name: string = $state('');
	let email: string = $state('');
	let vendor_id: string = $state('');

	let usernameError: string = $state('');
	let roleError: string = $state('');
	let emailError: string = $state('');
	let vendorError: string = $state('');
	let serverError: string = $state('');
	let submitting: boolean = $state(false);

	let vendors: VendorListItem[] = $state([]);
	let vendorsFetched: boolean = $state(false);

	// Iter 111: brand multi-select for buyer-side roles.
	const BRAND_SCOPABLE_ROLES: ReadonlyArray<UserRole> = [
		'SM',
		'FREIGHT_MANAGER',
		'QUALITY_LAB',
		'PROCUREMENT_MANAGER'
	];

	let brands: Brand[] = $state([]);
	let brandsFetched: boolean = $state(false);
	let selectedBrandIds: string[] = $state([]);

	const isVendorRole = $derived(role === 'VENDOR');
	const isBrandScopable = $derived(BRAND_SCOPABLE_ROLES.includes(role as UserRole));

	$effect(() => {
		if (isVendorRole && !vendorsFetched) {
			vendorsFetched = true;
			loadVendors();
		}
	});

	$effect(() => {
		if (isBrandScopable && !brandsFetched) {
			brandsFetched = true;
			loadBrands();
		}
	});

	async function loadVendors() {
		try {
			vendors = await listVendors({ status: 'ACTIVE' });
		} catch {
			// Vendor list failure leaves the dropdown empty; the form blocks submit.
		}
	}

	async function loadBrands() {
		try {
			brands = await listBrands({ status: 'ACTIVE' });
		} catch {
			// Brand list failure leaves the multi-select empty; user can still submit unscoped.
		}
	}

	function toggleBrand(brandId: string) {
		if (selectedBrandIds.includes(brandId)) {
			selectedBrandIds = selectedBrandIds.filter((id) => id !== brandId);
		} else {
			selectedBrandIds = [...selectedBrandIds, brandId];
		}
	}

	function validate(): boolean {
		usernameError = '';
		roleError = '';
		emailError = '';
		vendorError = '';
		let ok = true;
		if (!username.trim()) {
			usernameError = 'Username is required.';
			ok = false;
		}
		if (!role) {
			roleError = 'Role is required.';
			ok = false;
		}
		if (email.trim() && !EMAIL_PATTERN.test(email.trim())) {
			emailError = 'Email is not valid.';
			ok = false;
		}
		if (isVendorRole && !vendor_id) {
			vendorError = 'Vendor is required for VENDOR role.';
			ok = false;
		}
		return ok;
	}

	async function handleSubmit() {
		serverError = '';
		if (!validate()) return;
		submitting = true;
		try {
			const input: InviteUserInput = {
				username: username.trim(),
				display_name: display_name.trim() || username.trim(),
				role: role as UserRole,
				email: email.trim() ? email.trim() : null,
				vendor_id: isVendorRole ? vendor_id : null,
				// Iter 111: send brand_ids when role is brand-scopable; null means unscoped.
				brand_ids: isBrandScopable ? (selectedBrandIds.length > 0 ? selectedBrandIds : null) : null
			};
			const response = await inviteUser(input);
			onSuccess(response);
		} catch (e) {
			serverError = e instanceof Error ? e.message : 'Invite failed.';
		} finally {
			submitting = false;
		}
	}

	const vendorOptions = $derived([
		{ value: '', label: 'Select vendor…' },
		...vendors.map((v) => ({ value: v.id, label: v.name }))
	]);

	const roleSelectOptions = $derived([
		{ value: '', label: 'Select role…' },
		...ROLE_OPTIONS.map((opt) => ({ value: opt.value as string, label: opt.label }))
	]);
</script>

<div
	class="user-modal"
	role="dialog"
	aria-modal="true"
	aria-labelledby={titleId}
	data-testid="user-invite-modal"
>
	<div class="user-modal__card">
		<header class="user-modal__header">
			<h2 id={titleId} class="user-modal__title">Invite user</h2>
		</header>

		<div class="user-modal__body">
			{#if serverError}
				<div class="user-modal__error" role="alert" data-testid="user-invite-error">
					{serverError}
				</div>
			{/if}

			<FormField
				label="Username"
				required
				error={usernameError}
				data-testid="user-invite-username-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={username}
						{invalid}
						ariaLabel="Username"
						data-testid="user-invite-username"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Role"
				required
				error={roleError}
				data-testid="user-invite-role-field"
			>
				{#snippet children({ invalid })}
					<Select
						bind:value={role}
						options={roleSelectOptions}
						{invalid}
						ariaLabel="Role"
						data-testid="user-invite-role"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Display name"
				hint="Optional. Defaults to the username."
				data-testid="user-invite-display-name-field"
			>
				{#snippet children()}
					<Input
						bind:value={display_name}
						ariaLabel="Display name"
						data-testid="user-invite-display-name"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Email"
				error={emailError}
				hint="Optional."
				data-testid="user-invite-email-field"
			>
				{#snippet children({ invalid })}
					<Input
						type="email"
						bind:value={email}
						{invalid}
						ariaLabel="Email"
						data-testid="user-invite-email"
					/>
				{/snippet}
			</FormField>

			{#if isVendorRole}
				<FormField
					label="Vendor"
					required
					error={vendorError}
					data-testid="user-invite-vendor-field"
				>
					{#snippet children({ invalid })}
						<Select
							bind:value={vendor_id}
							options={vendorOptions}
							{invalid}
							ariaLabel="Vendor"
							data-testid="user-invite-vendor"
						/>
					{/snippet}
				</FormField>
			{/if}

			{#if isBrandScopable}
				<FormField
					label="Brands"
					hint="Leave empty to see all brands."
					data-testid="user-invite-brands-field"
				>
					{#snippet children()}
						<div class="brand-checklist" aria-label="Brands" data-testid="user-invite-brands">
							{#if brands.length === 0}
								<p class="brand-checklist__empty">No active brands.</p>
							{:else}
								{#each brands as brand (brand.id)}
									<label class="brand-checklist__item">
										<input
											type="checkbox"
											checked={selectedBrandIds.includes(brand.id)}
											onchange={() => toggleBrand(brand.id)}
										/>
										{brand.name}
									</label>
								{/each}
							{/if}
						</div>
					{/snippet}
				</FormField>
			{/if}
		</div>

		<footer class="user-modal__footer">
			<Button variant="secondary" onclick={onCancel} data-testid="user-invite-cancel">
				Cancel
			</Button>
			<Button
				variant="primary"
				disabled={submitting}
				onclick={handleSubmit}
				data-testid="user-invite-submit"
			>
				{submitting ? 'Sending…' : 'Send invite'}
			</Button>
		</footer>
	</div>
</div>

<style>
	.user-modal {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: var(--space-4);
	}
	.user-modal__card {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		max-width: 32rem;
		width: 100%;
		max-height: 90vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
	}
	.user-modal__header {
		padding: var(--space-6) var(--space-6) var(--space-2);
	}
	.user-modal__title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
	}
	.user-modal__body {
		padding: var(--space-2) var(--space-6) var(--space-4);
	}
	.user-modal__error {
		padding: var(--space-3);
		margin-bottom: var(--space-4);
		background-color: #fee2e2;
		color: #991b1b;
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
	}
	.user-modal__footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		border-top: 1px solid var(--gray-100);
	}
	.brand-checklist {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		max-height: 12rem;
		overflow-y: auto;
		padding: var(--space-2) 0;
	}
	.brand-checklist__item {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--font-size-sm);
		cursor: pointer;
	}
	.brand-checklist__empty {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
</style>
