<template>
	<div class="activity-heatmap w-full" @mouseleave="hideTooltip">
		<div class="flex flex-wrap items-center justify-between gap-3 mb-3">
			<div class="text-sm text-ink-gray-7">
				<span class="font-semibold text-ink-gray-9">{{ totalDisplay }}</span>
				{{ __(' active in {0}').format(selectedYear) }}
			</div>
			<select
				v-model="selectedYear"
				class="year-select text-sm border border-outline-gray-2 rounded-md px-2 py-1 bg-surface-white text-ink-gray-8"
				@change="loadHeatmap"
			>
				<option v-for="year in availableYears" :key="year" :value="year">
					{{ year }}
				</option>
			</select>
		</div>

		<div v-if="loading" class="text-sm text-ink-gray-6 py-6 text-center">
			{{ __('Loading heatmap...') }}
		</div>

		<div v-else class="heatmap-layout w-full">
			<div class="heatmap-grid-wrap w-full">
				<div
					class="month-row"
					:style="{ gridTemplateColumns: weekGridColumns }"
				>
					<div
						v-for="label in monthLabels"
						:key="`${label.weekIdx}-${label.month}`"
						class="month-label"
						:style="{ gridColumnStart: label.weekIdx + 1 }"
					>
						{{ label.month }}
					</div>
				</div>

				<div class="weeks-grid" :style="{ gridTemplateColumns: weekGridColumns }">
					<div
						v-for="(week, weekIdx) in weeks"
						:key="weekIdx"
						class="week-column"
					>
						<template v-for="day in week" :key="day.date">
							<span
								v-if="day.pad"
								class="heatmap-cell heatmap-level--1"
								aria-hidden="true"
							/>
							<button
								v-else
								type="button"
								class="heatmap-cell focus:outline-none focus:ring-1 focus:ring-orange-400"
								:class="[
									`heatmap-level-${day.level}`,
									{ 'heatmap-future': day.is_future },
								]"
								:aria-label="dayLabel(day)"
								@mouseenter="showTooltip($event, day)"
								@focus="showTooltip($event, day)"
								@blur="hideTooltip"
							/>
						</template>
					</div>
				</div>
			</div>
		</div>

		<div class="flex justify-end items-center gap-1.5 text-xs text-ink-gray-6 mt-3">
			<span>{{ __('Less') }}</span>
			<span
				v-for="level in 5"
				:key="level"
				class="heatmap-cell legend-cell"
				:class="`heatmap-level-${level - 1}`"
				aria-hidden="true"
			/>
			<span>{{ __('More') }}</span>
		</div>

		<Teleport to="body">
			<div
				v-if="tooltip.visible"
				class="activity-heatmap-tooltip"
				:style="tooltipStyle"
				role="tooltip"
			>
				<div class="font-semibold text-white mb-1 leading-snug">
					{{ tooltip.dateLabel }}
				</div>
				<div v-if="tooltip.isFuture" class="text-gray-400">
					{{ __('No activity yet') }}
				</div>
				<div v-else-if="tooltip.loading" class="text-gray-300">
					{{ __('Loading breakdown...') }}
				</div>
				<template v-else-if="tooltip.detail">
					<div class="text-gray-200 mb-2">
						<span class="font-medium text-white">{{ tooltip.detail.total_display }}</span>
						{{ __(' active') }}
					</div>
					<div
						v-if="tooltip.detail.breakdown?.length"
						class="space-y-1 border-t border-gray-600 pt-2"
					>
						<div
							v-for="row in tooltip.detail.breakdown"
							:key="row.label"
							class="flex justify-between gap-4"
						>
							<span class="text-gray-300">{{ __(row.label) }}</span>
							<span class="text-white font-medium tabular-nums shrink-0">
								{{ row.display }}
							</span>
						</div>
					</div>
					<div v-else-if="tooltip.detail.total_minutes === 0" class="text-gray-400">
						{{ __('No active time recorded') }}
					</div>
				</template>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { call } from 'frappe-ui'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import dayjs from '@/utils/dayjs'

const props = defineProps({
	userId: { type: String, required: true },
})

const loading = ref(true)
const selectedYear = ref(dayjs().year())
const availableYears = ref([
	dayjs().year(),
	dayjs().year() - 1,
	dayjs().year() - 2,
])
const heatmapDays = ref([])
const totalDisplay = ref('0m')

const tooltip = reactive({
	visible: false,
	x: 0,
	y: 0,
	dateLabel: '',
	loading: false,
	isFuture: false,
	detail: null,
})

const tooltipStyle = computed(() => ({
	left: `${tooltip.x}px`,
	top: `${tooltip.y}px`,
}))

const weekGridColumns = computed(() => {
	const count = weeks.value.length || 1
	return `repeat(${count}, minmax(0, 1fr))`
})

let tooltipCache = {}
let activeDate = null
let hideTimer = null

const weeks = computed(() => {
	const days = heatmapDays.value || []
	if (!days.length) return []

	const padded = [...days]
	const firstDow = dayjs(padded[0].date).day()
	for (let i = 0; i < firstDow; i++) {
		padded.unshift({ date: `pad-${i}`, level: -1, minutes: 0, pad: true })
	}

	const result = []
	let week = []
	for (const day of padded) {
		week.push(day)
		if (week.length === 7) {
			result.push(week)
			week = []
		}
	}
	if (week.length) {
		while (week.length < 7) {
			week.push({ date: `pad-end-${week.length}`, level: -1, minutes: 0, pad: true })
		}
		result.push(week)
	}
	return result
})

