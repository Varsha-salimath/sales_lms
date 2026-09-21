<template>
	<section class="space-y-4">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
			<div class="min-w-0">
				<h2 class="text-base font-semibold text-ink-gray-9">
					{{ embedded ? __('Learner Certification') : __('OJT Certification Analytics') }}
				</h2>
				<p class="text-xs text-ink-gray-6 mt-1">
					{{
						embedded
							? __(
									'Track OJT performance, assessment scores and certification status.'
								)
							: __(
									'Learner metrics from the Sales Admin OJT Certification sheet. Counts and scores are calculated from synced data.'
								)
					}}
				</p>
			</div>
			<div class="flex flex-wrap items-center gap-2 shrink-0">
				<span class="text-xs text-ink-gray-6">
					{{ lastSyncedLabel }}
				</span>
				<Button variant="outline" @click="showCsvImport = true">
					{{ __('Import CSV') }}
				</Button>
				<Button
					variant="outline"
					:loading="syncing"
					:disabled="syncing"
					@click="syncSheet"
				>
					{{ __('Sync Data') }}
				</Button>
			</div>
		</div>

		<div
			v-if="overview.loading && !overview.data"
			class="flex flex-nowrap gap-4 overflow-x-auto pb-1"
		>
			<div
				v-for="n in 6"
				:key="n"
				class="border rounded-lg bg-surface-white p-4 h-[92px] animate-pulse flex-1 min-w-[11rem] shrink-0"
			>
				<div class="h-3 w-24 bg-surface-gray-2 rounded mb-3" />
				<div class="h-7 w-16 bg-surface-gray-2 rounded" />
			</div>
		</div>
		<div v-else-if="overview.error" class="border rounded-lg bg-surface-white p-4 text-sm text-ink-red-4">
			{{ overview.error?.messages?.[0] || __('Failed to load OJT certification analytics.') }}
		</div>
		<template v-else>
			<div class="flex flex-nowrap gap-4 overflow-x-auto pb-1">
				<button
					v-for="card in kpiCards"
					:key="card.key"
					type="button"
					class="border rounded-lg bg-surface-white p-4 text-left transition-colors flex-1 min-w-[11rem] shrink-0"
					:class="
						activeFunnel === kpiToFunnel[card.key]
							? 'ring-1 ring-blue-500 border-blue-500'
							: 'hover:bg-surface-gray-1'
					"
					@click="onKpiClick(card.key)"
				>
					<div class="text-sm text-ink-gray-6 mb-1">{{ card.label }}</div>
					<div class="text-3xl font-semibold text-ink-gray-9 mb-1 tabular-nums">
						{{ card.value }}
					</div>
					<div class="text-xs text-ink-gray-5">{{ card.subtext }}</div>
				</button>
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<div class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
					<h3 class="text-base font-semibold text-ink-gray-9 mb-1">
						{{ __('Certification funnel') }}
					</h3>
					<p class="text-xs text-ink-gray-6 mb-4">
						{{ __('Click a stage to filter the learner report. Stages are derived from attendance and scores in the sheet.') }}
					</p>
					<div v-if="!funnel.length" class="py-10 text-center text-sm text-ink-gray-6">
						{{ __('No funnel data yet. Sync the OJT sheet to load learners.') }}
					</div>
					<ol v-else class="space-y-2">
						<li v-for="(step, index) in funnel" :key="step.key">
							<button
								type="button"
								class="w-full flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors"
								:class="
									activeFunnel === step.key
										? 'border-blue-500 bg-blue-50'
										: 'border-outline-gray-1 hover:bg-surface-gray-1'
								"
								@click="setFunnelStage(step.key)"
							>
								<span class="flex items-center gap-3 min-w-0">
									<span
										class="flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium"
										:class="
											activeFunnel === step.key
												? 'bg-blue-600 text-white'
												: 'bg-surface-gray-2 text-ink-gray-7'
										"
									>
										{{ index + 1 }}
									</span>
									<span class="text-sm font-medium text-ink-gray-9 truncate">
										{{ step.label }}
									</span>
								</span>
								<span class="text-sm font-semibold tabular-nums text-ink-gray-9">
									{{ step.value }}
								</span>
							</button>
							<div
								v-if="index < funnel.length - 1"
								class="flex justify-center py-1 text-ink-gray-4"
								aria-hidden="true"
							>
								↓
							</div>
						</li>
					</ol>
				</div>

				<div class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
					<h3 class="text-base font-semibold text-ink-gray-9 mb-1">
						{{ __('Average product test scores') }}
					</h3>
					<p class="text-xs text-ink-gray-6 mb-3">
						{{ __('Each product test is scored out of 20 in the OJT sheet.') }}
					</p>
					<div
						v-if="productChartData.length"
						class="analytics-chart-area h-[280px] w-full max-w-full overflow-hidden"
					>
						<AxisChart
							:config="{
								data: productChartData,
								xAxis: {
									key: 'label',
									title: __('Product test'),
									type: 'category',
								},
								yAxis: {
									title: __('Average / 20'),
									echartOptions: {
										min: 0,
										max: 20,
									},
								},
								series: [
									{
										name: 'score',
										type: 'bar',
										echartOptions: {
											itemStyle: { color: '#0075ff' },
										},
									},
								],
							}"
						/>
					</div>
					<div
						v-else
						class="flex h-[280px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('No product test scores in the synced sheet.') }}
					</div>
				</div>
			</div>

			<div class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
				<div class="flex flex-col gap-3 mb-4">
					<div class="flex flex-col sm:flex-row sm:items-center gap-3 min-w-0">
						<h3 class="text-base font-semibold text-ink-gray-9 shrink-0">
							{{ __('Learner certification report') }}
						</h3>
						<div class="flex flex-wrap items-center gap-2 sm:ml-auto">
							<FormControl
								v-model="search"
								type="text"
								:placeholder="__('Search learner...')"
								class="learner-search-input w-40 sm:w-52 shrink-0"
								@input="onSearchInput"
							/>
							<FormControl
								v-model="location"
								type="select"
								:options="locationOptions"
								class="analytics-chart-filter w-36 shrink-0"
								@update:modelValue="onFilterChange"
							/>
							<FormControl
								v-model="batchStart"
								type="select"
								:options="batchOptions"
								class="analytics-chart-filter w-40 shrink-0"
								@update:modelValue="onFilterChange"
							/>
							<FormControl
								v-model="fromDate"
								type="date"
								class="analytics-chart-filter w-36 shrink-0"
								@update:modelValue="onFilterChange"
							/>
							<FormControl
								v-model="toDate"
								type="date"
								class="analytics-chart-filter w-36 shrink-0"
								@update:modelValue="onFilterChange"
							/>
							<Button variant="solid" :loading="exporting" @click="exportReport">
								{{ __('Export Report') }}
							</Button>
							<Button variant="outline" @click="openCreate">
								<template #prefix>
									<Plus class="h-4 w-4" />
								</template>
								{{ __('Add Learner Report') }}
							</Button>
						</div>
					</div>
					<p v-if="activeFunnel && activeFunnel !== 'total'" class="text-xs text-ink-gray-6">
						{{ __('Filtered by funnel stage: {0}').format(activeFunnelLabel) }}
						<button type="button" class="text-blue-600 font-medium ms-1" @click="setFunnelStage('total')">
							{{ __('Clear') }}
						</button>
					</p>
				</div>

				<div v-if="learners.loading" class="py-12 text-center text-sm text-ink-gray-6">
					{{ __('Loading learners...') }}
				</div>
				<div v-else-if="learners.error" class="py-12 text-center text-sm text-ink-red-4">
					{{ learners.error?.messages?.[0] || __('Failed to load learners.') }}
				</div>
				<div v-else-if="!learnerRows.length" class="py-12 text-center text-sm text-ink-gray-6">
					{{ __('No learners match your search or filter.') }}
				</div>
				<div v-else>
					<div class="overflow-x-auto">
						<table class="w-full text-sm min-w-[880px]">
							<thead>
								<tr class="border-b text-left text-ink-gray-6">
									<th
										v-for="col in columns"
										:key="col.key"
										class="py-2 pr-4 font-medium whitespace-nowrap"
									>
										<button
											v-if="col.sort"
											type="button"
											class="inline-flex items-center gap-1 hover:text-ink-gray-9"
											@click="toggleSort(col.key)"
										>
											{{ col.label }}
											<span v-if="sortBy === col.key" class="text-[10px]">
												{{ sortOrder === 'desc' ? '▼' : '▲' }}
											</span>
										</button>
										<span v-else>{{ col.label }}</span>
									</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="row in learnerRows"
									:key="row.name"
									class="border-b last:border-0 hover:bg-surface-gray-1 cursor-pointer"
									@click="openDetail(row)"
								>
									<td class="py-2.5 pr-4 font-medium text-ink-gray-9 whitespace-nowrap">
										{{ row.employee_name }}
									</td>
									<td class="py-2.5 pr-4 text-ink-gray-7">{{ row.email }}</td>
									<td class="py-2.5 pr-4 text-ink-gray-7 whitespace-nowrap">
										{{ row.location || '—' }}
									</td>
									<td class="py-2.5 pr-4 text-ink-gray-7 whitespace-nowrap">
										{{ formatDate(row.batch_start) }}
									</td>
									<td class="py-2.5 pr-4 tabular-nums text-ink-gray-8">
										{{ displayNumber(row.attendance_days) }}
									</td>
									<td class="py-2.5 pr-4 tabular-nums text-ink-gray-8">
										{{ displayNumber(row.ai_mock_score) }}
									</td>
									<td class="py-2.5 pr-4 tabular-nums text-ink-gray-8">
										{{ displayNumber(row.audit_score) }}
									</td>
									<td class="py-2.5 pr-4 tabular-nums text-ink-gray-8">
										{{ displayNumber(row.product_avg) }}
									</td>
									<td class="py-2.5 pr-4">
										<span
											class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
											:class="stageClass(row.stage)"
										>
											{{ row.stage || '—' }}
										</span>
									</td>
									<td class="py-2.5 pr-0 whitespace-nowrap">
										<Button variant="ghost" @click.stop="openEdit(row)">
											{{ __('Edit') }}
										</Button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-4">
						<div class="flex items-center gap-3 text-xs text-ink-gray-6">
							<span class="tabular-nums">
								{{
									__('Showing {0}–{1} of {2} learners').format(
										learners.data?.start || 0,
										learners.data?.end || 0,
										learners.data?.total || 0
									)
								}}
							</span>
							<FormControl
								v-model="pageLength"
								type="select"
								:options="pageLengthOptions"
								class="analytics-chart-filter w-20"
								@update:modelValue="onPageLengthChange"
							/>
						</div>
						<div class="flex flex-wrap items-center gap-1">
							<Button
								variant="outline"
								:disabled="page <= 1 || learners.loading"
								@click="goToPage(page - 1)"
							>
								{{ __('Previous') }}
							</Button>
							<button
								v-for="item in pageItems"
								:key="String(item)"
								type="button"
								class="min-w-8 h-8 px-2 rounded-md text-xs"
								:class="
									item === page
										? 'bg-surface-gray-2 text-ink-gray-9 font-semibold'
										: item === '…'
										? 'text-ink-gray-5 cursor-default'
										: 'text-ink-gray-7 hover:bg-surface-gray-1'
								"
								:disabled="item === '…'"
								@click="item !== '…' && goToPage(item)"
							>
								{{ item }}
							</button>
							<Button
								variant="outline"
								:disabled="page >= totalPages || learners.loading"
								@click="goToPage(page + 1)"
							>
								{{ __('Next') }}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</template>

		<Dialog
			v-model="showDetail"
			:options="{ size: 'xl' }"
		>
			<template #body-title>
				<div>
					<div class="text-lg font-semibold text-ink-gray-9">
						{{ selectedLearner?.employee_name || __('Learner') }}
					</div>
					<p class="text-sm text-ink-gray-6 mt-0.5">
						{{ selectedLearner?.email }}
					</p>
				</div>
			</template>
			<template #body-content>
				<div v-if="selectedLearner" class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
					<div v-for="field in detailFields" :key="field.key">
						<div class="text-xs text-ink-gray-5 mb-0.5">{{ field.label }}</div>
						<div class="text-ink-gray-9">{{ field.value }}</div>
					</div>
				</div>
			</template>
			<template #actions="{ close }">
				<div class="flex justify-end gap-2">
					<Button variant="subtle" @click="close">
						{{ __('Close') }}
					</Button>
					<Button
						variant="solid"
						@click="
							() => {
								close()
								openEdit(selectedLearner)
							}
						"
					>
						{{ __('Edit') }}
					</Button>
				</div>
			</template>
		</Dialog>

		<OJTCertificationReportForm v-model="showForm" :record="editingRow" @saved="onReportSaved" />
		<OJTAttendanceCsvImport v-model="showCsvImport" />
	</section>
