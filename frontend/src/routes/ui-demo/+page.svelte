<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import StatusPill from '$lib/ui/StatusPill.svelte';
	import ProgressBar from '$lib/ui/ProgressBar.svelte';
	import Input from '$lib/ui/Input.svelte';
	import Select from '$lib/ui/Select.svelte';
	import DateInput from '$lib/ui/DateInput.svelte';
	import Toggle from '$lib/ui/Toggle.svelte';
	import FormField from '$lib/ui/FormField.svelte';
	import PanelCard from '$lib/ui/PanelCard.svelte';
	import AttributeList from '$lib/ui/AttributeList.svelte';
	import FormCard from '$lib/ui/FormCard.svelte';
	import KpiCard from '$lib/ui/KpiCard.svelte';
	import Timeline from '$lib/ui/Timeline.svelte';
	import ActivityFeed from '$lib/ui/ActivityFeed.svelte';
	import LoadingState from '$lib/ui/LoadingState.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import ErrorState from '$lib/ui/ErrorState.svelte';
	import DataTable from '$lib/ui/DataTable.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import DetailHeader from '$lib/ui/DetailHeader.svelte';
	import Sidebar from '$lib/ui/Sidebar.svelte';
	import TopBar from '$lib/ui/TopBar.svelte';

	let lastClicked = $state('');
	let page = $state(1);
	const tableRows = [
		{ id: 'row-1', name: 'Row 1' },
		{ id: 'row-2', name: 'Row 2' }
	];
	const tableColumns = [
		{ key: 'name', label: 'Name', render: (r: { name: string }) => r.name }
	];
</script>

<svelte:head>
	<title>UI Demo</title>
</svelte:head>

<h1>Phase 4.0 UI Demo</h1>

<section>
	<h2>Button</h2>
	<div style="display:flex;gap:1rem;">
		<Button data-testid="ui-btn-primary">Primary</Button>
		<Button variant="secondary" data-testid="ui-btn-secondary">Secondary</Button>
		<Button variant="ghost" data-testid="ui-btn-ghost">Ghost</Button>
		<Button disabled data-testid="ui-btn-disabled">Disabled</Button>
	</div>
</section>

<section>
	<h2>StatusPill</h2>
	<div style="display:flex;gap:1rem;flex-wrap:wrap;">
		<StatusPill tone="green" label="Delivered" data-testid="ui-pill-green" />
		<StatusPill tone="blue" label="In Transit" data-testid="ui-pill-blue" />
		<StatusPill tone="orange" label="In Production" data-testid="ui-pill-orange" />
		<StatusPill tone="red" label="Overdue" data-testid="ui-pill-red" />
		<StatusPill tone="gray" label="Draft" data-testid="ui-pill-gray" />
	</div>
</section>

<section>
	<h2>ProgressBar</h2>
	<ProgressBar value={60} label="60%" data-testid="ui-progress-60" />
</section>

<section>
	<h2>Form controls</h2>
	<div style="display:flex;flex-direction:column;gap:0.75rem;max-width:24rem;">
		<label>Name <Input data-testid="ui-input-name" /></label>
		<label>Country
			<Select
				options={[{ value: '', label: 'Select...' }, { value: 'US', label: 'United States' }, { value: 'IN', label: 'India' }]}
				data-testid="ui-select-country"
			/>
		</label>
		<label>Due <DateInput data-testid="ui-date-due" /></label>
		<Toggle label="Notifications" data-testid="ui-toggle" />
		<Input ariaLabel="Search" data-testid="ui-input-search" />
		<Select
			ariaLabel="Status"
			options={[{ value: '', label: 'Select...' }, { value: 'active', label: 'Active' }]}
			data-testid="ui-select-status"
		/>
		<DateInput ariaLabel="Delivery date" data-testid="ui-date-delivery" />
	</div>
</section>

