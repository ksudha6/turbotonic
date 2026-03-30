<script lang="ts">
	let { status }: { status: string } = $props();

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
</script>

<span class={badgeClass(status)}>{displayText(status)}</span>

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
</style>