const monthLabels = computed(() => {
	const labels = []
	const seen = new Set()

	weeks.value.forEach((week, weekIdx) => {
		for (const day of week) {
			if (day.pad || !day.date) continue
			const monthKey = dayjs(day.date).format('YYYY-MM')
			if (dayjs(day.date).date() === 1 || (weekIdx === 0 && !seen.has(monthKey))) {
				if (!seen.has(monthKey)) {
					seen.add(monthKey)
					labels.push({
						weekIdx,
						month: dayjs(day.date).format('MMM'),
					})
				}
				break
			}
		}
	})

	return labels
})

function formatMinutes(minutes) {
	const m = Number(minutes) || 0
	if (m <= 0) return '0m'
	const hours = Math.floor(m / 60)
	const mins = m % 60
	if (hours && mins) return `${hours}h ${mins}m`
	if (hours) return `${hours}h`
	return `${mins}m`
}

function dayLabel(day) {
	if (day.pad) return ''
	return `${dayjs(day.date).format('MMM D, YYYY')} — ${day.minutes} min`
}

async function loadHeatmap() {
	if (!props.userId) return
	loading.value = true
	try {
		const data = await call('lms.tracking.get_heatmap', {
			user_id: props.userId,
			year: selectedYear.value,
		})
		heatmapDays.value = data.heatmap || []
		availableYears.value = data.available_years || availableYears.value
		totalDisplay.value = data.total_display || '0m'
		if (data.year) {
			selectedYear.value = data.year
		}
	} catch {
		heatmapDays.value = []
		totalDisplay.value = '0m'
	} finally {
		loading.value = false
	}
}

function positionTooltip(event) {
	const rect = event.currentTarget.getBoundingClientRect()
	tooltip.x = rect.left + rect.width / 2
	tooltip.y = rect.top - 8
}

function showTooltip(event, day) {
	if (day.pad || !day.date) return
	if (hideTimer) {
		clearTimeout(hideTimer)
		hideTimer = null
	}

	positionTooltip(event)
	activeDate = day.date
	tooltip.visible = true
	tooltip.dateLabel = dayjs(day.date).format('dddd, MMM D, YYYY')
	tooltip.isFuture =
		day.is_future || dayjs(day.date).isAfter(dayjs(), 'day')

	if (tooltip.isFuture) {
		tooltip.loading = false
		tooltip.detail = null
		return
	}

	const cacheKey = `${props.userId}:${day.date}`
	if (tooltipCache[cacheKey]) {
		tooltip.detail = tooltipCache[cacheKey]
		tooltip.loading = false
		return
	}

	tooltip.detail = {
		total_minutes: day.minutes,
		total_display: formatMinutes(day.minutes),
		breakdown: [],
	}
	tooltip.loading = true
	loadDayDetail(day)
}

async function loadDayDetail(day) {
	const cacheKey = `${props.userId}:${day.date}`

	try {
		const detail = await call('lms.tracking.get_day_detail', {
			user_id: props.userId,
			date: day.date,
		})
		tooltipCache[cacheKey] = detail
		if (activeDate === day.date) {
			tooltip.detail = detail
			tooltip.loading = false
		}
	} catch {
		if (activeDate === day.date) {
			tooltip.detail = {
				total_minutes: day.minutes,
				total_display: formatMinutes(day.minutes),
				breakdown: [],
			}
			tooltip.loading = false
		}
	}
}

function hideTooltip() {
	hideTimer = setTimeout(() => {
		tooltip.visible = false
		activeDate = null
		tooltip.loading = false
		tooltip.isFuture = false
	}, 100)
}

watch(
	() => props.userId,
	() => {
		tooltipCache = {}
		loadHeatmap()
	}
)

onMounted(loadHeatmap)
</script>

<style scoped>
.heatmap-layout {
	width: 100%;
}

.heatmap-grid-wrap {
	width: 100%;
}

.month-row {
	display: grid;
	gap: 3px;
	min-height: 14px;
	margin-bottom: 4px;
}

.month-label {
	font-size: 10px;
	color: var(--ink-gray-5, #6b7280);
	line-height: 1;
	white-space: nowrap;
}

.weeks-grid {
	display: grid;
	gap: 3px;
	width: 100%;
}

.week-column {
	display: grid;
	grid-template-rows: repeat(7, minmax(0, 1fr));
	gap: 3px;
	min-width: 0;
}

.heatmap-cell {
	width: 100%;
	aspect-ratio: 1;
	border-radius: 2px;
	min-width: 0;
	min-height: 0;
	padding: 0;
}

.legend-cell {
	width: 11px;
	height: 11px;
	flex-shrink: 0;
}

.heatmap-level--1 {
	visibility: hidden;
}

.heatmap-level-0,
.heatmap-future {
	background: #f8fafc;
	border: 1px solid #e2e8f0;
}

.heatmap-level-1 {
	background: #fed7aa;
	border: 1px solid #fdba74;
}

.heatmap-level-2 {
	background: #fb923c;
	border: 1px solid #f97316;
}

.heatmap-level-3 {
	background: #ea580c;
	border: 1px solid #c2410c;
}

.heatmap-level-4 {
	background: #9a3412;
	border: 1px solid #7c2d12;
}

.year-select {
	min-width: 88px;
}
</style>

<style>
.activity-heatmap-tooltip {
	position: fixed;
	z-index: 99999;
	pointer-events: none;
	min-width: 200px;
	max-width: 260px;
	padding: 10px 12px;
	border-radius: 8px;
	background-color: #171717;
	color: #ffffff;
	font-size: 12px;
	line-height: 1.4;
	box-shadow:
		0 10px 25px rgba(0, 0, 0, 0.25),
		0 0 0 1px rgba(255, 255, 255, 0.08);
	transform: translate(-50%, calc(-100% - 4px));
}
</style>
