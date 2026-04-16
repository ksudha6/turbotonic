<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { loginOptions, loginVerify } from '$lib/auth';
	import { startAuthentication } from '$lib/webauthn';

	let username = $state('');
	let error = $state('');
	let loading = $state(false);

	// Redirect immediately if already authenticated
	$effect(() => {
		if (page.data.user) {
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

			const redirect = page.url.searchParams.get('redirect');
			if (redirect && redirect.startsWith('/')) {
				await goto(redirect);
			} else {
				await goto('/dashboard');
			}
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
</style>
