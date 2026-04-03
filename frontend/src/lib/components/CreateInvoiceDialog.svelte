<script lang="ts">
	import type { RemainingLine, InvoiceLineItemCreate } from '$lib/types';

	let {
		lines,
		onConfirm,
		onCancel
	}: {
		lines: RemainingLine[];
		onConfirm: (lineItems: InvoiceLineItemCreate[]) => void;
		onCancel: () => void;
	} = $props();

	let quantities: number[] = $state(lines.map((l) => l.remaining));

	const allZero = $derived(quantities.every((q) => q === 0));

	function handleConfirm() {
		const lineItems: InvoiceLineItemCreate[] = lines
			.map((l, i) => ({ part_number: l.part_number, quantity: quantities[i] }))
			.filter((item) => item.quantity > 0);
		onConfirm(lineItems);
	}
</script>

<div class="overlay">
	<div class="dialog">
		<h2 class="dialog-title">Create Invoice</h2>
		<div class="table-wrap">
			<table class="table">
				<thead>
					<tr>
						<th>Part Number</th>
						<th>Description</th>
						<th>Ordered</th>
						<th>Invoiced</th>
						<th>Remaining</th>
						<th>Invoice Qty</th>
					</tr>
				</thead>
				<tbody>
					{#each lines as line, i}
						<tr>
							<td>{line.part_number}</td>
							<td>{line.description}</td>
							<td>{line.ordered}</td>
							<td>{line.invoiced}</td>
							<td>{line.remaining}</td>
							<td>
								<input
									class="qty-input"
									type="number"
									min="0"
									max={line.remaining}
									bind:value={quantities[i]}
									disabled={line.remaining === 0}
								/>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<div class="dialog-actions">
			<button class="btn btn-secondary" onclick={onCancel}>Cancel</button>
			<button class="btn btn-primary" onclick={handleConfirm} disabled={allZero}>Create</button>
		</div>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.dialog {
		background-color: white;
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		padding: var(--space-6);
		max-width: 800px;
		width: 100%;
	}

	.dialog-title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin-bottom: var(--space-4);
	}

	.table-wrap {
		overflow-x: auto;
		margin-bottom: var(--space-4);
	}

	.qty-input {
		width: 80px;
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		margin-top: var(--space-4);
	}
</style>
