<script lang="ts">
	import AppShell from '$lib/ui/AppShell.svelte';
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
	<p>Shell demo content.</p>
</AppShell>
