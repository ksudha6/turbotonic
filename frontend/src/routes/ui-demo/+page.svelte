<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
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

<section>
	<h2>StatusPill</h2>
	<div style="display:flex;gap:1rem;flex-wrap:wrap;">
		<StatusPill tone="green" label="Delivered" data-testid="ui-pill-green" />
		<StatusPill tone="blue" label="In Transit" data-testid="ui-pill-blue" />
		<StatusPill tone="orange" label="In Production" data-testid="ui-pill-orange" />
		<StatusPill tone="red" label="Overdue" data-testid="ui-pill-red" />
		<StatusPill tone="gray" label="Draft" data-testid="ui-pill-gray" />
	</div>
</section>
