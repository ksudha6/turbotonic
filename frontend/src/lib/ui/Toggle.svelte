<script lang="ts">
	let {
		pressed = $bindable(false),
		disabled = false,
		label,
		'data-testid': testid
	}: {
		pressed?: boolean;
		disabled?: boolean;
		label?: string;
		'data-testid'?: string;
	} = $props();

	function toggle() {
		if (!disabled) pressed = !pressed;
	}
</script>

<button
	class="ui-toggle"
	type="button"
	aria-pressed={pressed}
	aria-label={label}
	{disabled}
	onclick={toggle}
	data-testid={testid}
	class:on={pressed}
>
	<span class="knob"></span>
</button>

<style>
	.ui-toggle {
		position: relative;
		width: 2.5rem;
		height: 1.375rem;
		border-radius: 999px;
		border: 1px solid var(--gray-300);
		background-color: var(--gray-200);
		cursor: pointer;
		padding: 0;
		transition: background-color 0.15s;
	}
	.ui-toggle:focus-visible {
		outline: 2px solid var(--brand-accent);
		outline-offset: 2px;
	}
	.ui-toggle:disabled { opacity: 0.5; cursor: not-allowed; }
	.ui-toggle.on { background-color: var(--button-solid-bg); border-color: var(--button-solid-bg); }
	.knob {
		display: block;
		width: 1rem;
		height: 1rem;
		margin: 1px;
		border-radius: 999px;
		background-color: var(--surface-card);
		transform: translateX(0);
		transition: transform 0.15s;
	}
	.ui-toggle.on .knob { transform: translateX(calc(2.5rem - 1rem - 4px)); }
</style>
