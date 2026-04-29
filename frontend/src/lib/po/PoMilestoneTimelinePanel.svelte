<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import Timeline from '$lib/ui/Timeline.svelte';
	import Button from '$lib/ui/Button.svelte';
	import {
		MILESTONE_ORDER,
		MILESTONE_LABELS,
		type MilestoneResponse,
		type ProductionMilestone,
		type UserRole
	} from '$lib/types';
	import { canPostMilestone } from '$lib/permissions';

	let {
		milestones,
		role,
		onPost = null,
		'data-testid': testid
	}: {
		milestones: MilestoneResponse[];
		role: UserRole | null;
		onPost?: ((milestone: ProductionMilestone) => Promise<void>) | null;
		'data-testid'?: string;
	} = $props();

	type StepState = 'done' | 'current' | 'upcoming' | 'overdue';

	function findPosted(value: ProductionMilestone): MilestoneResponse | undefined {
		return milestones.find((m) => m.milestone === value);
	}

	function formatPostedDate(posted_at: string): string {
		return new Date(posted_at).toLocaleDateString();
	}

	const lastPostedIndex = $derived(
		MILESTONE_ORDER.reduce(
			(acc, m, i) => (findPosted(m) ? i : acc),
			-1
		)
	);

	// Next expected milestone is undefined when all 5 are posted (terminal).
	const nextExpected = $derived(
		lastPostedIndex < MILESTONE_ORDER.length - 1
			? MILESTONE_ORDER[lastPostedIndex + 1]
			: undefined
	);

	const steps = $derived(
		MILESTONE_ORDER.map((m) => {
			const posted = findPosted(m);
			let state: StepState;
			let detail: string | undefined;
			if (posted) {
				if (posted.is_overdue) {
					state = 'overdue';
					detail =
						posted.days_overdue != null
							? `Overdue ${posted.days_overdue}d`
							: 'Overdue';
				} else {
					state = 'done';
					detail = formatPostedDate(posted.posted_at);
				}
			} else if (m === nextExpected) {
				state = 'current';
			} else {
				state = 'upcoming';
			}
			return { label: MILESTONE_LABELS[m], state, detail };
		})
	);

	const showPostButton = $derived(
		onPost != null && role != null && canPostMilestone(role) && nextExpected != null
	);

	let posting: boolean = $state(false);

	async function handlePost(): Promise<void> {
		if (!onPost || !nextExpected) return;
		posting = true;
		try {
			await onPost(nextExpected);
		} finally {
			posting = false;
		}
	}
</script>

<PanelCard title="Production Status" data-testid={testid ?? 'po-milestone-timeline'}>
	{#snippet children()}
		<Timeline steps={steps as Array<{ label: string; state: StepState; detail?: string }>} label="Production milestones" />
		{#if showPostButton && nextExpected}
			<div class="ui-po-milestone-timeline-panel__action">
				<Button
					onclick={handlePost}
					disabled={posting}
					data-testid="po-post-next-milestone-btn"
				>
					{posting ? 'Posting…' : `Post ${MILESTONE_LABELS[nextExpected]}`}
				</Button>
			</div>
		{/if}
	{/snippet}
</PanelCard>

<style>
	.ui-po-milestone-timeline-panel__action {
		display: flex;
		justify-content: flex-start;
		margin-top: var(--space-2);
	}
</style>
