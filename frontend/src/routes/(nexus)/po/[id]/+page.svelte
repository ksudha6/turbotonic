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
	import StatusPill from '$lib/components/StatusPill.svelte';
	import CreateInvoiceDialog from '$lib/components/CreateInvoiceDialog.svelte';
	import MilestoneTimeline from '$lib/components/MilestoneTimeline.svelte';
	import ActivityTimeline from '$lib/components/ActivityTimeline.svelte';
	import LineNegotiationRow from '$lib/components/LineNegotiationRow.svelte';
	import SubmitResponseBar from '$lib/components/SubmitResponseBar.svelte';
	import type {
		PurchaseOrder,
		InvoiceListItem,
		ReferenceData,
		RemainingLine,
		InvoiceLineItemCreate,
		MilestoneUpdate,
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
	let milestones: MilestoneUpdate[] = $state([]);
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
	let newLinePart: string = $state('');
	let newLineDescription: string = $state('');
	let newLineQuantity: number = $state(1);
	let newLineUom: string = $state('EA');
	let newLineUnitPrice: string = $state('0.00');
	let newLineHsCode: string = $state('8471.30');
	let newLineCountry: string = $state('US');

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
		newLinePart = '';
		newLineDescription = '';
		newLineQuantity = 1;
		newLineUom = 'EA';
		newLineUnitPrice = '0.00';
		newLineHsCode = '8471.30';
		newLineCountry = 'US';
		addLineError = '';
		showAddLineDialog = true;
	}

	async function handleAddLineSubmit() {
		addLineError = '';
		try {
			await addLinePostAccept(id, {
				part_number: newLinePart,
				description: newLineDescription,
				quantity: newLineQuantity,
				uom: newLineUom,
				unit_price: newLineUnitPrice,
				hs_code: newLineHsCode,
				country_of_origin: newLineCountry
			});
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

	async function handlePostMilestone(milestone: string) {
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

			<div class="section card">
				<div class="info-grid">
					<div class="info-item">
						<span class="field-label">Currency</span>
						<span class="value">{resolve('currencies', po.currency)}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Issued Date</span>
						<span class="value">{formatDate(po.issued_date)}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Delivery Date</span>
						<span class="value">{formatDate(po.required_delivery_date)}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Total Value</span>
						<span class="value">{formatValue(po.total_value, po.currency)}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Payment Terms</span>
						<span class="value">{resolve('payment_terms', po.payment_terms)}</span>
					</div>
					{#if po.marketplace}
						<div class="info-item">
							<span class="field-label">Marketplace</span>
							<span class="value">{po.marketplace}</span>
						</div>
					{/if}
				</div>
			</div>

			<div class="section card">
				<h2>Buyer</h2>
				<div class="info-grid">
					<div class="info-item">
						<span class="field-label">Name</span>
						<span class="value">{po.buyer_name}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Country</span>
						<span class="value">{resolve('countries', po.buyer_country)}</span>
					</div>
				</div>
			</div>

			<div class="section card">
				<h2>Vendor</h2>
				<div class="info-grid">
					<div class="info-item">
						<span class="field-label">Name</span>
						<span class="value">{po.vendor_name}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Country</span>
						<span class="value">{resolve('countries', po.vendor_country)}</span>
					</div>
				</div>
			</div>

			<div class="section card">
				<h2>Trade Details</h2>
				<div class="info-grid">
					<div class="info-item">
						<span class="field-label">Incoterm</span>
						<span class="value">{resolve('incoterms', po.incoterm)}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Port of Loading</span>
						<span class="value">{resolve('ports', po.port_of_loading)}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Port of Discharge</span>
						<span class="value">{resolve('ports', po.port_of_discharge)}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Country of Origin</span>
						<span class="value">{resolve('countries', po.country_of_origin)}</span>
					</div>
					<div class="info-item">
						<span class="field-label">Country of Destination</span>
						<span class="value">{resolve('countries', po.country_of_destination)}</span>
					</div>
				</div>
			</div>

			<div class="section card">
				<h2>Terms &amp; Conditions</h2>
				<p class="terms-text">{po.terms_and_conditions}</p>
			</div>

			<div class="section card">
				<h2>Line Items</h2>
				{#if po.status === 'ACCEPTED' && role && canModifyPostAccept(role)}
					<div class="post-accept-toolbar">
						<button
							class="btn btn-secondary"
							data-testid="add-line-btn"
							disabled={postAcceptGateClosed()}
							title={postAcceptGateClosed() ? 'Cannot add: advance paid or first milestone posted' : ''}
							onclick={openAddLineDialog}
						>Add Line</button>
					</div>
				{/if}

				{#if po.status === 'PENDING' || po.status === 'MODIFIED'}
					<!-- Iter 057: per-line negotiation list. Rows render their own actions
						 based on role and round_count. -->
					<div class="negotiation-list" data-testid="negotiation-list">
						{#each po.line_items as item (item.part_number)}
							<LineNegotiationRow
								line={item}
								role={role ? effectiveRole(role) : 'VENDOR'}
								round_count={po.round_count ?? 0}
								on_modify={(pn, fields) => handleModify(pn, fields)}
								on_accept={(pn) => handleAcceptNegotiation(pn)}
								on_remove={(pn) => handleRemoveNegotiation(pn)}
								on_force_accept={(pn) => handleForceAccept(pn)}
								on_force_remove={(pn) => handleForceRemove(pn)}
							/>
							{#if lineErrors.get(item.part_number)}
								<p class="error-message" data-testid="line-error-{item.part_number}">{lineErrors.get(item.part_number)}</p>
							{/if}
						{/each}
					</div>
				{:else}
					<table class="table">
						<thead>
							<tr>
								<th>Part Number</th>
								<th>Description</th>
								<th>Qty</th>
								{#if po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT'}
									<th>Invoiced</th>
									<th>Remaining</th>
								{/if}
								<th>UoM</th>
								<th>Unit Price</th>
								<th>HS Code</th>
								<th>Origin</th>
								<th>Cert</th>
								<th>Status</th>
								{#if po.status === 'ACCEPTED' && role && canModifyPostAccept(role)}
									<th>Actions</th>
								{/if}
							</tr>
						</thead>
						<tbody>
							{#each po.line_items as item (item.part_number)}
								<tr>
									<td>{item.part_number}</td>
									<td>{item.description}</td>
									<td>{item.quantity}</td>
									{#if po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT'}
										{@const r = remainingMap.get(item.part_number)}
										<td>{r ? r.invoiced : 0}</td>
										<td>{r ? r.remaining : 0}</td>
									{/if}
									<td>{item.uom}</td>
									<td>{parseFloat(item.unit_price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
									<td>{item.hs_code}</td>
									<td>{resolve('countries', item.country_of_origin)}</td>
									<td>
										{#if certRequired.has(item.part_number)}
											<span class="badge badge-cert">Required</span>
										{/if}
									</td>
									<td>
										<span class="badge badge-line-status badge-{item.status.toLowerCase()}">{item.status}</span>
									</td>
									{#if po.status === 'ACCEPTED' && role && canModifyPostAccept(role)}
										<td>
											{#if item.status !== 'REMOVED'}
												<button
													class="btn-remove-line"
													data-testid="remove-line-{item.part_number}"
													disabled={postAcceptGateClosed()}
													title={removeLineErrors.get(item.part_number) || (postAcceptGateClosed() ? 'Cannot remove: advance paid or first milestone posted' : '')}
													onclick={() => handleRemoveLinePostAccept(item.part_number)}
												>Remove</button>
												{#if removeLineErrors.get(item.part_number)}
													<p class="error-message">{removeLineErrors.get(item.part_number)}</p>
												{/if}
											{/if}
										</td>
									{/if}
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}

				{#if (po.status === 'PENDING' || po.status === 'MODIFIED') && role && canActOnNegotiation}
					<SubmitResponseBar
						lines={po.line_items}
						role={effectiveRole(role)}
						round_count={po.round_count ?? 0}
						on_submit={handleSubmitResponse}
					/>
					{#if submitResponseError}
						<p class="error-message" data-testid="submit-response-error">{submitResponseError}</p>
					{/if}
				{/if}
			</div>

			{#if po.status === 'ACCEPTED' && po.po_type === 'PROCUREMENT'}
				<div class="section card" data-testid="po-milestone-timeline">
					<h2>Production Status</h2>
					<MilestoneTimeline
						{milestones}
						onPost={role && canPostMilestone(role) ? handlePostMilestone : null}
					/>
				</div>
			{/if}

			{#if po.rejection_history.length > 0}
				<div class="section card">
					<h2>Rejection History</h2>
					{#each [...po.rejection_history].reverse() as record}
						<div class="rejection-record">
							<p class="rejection-comment">{record.comment}</p>
							<p class="rejection-date">{formatDate(record.rejected_at)}</p>
						</div>
					{/each}
				</div>
			{/if}

			{#if invoices.length > 0}
				<div class="section card">
					<h2>Invoices</h2>
					<table class="table">
						<thead>
							<tr>
								<th>Invoice #</th>
								<th>Status</th>
								<th>Subtotal</th>
								<th>Created</th>
							</tr>
						</thead>
						<tbody>
							{#each invoices as inv}
								<tr>
									<td><a href="/invoice/{inv.id}">{inv.invoice_number}</a></td>
									<td><StatusPill status={inv.status} /></td>
									<td>{formatValue(inv.subtotal, po.currency)}</td>
									<td>{formatDate(inv.created_at)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}

			<div class="section card">
				<h2>Activity</h2>
				<ActivityTimeline entityType="PO" entityId={po.id} />
			</div>

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

			{#if showAddLineDialog}
				<div class="dialog-backdrop" data-testid="add-line-dialog">
					<div class="dialog-card">
						<h3>Add Line</h3>
						<div class="add-line-fields">
							<label>
								<span class="field-label">Part Number</span>
								<input type="text" bind:value={newLinePart} />
							</label>
							<label>
								<span class="field-label">Description</span>
								<input type="text" bind:value={newLineDescription} />
							</label>
							<label>
								<span class="field-label">Quantity</span>
								<input type="number" min="1" bind:value={newLineQuantity} />
							</label>
							<label>
								<span class="field-label">UoM</span>
								<input type="text" bind:value={newLineUom} />
							</label>
							<label>
								<span class="field-label">Unit Price</span>
								<input type="text" bind:value={newLineUnitPrice} />
							</label>
							<label>
								<span class="field-label">HS Code</span>
								<input type="text" bind:value={newLineHsCode} />
							</label>
							<label>
								<span class="field-label">Country of Origin</span>
								<input type="text" bind:value={newLineCountry} />
							</label>
						</div>
						{#if addLineError}
							<p class="error-message">{addLineError}</p>
						{/if}
						<div class="dialog-actions">
							<button class="btn btn-secondary" onclick={() => (showAddLineDialog = false)}>Cancel</button>
							<button class="btn btn-primary" onclick={handleAddLineSubmit}>Add</button>
						</div>
					</div>
				</div>
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

	.info-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
	}

	.info-item .field-label {
		display: block;
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin-bottom: var(--space-1);
	}

	.info-item .value {
		font-size: var(--font-size-base);
		color: var(--gray-900);
	}

	.section h2 {
		margin-bottom: var(--space-4);
	}

	.terms-text {
		white-space: pre-wrap;
	}

	.error-message {
		color: var(--red-600);
		font-size: var(--font-size-sm);
		margin-top: var(--space-2);
	}

	.rejection-record {
		padding: var(--space-3) 0;
		border-bottom: 1px solid var(--gray-100);
	}

	.rejection-record:last-child {
		border-bottom: none;
	}

	.rejection-comment {
		color: var(--gray-800);
		margin-bottom: var(--space-1);
	}

	.rejection-date {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
	}

	.badge-cert {
		background-color: var(--amber-100);
		color: var(--amber-800);
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
