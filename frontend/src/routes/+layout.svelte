<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '$lib/styles/global.css';
	import NotificationBell from '$lib/components/NotificationBell.svelte';
	import { page } from '$app/state';
	import { logout } from '$lib/auth';
	import { goto } from '$app/navigation';
	import { canViewPOs, canViewInvoices, canManageVendors, canViewProducts } from '$lib/permissions';

	let { children } = $props();

	const user = $derived(page.data.user);

	// Phase 4.0+ revamp routes own their own chrome (AppShell, Sidebar, TopBar).
	// Pre-revamp root nav + container wrapper would double up and clip the new shell.
	const isRevampRoute = $derived(
		page.url.pathname.startsWith('/ui-demo') ||
			page.url.pathname.startsWith('/_smoke') ||
			page.url.pathname === '/dashboard' ||
			page.url.pathname.startsWith('/dashboard/') ||
			page.url.pathname === '/po' ||
			page.url.pathname.startsWith('/po/') ||
			page.url.pathname === '/invoices' ||
			page.url.pathname.startsWith('/invoice/') ||
			page.url.pathname === '/vendors' ||
			page.url.pathname.startsWith('/vendors/') ||
			page.url.pathname === '/products' ||
			page.url.pathname.startsWith('/products/')
	);


	async function handleLogout() {
		try {
			await logout();
		} catch {
			// proceed even if logout call fails
		}
		goto('/login');
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if user && !isRevampRoute}
	<nav>
		<div class="nav-inner">
			<a href="/" class="nav-brand">Vendor Portal</a>
			<ul class="nav-links">
				<li><a href="/dashboard">Dashboard</a></li>
				{#if canViewPOs(user.role)}
					<li><a href="/po">Purchase Orders</a></li>
				{/if}
				{#if canViewInvoices(user.role)}
					<li><a href="/invoices">Invoices</a></li>
				{/if}
				{#if canManageVendors(user.role)}
					<li><a href="/vendors">Vendors</a></li>
				{/if}
				{#if canViewProducts(user.role)}
					<li><a href="/products">Products</a></li>
				{/if}
			</ul>
			<div class="nav-actions">
				<NotificationBell />
				<span class="user-name">{user.display_name} · {user.role}</span>
				<button class="logout-btn" onclick={handleLogout}>Log out</button>
			</div>
		</div>
	</nav>
{/if}

{#if isRevampRoute}
	{@render children()}
{:else}
	<div class="container">
		{@render children()}
	</div>
{/if}

<style>
	nav {
		background-color: white;
		border-bottom: 1px solid var(--gray-200);
	}

	.nav-inner {
		max-width: 1200px;
		margin-inline: auto;
		padding-inline: var(--space-6);
		height: 3.5rem;
		display: flex;
		align-items: center;
		gap: var(--space-8);
	}

	.nav-brand {
		font-size: var(--font-size-lg);
		font-weight: 700;
		color: var(--gray-900);
		text-decoration: none;
	}

	.nav-brand:hover {
		text-decoration: none;
	}

	.nav-links {
		list-style: none;
		display: flex;
		gap: var(--space-6);
	}

	.nav-links a {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--gray-600);
		text-decoration: none;
	}

	.nav-links a:hover {
		color: var(--gray-900);
	}

	.nav-actions {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.user-name {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
	}

	.logout-btn {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		background: none;
		border: 1px solid var(--gray-300);
		border-radius: 0.25rem;
		padding: var(--space-1) var(--space-3);
		cursor: pointer;
	}

	.logout-btn:hover {
		color: var(--gray-900);
		border-color: var(--gray-400);
	}
</style>
