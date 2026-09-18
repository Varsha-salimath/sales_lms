<template>
	<div class="il-page min-h-full pb-12">
		<header class="flex flex-wrap items-end justify-between gap-3 pt-5 pb-4">
			<div>
				<h1 class="il-page-title">{{ __('Learner reports') }}</h1>
				<p class="mt-1 text-sm text-[color:var(--il-muted)]">
					{{ __('Sales CRT · combined report for training managers and above') }}
				</p>
			</div>
			<div class="flex items-center gap-3">
				<span v-if="report.data?.last_updated" class="text-xs text-[color:var(--il-muted)]">
					{{ __('Last updated') }}: {{ fmtDate(report.data.last_updated) }}
				</span>
				<button class="il-btn il-btn-primary" :disabled="!rows.length" @click="exportCsv">
					<Download class="h-4 w-4" />
					{{ __('Export') }}
				</button>
			</div>
		</header>

		<!-- Filters -->
		<section class="rp-filters">
			<label class="rp-select">
				<span>{{ __('Batch') }}</span>
				<select v-model="filters.batch_start">
					<option value="__all__">{{ __('All batches') }}</option>
					<option v-for="b in options.batch_start" :key="b" :value="b">{{ fmtDate(b) }}</option>
				</select>
			</label>
			<label class="rp-select">
				<span>{{ __('Location') }}</span>
				<select v-model="filters.location">
					<option value="__all__">{{ __('All locations') }}</option>
					<option v-for="l in options.location" :key="l" :value="l">{{ l }}</option>
				</select>
			</label>
			<label class="rp-select">
				<span>{{ __('Training manager') }}</span>
				<select v-model="filters.training_manager">
					<option value="__all__">{{ __('All managers') }}</option>
					<option v-for="m in options.training_manager" :key="m" :value="m">{{ managerName(m) }}</option>
				</select>
			</label>
			<label class="rp-search">
				<Search class="h-4 w-4 text-[color:var(--il-neutral-60)]" />
				<input v-model="search" :placeholder="__('Search learner or email')" />
			</label>
		</section>

		<div v-if="report.loading && !report.data" class="mt-6 space-y-4">
			<div class="h-40 animate-pulse rounded-3xl bg-[#e6e7e8]" />
			<div class="h-64 animate-pulse rounded-3xl bg-[#e6e7e8]" />
		</div>

		<div v-else-if="report.error" class="il-card mt-6 p-8 text-center text-sm text-[color:var(--il-error-50)]">
			{{ report.error.messages?.[0] || __('Could not load the report.') }}
		</div>

		<template v-else-if="report.data">
			<!-- Highlights -->
			<section class="il-card mt-4 p-5">
				<h2 class="rp-card-title">{{ __('Highlights') }}</h2>
				<div class="mt-3 grid gap-5 lg:grid-cols-[auto_1fr] lg:items-center">
					<div class="flex items-center gap-4">
						<div class="rp-donut" :style="donutStyle(stats.readiness?.avg)">
							<span>{{ fmtPct(stats.readiness?.avg) }}</span>
						</div>
						<div>
							<div class="text-base font-medium text-[color:var(--il-ink)]">{{ __('Average readiness') }}</div>
							<div class="text-xs text-[color:var(--il-muted)]">
								{{ rows.length }} {{ __('learners') }}
							</div>
						</div>
					</div>
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<div v-for="k in highlightKeys" :key="k.key" class="rp-stat">
							<div class="rp-stat-value">
								{{ fmt(stats[k.key]?.avg) }}<small>/{{ k.max }}</small>
							</div>
							<div class="rp-stat-label">{{ k.label }}</div>
						</div>
					</div>
					<div class="rp-insights lg:col-span-2">
						<div class="flex items-center gap-2">
							<Sparkles class="h-4 w-4 text-[#6D4AFF]" />
							<span class="text-sm font-medium text-[#5B3FD6]">{{ __('Insights') }}</span>
						</div>
						<ul class="mt-2 space-y-1.5">
							<li v-for="(line, i) in report.data.insights" :key="i" class="text-[13px] leading-5 text-[color:var(--il-ink)]">
								{{ line }}
							</li>
							<li v-if="!report.data.insights?.length" class="text-[13px] text-[color:var(--il-muted)]">
								{{ __('Insights appear once learners have scores.') }}
							</li>
						</ul>
					</div>
				</div>
			</section>

			<!-- Readiness bands -->
			<section class="il-card mt-6 p-5">
				<div class="flex flex-wrap items-center justify-between gap-2">
					<h2 class="rp-card-title">{{ __('Readiness distribution') }}</h2>
					<button v-if="bandFilter" class="text-sm font-medium text-[color:var(--il-primary-40)]" @click="bandFilter = null">
						{{ __('Clear filter') }}
					</button>
				</div>
				<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
					<button
						v-for="b in report.data.bands"
						:key="b.key"
						type="button"
						class="rp-band"
						:class="{ 'is-active': bandFilter === b.key, 'is-dim': bandFilter && bandFilter !== b.key }"
						:style="{ background: bandStyle(b.key).soft, borderColor: bandStyle(b.key).bg }"
						@click="bandFilter = bandFilter === b.key ? null : b.key"
					>
						<div>
							<div class="text-sm font-medium" :style="{ color: bandStyle(b.key).text }">{{ b.label }}</div>
							<div class="mt-1 text-xs text-[color:var(--il-muted)]">{{ b.count }} {{ __('learners') }}</div>
						</div>
						<div class="text-lg font-semibold" :style="{ color: bandStyle(b.key).text }">
							{{ rows.length ? Math.round((b.count / rows.length) * 100) : 0 }}%
						</div>
					</button>
				</div>
				<p class="mt-3 text-xs text-[color:var(--il-muted)]">{{ BAND_RULES }} {{ __('(of each metric\'s maximum)') }}</p>
			</section>

			<!-- Learner table -->
			<section class="il-card mt-6 overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-2 px-5 pt-5">
					<h2 class="rp-card-title">{{ __('Learners') }} <span class="text-[color:var(--il-muted)]">({{ visibleRows.length }})</span></h2>
					<span class="text-xs text-[color:var(--il-muted)]">{{ __('Click a learner to open their report card') }}</span>
				</div>
				<div class="rp-table-wrap mt-4">
					<table class="rp-table">
						<thead>
							<tr class="rp-group-row">
								<th colspan="3" class="rp-sticky">{{ __('Employee') }}</th>
								<th colspan="3">{{ __('Intent & Skill') }}</th>
								<th colspan="6">{{ __('Calling') }}</th>
								<th colspan="5">{{ __('Tests (out of 20)') }}</th>
								<th>{{ __('Overall') }}</th>
							</tr>
							<tr>
								<th v-for="col in columns" :key="col.key" :class="[col.sticky ? 'rp-sticky' : '', col.align || '']" @click="sortBy(col.key)">
									<span class="inline-flex items-center gap-1">
										{{ col.label }}
										<ArrowUpDown v-if="sort.key !== col.key" class="h-3 w-3 opacity-30" />
										<ArrowUp v-else-if="sort.dir === 'asc'" class="h-3 w-3" />
										<ArrowDown v-else class="h-3 w-3" />
									</span>
								</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in visibleRows" :key="row.name" @click="openCard(row)">
								<td class="rp-sticky">
									<div class="flex items-center gap-2.5">
										<span class="rp-avatar">{{ initials(row.employee_name) }}</span>
										<div class="min-w-0">
											<div class="truncate font-medium text-[color:var(--il-ink)]">{{ row.employee_name }}</div>
											<div class="truncate text-xs text-[color:var(--il-muted)]">{{ row.email }}</div>
										</div>
									</div>
								</td>
								<td>{{ row.location || '—' }}</td>
								<td class="whitespace-nowrap">{{ managerName(row.training_manager) }}</td>
								<td v-for="k in ['attendance_days', 'ai_mock_score', 'audit_score']" :key="k" class="text-center">
									<span class="rp-cell" :style="cellStyle(row.scores[k]?.band)">{{ fmt(row[k]) }}</span>
								</td>
								<td class="text-center tabular-nums">{{ fmt(row.dc) }}</td>
								<td class="text-center tabular-nums">{{ fmt(row.cc) }}</td>
								<td class="text-center tabular-nums">{{ row.talk_time || '—' }}</td>
								<td class="text-center tabular-nums">{{ fmt(row.booked) }}</td>
								<td class="text-center tabular-nums">{{ fmt(row.catered) }}</td>
								<td class="text-center tabular-nums">{{ fmtPct(row.booking_rate) }}</td>
								<td v-for="k in ['target_exam', 'cbse', 'test_prep', 'lsq', 'math_champ']" :key="k" class="text-center">
									<span class="rp-cell" :style="cellStyle(row.scores[k]?.band)">{{ fmt(row[k]) }}</span>
								</td>
								<td class="text-center">
									<span class="rp-cell rp-cell-strong" :style="cellStyle(row.readiness_band)">{{ fmtPct(row.readiness) }}</span>
								</td>
							</tr>
							<tr v-if="!visibleRows.length">
								<td :colspan="columns.length" class="py-10 text-center text-sm text-[color:var(--il-muted)]">
									{{ __('No learners match these filters.') }}
								</td>
							</tr>
						</tbody>
						<tfoot v-if="visibleRows.length">
							<tr>
								<td class="rp-sticky font-medium">{{ __('Batch average') }}</td>
								<td></td>
								<td></td>
								<td v-for="k in ['attendance_days', 'ai_mock_score', 'audit_score', 'dc', 'cc']" :key="k" class="text-center tabular-nums">{{ fmt(stats[k]?.avg) }}</td>
								<td class="text-center">{{ fmtDuration(stats.talk_seconds?.avg) }}</td>
								<td v-for="k in ['booked', 'catered']" :key="k" class="text-center tabular-nums">{{ fmt(stats[k]?.avg) }}</td>
								<td class="text-center">{{ fmtPct(stats.booking_rate?.avg) }}</td>
								<td v-for="k in ['target_exam', 'cbse', 'test_prep', 'lsq', 'math_champ']" :key="k" class="text-center tabular-nums">{{ fmt(stats[k]?.avg) }}</td>
								<td class="text-center font-medium">{{ fmtPct(stats.readiness?.avg) }}</td>
							</tr>
						</tfoot>
					</table>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search, Sparkles } from 'lucide-vue-next'
