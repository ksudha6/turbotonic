<script lang="ts">
	import type { UserRole } from '$lib/types';
	import Sidebar from './Sidebar.svelte';
	import TopBar from './TopBar.svelte';
	import ErrorBoundary from './ErrorBoundary.svelte';

	let {
		role,
		roleLabel,
		breadcrumb,
		userMenu,
		sidebarFooter,
		children,
		'data-testid': testid
	}: {
		role: UserRole;
		roleLabel?: string;
		breadcrumb?: string;
		userMenu?: import('svelte').Snippet;
		sidebarFooter?: import('svelte').Snippet;
		children: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();

	let sidebarOpen = $state(false);

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function closeSidebar() {
		sidebarOpen = false;
	}
</script>

<div class="ui-appshell" data-testid={testid}>
	<div
		class="sidebar-wrap"
		class:open={sidebarOpen}
		data-testid="ui-appshell-sidebar"
	>
		<Sidebar
			{role}
			{roleLabel}
			footer={sidebarFooter}
		/>
	</div>
	{#if sidebarOpen}
		<button
			type="button"
			class="overlay"
			aria-label="Close sidebar"
			onclick={closeSidebar}
			data-testid="ui-appshell-overlay"
		></button>
	{/if}
	<div class="main-col">
		<TopBar
			{breadcrumb}
			{userMenu}
			onToggleSidebar={toggleSidebar}
			data-testid="ui-appshell-topbar"
		/>
		<main data-testid="ui-appshell-main">
			<ErrorBoundary>
				{@render children()}
			</ErrorBoundary>
		</main>
	</div>
</div>

<style>
	.ui-appshell {
		display: grid;
		grid-template-columns: 240px 1fr;
		min-height: 100vh;
		background-color: var(--surface-page);
	}
	.main-col {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	main {
		flex: 1;
		padding: var(--space-6);
	}
	.overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.35);
		border: none;
		cursor: pointer;
		z-index: 40;
	}
	@media (min-width: 769px) {
		.overlay {
			display: none;
		}
	}
	@media (max-width: 768px) {
		.ui-appshell {
			grid-template-columns: 1fr;
		}
		.sidebar-wrap {
			position: fixed;
			top: 0;
			bottom: 0;
			left: 0;
			width: min(280px, 70vw);
			z-index: 50;
			transform: translateX(-100%);
			transition: transform 0.2s ease;
			visibility: hidden;
		}
		.sidebar-wrap.open {
			transform: translateX(0);
			visibility: visible;
		}
	}
</style>