</template>

<script setup>
import {
	AxisChart,
	Button,
	Dialog,
	FormControl,
	call,
	createResource,
	toast,
} from 'frappe-ui'
import { Plus } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import OJTCertificationReportForm from '@/components/Analytics/OJTCertificationReportForm.vue'
import OJTAttendanceCsvImport from '@/components/Analytics/OJTAttendanceCsvImport.vue'

defineProps({
	embedded: {
		type: Boolean,
		default: false,
	},
})

const ALL = '__all__'
const kpiToFunnel = {
	total: 'total',
	started: 'started',
	not_started: 'not_started',
	audit_completed: 'audit_completed',
}

const search = ref('')
const location = ref(ALL)
const batchStart = ref(ALL)
const fromDate = ref('')
const toDate = ref('')
const funnelStage = ref('total')
const sortBy = ref('employee_name')
const sortOrder = ref('asc')
const page = ref(1)
const pageLength = ref(25)
const showDetail = ref(false)
const selectedLearner = ref(null)
const showForm = ref(false)
const editingRow = ref(null)
const syncing = ref(false)
const showCsvImport = ref(false)
const exporting = ref(false)
let searchDebounce = null

const pageLengthOptions = [
	{ label: '10', value: 10 },
	{ label: '25', value: 25 },
	{ label: '50', value: 50 },
	{ label: '100', value: 100 },
]

