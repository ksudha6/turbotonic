<script lang="ts">
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { User, UserRole, UserStatus } from '$lib/types';
	import type { UserRowAction } from './user-row-actions';

	let {
		rows,
		onAction,
		'data-testid': testid
	}: {
		rows: User[];
		onAction: (id: string, action: UserRowAction) => void;
		'data-testid'?: string;
	} = $props();

	type Tone = 'green' | 'blue' | 'orange' | 'red' | 'gray';

	const STATUS_TONE: Readonly<Record<UserStatus, Tone>> = {
		ACTIVE: 'green',
		INACTIVE: 'gray',
		PENDING: 'orange'
	};

	const STATUS_LABEL: Readonly<Record<UserStatus, string>> = {
		ACTIVE: 'Active',
		INACTIVE: 'Inactive',
		PENDING: 'Pending'
	};

	const ROLE_LABEL: Readonly<Record<UserRole, string>> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};
</script>

<div class="user-list-table" data-testid={testid ?? 'user-table'}>
	<table class="user-list-table__desktop" data-testid="user-table-desktop">
		<thead>
			<tr>
				<th>Username</th>
				<th>Display Name</th>
				<th>Role</th>
				<th>Email</th>
				<th>Status</th>
				<th class="user-list-table__action-col">Actions</th>
			</tr>
		</thead>
		<tbody>
			{#each rows as row (row.id)}
				<tr data-testid={`user-row-${row.id}`}>
					<td data-testid={`user-row-username-${row.id}`}>{row.username}</td>
					<td>{row.display_name}</td>
					<td data-testid={`user-row-role-${row.id}`}>{ROLE_LABEL[row.role]}</td>
					<td data-testid={`user-row-email-${row.id}`}>{row.email ?? ''}</td>
					<td>
						<StatusPill
							tone={STATUS_TONE[row.status]}
							label={STATUS_LABEL[row.status]}
							data-testid={`user-row-status-${row.id}`}
						/>
					</td>
					<td class="user-list-table__action-col">
						<div class="user-list-table__actions">
							<Button
								variant="ghost"
								onclick={() => onAction(row.id, 'edit')}
								data-testid={`user-row-edit-${row.id}`}
							>
								Edit
							</Button>
							{#if row.status === 'ACTIVE'}
								<Button
									variant="secondary"
									onclick={() => onAction(row.id, 'deactivate')}
									data-testid={`user-row-deactivate-${row.id}`}
								>
									Deactivate
								</Button>
							{/if}
							{#if row.status === 'INACTIVE'}
								<Button
									variant="primary"
									onclick={() => onAction(row.id, 'reactivate')}
									data-testid={`user-row-reactivate-${row.id}`}
								>
									Reactivate
								</Button>
							{/if}
							{#if row.status === 'ACTIVE' || row.status === 'INACTIVE'}
								<Button
									variant="secondary"
									onclick={() => onAction(row.id, 'reset-credentials')}
									data-testid={`user-row-reset-${row.id}`}
								>
									Reset credentials
								</Button>
							{/if}
							{#if row.status === 'PENDING'}
								<Button
									variant="primary"
									onclick={() => onAction(row.id, 'reissue-invite')}
									data-testid={`user-row-reissue-${row.id}`}
								>
									Reissue invite
								</Button>
							{/if}
						</div>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>

	<ul class="user-list-table__mobile" data-testid="user-table-mobile">
		{#each rows as row (row.id)}
			<li class="user-row-card" data-testid={`user-row-${row.id}`}>
				<div class="user-row-card__header">
					<span class="user-row-card__name" data-testid={`user-row-username-${row.id}`}>
						{row.username}
					</span>
					<StatusPill
						tone={STATUS_TONE[row.status]}
						label={STATUS_LABEL[row.status]}
						data-testid={`user-row-status-${row.id}`}
					/>
				</div>
				<div class="user-row-card__meta">
					<span>{row.display_name}</span>
					<span>·</span>
					<span data-testid={`user-row-role-${row.id}`}>{ROLE_LABEL[row.role]}</span>
					{#if row.email}
						<span>·</span>
						<span data-testid={`user-row-email-${row.id}`}>{row.email}</span>
					{:else}
						<span data-testid={`user-row-email-${row.id}`} hidden></span>
					{/if}
				</div>
				<div class="user-row-card__actions">
					<Button
						variant="ghost"
						onclick={() => onAction(row.id, 'edit')}
						data-testid={`user-row-edit-${row.id}`}
					>
						Edit
					</Button>
					{#if row.status === 'ACTIVE'}
						<Button
							variant="secondary"
							onclick={() => onAction(row.id, 'deactivate')}
							data-testid={`user-row-deactivate-${row.id}`}
						>
							Deactivate
						</Button>
					{/if}
					{#if row.status === 'INACTIVE'}
						<Button
							variant="primary"
							onclick={() => onAction(row.id, 'reactivate')}
							data-testid={`user-row-reactivate-${row.id}`}
						>
							Reactivate
						</Button>
					{/if}
					{#if row.status === 'ACTIVE' || row.status === 'INACTIVE'}
						<Button
							variant="secondary"
							onclick={() => onAction(row.id, 'reset-credentials')}
							data-testid={`user-row-reset-${row.id}`}
						>
							Reset credentials
						</Button>
					{/if}
					{#if row.status === 'PENDING'}
						<Button
							variant="primary"
							onclick={() => onAction(row.id, 'reissue-invite')}
							data-testid={`user-row-reissue-${row.id}`}
						>
							Reissue invite
						</Button>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
</div>

<style>
	.user-list-table {
		display: block;
	}
	.user-list-table__desktop {
		display: none;
	}
	.user-list-table__mobile {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.user-row-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		background-color: var(--surface-card);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
	}
	.user-row-card__header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
	}
	.user-row-card__name {
		font-weight: 600;
		font-size: var(--font-size-base);
		color: var(--gray-900);
	}
	.user-row-card__meta {
		display: flex;
		gap: var(--space-2);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		flex-wrap: wrap;
	}
	.user-row-card__actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		justify-content: flex-end;
	}

	@media (min-width: 768px) {
		.user-list-table__mobile { display: none; }
		.user-list-table__desktop {
			display: table;
			width: 100%;
			border-collapse: collapse;
			font-size: var(--font-size-sm);
		}
		.user-list-table__desktop th {
			text-align: left;
			padding: var(--space-3) var(--space-4);
			font-weight: 600;
			color: var(--gray-600);
			border-bottom: 1px solid var(--gray-200);
			background-color: var(--gray-50);
			white-space: nowrap;
		}
		.user-list-table__desktop td {
			padding: var(--space-3) var(--space-4);
			border-bottom: 1px solid var(--gray-100);
			vertical-align: middle;
		}
		.user-list-table__action-col {
			text-align: right;
			white-space: nowrap;
		}
		.user-list-table__actions {
			display: flex;
			gap: var(--space-2);
			flex-wrap: wrap;
			justify-content: flex-end;
		}
	}
</style>
