<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import {
		getPO,
		submitPO,
		acceptPO,
		resubmitPO,
		downloadPoPdf,
		createInvoice,
		listInvoicesByPO,
		fetchReferenceData,
		getRemainingQuantities,
		listMilestones,
		postMilestone,
		listProducts,
		markAdvancePaid,
		addLinePostAccept,
		removeLinePostAccept,
		modifyLine,
		acceptLine,
		removeLine,
		forceAcceptLine,
		forceRemoveLine,
		submitResponse
	} from '$lib/api';
	import type { ModifyLineFields } from '$lib/api';
	import CreateInvoiceDialog from '$lib/components/CreateInvoiceDialog.svelte';
	import PoLineNegotiationTable from '$lib/po/PoLineNegotiationTable.svelte';
	import PoMetadataPanels from '$lib/po/PoMetadataPanels.svelte';
	import PoRejectionHistoryPanel from '$lib/po/PoRejectionHistoryPanel.svelte';
	import PoInvoicesPanel from '$lib/po/PoInvoicesPanel.svelte';
	import PoActivityPanel from '$lib/po/PoActivityPanel.svelte';
	import PoLineAcceptedTable from '$lib/po/PoLineAcceptedTable.svelte';
	import PoMilestoneTimelinePanel from '$lib/po/PoMilestoneTimelinePanel.svelte';
	import PoAddLineDialog from '$lib/po/PoAddLineDialog.svelte';
	import PoSubmitResponseBar from '$lib/po/PoSubmitResponseBar.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type {
		PurchaseOrder,
		InvoiceListItem,
		ReferenceData,
		RemainingLine,
		InvoiceLineItemCreate,
		MilestoneResponse,
		ProductionMilestone,
		UserRole,
		CertWarning
	} from '$lib/types';
	import { buildLabelResolver } from '$lib/labels';
	import {
		canEditPO,
		canSubmitPO,
		canAcceptRejectPO,
		canCreateInvoice,
		canPostMilestone,
		canModifyPostAccept
	} from '$lib/permissions';
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
	import PoDetailHeader from '$lib/po/PoDetailHeader.svelte';
	import PoActionRail from '$lib/po/PoActionRail.svelte';
	import PoAdvancePaymentPanel from '$lib/po/PoAdvancePaymentPanel.svelte';
	import PoCertWarningsBanner from '$lib/po/PoCertWarningsBanner.svelte';

	const ROLE_LABEL: Record<UserRole, string> = {
		ADMIN: 'Administrator',
		SM: 'Supply Manager',
		VENDOR: 'Vendor',
		FREIGHT_MANAGER: 'Freight Manager',
		QUALITY_LAB: 'Quality Lab',
		PROCUREMENT_MANAGER: 'Procurement Manager'
	};

	let po: PurchaseOrder | null = $state(null);
	let loading: boolean = $state(true);
	let invoices: InvoiceListItem[] = $state([]);
	let refData: ReferenceData | null = $state(null);
	let resolver: ReturnType<typeof buildLabelResolver> | null = $state(null);
	let remainingMap: Map<string, RemainingLine> = $state(new Map());
	let showInvoiceDialog: boolean = $state(false);
	let remainingLines: RemainingLine[] = $state([]);
	let opexError: string = $state('');
	let milestones: MilestoneResponse[] = $state([]);
	let certRequired: Set<string> = $state(new Set());
	// Iter 057 negotiation errors surface next to the action that failed.
	let lineErrors: Map<string, string> = $state(new Map());
	let submitResponseError: string = $state('');
	// Iter 059: advance-payment gate and post-accept mutation UI state.
	let advanceError: string = $state('');
	// Iter 039: cert warnings from quality gate on submit/resubmit.
	let certWarnings: CertWarning[] = $state([]);
	let certWarningsDismissed: boolean = $state(false);
	let showAddLineDialog: boolean = $state(false);
	let addLineError: string = $state('');
	let removeLineErrors: Map<string, string> = $state(new Map());

	const id: string = page.params.id ?? '';
	const role = $derived<UserRole | undefined>(page.data.user?.role);
	const user = $derived(page.data.user);
	const userName = $derived(user?.display_name ?? user?.username ?? 'Guest');
	const shellRole = $derived<UserRole>(role ?? 'ADMIN');
	const roleLabel = $derived(ROLE_LABEL[shellRole]);

	function resolve(category: string, code: string): string {
		if (!resolver) return code;
		return resolver.resolve(category, code);
	}

	async function fetchPO() {
		loading = true;
		try {
			[po, invoices, refData] = await Promise.all([
				getPO(id),
				listInvoicesByPO(id),
				fetchReferenceData()
			]);
			resolver = buildLabelResolver(refData);
			// Products endpoint is SM/QUALITY_LAB/ADMIN only; vendors rely on server-side cert gate on submit.
			if (role !== 'VENDOR') {
				const products = await listProducts({ vendor_id: po.vendor_id });
				certRequired = new Set(
					products
						.filter((p) => p.qualifications.some((q) => q.name === 'QUALITY_CERTIFICATE'))
						.map((p) => p.part_number)
				);
			}
			if (po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT') {
				const resp = await getRemainingQuantities(id);
				remainingMap = new Map(resp.lines.map((l) => [l.part_number, l]));
				milestones = await listMilestones(id);
			}
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchPO();
	});

	async function handleEdit() {
		if (!po) return;
		await goto(`/po/${po.id}/edit`);
	}

	async function handleSubmit() {
		const result = await submitPO(id);
		certWarnings = result.cert_warnings;
		certWarningsDismissed = false;
		await fetchPO();
	}

	async function handleAccept() {
		await acceptPO(id);
		await fetchPO();
	}

	async function handleResubmit() {
		const result = await resubmitPO(id);
		certWarnings = result.cert_warnings;
		certWarningsDismissed = false;
		await fetchPO();
	}

	async function handleDownloadPdf() {
		await downloadPoPdf(id);
	}

	async function handleCreateInvoice() {
		if (!po) return;
		if (po.po_type === 'OPEX') {
			await handleCreateOpexInvoice();
			return;
		}
		const resp = await getRemainingQuantities(id);
		const allInvoiced = resp.lines.every((l) => l.remaining === 0);
		if (allInvoiced) {
			alert('All quantities already invoiced');
			return;
		}
		remainingLines = resp.lines;
		showInvoiceDialog = true;
	}

	async function handleInvoiceConfirm(lineItems: InvoiceLineItemCreate[]) {
		showInvoiceDialog = false;
		const invoice = await createInvoice(id, lineItems);
		goto(`/invoice/${invoice.id}`);
	}

	// The action rail's Post Milestone button scrolls the user to the production
	// timeline panel where the timeline owns the per-milestone Post buttons. The
	// rail's onPostMilestone is parameterless; the timeline takes the milestone arg.
	async function handlePostMilestoneAction() {
		await tick();
		const node = document.querySelector('[data-testid="po-milestone-timeline"]');
		if (node) {
			node.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}

	// ---------------------------------------------------------------------------
	// Iter 057 -- Line-level negotiation actions
	// ---------------------------------------------------------------------------

	// Whether the current actor can act on a PENDING or MODIFIED PO. PENDING
	// belongs to VENDOR (initial response). MODIFIED belongs to whichever role
	// is not the last actor. ADMIN acts as SM for these purposes.
	const canActOnNegotiation = $derived(computeCanActOnNegotiation());

	function computeCanActOnNegotiation(): boolean {
		if (!po || !role) return false;
		if (po.status !== 'PENDING' && po.status !== 'MODIFIED') return false;
		if (po.status === 'PENDING') {
			return role === 'VENDOR';
		}
		// MODIFIED: whoever is NOT the last_actor_role must respond.
		const actorRole: 'VENDOR' | 'SM' = role === 'VENDOR' ? 'VENDOR' : 'SM';
		return po.last_actor_role !== actorRole;
	}

	function setLineError(partNumber: string, msg: string) {
		const next = new Map(lineErrors);
		if (msg) {
			next.set(partNumber, msg);
		} else {
			next.delete(partNumber);
		}
		lineErrors = next;
	}

	async function handleModify(partNumber: string, fields: ModifyLineFields) {
		setLineError(partNumber, '');
		try {
			await modifyLine(id, partNumber, fields);
			await fetchPO();
		} catch (err: unknown) {
			setLineError(partNumber, err instanceof Error ? err.message : String(err));
		}
	}

	async function handleAcceptNegotiation(partNumber: string) {
		setLineError(partNumber, '');
		try {
			await acceptLine(id, partNumber);
			await fetchPO();
		} catch (err: unknown) {
			setLineError(partNumber, err instanceof Error ? err.message : String(err));
		}
	}

	async function handleRemoveNegotiation(partNumber: string) {
		setLineError(partNumber, '');
		try {
			await removeLine(id, partNumber);
			await fetchPO();
		} catch (err: unknown) {
			setLineError(partNumber, err instanceof Error ? err.message : String(err));
		}
	}

	async function handleForceAccept(partNumber: string) {
		setLineError(partNumber, '');
		try {
			await forceAcceptLine(id, partNumber);
			await fetchPO();
		} catch (err: unknown) {
			setLineError(partNumber, err instanceof Error ? err.message : String(err));
		}
	}

	async function handleForceRemove(partNumber: string) {
		setLineError(partNumber, '');
		try {
			await forceRemoveLine(id, partNumber);
			await fetchPO();
		} catch (err: unknown) {
			setLineError(partNumber, err instanceof Error ? err.message : String(err));
		}
	}

	async function handleSubmitResponse() {
		submitResponseError = '';
		try {
			await submitResponse(id);
			await fetchPO();
		} catch (err: unknown) {
			submitResponseError = err instanceof Error ? err.message : String(err);
		}
	}

	// Role hand-off indicator: the VENDOR on PENDING PO, or whoever is not the
	// last actor on a MODIFIED PO.
	function effectiveRole(r: UserRole): 'VENDOR' | 'SM' {
		return r === 'VENDOR' ? 'VENDOR' : 'SM';
	}

	// ---------------------------------------------------------------------------
	// Iter 059 -- Advance-payment gate and post-accept line mutations
	// ---------------------------------------------------------------------------

	async function handleMarkAdvancePaid() {
		advanceError = '';
		try {
			await markAdvancePaid(id);
			await fetchPO();
		} catch (err: unknown) {
			advanceError = err instanceof Error ? err.message : String(err);
		}
	}

	function paymentTermHasAdvance(): boolean {
		if (!po || !refData) return false;
		const entry = refData.payment_terms.find((t) => t.code === po!.payment_terms);
		return !!entry?.has_advance;
	}

	const advancePanelVisibleStatuses: ReadonlyArray<string> = [
		'PENDING',
		'MODIFIED',
		'ACCEPTED',
		'REJECTED',
		'REVISED'
	] as const;

	const showAdvancePanel = $derived(
		!!po && paymentTermHasAdvance() && advancePanelVisibleStatuses.includes(po.status)
	);

	const firstMilestonePosted = $derived(milestones.length > 0);

	function postAcceptGateClosed(): boolean {
		// The gate closes on either (a) a milestone posted, or (b) advance paid.
		// Router returns a 409 with detail when closed; this is a client-side hint only.
		if (!po) return true;
		if (po.status !== 'ACCEPTED') return true;
		if (milestones.length > 0) return true;
		if (paymentTermHasAdvance() && po.advance_paid_at) return true;
		return false;
	}

	function openAddLineDialog() {
		addLineError = '';
		showAddLineDialog = true;
	}

	function closeAddLineDialog() {
		showAddLineDialog = false;
		addLineError = '';
	}

	// Iter 082: PoAddLineDialog owns the form state and posts the validated
	// payload back via on_submit. The page handles the API call + close on
	// success / surfaces the server error string back into the dialog.
	async function handleAddLineSubmit(fields: {
		part_number: string;
		description: string;
		quantity: number;
		uom: string;
		unit_price: string;
		hs_code: string;
		country_of_origin: string;
	}) {
		addLineError = '';
		try {
			await addLinePostAccept(id, fields);
			showAddLineDialog = false;
			await fetchPO();
		} catch (err: unknown) {
			addLineError = err instanceof Error ? err.message : String(err);
		}
	}

	async function handleRemoveLinePostAccept(partNumber: string) {
		removeLineErrors = new Map(removeLineErrors).set(partNumber, '');
		const result = await removeLinePostAccept(id, partNumber);
		if (result.ok) {
			removeLineErrors = new Map(removeLineErrors);
			removeLineErrors.delete(partNumber);
			await fetchPO();
		} else {
			removeLineErrors = new Map(removeLineErrors).set(partNumber, result.detail);
		}
	}

	async function handlePostMilestone(milestone: ProductionMilestone) {
		await postMilestone(id, milestone);
		milestones = await listMilestones(id);
	}

	async function handleCreateOpexInvoice() {
		opexError = '';
		try {
			const invoice = await createInvoice(id);
			goto(`/invoice/${invoice.id}`);
		} catch (err: unknown) {
			const msg = err instanceof Error ? err.message : String(err);
			opexError = msg || 'Failed to create invoice';
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatValue(value: string, currency: string): string {
		return `${parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
	}
</script>

<svelte:head>
	<title>{po ? po.po_number : 'Purchase Order'}</title>
</svelte:head>

<AppShell role={shellRole} {roleLabel} breadcrumb="Purchase Orders">
	{#snippet userMenu()}
		<UserMenu name={userName} role={shellRole} />
	{/snippet}

	{#if loading}
		<p>Loading...</p>
	{:else if po}
		<div class="po-detail-page">
			<PoDetailHeader {po}>
				{#snippet actionRail()}
					{#if role}
						<div class="po-detail-page__rail-inline">
							<PoActionRail
								{po}
								{role}
								mode="inline"
								onEdit={handleEdit}
								onSubmit={handleSubmit}
								onResubmit={handleResubmit}
								onAccept={handleAccept}
								onMarkAdvancePaid={handleMarkAdvancePaid}
								onCreateInvoice={handleCreateInvoice}
								onPostMilestone={handlePostMilestoneAction}
								onDownloadPdf={handleDownloadPdf}
							/>
						</div>
					{/if}
				{/snippet}
			</PoDetailHeader>

			{#if certWarnings.length > 0 && !certWarningsDismissed}
				<PoCertWarningsBanner warnings={certWarnings} bind:dismissed={certWarningsDismissed} />
			{/if}

			{#if showAdvancePanel && role}
				<PoAdvancePaymentPanel
					{po}
					{role}
					paymentTermHasAdvance={true}
					{firstMilestonePosted}
					onMarkAdvancePaid={handleMarkAdvancePaid}
				/>
				{#if advanceError}
					<p class="error-message" data-testid="po-advance-error">{advanceError}</p>
				{/if}
			{/if}

			<PoMetadataPanels {po} {resolve} {formatDate} {formatValue} />

			<div class="section card">
				<h2>Line Items</h2>
				{#if po.status === 'ACCEPTED' && role && canModifyPostAccept(role)}
					<div class="post-accept-toolbar">
						{#if !postAcceptGateClosed()}
							<Button
								onclick={openAddLineDialog}
								data-testid="add-line-btn"
							>
								Add Line
							</Button>
						{/if}
					</div>
					{#if postAcceptGateClosed()}
						<p
							class="post-accept-gate-note"
							data-testid="po-post-accept-gate-closed-note"
						>
							Post-acceptance line edits closed: advance paid or first milestone
							posted.
						</p>
					{/if}
				{/if}

				{#if po.status === 'PENDING' || po.status === 'MODIFIED'}
					<!-- Iter 081: PoLineNegotiationTable owns row layout, errors, and
						 the View-changes diff/history toggle per line. -->
					<PoLineNegotiationTable
						lines={po.line_items}
						role={role ? effectiveRole(role) : 'VENDOR'}
						round_count={po.round_count ?? 0}
						errors={lineErrors}
						on_modify={(pn, fields) => handleModify(pn, fields)}
						on_accept={(pn) => handleAcceptNegotiation(pn)}
						on_remove={(pn) => handleRemoveNegotiation(pn)}
						on_force_accept={(pn) => handleForceAccept(pn)}
						on_force_remove={(pn) => handleForceRemove(pn)}
					/>
				{:else}
					<!-- Iter 082: PoLineAcceptedTable owns the ACCEPTED-PO row layout,
						 cert badges, status pills, per-row Remove button, and per-row
						 inline error rendering. -->
					<PoLineAcceptedTable
						lines={po.line_items}
						role={role ?? null}
						po_type={po.po_type}
						cert_required={certRequired}
						remaining_map={new Map(
							[...remainingMap].map(([pn, r]) => [
								pn,
								{ invoiced: r.invoiced, remaining: r.remaining }
							])
						)}
						gate_closed={postAcceptGateClosed()}
						errors={removeLineErrors}
						on_remove={role && canModifyPostAccept(role)
							? handleRemoveLinePostAccept
							: null}
						resolve_country={(code) => resolve('countries', code)}
					/>
				{/if}

				{#if (po.status === 'PENDING' || po.status === 'MODIFIED') && role && canActOnNegotiation}
					<PoSubmitResponseBar
						lines={po.line_items}
						role={effectiveRole(role)}
						round_count={po.round_count ?? 0}
						error={submitResponseError}
						on_submit={handleSubmitResponse}
					/>
				{/if}
			</div>

			{#if po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT'}
				<PoMilestoneTimelinePanel
					{milestones}
					role={role ?? null}
					onPost={role && canPostMilestone(role) ? handlePostMilestone : null}
				/>
			{/if}

			{#if po.rejection_history.length > 0}
				<PoRejectionHistoryPanel records={po.rejection_history} {formatDate} />
			{/if}

			<PoInvoicesPanel {invoices} {po} {remainingMap} {formatDate} {formatValue} />

			<PoActivityPanel poId={po.id} />

			{#if opexError}
				<p class="error-message">{opexError}</p>
			{/if}

			{#if role}
				<div class="po-detail-page__rail-mobile" data-testid="po-detail-page-rail-mobile">
					<PoActionRail
						{po}
						{role}
						mode="sticky-bottom"
						onEdit={handleEdit}
						onSubmit={handleSubmit}
						onResubmit={handleResubmit}
						onAccept={handleAccept}
						onMarkAdvancePaid={handleMarkAdvancePaid}
						onCreateInvoice={handleCreateInvoice}
						onPostMilestone={handlePostMilestoneAction}
						onDownloadPdf={handleDownloadPdf}
					/>
				</div>
			{/if}

			{#if showInvoiceDialog}
				<CreateInvoiceDialog
					lines={remainingLines}
					onConfirm={handleInvoiceConfirm}
					onCancel={() => (showInvoiceDialog = false)}
				/>
			{/if}

			{#if showAddLineDialog && refData}
				<PoAddLineDialog
					reference_data={refData}
					error={addLineError}
					on_submit={handleAddLineSubmit}
					on_close={closeAddLineDialog}
				/>
			{/if}
		</div>
	{/if}
</AppShell>

<style>
	.po-detail-page {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.error-message {
		color: var(--red-600);
		font-size: var(--font-size-sm);
		margin-top: var(--space-2);
	}

	.post-accept-toolbar {
		display: flex;
		justify-content: flex-end;
		margin-bottom: var(--space-3);
	}

	.post-accept-gate-note {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		background: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0 0 var(--space-3);
	}

	/* Inline rail (>= 768px) lives inside the header; sticky rail pins to the
	   viewport bottom on narrow screens. Each renders only at its own breakpoint. */
	.po-detail-page__rail-inline {
		display: none;
	}
	@media (min-width: 768px) {
		.po-detail-page__rail-inline {
			display: flex;
		}
	}

	.po-detail-page__rail-mobile {
		display: none;
	}
	@media (max-width: 767px) {
		.po-detail-page__rail-mobile {
			display: block;
			position: fixed;
			bottom: 0;
			left: 0;
			right: 0;
			z-index: 10;
		}
		.po-detail-page {
			padding-bottom: 5rem;
		}
	}
</style>
