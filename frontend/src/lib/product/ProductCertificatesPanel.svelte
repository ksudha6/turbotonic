<script lang="ts">
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import Button from '$lib/ui/Button.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Select from '$lib/ui/Select.svelte';
	import DateInput from '$lib/ui/DateInput.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import type {
		CertificateListItem,
		CertificateStatus,
		QualificationTypeListItem
	} from '$lib/types';

	const MAX_FILE_SIZE = 10 * 1024 * 1024;

	export type CertificateAddFields = {
		qualification_type_id: string;
		target_market: string;
		cert_number: string;
		issuer: string;
		testing_lab: string;
		issue_date: string;
		expiry_date: string | null;
		test_date: string | null;
	};

	let {
		certs,
		qualifications,
		canManage,
		error = '',
		addError = '',
		adding = false,
		on_add_cert,
		on_upload_doc
	}: {
		certs: CertificateListItem[];
		qualifications: QualificationTypeListItem[];
		canManage: boolean;
		error?: string;
		addError?: string;
		adding?: boolean;
		on_add_cert: (fields: CertificateAddFields) => Promise<void> | void;
		on_upload_doc: (certId: string, file: File) => Promise<void> | void;
	} = $props();

	let showAddForm: boolean = $state(false);
	let qualification_type_id: string = $state('');
	let target_market: string = $state('');
	let cert_number: string = $state('');
	let issuer: string = $state('');
	let testing_lab: string = $state('');
	let issue_date: string = $state('');
	let expiry_date: string = $state('');
	let test_date: string = $state('');

	let qualError: string = $state('');
	let targetMarketError: string = $state('');
	let certNumberError: string = $state('');
	let issuerError: string = $state('');
	let issueDateError: string = $state('');
	let uploadErrors: Record<string, string> = $state({});

	const qualificationById = $derived(() => {
		const map: Record<string, QualificationTypeListItem> = {};
		for (const q of qualifications) map[q.id] = q;
		return map;
	});

	const qualOptions = $derived([
		{ value: '', label: 'Select qualification…' },
		...qualifications.map((q) => ({ value: q.id, label: `${q.name} — ${q.target_market}` }))
	]);

	$effect(() => {
		if (!qualification_type_id) return;
		const qt = qualificationById()[qualification_type_id];
		if (qt && target_market.trim().length === 0) target_market = qt.target_market;
	});

	const groupedCerts = $derived(() => {
		const groups: Record<string, { label: string; rows: CertificateListItem[] }> = {};
		for (const cert of certs) {
			const qt = qualificationById()[cert.qualification_type_id];
			const key = cert.qualification_type_id;
			const label = qt ? `${qt.name} — ${qt.target_market}` : cert.qualification_type_id;
			if (!groups[key]) groups[key] = { label, rows: [] };
			groups[key].rows.push(cert);
		}
		return groups;
	});

	type Tone = 'green' | 'gray' | 'blue' | 'orange' | 'red';
	function statusTone(status: CertificateStatus): Tone {
		if (status === 'VALID') return 'green';
		if (status === 'EXPIRED') return 'red';
		return 'gray';
	}

	function isBlank(v: string): boolean {
		return v.trim().length === 0;
	}

	function validate(): boolean {
		qualError = '';
		targetMarketError = '';
		certNumberError = '';
		issuerError = '';
		issueDateError = '';
		let ok = true;
		if (isBlank(qualification_type_id)) {
			qualError = 'Qualification is required.';
			ok = false;
		}
		if (isBlank(target_market)) {
			targetMarketError = 'Target market is required.';
			ok = false;
		}
		if (isBlank(cert_number)) {
			certNumberError = 'Cert number is required.';
			ok = false;
		}
		if (isBlank(issuer)) {
			issuerError = 'Issuer is required.';
			ok = false;
		}
		if (isBlank(issue_date)) {
			issueDateError = 'Issue date is required.';
			ok = false;
		}
		return ok;
	}

	function resetForm() {
		qualification_type_id = '';
		target_market = '';
		cert_number = '';
		issuer = '';
		testing_lab = '';
		issue_date = '';
		expiry_date = '';
		test_date = '';
		qualError = '';
		targetMarketError = '';
		certNumberError = '';
		issuerError = '';
		issueDateError = '';
	}

	function toggleAddForm() {
		showAddForm = !showAddForm;
		if (!showAddForm) resetForm();
	}

	async function handleAddSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!validate()) return;
		await on_add_cert({
			qualification_type_id,
			target_market: target_market.trim(),
			cert_number: cert_number.trim(),
			issuer: issuer.trim(),
			testing_lab: testing_lab.trim(),
			issue_date,
			expiry_date: expiry_date || null,
			test_date: test_date || null
		});
	}

	let wasAdding = $state(false);
	$effect(() => {
		if (adding) wasAdding = true;
		else if (wasAdding && !addError) {
			wasAdding = false;
			showAddForm = false;
			resetForm();
		} else if (wasAdding && addError) {
			wasAdding = false;
		}
	});

	function formatDate(iso: string | null): string {
		if (!iso) return '—';
		return iso.slice(0, 10);
	}

	async function handleFileChange(certId: string, ev: Event) {
		const input = ev.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		input.value = '';
		if (!file) return;
		uploadErrors = { ...uploadErrors, [certId]: '' };
		if (file.type !== 'application/pdf') {
			uploadErrors = { ...uploadErrors, [certId]: 'File must be a PDF.' };
			return;
		}
		if (file.size > MAX_FILE_SIZE) {
			uploadErrors = { ...uploadErrors, [certId]: 'File exceeds 10MB.' };
			return;
		}
		try {
			await on_upload_doc(certId, file);
		} catch (err) {
			uploadErrors = {
				...uploadErrors,
				[certId]: err instanceof Error ? err.message : 'Upload failed.'
			};
		}
	}

	function triggerUpload(certId: string) {
		const el = document.querySelector<HTMLInputElement>(
			`[data-testid="product-certificates-row-upload-input-${certId}"]`
		);
		el?.click();
	}
