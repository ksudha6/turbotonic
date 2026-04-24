<script lang="ts">
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
</script>

<AppShell
	role="ADMIN"
	roleLabel="Supply Manager"
	breadcrumb="Workspace / Shell Demo"
	data-testid="ui-appshell"
>
	{#snippet sidebarFooter()}
		<div>
			<strong>Demo workspace</strong>
			<div>Shell preview</div>
		</div>
	{/snippet}
	{#snippet userMenu()}
		<UserMenu name="Supply Manager" role="ADMIN" data-testid="ui-usermenu" />
	{/snippet}
	<p>Shell demo content.</p>
</AppShell>