const columns = [
	{ key: 'employee_name', label: __('Learner Name'), sort: true },
	{ key: 'email', label: __('Email ID'), sort: true },
	{ key: 'location', label: __('Location'), sort: true },
	{ key: 'batch_start', label: __('Batch Start'), sort: true },
	{ key: 'attendance_days', label: __('Attendance'), sort: true },
	{ key: 'ai_mock_score', label: __('AI Mock'), sort: true },
	{ key: 'audit_score', label: __('Audit / 20'), sort: true },
	{ key: 'product_avg', label: __('Product avg / 20'), sort: true },
	{ key: 'stage', label: __('Stage'), sort: true },
	{ key: 'actions', label: __('Actions'), sort: false },
]

const overview = createResource({
	url: 'lms.lms.ojt_certification.get_ojt_certification_overview',
	auto: true,
})

const learners = createResource({
	url: 'lms.lms.ojt_certification.get_ojt_certification_learners',
	auto: true,
	makeParams() {
		return {
			search: search.value?.trim() || undefined,
			location: location.value === ALL ? undefined : location.value,
			batch_start: batchStart.value === ALL ? undefined : batchStart.value,
			from_date: fromDate.value || undefined,
			to_date: toDate.value || undefined,
			funnel_stage: funnelStage.value === 'total' ? undefined : funnelStage.value,
			sort_by: sortBy.value,
			sort_order: sortOrder.value,
			page: page.value,
			page_length: pageLength.value,
		}
	},
})

