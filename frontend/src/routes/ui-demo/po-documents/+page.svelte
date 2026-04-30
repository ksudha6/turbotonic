<script lang="ts">
	import Select from '$lib/ui/Select.svelte';
	import PoDocumentsPanel from '$lib/po/PoDocumentsPanel.svelte';
	import type { PurchaseOrder, User, UserRole } from '$lib/types';

	// ---------------------------------------------------------------------------
	// POFileListItem mirrors the shape returned by GET /api/v1/po/{id}/documents
	// ---------------------------------------------------------------------------
	interface POFileListItem {
		id: string;
		entity_type: string;
		entity_id: string;
		file_type: string;
		original_name: string;
		content_type: string;
		size_bytes: number;
		uploaded_at: string;
		uploaded_by: string | null;
		uploaded_by_username: string | null;
	}

	// ---------------------------------------------------------------------------
	// Toggle option types
	// ---------------------------------------------------------------------------
	type POTypeOption = 'PROCUREMENT' | 'OPEX';
	type RoleOption =
		| 'ADMIN'
		| 'SM'
		| 'VENDOR_OWN'
		| 'VENDOR_OTHER'
		| 'FREIGHT_MANAGER'
		| 'PROCUREMENT_MANAGER'
		| 'QUALITY_LAB';
	type FilesOption = '0' | '1' | '3';

	const PO_TYPE_OPTIONS: ReadonlyArray<{ value: POTypeOption; label: string }> = [
		{ value: 'PROCUREMENT', label: 'PROCUREMENT' },
		{ value: 'OPEX', label: 'OPEX' }
	];

	const ROLE_OPTIONS: ReadonlyArray<{ value: RoleOption; label: string }> = [
		{ value: 'ADMIN', label: 'ADMIN' },
		{ value: 'SM', label: 'SM' },
		{ value: 'VENDOR_OWN', label: 'VENDOR (own)' },
		{ value: 'VENDOR_OTHER', label: 'VENDOR (other)' },
		{ value: 'FREIGHT_MANAGER', label: 'FREIGHT_MANAGER' },
		{ value: 'PROCUREMENT_MANAGER', label: 'PROCUREMENT_MANAGER' },
		{ value: 'QUALITY_LAB', label: 'QUALITY_LAB' }
	];

	const FILES_OPTIONS: ReadonlyArray<{ value: FilesOption; label: string }> = [
		{ value: '0', label: '0 files' },
		{ value: '1', label: '1 file' },
		{ value: '3', label: '3 files' }
	];

	// ---------------------------------------------------------------------------
	// Toggle state
	// ---------------------------------------------------------------------------
	let poTypeValue: string = $state('PROCUREMENT');
	let roleValue: string = $state('SM');
	let filesValue: string = $state('1');

	const poTypeOption = $derived(poTypeValue as POTypeOption);
	const roleOption = $derived(roleValue as RoleOption);
	const filesOption = $derived(filesValue as FilesOption);

	// ---------------------------------------------------------------------------
	// Derived fake PO — vendor_id fixed so VENDOR_OWN matches
	// ---------------------------------------------------------------------------
	const PO_VENDOR_ID = 'vendor-A';

	const po = $derived<PurchaseOrder>({
		id: 'demo-po-docs',
		po_number: 'PO-2026-DOCS',
		status: 'ACCEPTED',
		po_type: poTypeOption,
		vendor_id: PO_VENDOR_ID,
		vendor_name: 'Acme Manufacturing',
		vendor_country: 'CN',
		buyer_name: 'TurboTonic Ltd',
		buyer_country: 'US',
		ship_to_address: '123 Commerce St, New York, NY',
		payment_terms: 'NET30',
		currency: 'USD',
		issued_date: '2026-01-15T00:00:00+00:00',
		required_delivery_date: '2026-06-30T00:00:00+00:00',
		terms_and_conditions: 'Standard terms and conditions apply.',
		incoterm: 'FOB',
		port_of_loading: 'CNSHA',
		port_of_discharge: 'USLAX',
		country_of_origin: 'CN',
		country_of_destination: 'US',
		marketplace: null,
		line_items: [],
		rejection_history: [],
		total_value: '48500.00',
		created_at: '2026-01-10T00:00:00+00:00',
		updated_at: '2026-01-10T00:00:00+00:00',
		round_count: 0,
		last_actor_role: null,
		advance_paid_at: null,
		has_removed_line: false,
		current_milestone: null
	} as unknown as PurchaseOrder);

	// ---------------------------------------------------------------------------
	// Derived fake User
	// ---------------------------------------------------------------------------
	const user = $derived<User>(buildUser(roleOption));

	function buildUser(opt: RoleOption): User {
		if (opt === 'VENDOR_OWN') {
			return {
				id: 'u-vendor-own',
				username: 'vendor_own',
				display_name: 'Vendor Own',
				role: 'VENDOR',
				status: 'ACTIVE',
				vendor_id: PO_VENDOR_ID,
				email: null
			};
		}
		if (opt === 'VENDOR_OTHER') {
			return {
				id: 'u-vendor-other',
				username: 'vendor_other',
				display_name: 'Vendor Other',
				role: 'VENDOR',
				status: 'ACTIVE',
				vendor_id: 'vendor-B',
				email: null
			};
		}
		const roleMap: Record<Exclude<RoleOption, 'VENDOR_OWN' | 'VENDOR_OTHER'>, UserRole> = {
			ADMIN: 'ADMIN',
			SM: 'SM',
			FREIGHT_MANAGER: 'FREIGHT_MANAGER',
			PROCUREMENT_MANAGER: 'PROCUREMENT_MANAGER',
			QUALITY_LAB: 'QUALITY_LAB'
		};
		return {
			id: `u-${opt.toLowerCase()}`,
			username: opt.toLowerCase(),
			display_name: opt,
			role: roleMap[opt as keyof typeof roleMap],
			status: 'ACTIVE',
			vendor_id: null,
			email: null
		};
	}

	// ---------------------------------------------------------------------------
	// Derived fake file list
	// ---------------------------------------------------------------------------
	const ALL_FILES: POFileListItem[] = [
		{
			id: 'file-001',
			entity_type: 'PO',
			entity_id: 'demo-po-docs',
			file_type: 'SIGNED_PO',
			original_name: 'signed-po.pdf',
			content_type: 'application/pdf',
			size_bytes: 48210,
			uploaded_at: '2026-02-01T10:00:00+00:00',
			uploaded_by: 'u-alice',
			uploaded_by_username: 'alice'
		},
		{
			id: 'file-002',
			entity_type: 'PO',
			entity_id: 'demo-po-docs',
			file_type: 'COUNTERSIGNED_PO',
			original_name: 'countersigned-po.pdf',
			content_type: 'application/pdf',
			size_bytes: 51340,
			uploaded_at: '2026-02-05T14:30:00+00:00',
			uploaded_by: 'u-bob',
			uploaded_by_username: 'bob'
		},
		{
			id: 'file-003',
			entity_type: 'PO',
			entity_id: 'demo-po-docs',
			file_type: 'AMENDMENT',
			original_name: 'amendment-1.pdf',
			content_type: 'application/pdf',
			size_bytes: 22100,
			uploaded_at: '2026-03-10T09:15:00+00:00',
			uploaded_by: 'u-carol',
			uploaded_by_username: 'carol'
		}
	];

	const files = $derived<POFileListItem[]>(buildFiles(filesOption));

	function buildFiles(opt: FilesOption): POFileListItem[] {
		if (opt === '0') return [];
		if (opt === '1') return ALL_FILES.slice(0, 1);
		return ALL_FILES;
	}

	// ---------------------------------------------------------------------------
	// Intercept fetch for upload + delete so demo actions don't hit the backend.
	// Scoped to this page only — overwritten when the page unloads.
	// ---------------------------------------------------------------------------
	const originalFetch = globalThis.fetch;

	$effect(() => {
		globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
			const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url;
			const method = (init?.method ?? (input instanceof Request ? input.method : 'GET')).toUpperCase();

			// Match /api/v1/po/.../documents or /api/v1/po/.../documents/{id}
			if (/\/api\/v1\/po\/[^/]+\/documents/.test(url)) {
				if (method === 'POST') {
					// Simulate upload — return a fake new file entry
					const newFile: POFileListItem = {
						id: `file-mock-${Date.now()}`,
						entity_type: 'PO',
						entity_id: 'demo-po-docs',
						file_type: 'SIGNED_PO',
						original_name: 'uploaded-file.pdf',
						content_type: 'application/pdf',
						size_bytes: 10240,
						uploaded_at: new Date().toISOString(),
						uploaded_by: null,
						uploaded_by_username: 'demo'
					};
					return new Response(JSON.stringify(newFile), {
						status: 200,
						headers: { 'Content-Type': 'application/json' }
					});
				}
				if (method === 'DELETE') {
					return new Response(null, { status: 204 });
				}
			}
			return originalFetch(input, init);
		};

		return () => {
			globalThis.fetch = originalFetch;
		};
	});