<section>
	<h2>FormField</h2>
	<FormField
		label="Part number"
		error="Part number is required"
		required
		data-testid="ui-field"
	>
		{#snippet children({ invalid })}
			<Input data-testid="ui-field-input" invalid={invalid} />
		{/snippet}
	</FormField>
	<FormField label="Email" data-testid="ui-field-email">
		{#snippet children({ invalid })}
			<Input data-testid="ui-field-email-input" invalid={invalid} />
		{/snippet}
	</FormField>
</section>

<section>
	<h2>Panel + Attributes</h2>
	<PanelCard title="Details" data-testid="ui-panel">
		<AttributeList
			items={[
				{ label: 'Vendor', value: 'Acme Inc' },
				{ label: 'Country', value: 'US' }
			]}
			data-testid="ui-attr-list"
		/>
	</PanelCard>
	<PanelCard title="Line items" data-testid="ui-panel-lineitems">
		<AttributeList
			label="PO summary"
			items={[{ label: 'Total', value: '$100' }]}
			data-testid="ui-attr-list-labeled"
		/>
	</PanelCard>
</section>

<section>
	<h2>FormCard</h2>
	<FormCard title="New thing" onSubmit={() => console.log('submit')} onCancel={() => console.log('cancel')} data-testid="ui-formcard">
		<label>Thing name <Input data-testid="ui-formcard-input" /></label>
	</FormCard>
	<FormCard title="Edit vendor" onSubmit={() => console.log('submit')} data-testid="ui-formcard-editvendor">
		<label>Name <Input data-testid="ui-formcard-editvendor-input" /></label>
	</FormCard>
</section>

<section>
	<h2>KpiCard</h2>
	<KpiCard
		label="OUTSTANDING"
		value="$24,300"
		delta={{ value: '+12%', tone: 'positive' }}
		data-testid="ui-kpi"
	>
		{#snippet icon()}
			<span data-testid="ui-kpi-icon">📄</span>
		{/snippet}
	</KpiCard>
	<KpiCard label="Pending POs" value="7" data-testid="ui-kpi-pending" />
</section>

<section>
	<h2>Timeline</h2>
	<Timeline
		steps={[
			{ label: 'Queued', state: 'done' },
			{ label: 'In production', state: 'current', detail: 'Day 2 of 5' },
			{ label: 'QC inspection', state: 'upcoming' }
		]}
		data-testid="ui-timeline"
	/>
</section>

<section>
	<h2>Timeline (overdue state)</h2>
	<Timeline
		steps={[
			{ label: 'Raw materials', state: 'overdue', detail: 'Overdue 4d' }
		]}
		label="Overdue stage"
		data-testid="ui-timeline-overdue"
	/>
</section>

<section>
	<h2>ActivityFeed</h2>
	<ActivityFeed
		entries={[
			{ id: '1', primary: 'PO accepted', secondary: '2m ago', tone: 'green' },
			{ id: '2', primary: 'Invoice submitted', secondary: '1h ago', tone: 'blue' }
		]}
		data-testid="ui-feed"
	/>
</section>

<section>
	<h2>State primitives</h2>
	<div style="display:flex;flex-direction:column;gap:1.5rem;">
		<LoadingState data-testid="ui-loading" />
		<EmptyState title="No results" description="Try adjusting filters." data-testid="ui-empty" />
		<ErrorState message="Something broke" onRetry={() => console.log('retry')} data-testid="ui-error" />
	</div>
</section>

<section>
	<h2>DataTable</h2>
	<DataTable
		columns={tableColumns}
		rows={tableRows}
		pagination={{
			page,
			pageSize: 2,
			total: 10,
			onPageChange: (p) => (page = p)
		}}
		onRowClick={(row) => (lastClicked = row.id)}
		data-testid="ui-table"
	/>
	<p data-testid="ui-table-click">{lastClicked}</p>
	<DataTable
		label="Users"
		columns={tableColumns}
		rows={tableRows}
		data-testid="ui-table-labeled"
	/>
</section>

<section>
	<h2>Headers</h2>
	<PageHeader title="Invoices" subtitle="Manage invoicing" data-testid="ui-pageheader">
		{#snippet action()}
			<Button data-testid="ui-pageheader-action">+ New invoice</Button>
		{/snippet}
	</PageHeader>
	<PageHeader title="Purchase Orders" data-testid="ui-pageheader-po" />
	<DetailHeader
		backHref="/ui-demo"
		backLabel="All invoices"
		title="INV-001"
		subtitle="Acme Inc"
		data-testid="ui-detailheader"
	>
		{#snippet statusPill()}
			<StatusPill tone="blue" label="Submitted" />
		{/snippet}
	</DetailHeader>
	<DetailHeader
		backHref="/ui-demo"
		backLabel="All POs"
		title="PO-001"
		data-testid="ui-detailheader-po"
	/>
</section>

<section>
	<h2>Sidebar</h2>
	<Sidebar role="ADMIN" roleLabel="Supply Manager" data-testid="ui-sidebar">
		{#snippet footer()}
			<div>
				<strong>Demo workspace</strong>
				<div>All data is simulated</div>
			</div>
		{/snippet}
	</Sidebar>
</section>

<section>
	<h2>TopBar</h2>
	<TopBar breadcrumb="Workspace / Operations" onToggleSidebar={() => {}} data-testid="ui-topbar" />
</section>