</script>

<div data-testid="product-certificates-panel">
	<PanelCard title="Certificates">
		{#snippet action()}
			{#if canManage}
				<Button
					variant="secondary"
					onclick={toggleAddForm}
					data-testid="product-certificates-add-trigger"
					disabled={qualifications.length === 0}
				>
					{showAddForm ? 'Cancel' : 'Add Certificate'}
				</Button>
			{/if}
		{/snippet}

		{#if error}
			<p
				class="product-certificates-panel__error"
				role="alert"
				data-testid="product-certificates-error"
			>
				{error}
			</p>
		{/if}

		{#if canManage && qualifications.length === 0}
			<p class="product-certificates-panel__hint">
				Assign a qualification first to upload certificates against it.
			</p>
		{/if}

		{#if canManage && showAddForm}
			<form
				class="product-certificates-panel__add-form"
				onsubmit={handleAddSubmit}
				data-testid="product-certificates-add-form"
				novalidate
			>
				<div class="product-certificates-panel__add-grid">
					<FormField label="Qualification" required error={qualError}>
						{#snippet children({ invalid })}
							<Select
								bind:value={qualification_type_id}
								options={qualOptions}
								{invalid}
								ariaLabel="Qualification"
								data-testid="product-certificates-add-qualification"
							/>
						{/snippet}
					</FormField>

					<FormField label="Target Market" required error={targetMarketError}>
						{#snippet children({ invalid })}
							<Input
								bind:value={target_market}
								{invalid}
								ariaLabel="Target market"
								data-testid="product-certificates-add-target-market"
							/>
						{/snippet}
					</FormField>

					<FormField label="Cert Number" required error={certNumberError}>
						{#snippet children({ invalid })}
							<Input
								bind:value={cert_number}
								{invalid}
								ariaLabel="Cert number"
								data-testid="product-certificates-add-cert-number"
							/>
						{/snippet}
					</FormField>

					<FormField label="Issuer" required error={issuerError}>
						{#snippet children({ invalid })}
							<Input
								bind:value={issuer}
								{invalid}
								ariaLabel="Issuer"
								data-testid="product-certificates-add-issuer"
							/>
						{/snippet}
					</FormField>

					<FormField label="Testing Lab">
						{#snippet children()}
							<Input
								bind:value={testing_lab}
								ariaLabel="Testing lab"
								data-testid="product-certificates-add-testing-lab"
							/>
						{/snippet}
					</FormField>

					<FormField label="Issue Date" required error={issueDateError}>
						{#snippet children({ invalid })}
							<DateInput
								bind:value={issue_date}
								{invalid}
								ariaLabel="Issue date"
								data-testid="product-certificates-add-issue-date"
							/>
						{/snippet}
					</FormField>

					<FormField label="Expiry Date">
						{#snippet children()}
							<DateInput
								bind:value={expiry_date}
								ariaLabel="Expiry date"
								data-testid="product-certificates-add-expiry-date"
							/>
						{/snippet}
					</FormField>

					<FormField label="Test Date">
						{#snippet children()}
							<DateInput
								bind:value={test_date}
								ariaLabel="Test date"
								data-testid="product-certificates-add-test-date"
							/>
						{/snippet}
					</FormField>
				</div>

				{#if addError}
					<p
						class="product-certificates-panel__error"
						role="alert"
						data-testid="product-certificates-add-error"
					>
						{addError}
					</p>
				{/if}

				<div class="product-certificates-panel__add-footer">
					<Button
						variant="secondary"
						onclick={toggleAddForm}
						data-testid="product-certificates-add-cancel"
					>
						Cancel
					</Button>
					<Button
						type="submit"
						variant="primary"
						disabled={adding}
						data-testid="product-certificates-add-submit"
					>
						{adding ? 'Adding…' : 'Add Certificate'}
					</Button>
				</div>
			</form>
		{/if}

		{#if certs.length === 0}
			<EmptyState title="No certificates uploaded yet." />
		{:else}
			{#each Object.entries(groupedCerts()) as [qtId, group] (qtId)}
				<section class="product-certificates-panel__group">
					<h3 class="product-certificates-panel__group-heading">{group.label}</h3>
					<ul class="product-certificates-panel__list">
						{#each group.rows as cert (cert.id)}
							<li
								class="product-certificates-panel__row"
								data-testid={`product-certificates-row-${cert.id}`}
							>
								<div class="product-certificates-panel__row-info">
									<span class="product-certificates-panel__cert-number">{cert.cert_number}</span>
									<span class="product-certificates-panel__cert-meta">
										{cert.issuer} · {cert.target_market} · expires {formatDate(cert.expiry_date)}
									</span>
									{#if uploadErrors[cert.id]}
										<span
											class="product-certificates-panel__upload-error"
											role="alert"
											data-testid={`product-certificates-row-upload-error-${cert.id}`}
										>
											{uploadErrors[cert.id]}
										</span>
									{/if}
								</div>
								<div class="product-certificates-panel__row-meta">
									<StatusPill
										tone={statusTone(cert.status)}
										label={cert.status}
										data-testid={`product-certificates-row-status-${cert.id}`}
									/>
									{#if canManage && cert.document_id === null}
										<Button
											variant="secondary"
											onclick={() => triggerUpload(cert.id)}
											data-testid={`product-certificates-row-upload-${cert.id}`}
										>
											Upload PDF
										</Button>
										<input
											type="file"
											accept="application/pdf"
											class="product-certificates-panel__file-input"
											onchange={(ev) => handleFileChange(cert.id, ev)}
											data-testid={`product-certificates-row-upload-input-${cert.id}`}
										/>
									{/if}
								</div>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		{/if}
	</PanelCard>
</div>

<style>
	.product-certificates-panel__error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		margin: 0 0 var(--space-3);
	}
	.product-certificates-panel__hint {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
		margin: 0 0 var(--space-3);
	}
	.product-certificates-panel__add-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		background-color: var(--gray-50);
		border: 1px solid var(--gray-200);
		border-radius: var(--radius-md);
		margin-bottom: var(--space-4);
	}
	.product-certificates-panel__add-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-3);
	}
	@media (min-width: 768px) {
		.product-certificates-panel__add-grid {
			grid-template-columns: 1fr 1fr;
		}
	}
	.product-certificates-panel__add-footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}
	.product-certificates-panel__group {
		margin-top: var(--space-4);
	}
	.product-certificates-panel__group:first-of-type {
		margin-top: 0;
	}
	.product-certificates-panel__group-heading {
		font-size: var(--font-size-base);
		font-weight: 600;
		color: var(--gray-900);
		margin: 0 0 var(--space-2);
	}
	.product-certificates-panel__list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}
	.product-certificates-panel__row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--gray-100);
	}
	.product-certificates-panel__row:last-child {
		border-bottom: none;
	}
	.product-certificates-panel__row-info {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.product-certificates-panel__cert-number {
		font-weight: 500;
		color: var(--gray-900);
	}
	.product-certificates-panel__cert-meta {
		font-size: var(--font-size-sm);
		color: var(--gray-700);
	}
	.product-certificates-panel__upload-error {
		font-size: var(--font-size-sm);
		color: var(--red-700);
	}
	.product-certificates-panel__row-meta {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	.product-certificates-panel__file-input {
		display: none;
	}
</style>
