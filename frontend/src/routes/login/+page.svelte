<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { devLogin, getDevUsers, loginOptions, loginVerify, type DevUser } from '$lib/auth';
	import { startAuthentication } from '$lib/webauthn';
	import Button from '$lib/ui/Button.svelte';

	let username = $state('');
	let error = $state('');
	let loading = $state(false);
	// null = dev surface disabled (404 from /dev-users); array = render quick-login row.
	let devUsers = $state<DevUser[] | null>(null);
	// Flips true once a login flow has captured a redirect target. The auto-
	// redirect $effect must not re-route to /dashboard once the explicit
	// post-login redirect is already in flight, otherwise the dev-login flow
	// races itself on the redirect query param.
	let redirecting = $state(false);

	// Redirect immediately if already authenticated
	$effect(() => {
		if (page.data.user && !redirecting) {
			goto('/dashboard');
		}
	});

	onMount(async () => {
		devUsers = await getDevUsers();
	});

	function postLoginRedirect(): Promise<void> {
		// Snapshot the redirect target before navigation so a layout load that
		// resolves the user mid-flight cannot trip the auto-redirect $effect
		// over the explicit redirect we picked here.
		redirecting = true;
		const redirect = page.url.searchParams.get('redirect');
		if (redirect && redirect.startsWith('/')) {
			return goto(redirect);
		}
		return goto('/dashboard');
	}

	async function handleDevLogin(devUsername: string) {
		error = '';
		loading = true;
		try {
			await devLogin(devUsername);
			await postLoginRedirect();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Dev login failed.';
		} finally {
			loading = false;
		}
	}

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = '';

		if (!window.PublicKeyCredential) {
			error = 'WebAuthn is not supported in this browser';
			return;
		}

		loading = true;
		try {
			const { options } = await loginOptions(username);
			let credential;
			try {
				credential = await startAuthentication(options);
			} catch (e: unknown) {
				if (e instanceof Error && e.name === 'NotAllowedError') {
					error = 'Authentication was cancelled. Try again.';
				} else {
					error = 'No passkeys found on this device.';
				}
				return;
			}

			await loginVerify(username, credential);
			await postLoginRedirect();
		} catch (e: unknown) {
			if (e instanceof Error) {
				error = e.message;
			} else {
				error = 'An unexpected error occurred.';
			}
		} finally {
			loading = false;
		}
	}
</script>

<div class="page">
	<div class="card login-card">
		<h1>Vendor Portal</h1>
		<p class="subtitle">Sign in to your account</p>

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

			{#if error}
				<p class="error-message">{error}</p>
			{/if}

			<button type="submit" class="btn btn-primary btn-full" disabled={loading}>
				{loading ? 'Logging in...' : 'Log in'}
			</button>
		</form>

		{#if devUsers}
			<div class="dev-login-row" data-testid="dev-login-row">
				<p class="dev-login-label">Dev quick-login</p>
				<div class="dev-login-buttons">
					{#each devUsers as devUser (devUser.username)}
						<Button
							variant="secondary"
							disabled={loading}
							onclick={() => handleDevLogin(devUser.username)}
							data-testid={`dev-login-${devUser.username}`}
						>
							{devUser.display_name} ({devUser.role})
						</Button>
					{/each}
				</div>
			</div>
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

	.login-card {
		width: 100%;
		max-width: 400px;
	}

	.login-card h1 {
		text-align: center;
		margin-bottom: var(--space-2);
	}

	.subtitle {
		text-align: center;
		color: var(--gray-500);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-8);
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

	.dev-login-row {
		margin-top: var(--space-6);
		padding-top: var(--space-4);
		border-top: 1px solid var(--gray-200);
	}

	.dev-login-label {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-bottom: var(--space-2);
	}

	.dev-login-buttons {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}
</style>
