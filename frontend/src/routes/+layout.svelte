<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '$lib/styles/global.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<nav>
	<div class="nav-inner">
		<a href="/" class="nav-brand">Vendor Portal</a>
		<ul class="nav-links">
			<li><a href="/po">Purchase Orders</a></li>
		</ul>
	</div>
</nav>

<div class="container">
	{@render children()}
</div>

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
</style>
