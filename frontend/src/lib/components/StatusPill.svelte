<script lang="ts">
	// `status` is the raw backend status. `label` optionally overrides the pill
	// text (used for synthetic pills like "Partial" that aren't a distinct status).
	let { status, label }: { status: string; label?: string } = $props();

	function badgeClass(s: string): string {
		switch (s) {
			case 'DRAFT':
				return 'badge badge-draft';
			case 'PENDING':
				return 'badge badge-pending';
			case 'ACCEPTED':
				return 'badge badge-accepted';
			case 'REJECTED':
				return 'badge badge-rejected';
			case 'REVISED':
				return 'badge badge-revised';
			// Iter 058: MODIFIED is the in-flight negotiation status. "Partial" is a
			// synthetic label on top of ACCEPTED and reuses a warning palette.
			case 'MODIFIED':
				return 'badge badge-modified';
			case 'PARTIAL':
				return 'badge badge-partial';
			case 'SUBMITTED':
				return 'badge badge-submitted';
			case 'APPROVED':
				return 'badge badge-approved';
			case 'PAID':
				return 'badge badge-paid';
			case 'DISPUTED':
				return 'badge badge-disputed';
			default:
				return 'badge badge-draft';
		}
	}

	function displayText(s: string): string {
		return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
	}

	const pillText = $derived(label ?? displayText(status));
	const pillClass = $derived(badgeClass(label === 'Partial' ? 'PARTIAL' : status));
</script>

<span class={pillClass}>{pillText}</span>

<style>
	:global(.badge-submitted) {
		background-color: var(--blue-100);
		color: var(--blue-800);
	}

	:global(.badge-approved) {
		background-color: var(--green-100);
		color: var(--green-800);
	}

	:global(.badge-paid) {
		background-color: var(--green-100);
		color: var(--green-700);
		font-weight: 600;
	}

	:global(.badge-disputed) {
		background-color: var(--red-100);
		color: var(--red-800);
	}

	:global(.badge-modified) {
		background-color: var(--blue-100);
		color: var(--blue-800);
	}

	:global(.badge-partial) {
		background-color: var(--amber-100, #fef3c7);
		color: var(--amber-800, #92400e);
	}
</style>
