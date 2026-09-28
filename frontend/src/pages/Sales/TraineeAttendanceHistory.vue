<!-- frontend/src/pages/Sales/TraineeAttendanceHistory.vue -->
<template>
	<div class="min-h-full w-full px-4 pb-8 pt-4 sm:px-6 lg:px-8">
		<h1 class="mb-4 text-xl font-semibold text-[color:var(--genius-navy)]">Attendance History</h1>

		<div class="genius-card mb-6 flex flex-wrap items-center gap-2 rounded-2xl p-4 sm:p-5">
			<div class="flex overflow-hidden rounded-lg border" style="border-color: var(--genius-border)">
				<button
					type="button"
					class="px-3 py-1.5 text-sm font-medium"
					:class="view === 'daily' ? 'bg-[color:var(--genius-blue)] text-white' : 'text-[color:var(--genius-muted)]'"
					@click="view = 'daily'"
				>
					Daily
				</button>
				<button
					type="button"
					class="px-3 py-1.5 text-sm font-medium"
					:class="view === 'weekly' ? 'bg-[color:var(--genius-blue)] text-white' : 'text-[color:var(--genius-muted)]'"
					@click="view = 'weekly'"
				>
					Weekly
				</button>
			</div>
			<input
				v-if="view === 'daily'"
				v-model="date"
				type="date"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				style="border-color: var(--genius-border)"
			/>
			<input
				v-else
				v-model="weekStart"
				type="date"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				style="border-color: var(--genius-border)"
			/>
			<select
				v-model="cohort"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				style="border-color: var(--genius-border)"
			>
				<option value="">All cohorts</option>
				<option v-for="c in cohorts.data" :key="c.name" :value="c.name">{{ c.cohort_name }}</option>
			</select>
			<Button v-if="view === 'weekly' && canExportWeekly" size="sm" :loading="exporting" @click="exportWeekly">
				Export weekly attendance
			</Button>
		</div>

		<div v-if="view === 'daily'" class="genius-card rounded-2xl p-4 sm:p-5">
			<p class="mb-3 text-sm text-[color:var(--genius-muted)]">
				<span class="font-semibold text-[color:var(--genius-navy)]">{{ missing.length }}</span>
				not marked for {{ date }}
			</p>
			<div class="overflow-x-auto">
				<table class="min-w-full text-left text-sm">
					<thead>
						<tr
							class="border-b text-[11px] uppercase tracking-wide text-[color:var(--genius-muted)]"
							style="border-color: var(--genius-border)"
						>
							<th class="pb-2 pr-3 font-medium">Trainee</th>
							<th class="pb-2 font-medium">Status</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="t in trainees.data"
							:key="t.name"
							class="border-b last:border-0"
							style="border-color: var(--genius-border)"
						>
							<td class="py-2.5 pr-3 font-medium text-[color:var(--genius-navy)]">{{ t.trainee_name }}</td>
							<td class="py-2.5">
								<span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="dailyStatusBadge(t.name)">
									{{ dailyStatusFor(t.name) }}
								</span>
							</td>
						</tr>
					</tbody>
				</table>
				<div v-if="!trainees.loading && !trainees.data?.length" class="py-8 text-center text-sm text-[color:var(--genius-muted)]">
					No trainees in this scope.
				</div>
			</div>
		</div>

		<div v-else class="genius-card rounded-2xl p-4 sm:p-5">
			<div class="overflow-x-auto">
				<table class="min-w-full text-left text-sm">
					<thead>
						<tr
							class="border-b text-[11px] uppercase tracking-wide text-[color:var(--genius-muted)]"
							style="border-color: var(--genius-border)"
						>
							<th class="pb-2 pr-3 font-medium">Trainee</th>
							<th v-for="d in weekDays" :key="d" class="pb-2 pr-3 font-medium">{{ formatDay(d) }}</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="t in trainees.data"
							:key="t.name"
							class="border-b last:border-0"
							style="border-color: var(--genius-border)"
						>
							<td class="py-2.5 pr-3 font-medium text-[color:var(--genius-navy)]">{{ t.trainee_name }}</td>
							<td v-for="d in weekDays" :key="d" class="py-2.5 pr-3">
								<span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="weeklyStatusBadge(t.name, d)">
									{{ weeklyStatusFor(t.name, d) }}
								</span>
							</td>
						</tr>
					</tbody>
				</table>
				<div v-if="!trainees.loading && !trainees.data?.length" class="py-8 text-center text-sm text-[color:var(--genius-muted)]">
					No trainees in this scope.
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { call, createListResource, Button } from 'frappe-ui'
import { usersStore } from '@/stores/user'

const { userResource } = usersStore()
const canExportWeekly = computed(() => {
	const roles = userResource?.data?.roles || []
	return roles.includes('Sales Training Finance') || roles.includes('Sales Training Team')
})

