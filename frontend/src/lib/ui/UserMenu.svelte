<script lang="ts">
	import { logout } from '$lib/auth';
	import { goto } from '$app/navigation';
	import type { UserRole } from '$lib/types';

	let {
		name,
		role,
		ariaLabel = 'Open user menu',
		'data-testid': testid
	}: {
		name: string;
		role: UserRole;
		ariaLabel?: string;
		'data-testid'?: string;
	} = $props();

	let open = $state(false);

	async function handleLogout() {
		try {
			await logout();
		} catch {
			// Swallow network/API errors so logout always redirects the user out.
		}
		goto('/login');
	}

	function toggle() {
		open = !open;
	}

	function initials(n: string) {
		return n
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((s) => s[0]?.toUpperCase() ?? '')
			.join('');
	}
</script>

<div class="ui-user-menu">
	<button
		type="button"
		class="pill"
		onclick={toggle}
		aria-haspopup="menu"
		aria-expanded={open}
		aria-label={ariaLabel}
		data-testid={testid}
	>
		<span class="avatar" aria-hidden="true">{initials(name)}</span>
		<span class="meta">
			<span class="name">{name}</span>
			<span class="role">{role}</span>
		</span>
		<span class="chevron" aria-hidden="true">▾</span>
	</button>
	{#if open}
		<div class="menu" role="menu" aria-label="Account actions">
			{#if import.meta.env.DEV}
				<button
					type="button"
					role="menuitem"
					class="item dev"
					disabled
					data-testid="{testid}-switch-role"
					title="Dev-only role switcher (wiring deferred)"
				>
					Switch role (dev)
				</button>
			{/if}
			<button
				type="button"
				role="menuitem"
				class="item"
				onclick={handleLogout}
				data-testid="{testid}-logout"
			>
				Log out
			</button>
		</div>
	{/if}
</div>

<style>
	.ui-user-menu { position: relative; }
	.pill {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-2);
		background: none;
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		cursor: pointer;
		font-family: inherit;
		color: inherit;
	}
	.pill:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 2px;
	}
	.avatar {
		width: 1.75rem;
		height: 1.75rem;
		border-radius: var(--radius-sm);
		background-color: var(--button-solid-bg);
		color: var(--button-solid-fg);
		font-size: var(--font-size-xs);
		font-weight: 600;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.meta {
		display: flex;
		flex-direction: column;
		text-align: left;
		min-width: 0;
	}
	.name {
		font-size: var(--font-size-sm);
		color: var(--gray-900);
		white-space: nowrap;
	}
	.role {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
	}
	.chevron {
		font-size: var(--font-size-xs);
		color: var(--gray-500);
	}
	.menu {
		position: absolute;
		right: 0;
		top: calc(100% + 0.5rem);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-md);
		padding: var(--space-2);
		min-width: 12rem;
		z-index: 30;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.item {
		width: 100%;
		text-align: left;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		font-family: inherit;
		color: inherit;
	}
	.item:hover:not(:disabled) { background-color: var(--gray-100); }
	.item:focus-visible { outline: 2px solid var(--brand-accent); outline-offset: -2px; }
	.item.dev {
		color: var(--gray-500);
		font-style: italic;
	}
	.item:disabled {
		cursor: not-allowed;
	}
	@media (max-width: 767px) {
		.meta { display: none; }
	}
</style>