const kpiCards = computed(() => overview.data?.kpis || [])
const funnel = computed(() => overview.data?.funnel || [])
const activeFunnel = computed(() => funnelStage.value)
const activeFunnelLabel = computed(() => {
	const step = funnel.value.find((item) => item.key === funnelStage.value)
	return step?.label || funnelStage.value
})
const learnerRows = computed(() => learners.data?.rows || [])
const totalPages = computed(() => learners.data?.total_pages || 1)

const lastSyncedLabel = computed(() => {
	const sync = overview.data?.sync
	if (!sync?.last_synced) {
		return __('Last synced: never')
	}
	const when = formatDateTime(sync.last_synced)
	const source = sync.last_sync_source ? ` · ${sync.last_sync_source}` : ''
	return `${__('Last synced: {0}').format(when)}${source}`
})

const locationOptions = computed(() => {
	const items = overview.data?.filters?.locations || []
	return [
		{ label: __('All locations'), value: ALL },
		...items.map((item) => ({ label: item, value: item })),
	]
})

const batchOptions = computed(() => {
	const items = overview.data?.filters?.batches || []
	return [
		{ label: __('All batches'), value: ALL },
		...items.map((item) => ({
			label: formatDate(item),
			value: item,
		})),
	]
})

const productChartData = computed(() => {
	return (overview.data?.charts?.product_scores || [])
		.filter((row) => row.value)
		.map((row) => ({ label: row.label, score: row.value }))
})