</script>

<svelte:head>
	<title>PO documents mock — iter 084</title>
</svelte:head>

<div class="page">
	<header class="page__intro">
		<h1>PO documents mock — iter 084</h1>
		<p>
			Toggleable matrix for the Documents panel: PO type, role, and file count. Auth-free visual
			verification surface.
		</p>
	</header>

	<section class="page__controls" aria-label="Mock controls">
		<h2>Controls</h2>
		<div class="page__grid">
			<label class="page__field">
				<span>PO type</span>
				<Select
					bind:value={poTypeValue}
					options={PO_TYPE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="PO type"
					data-testid="ui-demo-po-type-toggle"
				/>
			</label>
			<label class="page__field">
				<span>Role</span>
				<Select
					bind:value={roleValue}
					options={ROLE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Role"
					data-testid="ui-demo-role-toggle"
				/>
			</label>
			<label class="page__field">
				<span>Files</span>
				<Select
					bind:value={filesValue}
					options={FILES_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
					ariaLabel="Files"
					data-testid="ui-demo-files-toggle"
				/>
			</label>
		</div>
	</section>

	<section class="page__section">
		<h2>Documents Panel</h2>
		<PoDocumentsPanel {po} {user} mockFiles={files} />
		{#if !files.length}
			<p class="page__hint">
				Panel hidden when empty + view-only role; shows empty state when empty + manage role.
			</p>
		{/if}
	</section>
</div>

<style>
	.page {
		max-width: 80rem;
		margin: 0 auto;
		padding: var(--space-6) var(--space-4) var(--space-20);
		display: flex;
		flex-direction: column;
		gap: var(--space-8);
	}
	.page__intro h1 {
		font-size: var(--font-size-2xl);
		margin: 0 0 var(--space-2);
	}
	.page__intro p {
		font-size: var(--font-size-sm);
		color: var(--gray-600);
		margin: 0;
	}
	.page__controls {
		background: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-lg);
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.page__controls h2 {
		font-size: var(--font-size-lg);
		margin: 0;
	}
	.page__grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--space-3);
	}
	.page__field {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.page__section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-4);
		border: 1px dashed var(--gray-300);
		border-radius: var(--radius-lg);
	}
	.page__section h2 {
		font-size: var(--font-size-lg);
		margin: 0;
	}
	.page__hint {
		font-size: var(--font-size-sm);
		color: var(--gray-500);
		margin: 0;
	}
</style>
