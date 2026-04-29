<script lang="ts">
	import type { RemainingLine, InvoiceLineItemCreate } from '$lib/types';
	import Button from '$lib/ui/Button.svelte';
	import Input from '$lib/ui/Input.svelte';

	let {
		lines,
		onConfirm,
		onCancel
	}: {
		lines: RemainingLine[];
		onConfirm: (lineItems: InvoiceLineItemCreate[]) => void;
		onCancel: () => void;
	} = $props();

	const titleId = crypto.randomUUID();

	// Phase 4.0 Input is string-only (same as PoForm.LineFormState in iter 085).
	// Default each row to its remaining count so the common "invoice everything"
	// path is one click. Lines with remaining===0 stay at "0" and are disabled.
	let quantities: Record<string, string> = $state(
		Object.fromEntries(lines.map((l) => [l.part_number, String(l.remaining)]))
	);

	function parseQty(v: string): number {
		const n = Number.parseInt(v, 10);
		return Number.isFinite(n) && n > 0 ? n : 0;
	}

	const allZero = $derived(
		lines.every((l) => parseQty(quantities[l.part_number] ?? '0') === 0)
	);

	function handleConfirm() {
		const lineItems: InvoiceLineItemCreate[] = lines
			.map((l) => ({
				part_number: l.part_number,
				quantity: Math.min(parseQty(quantities[l.part_number] ?? '0'), l.remaining)
			}))
			.filter((item) => item.quantity > 0);
		onConfirm(lineItems);
	}
</script>

<div
	class="invoice-create-modal__overlay"
	role="dialog"
	aria-modal="true"
	aria-labelledby={titleId}
	data-testid="invoice-create-modal"
>
	<div class="invoice-create-modal">
		<header class="invoice-create-modal__header">
			<h2 id={titleId} class="invoice-create-modal__title">Create Invoice</h2>
		</header>

		<div class="invoice-create-modal__body">
			<table class="invoice-create-modal__table" data-testid="invoice-create-table">
				<thead>
					<tr>
						<th>Part Number</th>
						<th>Description</th>
						<th class="invoice-create-modal__num">Ordered</th>
						<th class="invoice-create-modal__num">Invoiced</th>
						<th class="invoice-create-modal__num">Remaining</th>
						<th class="invoice-create-modal__num">Invoice Qty</th>
					</tr>
				</thead>
				<tbody>
					{#each lines as line (line.part_number)}
						<tr data-testid={`invoice-create-row-${line.part_number}`}>
							<td>{line.part_number}</td>
							<td>{line.description}</td>
							<td class="invoice-create-modal__num">{line.ordered}</td>
							<td class="invoice-create-modal__num">{line.invoiced}</td>
							<td class="invoice-create-modal__num">{line.remaining}</td>
							<td class="invoice-create-modal__num">
								<Input
									type="number"
									bind:value={quantities[line.part_number]}
									disabled={line.remaining === 0}
									ariaLabel={`Invoice quantity for ${line.part_number}`}
									data-testid={`invoice-create-qty-input-${line.part_number}`}
								/>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>

			<ul class="invoice-create-modal__cards" data-testid="invoice-create-cards">
				{#each lines as line (line.part_number)}
					<li
						class="invoice-create-modal__card"
						data-testid={`invoice-create-row-${line.part_number}`}
					>
						<div class="invoice-create-modal__card-header">
							<span class="invoice-create-modal__card-part">{line.part_number}</span>
							<span class="invoice-create-modal__card-meta">
								{line.invoiced} / {line.ordered} invoiced
							</span>
						</div>
						<p class="invoice-create-modal__card-desc">{line.description}</p>
						<div class="invoice-create-modal__card-row">
							<span class="invoice-create-modal__card-label">Remaining</span>
							<span class="invoice-create-modal__card-value">{line.remaining}</span>
						</div>
						<div class="invoice-create-modal__card-row">
							<span class="invoice-create-modal__card-label">Invoice qty</span>
							<div class="invoice-create-modal__card-input">
								<Input
									type="number"
									bind:value={quantities[line.part_number]}
									disabled={line.remaining === 0}
									ariaLabel={`Invoice quantity for ${line.part_number}`}
									data-testid={`invoice-create-qty-input-${line.part_number}`}
								/>
							</div>
						</div>
					</li>
				{/each}
			</ul>
		</div>

		<footer class="invoice-create-modal__footer">
			<Button
				variant="secondary"
				onclick={onCancel}
				data-testid="invoice-create-cancel"
			>
				Cancel
			</Button>
			<Button
				variant="primary"
				onclick={handleConfirm}
				disabled={allZero}
				data-testid="invoice-create-confirm"
			>
				Create
			</Button>
		</footer>
	</div>
</div>

<style>
	.invoice-create-modal__overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4);
		z-index: 100;
	}
	.invoice-create-modal {
		background-color: var(--surface-card);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-xl);
		max-width: 50rem;
		width: 100%;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
	}
	.invoice-create-modal__header {
		padding: var(--space-6) var(--space-6) var(--space-2);
	}
	.invoice-create-modal__title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin: 0;
		color: var(--gray-900);
	}
	.invoice-create-modal__body {
		padding: var(--space-2) var(--space-6) var(--space-4);
		overflow-y: auto;
	}

	.invoice-create-modal__table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--font-size-sm);
	}
	.invoice-create-modal__table thead th {
		text-align: left;
		padding: var(--space-2) var(--space-3);
		font-weight: 600;
		color: var(--gray-700);
		border-bottom: 1px solid var(--gray-200);
	}
	.invoice-create-modal__table tbody td {
		padding: var(--space-2) var(--space-3);
		color: var(--gray-900);
		border-bottom: 1px solid var(--gray-100);
		vertical-align: middle;
	}
	.invoice-create-modal__num { text-align: right; }
	.invoice-create-modal__num :global(.ui-input) { max-width: 6rem; margin-left: auto; }

	.invoice-create-modal__cards { display: none; list-style: none; padding: 0; margin: 0; }
	.invoice-create-modal__card {
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		padding: var(--space-3);
		margin-bottom: var(--space-3);
		background-color: var(--surface-card);
	}
	.invoice-create-modal__card-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--space-2);
		margin-bottom: var(--space-1);
	}
	.invoice-create-modal__card-part {
		font-weight: 600;
		color: var(--gray-900);
	}
	.invoice-create-modal__card-meta {
		font-size: var(--font-size-xs);
		color: var(--gray-600);
	}
	.invoice-create-modal__card-desc {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0 0 var(--space-2);
	}
	.invoice-create-modal__card-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-1) 0;
	}
	.invoice-create-modal__card-label {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.invoice-create-modal__card-value {
		font-size: var(--font-size-sm);
		color: var(--gray-900);
	}
	.invoice-create-modal__card-input { flex: 1; max-width: 8rem; }

	.invoice-create-modal__footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		border-top: 1px solid var(--gray-100);
	}

	@media (max-width: 767px) {
		.invoice-create-modal__table { display: none; }
		.invoice-create-modal__cards { display: block; }
	}
</style>
