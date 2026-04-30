<script lang="ts">
	import Button from '$lib/ui/Button.svelte';

	let {
		caption,
		token,
		onDismiss
	}: {
		caption: string;
		token: string;
		onDismiss: () => void;
	} = $props();

	const labelId = crypto.randomUUID();

	const url = $derived(
		typeof window !== 'undefined' ? `${window.location.origin}/register?token=${token}` : `/register?token=${token}`
	);

	let copied: boolean = $state(false);

	async function handleCopy() {
		try {
			await navigator.clipboard.writeText(url);
			copied = true;
			setTimeout(() => {
				copied = false;
			}, 2000);
		} catch {
			// Clipboard API failure is rare; the URL is visible for manual copy.
		}
	}
</script>

<section
	class="invite-link-panel"
	aria-labelledby={labelId}
	data-testid="invite-link-panel"
>
	<header class="invite-link-panel__header">
		<h3 id={labelId} class="invite-link-panel__caption">{caption}</h3>
		<Button variant="ghost" onclick={onDismiss} data-testid="invite-link-dismiss">
			Dismiss
		</Button>
	</header>
	<div class="invite-link-panel__row">
		<code class="invite-link-panel__url" data-testid="invite-link-url">{url}</code>
		<Button variant="primary" onclick={handleCopy} data-testid="invite-link-copy">
			{copied ? 'Copied' : 'Copy link'}
		</Button>
	</div>
</section>

<style>
	.invite-link-panel {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-4);
		background-color: #ecfeff;
		border: 1px solid #67e8f9;
		border-radius: var(--radius-md);
	}
	.invite-link-panel__header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
	}
	.invite-link-panel__caption {
		font-size: var(--font-size-base);
		font-weight: 600;
		margin: 0;
		color: var(--gray-900);
	}
	.invite-link-panel__row {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.invite-link-panel__url {
		display: block;
		padding: var(--space-2) var(--space-3);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		font-family: var(--font-family-mono, monospace);
		font-size: var(--font-size-sm);
		color: var(--gray-900);
		word-break: break-all;
	}
	@media (min-width: 768px) {
		.invite-link-panel__row {
			flex-direction: row;
			align-items: center;
		}
		.invite-link-panel__url {
			flex: 1;
		}
	}
</style>
