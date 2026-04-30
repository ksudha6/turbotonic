<script lang="ts">
	import { onMount } from 'svelte';
	import { page as appPage } from '$app/state';
	import {
		listUsers,
		deactivateUser,
		reactivateUser,
		resetCredentials,
		reissueInvite
	} from '$lib/api';
	import type { InviteUserResponse, User, UserRole, UserStatus } from '$lib/types';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import Button from '$lib/ui/Button.svelte';
	import UserListFilters from '$lib/user/UserListFilters.svelte';
	import UserListTable from '$lib/user/UserListTable.svelte';
	import type { UserRowAction } from '$lib/user/user-row-actions';
	import UserInviteModal from '$lib/user/UserInviteModal.svelte';
	import UserEditModal from '$lib/user/UserEditModal.svelte';
	import UserActionConfirm from '$lib/user/UserActionConfirm.svelte';
	import InviteLinkPanel from '$lib/user/InviteLinkPanel.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let status: UserStatus | '' = $state('' as UserStatus | '');
	let role: UserRole | '' = $state('' as UserRole | '');

	let users: User[] = $state([]);
	let loading: boolean = $state(true);
	let errorMessage: string = $state('');
	let initialFetchComplete: boolean = $state(false);

	const sessionUser = $derived(appPage.data.user);
	const sessionRole = $derived<UserRole>((sessionUser?.role as UserRole | undefined) ?? 'ADMIN');
	const sessionName = $derived(
		sessionUser?.display_name ?? sessionUser?.username ?? 'Guest'
	);
	const sessionRoleLabel = $derived(ROLE_LABEL[sessionRole]);

	const hasAnyFilter = $derived(Boolean(status || role));

	let inviteModalOpen: boolean = $state(false);
	let editTarget: User | null = $state(null);

	type ConfirmKind = 'deactivate' | 'reset-credentials' | 'reissue-invite';
	let confirmTarget: { user: User; kind: ConfirmKind } | null = $state(null);

	let invitePanel: { caption: string; token: string } | null = $state(null);

	let initialized = false;
	$effect(() => {
		status;
		role;
		if (!initialized) {
			initialized = true;
			return;
		}
		fetchUsers();
	});

	onMount(() => {
		fetchUsers();
	});

	async function fetchUsers() {
		loading = true;
		errorMessage = '';
		try {
			const { users: list } = await listUsers({
				status: status || undefined,
				role: role || undefined
			});
			users = list;
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Failed to load users';
			users = [];
		} finally {
			loading = false;
			initialFetchComplete = true;
		}
	}

	function clearFilters() {
		status = '';
		role = '';
	}

	function handleRowAction(id: string, action: UserRowAction) {
		const target = users.find((u) => u.id === id);
		if (!target) return;
		if (action === 'edit') {
			editTarget = target;
			return;
		}
		if (action === 'reactivate') {
			// Reactivate is a single-button confirmation-less path: low-risk transition,
			// no destructive consequence. Mirrors VendorListTable's reactivate-on-click.
			void runReactivate(target);
			return;
		}
		confirmTarget = { user: target, kind: action };
	}

	async function runReactivate(target: User) {
		try {
			const { user: updated } = await reactivateUser(target.id);
			users = users.map((u) => (u.id === updated.id ? updated : u));
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Reactivate failed';
		}
	}

	async function runConfirm() {
		if (!confirmTarget) return;
		const { user: target, kind } = confirmTarget;
		if (kind === 'deactivate') {
			const { user: updated } = await deactivateUser(target.id);
			users = users.map((u) => (u.id === updated.id ? updated : u));
			confirmTarget = null;
		} else if (kind === 'reset-credentials') {
			const response: InviteUserResponse = await resetCredentials(target.id);
			users = users.map((u) => (u.id === response.user.id ? response.user : u));
			invitePanel = {
				caption: `Reset complete — new invite link for ${response.user.username}`,
				token: response.invite_token
			};
			confirmTarget = null;
		} else if (kind === 'reissue-invite') {
			const response: InviteUserResponse = await reissueInvite(target.id);
			users = users.map((u) => (u.id === response.user.id ? response.user : u));
			invitePanel = {
				caption: `Reissue complete — new invite link for ${response.user.username}`,
				token: response.invite_token
			};
			confirmTarget = null;
		}
	}

	function handleInviteSuccess(response: InviteUserResponse) {
		inviteModalOpen = false;
		invitePanel = {
			caption: `New invite link for ${response.user.username}`,
			token: response.invite_token
		};
		// Refetch so the new PENDING row shows up under any active filter.
		void fetchUsers();
	}

	function handleEditSuccess(updated: User) {
		users = users.map((u) => (u.id === updated.id ? updated : u));
		editTarget = null;
	}

	const confirmCopy = $derived(buildConfirmCopy(confirmTarget));

	function buildConfirmCopy(target: typeof confirmTarget) {
		if (!target) return null;
		const username = target.user.username;
		if (target.kind === 'deactivate') {
			return {
				title: 'Deactivate user',
				body: `${username} will no longer be able to log in. Reactivating restores access without re-issuing credentials.`,
				confirmLabel: 'Deactivate'
			};
		}
		if (target.kind === 'reset-credentials') {
			return {
				title: 'Reset credentials',
				body: `${username}'s passkeys will be revoked and a fresh invite link will be issued. They will need to register a new device before logging in.`,
				confirmLabel: 'Reset credentials'
			};
		}
		return {
			title: 'Reissue invite',
			body: `A new invite link will be generated for ${username}. The previous link will stop working.`,
			confirmLabel: 'Reissue invite'
		};
	}
