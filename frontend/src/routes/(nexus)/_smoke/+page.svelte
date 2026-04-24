<script lang="ts">
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import { page } from '$app/state';
	import type { UserRole } from '$lib/types';

	const user = $derived(page.data.user);
	const role = $derived((user?.role as UserRole | undefined) ?? 'ADMIN');
	const name = $derived(user?.display_name ?? user?.username ?? 'Guest');

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};
	const roleLabel = $derived(ROLE_LABEL[role]);
</script>

<svelte:head>
	<title>Nexus smoke</title>
</svelte:head>

<AppShell {role} {roleLabel} breadcrumb="Smoke" data-testid="smoke-shell">
	{#snippet userMenu()}
		<UserMenu {name} {role} data-testid="smoke-usermenu" />
	{/snippet}
	<h1>Nexus smoke</h1>
</AppShell>
