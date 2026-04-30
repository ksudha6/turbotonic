<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { registerOptions, registerVerify } from '$lib/auth';
	import { startRegistration } from '$lib/webauthn';
	import type { User } from '$lib/types';
	import Button from '$lib/ui/Button.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';

	type LoadState = 'loading' | 'invalid' | 'error' | 'ready' | 'registering';

	let loadState: LoadState = $state('loading');
	let error = $state('');
	let user: User | null = $state(null);
	let registrationOptions: Record<string, unknown> | null = $state(null);

	const token = page.url.searchParams.get('token')?.trim() ?? '';

	// Redirect immediately if already authenticated
	$effect(() => {
		if (page.data.user && page.data.user.status === 'ACTIVE') {
			goto('/dashboard');
		}
	});

	onMount(async () => {
		if (!token) {
			loadState = 'invalid';
			return;
		}

		try {
			const result = await registerOptions(token);
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
			await registerVerify(token, credential);
			await goto('/dashboard');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Registration failed.';
			loadState = 'ready';
		}
	}
</script>

<div class="auth-page">
	<div class="auth-card">
		<PanelCard title="Register Your Account">
			{#if loadState === 'loading'}
				<p class="auth-status">Setting up...</p>
			{:else if loadState === 'invalid'}
				<p class="auth-error" data-testid="register-error">Invalid invite link.</p>
				<a href="/login">Go to sign in</a>
			{:else if loadState === 'error'}
				<p class="auth-error" data-testid="register-error">{error}</p>
				<a href="/login">Go to sign in</a>
			{:else if loadState === 'ready' || loadState === 'registering'}
				{#if user}
					<p class="welcome-message">Welcome, {user.display_name}</p>
					<p class="role-label">{user.role}</p>
				{/if}

				{#if error}
					<p class="auth-error" data-testid="register-error">{error}</p>
				{/if}

				<Button
					disabled={loadState === 'registering'}
					onclick={handleRegister}
					data-testid="register-submit"
				>
					{loadState === 'registering' ? 'Registering...' : 'Register passkey'}
				</Button>

				<p class="signin-link"><a href="/login">Already registered? Sign in</a></p>
			{/if}
		</PanelCard>
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

	.auth-status {
		color: var(--gray-500);
		font-size: var(--font-size-sm);
		text-align: center;
		margin: 0;
	}

	.welcome-message {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0 0 var(--space-1) 0;
	}

	.role-label {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0 0 var(--space-3) 0;
	}

	.auth-error {
		color: var(--red-700);
		font-size: var(--font-size-sm);
		margin: 0 0 var(--space-3) 0;
	}

	.signin-link {
		text-align: center;
		font-size: var(--font-size-sm);
		margin: var(--space-3) 0 0 0;
	}
</style>
