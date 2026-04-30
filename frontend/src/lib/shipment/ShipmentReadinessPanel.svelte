<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import { labelForDocumentType } from './document-type-labels';
	import type { ReadinessResult } from '$lib/types';

	let {
		readiness,
		productLookup,
		loading,
		error
	}: {
		readiness: ReadinessResult;
		productLookup: Map<string, { part_number: string; description: string }>;
		loading: boolean;
		error: string | null;
	} = $props();

	function partNumber(productId: string): string {
		return productLookup.get(productId)?.part_number ?? productId;
	}
</script>

{#snippet overallPill()}
	{#if readiness?.is_ready}
		<StatusPill tone="green" label="Ready to ship" data-testid="shipment-readiness-overall" />
	{:else}
		<StatusPill tone="red" label="Not ready" data-testid="shipment-readiness-overall" />
	{/if}
{/snippet}

<PanelCard title="Readiness" data-testid="shipment-readiness-panel" action={overallPill}>
	{#if loading}
		<LoadingState />
	{:else if error !== null}
		<p class="error">{error}</p>
	{:else}
		<section data-testid="shipment-readiness-documents">
			<header class="section-header">
				<h4>Documents</h4>
				<StatusPill
					tone={readiness.documents_ready ? 'green' : 'red'}
					label={readiness.documents_ready ? 'Ready' : 'Missing'}
				/>
			</header>
			{#if !readiness.documents_ready}
				<ul>
					{#each readiness.missing_documents as t}
						<li data-testid="shipment-readiness-missing-document-{t}">{labelForDocumentType(t)}</li>
					{/each}
				</ul>
			{/if}
		</section>

		<section data-testid="shipment-readiness-certificates">
			<header class="section-header">
				<h4>Certificates</h4>
				<StatusPill
					tone={readiness.certificates_ready ? 'green' : 'red'}
					label={readiness.certificates_ready ? 'Ready' : 'Missing'}
				/>
			</header>
			{#if !readiness.certificates_ready}
				<ul>
					{#each readiness.missing_certificates as item}
						<li
							data-testid="shipment-readiness-missing-cert-{item.product_id}-{item.qualification_type}"
						>
							{partNumber(item.product_id)} — {item.qualification_type}
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		<section data-testid="shipment-readiness-packaging">
			<header class="section-header">
				<h4>Packaging</h4>
				<StatusPill
					tone={readiness.packaging_ready ? 'green' : 'red'}
					label={readiness.packaging_ready ? 'Ready' : 'Missing'}
				/>
			</header>
			{#if !readiness.packaging_ready}
				<ul>
					{#each readiness.missing_packaging as item}
						<li data-testid="shipment-readiness-missing-packaging-{item.product_id}">
							{partNumber(item.product_id)} — {item.marketplace}
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}
</PanelCard>

<style>
	.section-header {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: var(--space-2);
	}
	h4 {
		font-size: var(--font-size-sm);
		font-weight: 600;
		margin: 0;
	}
	ul {
		margin: 0 0 var(--space-2) var(--space-4);
		padding: 0;
		list-style: disc;
	}
	li {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		padding: var(--space-1) 0;
	}
	.error {
		color: var(--red-600, #dc2626);
		font-size: var(--font-size-sm);
		margin: 0;
	}
</style>