import {
	BAND_RULES,
	bandStyle,
	fmt,
	fmtDate,
	fmtDuration,
	fmtPct,
	initials,
	managerName,
} from './reportUtils'

const router = useRouter()
const filters = reactive({ batch_start: '__all__', location: '__all__', training_manager: '__all__' })
const search = ref('')
const bandFilter = ref(null)
const sort = reactive({ key: 'readiness', dir: 'desc' })

const report = createResource({
	url: 'lms.lms.learner_report.get_combined_report',
	makeParams: () => ({ ...filters }),
	auto: true,
})
watch(filters, () => report.reload())

const options = computed(() => report.data?.options || { batch_start: [], location: [], training_manager: [] })
const stats = computed(() => report.data?.stats || {})
const rows = computed(() => report.data?.rows || [])

const highlightKeys = [
	{ key: 'attendance_days', label: __('Attendance days'), max: 15 },
	{ key: 'ai_mock_score', label: __('AI mock'), max: 20 },
	{ key: 'audit_score', label: __('Audit'), max: 20 },
	{ key: 'product_avg', label: __('Product tests'), max: 20 },
]

const columns = [
	{ key: 'employee_name', label: __('Name'), sticky: true },
	{ key: 'location', label: __('Location') },
	{ key: 'training_manager', label: __('Training manager') },
	{ key: 'attendance_days', label: __('Attendance'), align: 'text-center' },
	{ key: 'ai_mock_score', label: __('AI mock'), align: 'text-center' },
	{ key: 'audit_score', label: __('Audit'), align: 'text-center' },
	{ key: 'dc', label: 'DC', align: 'text-center' },
	{ key: 'cc', label: 'CC', align: 'text-center' },
	{ key: 'talk_seconds', label: __('Talk time'), align: 'text-center' },
	{ key: 'booked', label: __('Booked'), align: 'text-center' },
	{ key: 'catered', label: __('Catered'), align: 'text-center' },
	{ key: 'booking_rate', label: __('Book %'), align: 'text-center' },
	{ key: 'target_exam', label: __('Target exam'), align: 'text-center' },
	{ key: 'cbse', label: 'CBSE', align: 'text-center' },
	{ key: 'test_prep', label: __('Test prep'), align: 'text-center' },
	{ key: 'lsq', label: 'LSQ', align: 'text-center' },
	{ key: 'math_champ', label: __('Math champ'), align: 'text-center' },
	{ key: 'readiness', label: __('Readiness'), align: 'text-center' },
]

