<script lang="ts">
	import NotificationBell from '$lib/components/NotificationBell.svelte';

	let {
		breadcrumb,
		userMenu,
		onToggleSidebar,
		'data-testid': testid
	}: {
		breadcrumb?: string;
		userMenu?: import('svelte').Snippet;
		onToggleSidebar?: () => void;
		'data-testid'?: string;
	} = $props();
</script>

<header class="ui-topbar" data-testid={testid}>
	{#if onToggleSidebar}
		<button
			type="button"
			class="toggle"
			aria-label="Toggle sidebar"
			onclick={onToggleSidebar}
			data-testid="topbar-toggle"
		>
			<span aria-hidden="true">≡</span>
		</button>
	{/if}
	{#if breadcrumb}
		<span class="breadcrumb">{breadcrumb}</span>
	{/if}
	<div class="actions">
		<NotificationBell />
		{#if userMenu}{@render userMenu()}{/if}
	</div>
</header>

<style>
	.ui-topbar {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		padding: var(--space-3) var(--space-6);
		background-color: var(--surface-card);
		border-bottom: 1px solid var(--gray-200);
	}
	.toggle {
		background: none;
		border: 1px solid var(--gray-300);
		border-radius: var(--radius-md);
		padding: var(--space-1) var(--space-3);
		cursor: pointer;
		font-size: var(--font-size-lg);
		font-family: inherit;
		color: inherit;
	}
	.toggle:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 2px;
	}
	.breadcrumb {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}
	.actions {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	@media (max-width: 767px) {
		.breadcrumb {
			display: none;
		}
	}
</style>
