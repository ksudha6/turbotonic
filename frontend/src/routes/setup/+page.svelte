<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { bootstrap, registerVerify } from '$lib/auth';
	import { startRegistration } from '$lib/webauthn';

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
			const { options } = await bootstrap(username, displayName);

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

			await registerVerify(username, credential);
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

<div class="page">
	<div class="card setup-card">
		{#if page.data.user?.status === 'PENDING'}
			<h1>System Setup</h1>
			<p class="pending-message">
				Your account is pending approval. Contact your administrator.
			</p>
		{:else if alreadyConfigured}
			<h1>System Setup</h1>
			<p class="info-message">System already configured.</p>
			<a href="/login">Go to login</a>
		{:else}
			<h1>System Setup</h1>
			<p class="subtitle">Create the first admin account</p>

			<form onsubmit={handleSubmit}>
				<div class="form-group">
					<label for="username">Username</label>
					<input
						id="username"
						class="input"
						type="text"
						autocomplete="username"
						bind:value={username}
						disabled={loading}
					/>
				</div>

				<div class="form-group">
					<label for="display-name">Display Name</label>
					<input
						id="display-name"
						class="input"
						type="text"
						autocomplete="name"
						bind:value={displayName}
						disabled={loading}
					/>
				</div>

				{#if error}
					<p class="error-message">{error}</p>
				{/if}

				<button type="submit" class="btn btn-primary btn-full" disabled={loading}>
					{loading ? 'Creating account...' : 'Create Admin Account'}
				</button>
			</form>
		{/if}
	</div>
</div>

<style>
	.page {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4);
	}

	.setup-card {
		width: 100%;
		max-width: 400px;
	}

	.setup-card h1 {
		text-align: center;
		margin-bottom: var(--space-2);
	}

	.subtitle {
		text-align: center;
		color: var(--gray-500);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-8);
	}

	.pending-message {
		color: var(--gray-600);
		font-size: var(--font-size-sm);
		text-align: center;
		margin-top: var(--space-4);
	}

	.info-message {
		color: var(--gray-600);
		font-size: var(--font-size-sm);
		text-align: center;
		margin-top: var(--space-4);
		margin-bottom: var(--space-4);
	}

	.error-message {
		color: var(--red-600);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-4);
	}

	.btn-full {
		width: 100%;
		padding: var(--space-3) var(--space-4);
	}
</style>
