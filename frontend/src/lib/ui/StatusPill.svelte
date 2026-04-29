<!-- Status text is the implicit accessible name; query via getByText. -->
<script lang="ts">
	type Tone = 'green' | 'blue' | 'orange' | 'red' | 'gray';
	let {
		tone = 'gray',
		label,
		'data-testid': testid
	}: { tone?: Tone; label: string; 'data-testid'?: string } = $props();
</script>

<span class="ui-pill {tone}" data-testid={testid}>
	<span class="dot" aria-hidden="true"></span>
	{label}
</span>

<style>
	.ui-pill {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-xs);
		font-weight: 500;
		border-radius: 999px;
		background-color: var(--gray-100);
		color: var(--gray-700);
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 999px;
		background-color: var(--dot-gray);
	}
	.green { background-color: #dcfce7; color: #166534; }
	.green .dot { background-color: var(--dot-green); }
	.blue { background-color: #dbeafe; color: #1e40af; }
	.blue .dot { background-color: var(--dot-blue); }
	.orange { background-color: #fef3c7; color: #92400e; }
	.orange .dot { background-color: var(--dot-orange); }
	.red { background-color: #fee2e2; color: #991b1b; }
	.red .dot { background-color: var(--dot-red); }
	.gray { background-color: #f3f4f6; color: #374151; }
	.gray .dot { background-color: var(--dot-gray); }
</style>
