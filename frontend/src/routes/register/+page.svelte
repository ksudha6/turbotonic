<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { registerOptions, registerVerify } from '$lib/auth';
	import { startRegistration } from '$lib/webauthn';
	import type { User } from '$lib/types';

	type LoadState = 'loading' | 'invalid' | 'error' | 'ready' | 'registering';

	let loadState: LoadState = $state('loading');
	let error = $state('');
	let user: User | null = $state(null);
	let registrationOptions: Record<string, unknown> | null = $state(null);

	const username = page.url.searchParams.get('username')?.trim() ?? '';

	// Redirect immediately if already authenticated
	$effect(() => {
		if (page.data.user && page.data.user.status === 'ACTIVE') {
			goto('/dashboard');
		}
	});

	onMount(async () => {
		if (!username) {
			loadState = 'invalid';
			return;
		}

		try {
			const result = await registerOptions(username);
			user = result.user;
			registrationOptions = result.options;
			loadState = 'ready';
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Failed to load registration options.';
			loadState = 'error';
		}
	});

	async function handleRegister() {
		if (!window.PublicKeyCredential) {
			error = 'WebAuthn is not supported in this browser.';
			loadState = 'error';
			return;
		}

		loadState = 'registering';
		error = '';

		let credential: Record<string, unknown>;
		try {
			credential = await startRegistration(registrationOptions!);
		} catch (e: unknown) {
			if (e instanceof Error && e.name === 'NotAllowedError') {
				error = 'Registration was cancelled. Try again.';
			} else {
				error = 'Passkey registration failed.';
			}
			loadState = 'ready';
			return;
		}

		try {
			await registerVerify(username, credential);
			await goto('/dashboard');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Registration failed.';
			loadState = 'ready';
		}
	}
</script>

<div class="page">
	<div class="card register-card">
		<h1>Register Your Account</h1>

		{#if loadState === 'loading'}
			<p class="status-message">Setting up...</p>
		{:else if loadState === 'invalid'}
			<p class="error-message">Invalid invite link.</p>
			<a href="/login">Go to sign in</a>
		{:else if loadState === 'error'}
			<p class="error-message">{error}</p>
			<a href="/login">Go to sign in</a>
		{:else if loadState === 'ready' || loadState === 'registering'}
			{#if user}
				<p class="welcome-message">Welcome, {user.display_name}</p>
				<p class="role-label">{user.role}</p>
			{/if}

			{#if error}
				<p class="error-message">{error}</p>
			{/if}

			<button
				class="btn btn-primary btn-full"
				disabled={loadState === 'registering'}
				onclick={handleRegister}
			>
				{loadState === 'registering' ? 'Registering...' : 'Register passkey'}
			</button>

			<p class="signin-link"><a href="/login">Already registered? Sign in</a></p>
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

	.register-card {
		width: 100%;
		max-width: 400px;
	}

	.register-card h1 {
		text-align: center;
		margin-bottom: var(--space-6);
	}

	.status-message {
		text-align: center;
		color: var(--gray-500);
		font-size: var(--font-size-sm);
	}

	.welcome-message {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin-bottom: var(--space-1);
	}

	.role-label {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-bottom: var(--space-6);
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

	.signin-link {
		text-align: center;
		font-size: var(--font-size-sm);
		margin-top: var(--space-4);
	}
</style>
