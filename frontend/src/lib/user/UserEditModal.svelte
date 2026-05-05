<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import { listBrands, patchUser } from '$lib/api';
	import type { Brand, PatchUserInput, User } from '$lib/types';

	let {
		user,
		onSuccess,
		onCancel
	}: {
		user: User;
		onSuccess: (updated: User) => void;
		onCancel: () => void;
	} = $props();

	const titleId = crypto.randomUUID();
	const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

	// Iter 111: roles subject to brand scoping.
	const BRAND_SCOPABLE_ROLES: ReadonlyArray<string> = [
		'SM',
		'FREIGHT_MANAGER',
		'QUALITY_LAB',
		'PROCUREMENT_MANAGER'
	];

	let display_name: string = $state(user.display_name);
	let email: string = $state(user.email ?? '');

	// Iter 111: brand scope state.
	const isBrandScopable = $derived(BRAND_SCOPABLE_ROLES.includes(user.role));
	let brands: Brand[] = $state([]);
	let selectedBrandIds: string[] = $state([...(user.brand_ids ?? [])]);

	let displayNameError: string = $state('');
	let emailError: string = $state('');
	let serverError: string = $state('');
	let submitting: boolean = $state(false);

	$effect(() => {
		if (isBrandScopable) {
			listBrands({ status: 'ACTIVE' })
				.then((result) => {
					brands = result;
				})
				.catch(() => {
					// Brand list failure leaves the multi-select empty.
				});
		}
	});

	function toggleBrand(brandId: string) {
		if (selectedBrandIds.includes(brandId)) {
			selectedBrandIds = selectedBrandIds.filter((id) => id !== brandId);
		} else {
			selectedBrandIds = [...selectedBrandIds, brandId];
		}
	}

	function validate(): boolean {
		displayNameError = '';
		emailError = '';
		let ok = true;
		if (!display_name.trim()) {
			displayNameError = 'Display name is required.';
			ok = false;
		}
		if (email.trim() && !EMAIL_PATTERN.test(email.trim())) {
			emailError = 'Email is not valid.';
			ok = false;
		}
		return ok;
	}

	async function handleSubmit() {
		serverError = '';
		if (!validate()) return;
		submitting = true;
		try {
			const body: PatchUserInput = {
				display_name: display_name.trim(),
				// Empty input clears email server-side via explicit null.
				email: email.trim() ? email.trim() : null,
				// Iter 111: always send brand_ids for brand-scopable roles so the
				// server replaces the set. Empty array clears all assignments.
				...(isBrandScopable ? { brand_ids: selectedBrandIds } : {})
			};
			const { user: updated } = await patchUser(user.id, body);
			onSuccess(updated);
		} catch (e) {
			serverError = e instanceof Error ? e.message : 'Update failed.';
		} finally {
			submitting = false;
		}
	}
</script>

<div
	class="user-modal"
	role="dialog"
	aria-modal="true"
	aria-labelledby={titleId}
	data-testid="user-edit-modal"
>
	<div class="user-modal__card">
		<header class="user-modal__header">
			<h2 id={titleId} class="user-modal__title">Edit {user.username}</h2>
		</header>

		<div class="user-modal__body">
			{#if serverError}
				<div class="user-modal__error" role="alert" data-testid="user-edit-error">
					{serverError}
				</div>
			{/if}

			<FormField
				label="Display name"
				required
				error={displayNameError}
				data-testid="user-edit-display-name-field"
			>
				{#snippet children({ invalid })}
					<Input
						bind:value={display_name}
						{invalid}
						ariaLabel="Display name"
						data-testid="user-edit-display-name"
					/>
				{/snippet}
			</FormField>

			<FormField
				label="Email"
				error={emailError}
				hint="Leave blank to clear."
				data-testid="user-edit-email-field"
			>
				{#snippet children({ invalid })}
					<Input
						type="email"
						bind:value={email}
						{invalid}
						ariaLabel="Email"
						data-testid="user-edit-email"
					/>
				{/snippet}
			</FormField>

			{#if isBrandScopable}
				<FormField
					label="Brands"
					hint="Leave empty to see all brands."
					data-testid="user-edit-brands-field"
				>
					{#snippet children()}
						<div class="brand-checklist" aria-label="Brands" data-testid="user-edit-brands">
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
			<Button variant="secondary" onclick={onCancel} data-testid="user-edit-cancel">
				Cancel
			</Button>
			<Button
				variant="primary"
				disabled={submitting}
				onclick={handleSubmit}
				data-testid="user-edit-submit"
			>
				{submitting ? 'Saving…' : 'Save'}
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
