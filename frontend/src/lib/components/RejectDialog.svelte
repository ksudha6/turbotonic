<script lang="ts">
	let { onConfirm, onCancel }: { onConfirm: (comment: string) => void; onCancel: () => void } =
		$props();

	let comment: string = $state('');
</script>

<div class="overlay">
	<div class="dialog">
		<h2 class="dialog-title">Reject Purchase Order</h2>
		<div class="form-group">
			<textarea
				class="textarea"
				bind:value={comment}
				placeholder="Enter rejection reason..."
				rows="4"
			></textarea>
		</div>
		<div class="dialog-actions">
			<button class="btn btn-secondary" onclick={onCancel}>Cancel</button>
			<button
				class="btn btn-danger"
				onclick={() => onConfirm(comment)}
				disabled={comment.trim().length === 0}
			>
				Reject
			</button>
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
		max-width: 500px;
		width: 100%;
	}

	.dialog-title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		margin-bottom: var(--space-4);
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		margin-top: var(--space-4);
	}
</style>
