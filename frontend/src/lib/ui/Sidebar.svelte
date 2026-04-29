<script lang="ts">
	import type { UserRole } from '$lib/types';
	import { sidebarItemsFor } from './sidebar-items';
	import { page } from '$app/state';

	let {
		role,
		brand = 'Turbo Tonic',
		roleLabel,
		footer,
		'data-testid': testid
	}: {
		role: UserRole;
		brand?: string;
		roleLabel?: string;
		footer?: import('svelte').Snippet;
		'data-testid'?: string;
	} = $props();

	const sections = $derived(sidebarItemsFor(role));
	const pathname = $derived(page.url.pathname);
	const displayRole = $derived(roleLabel ?? role);

	// Stable per-section ids for aria-labelledby; generated once at component init.
	const sectionIds = $derived(sections.map(() => crypto.randomUUID()));
</script>

<aside class="ui-sidebar" data-testid={testid} aria-label="Primary navigation">
	<div class="brand">
		<span class="brand-mark" aria-hidden="true"></span>
		<span class="brand-text">
			<span class="brand-name">{brand}</span>
			<span class="brand-role">{displayRole}</span>
		</span>
	</div>
	<nav>
		{#each sections as section, i (section.label)}
			<div class="section">
				<span class="section-label" id={sectionIds[i]}>{section.label}</span>
				<ul aria-labelledby={sectionIds[i]}>
					{#each section.items as item (item.href)}
						{@const isActive = item.match(pathname)}
						<li>
							<a
								href={item.href}
								aria-current={isActive ? 'page' : undefined}
								class:active={isActive}
							>
								{item.label}
							</a>
						</li>
					{/each}
				</ul>
			</div>
		{/each}
	</nav>
	{#if footer}
		<div class="footer" data-testid="{testid}-footer">{@render footer()}</div>
	{/if}
</aside>

<style>
	.ui-sidebar {
		width: 240px;
		height: 100%;
		background-color: var(--surface-sidebar);
		color: var(--text-sidebar);
		padding: var(--space-6);
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
		box-sizing: border-box;
	}
	.brand {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	.brand-mark {
		width: 2rem;
		height: 2rem;
		border-radius: var(--radius-md);
		background-color: var(--brand-accent);
	}
	.brand-text {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.brand-name {
		font-weight: 600;
		font-size: var(--font-size-sm);
	}
	.brand-role {
		font-size: var(--font-size-xs);
		color: var(--text-sidebar-muted);
	}
	nav {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}
	.section {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.section-label {
		font-size: var(--font-size-xs);
		font-weight: 600;
		letter-spacing: var(--letter-spacing-wide);
		text-transform: uppercase;
		color: var(--text-sidebar-muted);
	}
	nav ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	a {
		display: block;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		color: var(--text-sidebar-muted);
		text-decoration: none;
		border-radius: var(--radius-md);
	}
	a:hover { color: var(--text-sidebar); background-color: rgba(255, 255, 255, 0.05); }
	a.active { color: var(--text-sidebar); background-color: rgba(255, 255, 255, 0.08); }
	a:focus-visible { outline: 2px solid var(--brand-accent); outline-offset: 2px; }
	.footer {
		margin-top: auto;
		padding-top: var(--space-4);
		border-top: 1px solid rgba(255, 255, 255, 0.08);
		font-size: var(--font-size-xs);
		color: var(--text-sidebar-muted);
	}
</style>