const STATUS_BADGES = {
	Present: 'bg-green-50 text-green-700',
	Absent: 'bg-red-50 text-red-700',
	Leave: 'bg-amber-50 text-amber-700',
	Holiday: 'bg-gray-100 text-gray-600',
}
const NOT_MARKED_BADGE = 'bg-gray-100 text-gray-500'
const NOT_MARKED_LABEL = 'Not marked'

const view = ref('daily')
const cohort = ref('')
const date = ref(new Date().toISOString().slice(0, 10))
const weekStart = ref(mondayOf(new Date()).toISOString().slice(0, 10))
const exporting = ref(false)
const missing = ref([])

function mondayOf(d) {
	const day = d.getDay()
	const diff = (day === 0 ? -6 : 1) - day
	const monday = new Date(d)
	monday.setDate(d.getDate() + diff)
	return monday
}

const weekDays = computed(() => {
	const start = new Date(weekStart.value)
	return Array.from({ length: 7 }, (_, i) => {
		const d = new Date(start)
		d.setDate(start.getDate() + i)
		return d.toISOString().slice(0, 10)
	})
})
const weekEnd = computed(() => weekDays.value[6])

function formatDay(iso) {
	return new Date(iso).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })
}

const cohorts = createListResource({
	doctype: 'Sales Trainee Cohort',
	fields: ['name', 'cohort_name'],
	auto: true,
	pageLength: 100,
})

const trainees = createListResource({
	doctype: 'Sales Trainee',
	fields: ['name', 'trainee_name'],
	filters: { training_status: 'In Training' },
	auto: true,
	pageLength: 500,
	onSuccess: () => {
		loadDaily()
		loadWeekly()
	},
})

function trainerFilters() {
	const filters = { training_status: 'In Training' }
	if (cohort.value) filters.cohort = cohort.value
	return filters
}

watch(cohort, () => {
	trainees.update({ filters: trainerFilters() })
	trainees.reload()
})

// Daily view
const dailyMarks = reactive({})

const dailyAttendance = createListResource({
	doctype: 'Sales Trainee Attendance',
	fields: ['trainee', 'status'],
	filters: { trainee: ['in', ['']], attendance_date: date.value },
	pageLength: 1000,
	auto: false,
	onSuccess(rows) {
		Object.keys(dailyMarks).forEach((k) => delete dailyMarks[k])
		for (const r of rows) dailyMarks[r.trainee] = r.status
	},
})

async function loadDaily() {
	if (view.value !== 'daily') return
	const names = (trainees.data || []).map((t) => t.name)
	if (!names.length) return
	dailyAttendance.update({ filters: { trainee: ['in', names], attendance_date: date.value } })
	dailyAttendance.reload()
	missing.value = await call('lms.lms.trainee_cohort_stats.list_missing_attendance', {
		attendance_date: date.value,
		cohort: cohort.value || undefined,
	})
}

function dailyStatusFor(trainee) {
	return dailyMarks[trainee] || NOT_MARKED_LABEL
}
function dailyStatusBadge(trainee) {
	return STATUS_BADGES[dailyMarks[trainee]] || NOT_MARKED_BADGE
}

watch([date, () => trainees.data], loadDaily)
watch(view, (v) => {
	if (v === 'daily') loadDaily()
	else loadWeekly()
})

// Weekly view
const weeklyMarks = reactive({})

const weeklyAttendance = createListResource({
	doctype: 'Sales Trainee Attendance',
	fields: ['trainee', 'attendance_date', 'status'],
	filters: { trainee: ['in', ['']], attendance_date: ['between', [weekStart.value, weekEnd.value]] },
	pageLength: 5000,
	auto: false,
	onSuccess(rows) {
		Object.keys(weeklyMarks).forEach((k) => delete weeklyMarks[k])
		for (const r of rows) weeklyMarks[`${r.trainee}::${r.attendance_date}`] = r.status
	},
})

function loadWeekly() {
	if (view.value !== 'weekly') return
	const names = (trainees.data || []).map((t) => t.name)
	if (!names.length) return
	weeklyAttendance.update({
		filters: { trainee: ['in', names], attendance_date: ['between', [weekStart.value, weekEnd.value]] },
	})
	weeklyAttendance.reload()
}

function weeklyStatusFor(trainee, day) {
	return weeklyMarks[`${trainee}::${day}`] || '—'
}
function weeklyStatusBadge(trainee, day) {
	return STATUS_BADGES[weeklyMarks[`${trainee}::${day}`]] || NOT_MARKED_BADGE
}

watch([weekStart, () => trainees.data], loadWeekly)

async function exportWeekly() {
	exporting.value = true
	try {
		const encoded = await call('lms.lms.trainee_reports.export_weekly_attendance_payroll_report', {
			week_start: weekStart.value,
			week_end: weekEnd.value,
			cohort: cohort.value || undefined,
		})
		const link = document.createElement('a')
		link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${encoded}`
		link.download = `weekly-attendance-${weekStart.value}.xlsx`
		link.click()
	} finally {
		exporting.value = false
	}
}
</script>