const visibleRows = computed(() => {
	const term = search.value.trim().toLowerCase()
	let list = rows.value.filter(
		(r) =>
			(!bandFilter.value || r.readiness_band === bandFilter.value) &&
			(!term || `${r.employee_name} ${r.email}`.toLowerCase().includes(term))
	)
	const dir = sort.dir === 'asc' ? 1 : -1
	return [...list].sort((a, b) => {
		const x = a[sort.key]
		const y = b[sort.key]
		if (x === y) return 0
		if (x === null || x === undefined || x === '') return 1
		if (y === null || y === undefined || y === '') return -1
		return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * dir
	})
})

function sortBy(key) {
	if (sort.key === key) sort.dir = sort.dir === 'asc' ? 'desc' : 'asc'
	else Object.assign(sort, { key, dir: ['employee_name', 'location', 'training_manager'].includes(key) ? 'asc' : 'desc' })
}

function cellStyle(band) {
	const s = bandStyle(band)
	return { background: s.soft, color: s.text, borderColor: s.bg }
}

function donutStyle(value) {
	const p = Math.max(0, Math.min(100, Number(value) || 0))
	return { '--p': p }
}

function openCard(row) {
	router.push({ name: 'LearnerReportCard', params: { name: row.name } })
}

function exportCsv() {
	const keys = ['employee_name', 'email', 'location', 'training_manager', 'batch_start', 'attendance_days', 'ai_mock_score', 'audit_score', 'dc', 'cc', 'talk_time', 'booked', 'catered', 'booking_rate', 'target_exam', 'cbse', 'test_prep', 'lsq', 'math_champ', 'readiness']
	const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
	const csv = [keys.join(','), ...visibleRows.value.map((r) => keys.map((k) => esc(r[k])).join(','))].join('\n')
	const link = document.createElement('a')
	link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
	link.download = 'learner-report.csv'
	link.click()
}
</script>