const pageItems = computed(() => {
	const total = totalPages.value
	const current = page.value
	if (total <= 7) {
		return Array.from({ length: total }, (_, i) => i + 1)
	}
	const items = [1]
	if (current > 3) items.push('…')
	const start = Math.max(2, current - 1)
	const end = Math.min(total - 1, current + 1)
	for (let i = start; i <= end; i += 1) items.push(i)
	if (current < total - 2) items.push('…')
	items.push(total)
	return items
})

const detailFields = computed(() => {
	const row = selectedLearner.value
	if (!row) return []
	return [
		{ key: 'employee_name', label: __('Learner Name'), value: row.employee_name || '—' },
		{ key: 'email', label: __('Email ID'), value: row.email || '—' },
		{ key: 'location', label: __('Location'), value: row.location || '—' },
		{ key: 'training_manager', label: __('Training Manager'), value: row.training_manager || '—' },
		{ key: 'batch_start', label: __('Batch Start'), value: formatDate(row.batch_start) },
		{ key: 'attendance_days', label: __('Attendance Days'), value: displayNumber(row.attendance_days) },
		{ key: 'ai_mock_score', label: __('AI Mock Score'), value: displayNumber(row.ai_mock_score) },
		{ key: 'audit_score', label: __('Audit Score (max 20)'), value: displayNumber(row.audit_score) },
		{ key: 'stage', label: __('Stage'), value: row.stage || '—' },
		{ key: 'dc', label: __('DC'), value: displayNumber(row.dc) },
		{ key: 'cc', label: __('CC'), value: displayNumber(row.cc) },
		{ key: 'talk_time', label: __('TT'), value: row.talk_time || '—' },
		{ key: 'booked', label: __('Booked'), value: displayNumber(row.booked) },
		{ key: 'catered', label: __('Catered'), value: displayNumber(row.catered) },
		{ key: 'target_exam', label: __('Target Exam / 20'), value: displayNumber(row.target_exam) },
		{ key: 'cbse', label: __('CBSE / 20'), value: displayNumber(row.cbse) },
		{ key: 'test_prep', label: __('Test Prep / 20'), value: displayNumber(row.test_prep) },
		{ key: 'lsq', label: __('LSQ / 20'), value: displayNumber(row.lsq) },
		{ key: 'math_champ', label: __('Math Champ / 20'), value: displayNumber(row.math_champ) },
		{ key: 'product_avg', label: __('Product average / 20'), value: displayNumber(row.product_avg) },
	]
})