</script>

<svelte:head>
	<title>Users</title>
</svelte:head>

<AppShell role={sessionRole} roleLabel={sessionRoleLabel} breadcrumb="Users">
	{#snippet userMenu()}
		<UserMenu name={sessionName} role={sessionRole} />
	{/snippet}

	<PageHeader title="Users">
		{#snippet action()}
			<Button
				variant="primary"
				onclick={() => (inviteModalOpen = true)}
				data-testid="user-page-header-action"
			>
				Invite user
			</Button>
		{/snippet}
	</PageHeader>

	<div class="user-list-page">
		<UserListFilters bind:status bind:role onClear={clearFilters} />

		{#if invitePanel}
			<InviteLinkPanel
				caption={invitePanel.caption}
				token={invitePanel.token}
				onDismiss={() => (invitePanel = null)}
			/>
		{/if}

		{#if errorMessage && !loading}
			<ErrorState message={errorMessage} onRetry={fetchUsers} />
		{:else if loading && !initialFetchComplete}
			<LoadingState label="Loading users" data-testid="user-list-loading" />
		{:else if users.length === 0}
			{#if hasAnyFilter}
				<EmptyState title="No matching users" description="Try adjusting filters." />
			{:else}
				<EmptyState
					title="No users yet"
					description="Invite a user to get started."
				/>
			{/if}
		{:else}
			<div class="user-list-table-region">
				<UserListTable rows={users} onAction={handleRowAction} />
				{#if loading && users.length > 0}
					<div class="user-list-loading-overlay">
						<LoadingState label="Refreshing" data-testid="user-list-loading" />
					</div>
				{/if}
			</div>
		{/if}
	</div>

	{#if inviteModalOpen}
		<UserInviteModal
			onSuccess={handleInviteSuccess}
			onCancel={() => (inviteModalOpen = false)}
		/>
	{/if}

	{#if editTarget}
		<UserEditModal
			user={editTarget}
			onSuccess={handleEditSuccess}
			onCancel={() => (editTarget = null)}
		/>
	{/if}

	{#if confirmTarget && confirmCopy}
		<UserActionConfirm
			title={confirmCopy.title}
			body={confirmCopy.body}
			confirmLabel={confirmCopy.confirmLabel}
			onConfirm={runConfirm}
			onCancel={() => (confirmTarget = null)}
		/>
	{/if}
</AppShell>

<style>
	.user-list-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.user-list-table-region {
		position: relative;
	}
	.user-list-loading-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(255, 255, 255, 0.6);
		z-index: 1;
	}
</style>