<style scoped>
.rp-filters {
	display: flex;
	flex-wrap: wrap;
	gap: 0.75rem;
}

.rp-select,
.rp-search {
	display: inline-flex;
	align-items: center;
	gap: 0.5rem;
	height: 2.75rem;
	padding: 0 1rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 999px;
	background: #fff;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
	font-size: 0.875rem;
}

.rp-select span {
	color: var(--il-muted);
	font-size: 0.75rem;
}

.rp-select select {
	border: 0;
	padding: 0 1.25rem 0 0;
	background-color: transparent;
	color: var(--il-primary-40);
	font-weight: 500;
	font-size: 0.875rem;
	box-shadow: none;
}

.rp-search {
	flex: 1;
	min-width: 14rem;
}

.rp-search input {
	flex: 1;
	border: 0;
	padding: 0;
	background: transparent;
	box-shadow: none;
	font-size: 0.875rem;
}

.rp-card-title {
	margin: 0;
	color: var(--il-ink);
	font-size: 1.125rem;
	font-weight: 500;
}

.rp-donut {
	--p: 0;
	display: grid;
	place-items: center;
	width: 5.5rem;
	height: 5.5rem;
	border-radius: 999px;
	background: radial-gradient(closest-side, #fff 76%, transparent 77%),
		conic-gradient(#35c759 calc(var(--p) * 1%), #e6e7e8 0);
}

.rp-donut span {
	color: var(--il-ink);
	font-size: 1.125rem;
	font-weight: 600;
}

.rp-stat {
	border: 1px solid var(--il-neutral-90);
	border-radius: 16px;
	padding: 0.75rem 1rem;
	text-align: center;
}

.rp-stat-value {
	color: var(--il-ink);
	font-size: 1.25rem;
	font-weight: 600;
}

.rp-stat-value small {
	color: var(--il-neutral-60);
	font-size: 0.75rem;
	font-weight: 400;
}

.rp-stat-label {
	margin-top: 0.15rem;
	color: var(--il-muted);
	font-size: 0.75rem;
}

.rp-insights {
	border-radius: 16px;
	padding: 1rem 1.25rem;
	background: linear-gradient(100deg, #ffffff 0%, #f3efff 55%, #e9e3ff 100%);
}

.rp-band {
	display: flex;
	align-items: center;
	justify-content: space-between;
	border: 1px solid;
	border-radius: 16px;
	padding: 0.85rem 1rem;
	text-align: left;
	transition: opacity 0.15s ease, box-shadow 0.15s ease;
}

.rp-band.is-active {
	box-shadow: 0 0 0 2px var(--il-primary-50);
}

.rp-band.is-dim {
	opacity: 0.5;
}

.rp-table-wrap {
	overflow-x: auto;
}

.rp-table {
	width: 100%;
	border-collapse: separate;
	border-spacing: 0;
	font-size: 0.8125rem;
}

.rp-table th {
	padding: 0.6rem 0.75rem;
	background: #f7f9fc;
	color: var(--il-muted);
	font-size: 0.75rem;
	font-weight: 500;
	white-space: nowrap;
	cursor: pointer;
	user-select: none;
	border-bottom: 1px solid var(--il-neutral-90);
}

.rp-group-row th {
	background: #eef5ff;
	color: var(--il-primary-20);
	font-weight: 600;
	text-align: center;
	cursor: default;
	border-left: 2px solid #fff;
}

.rp-table td {
	padding: 0.55rem 0.75rem;
	border-bottom: 1px solid var(--il-neutral-95);
	color: var(--il-ink);
	white-space: nowrap;
}

.rp-table tbody tr {
	cursor: pointer;
}

.rp-table tbody tr:hover td {
	background: #f7fbff;
}

.rp-table tfoot td {
	background: #f7f9fc;
	color: var(--il-ink);
	font-weight: 500;
}

.rp-sticky {
	position: sticky;
	left: 0;
	z-index: 1;
	min-width: 14rem;
	background: #fff;
	text-align: left;
}

.rp-table th.rp-sticky {
	background: #f7f9fc;
}

.rp-group-row th.rp-sticky {
	background: #eef5ff;
}

.rp-avatar {
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 2rem;
	height: 2rem;
	border-radius: 999px;
	background: var(--il-primary-95);
	color: var(--il-primary-40);
	font-size: 0.75rem;
	font-weight: 600;
}

.rp-cell {
	display: inline-block;
	min-width: 2.5rem;
	border: 1px solid;
	border-radius: 8px;
	padding: 0.15rem 0.5rem;
	font-variant-numeric: tabular-nums;
	font-weight: 500;
}

.rp-cell-strong {
	min-width: 3.5rem;
	font-weight: 600;
}
</style>
