<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { bootstrap, registerVerify } from '$lib/auth';
	import { startRegistration } from '$lib/webauthn';
	import Button from '$lib/ui/Button.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';

	let username = $state('');
	let displayName = $state('');
	let error = $state('');
	let loading = $state(false);
	let alreadyConfigured = $state(false);

	onMount(() => {
		if (page.data.user?.status === 'ACTIVE') {
			goto('/dashboard');
		}
	});

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = '';

		if (!window.PublicKeyCredential) {
			error = 'WebAuthn is not supported in this browser';
			return;
		}

		loading = true;
		try {
			const { options, invite_token } = await bootstrap(username, displayName);

			let credential;
			try {
				credential = await startRegistration(options);
			} catch (e: unknown) {
				if (e instanceof Error && e.name === 'NotAllowedError') {
					error = 'Registration was cancelled. Try again.';
				} else {
					error = 'Passkey creation failed. Try again.';
				}
				return;
			}

			await registerVerify(invite_token, credential);
			await goto('/dashboard');
		} catch (e: unknown) {
			if (e instanceof Error) {
				if (e.message.toLowerCase().includes('already exist')) {
					alreadyConfigured = true;
				} else {
					error = e.message;
				}
			} else {
				error = 'An unexpected error occurred.';
			}
		} finally {
			loading = false;
		}
	}
</script>

<div class="auth-page">
	<div class="auth-card">
		{#if page.data.user?.status === 'PENDING'}
			<PanelCard title="System Setup">
				<p class="auth-info">
					Your account is pending approval. Contact your administrator.
				</p>
			</PanelCard>
		{:else if alreadyConfigured}
			<PanelCard title="System Setup">
				<p class="auth-info">System already configured.</p>
				<a href="/login">Go to login</a>
			</PanelCard>
		{:else}
			<PanelCard title="System Setup" subtitle="Create the first admin account">
				<form onsubmit={handleSubmit}>
					<FormField label="Username">
						{#snippet children()}
							<Input
								bind:value={username}
								disabled={loading}
								ariaLabel="Username"
								data-testid="setup-username"
							/>
						{/snippet}
					</FormField>

					<FormField label="Display Name">
						{#snippet children()}
							<Input
								bind:value={displayName}
								disabled={loading}
								ariaLabel="Display Name"
								data-testid="setup-display-name"
							/>
						{/snippet}
					</FormField>

					{#if error}
						<p class="auth-error" data-testid="setup-error">{error}</p>
					{/if}

					<Button type="submit" disabled={loading} data-testid="setup-submit">
						{loading ? 'Creating account...' : 'Create Admin Account'}
					</Button>
				</form>
			</PanelCard>
		{/if}
	</div>
</div>

<style>
	.auth-page {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4);
	}

	.auth-card {
		width: 100%;
		max-width: 400px;
	}

	.auth-info {
		color: var(--gray-600);
		font-size: var(--font-size-sm);
		text-align: center;
		margin: 0 0 var(--space-3) 0;
	}

	.auth-error {
		color: var(--red-700);
		font-size: var(--font-size-sm);
		margin: 0 0 var(--space-3) 0;
	}
</style>