function learnerParams() {
	return {
		search: search.value?.trim() || undefined,
		location: location.value === ALL ? undefined : location.value,
		batch_start: batchStart.value === ALL ? undefined : batchStart.value,
		from_date: fromDate.value || undefined,
		to_date: toDate.value || undefined,
		funnel_stage: funnelStage.value === 'total' ? undefined : funnelStage.value,
		sort_by: sortBy.value,
		sort_order: sortOrder.value,
	}
}

function reloadLearners() {
	learners.reload()
}

function onSearchInput() {
	clearTimeout(searchDebounce)
	searchDebounce = setTimeout(() => {
		page.value = 1
		reloadLearners()
	}, 300)
}

function onFilterChange() {
	page.value = 1
	reloadLearners()
}

function openDetail(row) {
	selectedLearner.value = row
	showDetail.value = true
}

function onPageLengthChange() {
	page.value = 1
	reloadLearners()
}

function goToPage(next) {
	if (next < 1 || next > totalPages.value) return
	page.value = next
	reloadLearners()
}

function setFunnelStage(key) {
	funnelStage.value = funnelStage.value === key && key !== 'total' ? 'total' : key
	page.value = 1
	reloadLearners()
}

function onKpiClick(key) {
	const mapped = kpiToFunnel[key]
	if (!mapped) return
	setFunnelStage(mapped)
}

function toggleSort(key) {
	if (sortBy.value === key) {
		sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
	} else {
		sortBy.value = key
		sortOrder.value = 'asc'
	}
	page.value = 1
	reloadLearners()
}

function openCreate() {
	editingRow.value = null
	showForm.value = true
}

function openEdit(row) {
	editingRow.value = row
	showForm.value = true
}

function onReportSaved() {
	overview.reload()
	reloadLearners()
}

function stageClass(stage) {
	if (stage === 'Product Tests Completed') return 'text-green-700 bg-green-50'
	if (stage === 'Audit Completed') return 'text-blue-700 bg-blue-50'
	if (stage === 'Mock Completed' || stage === 'Started') return 'text-amber-700 bg-amber-50'
	return 'text-ink-gray-6 bg-surface-gray-2'
}

function displayNumber(value) {
	if (value === null || value === undefined || value === '') return '—'
	return value
}

function formatDate(value) {
	if (!value) return '—'
	try {
		return new Date(`${value}T00:00:00`).toLocaleDateString('en-GB', {
			day: '2-digit',
			month: 'short',
			year: 'numeric',
		})
	} catch (error) {
		return value
	}
}

function formatDateTime(value) {
	if (!value) return '—'
	try {
		return new Date(value).toLocaleString()
	} catch (error) {
		return value
	}
}

async function syncSheet() {
	syncing.value = true
	try {
		await call('lms.lms.ojt_certification.sync_ojt_certification_metrics')
		toast.success(__('OJT certification data synced'))
		page.value = 1
		overview.reload()
		reloadLearners()
	} catch (error) {
		toast.error(error?.messages?.[0] || error?.message || __('Sync failed'))
	} finally {
		syncing.value = false
	}
}

async function exportReport() {
	exporting.value = true
	try {
		const result = await call(
			'lms.lms.ojt_certification.export_ojt_certification_report',
			learnerParams()
		)
		const csv = result?.csv || result?.message?.csv
		const filename = result?.filename || result?.message?.filename || 'ojt-certification-report.csv'
		if (!csv) {
			throw new Error(__('Export returned no data'))
		}
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
		const url = URL.createObjectURL(blob)
		const link = document.createElement('a')
		link.href = url
		link.download = filename
		link.click()
		URL.revokeObjectURL(url)
		toast.success(__('Exported {0} learners').format(result?.count ?? result?.message?.count ?? ''))
	} catch (error) {
		toast.error(error?.messages?.[0] || error?.message || __('Export failed'))
	} finally {
		exporting.value = false
	}
}
</script>
