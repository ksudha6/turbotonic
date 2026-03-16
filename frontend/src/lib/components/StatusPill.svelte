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
			default:
				return 'badge badge-draft';
		}
	}

	function displayText(s: string): string {
		return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
	}
</script>

<span class={badgeClass(status)}>{displayText(status)}</span>
