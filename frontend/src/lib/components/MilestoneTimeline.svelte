<script lang="ts">
	import type { MilestoneUpdate, ProductionMilestone } from '$lib/types';

	interface Props {
		milestones: MilestoneUpdate[];
		onPost: ((milestone: string) => Promise<void>) | null;
	}

	const { milestones, onPost }: Props = $props();

	const ALL_MILESTONES: { value: ProductionMilestone; label: string }[] = [
		{ value: 'RAW_MATERIALS', label: 'Raw Materials' },
		{ value: 'PRODUCTION_STARTED', label: 'Production Started' },
		{ value: 'QC_PASSED', label: 'QC Passed' },
		{ value: 'READY_TO_SHIP', label: 'Ready to Ship' },
		{ value: 'SHIPPED', label: 'Shipped' },
	];

	function isPosted(value: ProductionMilestone): boolean {
		return milestones.some((m) => m.milestone === value);
	}

	function getPostedAt(value: ProductionMilestone): string | null {
		const m = milestones.find((m) => m.milestone === value);
		return m ? new Date(m.posted_at).toLocaleDateString() : null;
	}

	// Index of the last posted milestone (-1 if none posted)
	const lastPostedIndex = $derived(
		ALL_MILESTONES.reduce((acc, ms, i) => (isPosted(ms.value) ? i : acc), -1)
	);

	// Next milestone to post (undefined if all done)
	const nextMilestone = $derived(
		lastPostedIndex < ALL_MILESTONES.length - 1
			? ALL_MILESTONES[lastPostedIndex + 1]
			: undefined
	);

	let posting = $state(false);

	async function handlePost() {
		if (!nextMilestone || !onPost) return;
		posting = true;
		try {
			await onPost(nextMilestone.value);
		} finally {
			posting = false;
		}
	}
</script>

<div class="timeline-wrapper">
	<div class="timeline">
		{#each ALL_MILESTONES as ms, i}
			{@const posted = isPosted(ms.value)}
			{@const isCurrent = i === lastPostedIndex}
			{@const postedAt = getPostedAt(ms.value)}
			<div class="step">
				{#if i > 0}
					<div class="connector {posted ? 'connector-done' : ''}"></div>
				{/if}
				<div class="indicator {posted ? (isCurrent ? 'indicator-current' : 'indicator-done') : 'indicator-future'}">
					{#if posted}
						<span class="checkmark">✓</span>
					{:else}
						<span class="step-number">{i + 1}</span>
					{/if}
				</div>
				<div class="step-label {posted ? 'label-done' : 'label-future'}">{ms.label}</div>
				{#if postedAt}
					<div class="step-date">{postedAt}</div>
				{/if}
			</div>
		{/each}
	</div>

	{#if nextMilestone && onPost}
		<div class="post-action">
			<button class="btn btn-primary" onclick={handlePost} disabled={posting}>
				{posting ? 'Posting...' : `Mark ${nextMilestone.label}`}
			</button>
		</div>
	{/if}
</div>

<style>
	.timeline-wrapper {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.timeline {
		display: flex;
		align-items: flex-start;
		gap: 0;
	}

	.step {
		display: flex;
		flex-direction: column;
		align-items: center;
		flex: 1;
		position: relative;
		min-width: 0;
	}

	.connector {
		position: absolute;
		top: 1rem;
		right: 50%;
		width: 100%;
		height: 2px;
		background-color: var(--gray-300);
		transform: translateY(-50%);
		z-index: 0;
	}

	.connector-done {
		background-color: var(--blue-600);
	}

	.indicator {
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: var(--font-size-sm);
		font-weight: 600;
		position: relative;
		z-index: 1;
	}

	.indicator-done {
		background-color: var(--blue-600);
		color: var(--white);
	}

	.indicator-current {
		background-color: var(--blue-600);
		color: var(--white);
		box-shadow: 0 0 0 3px var(--blue-100);
	}

	.indicator-future {
		background-color: var(--white);
		color: var(--gray-400);
		border: 2px solid var(--gray-300);
	}

	.checkmark {
		font-size: var(--font-size-base);
	}

	.step-number {
		font-size: var(--font-size-sm);
	}

	.step-label {
		margin-top: var(--space-2);
		font-size: var(--font-size-sm);
		font-weight: 500;
		text-align: center;
		line-height: 1.3;
		padding-inline: var(--space-1);
	}

	.label-done {
		color: var(--gray-800);
	}

	.label-future {
		color: var(--gray-400);
	}

	.step-date {
		margin-top: var(--space-1);
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		text-align: center;
	}

	.post-action {
		display: flex;
	}
</style>
