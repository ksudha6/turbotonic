<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
</script>

<h1>Phase 4.0 UI Demo</h1>

<section>
	<h2>Button</h2>
	<div style="display:flex;gap:1rem;">
		<Button data-testid="ui-btn-primary">Primary</Button>
		<Button variant="secondary" data-testid="ui-btn-secondary">Secondary</Button>
		<Button variant="ghost" data-testid="ui-btn-ghost">Ghost</Button>
		<Button disabled data-testid="ui-btn-disabled">Disabled</Button>
	</div>
</section>
