<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
		</header>
		<div class="p-5">
			<div class="text-base font-semibold text-ink-gray-9 mb-3">
				{{ __('Overview') }}
			</div>

			<div v-if="overview.loading" class="text-sm text-ink-gray-6">
				{{ __('Loading...') }}
			</div>

			<div
				v-else-if="overview.data"
				class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4"
			>
				<div
					v-for="card in overviewCards"
					:key="card.key"
					class="border rounded-lg bg-surface-white p-4"
				>
					<div class="text-sm text-ink-gray-6 mb-1">
						{{ __(card.label) }}
					</div>
					<div class="text-3xl font-semibold text-ink-gray-9 mb-1">
						{{ card.displayValue }}
					</div>
					<div class="text-xs text-ink-gray-5">
						{{ card.subtext }}
					</div>
				</div>
			</div>

			<div
				v-else-if="overview.error"
				class="text-sm text-ink-red-4"
			>
				{{ overview.error?.messages?.[0] || __('Failed to load analytics.') }}
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
				<!-- Lesson completion rate -->
				<div class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
					<div class="flex items-center gap-3 mb-4 min-w-0">
						<h2
							class="flex-1 min-w-0 text-base font-semibold text-ink-gray-9 leading-snug truncate"
						>
							{{ __('Lesson completion rate (%)') }}
						</h2>
						<Tooltip
							v-if="courseOptions.length"
							:text="selectedCourseLabel"
							placement="bottom"
						>
							<div class="analytics-chart-filter-wrap shrink-0">
								<FormControl
									v-model="selectedCourse"
									type="select"
									:options="courseOptions"
									class="analytics-chart-filter w-full"
									@update:modelValue="lessonCompletion.reload()"
								/>
							</div>
						</Tooltip>
					</div>
					<div
						v-if="!courseOptions.length"
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('No courses available.') }}
					</div>
					<div
						v-else-if="lessonCompletion.loading || !lessonCompletion.fetched"
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('Loading chart...') }}
					</div>
					<div
						v-else-if="lessonCompletionChartData.length"
						class="analytics-chart-area h-[300px] w-full max-w-full overflow-hidden"
					>
						<AxisChart
							:config="{
								data: lessonCompletionChartData,
								xAxis: {
									key: 'label',
									title: __('Lesson'),
									type: 'category',
								},
								yAxis: {
									title: __('Completion %'),
									echartOptions: {
										min: 0,
										max: 100,
										axisLabel: { formatter: '{value}%' },
									},
								},
								series: [
									{
										name: 'completion',
										type: 'bar',
										echartOptions: {
											itemStyle: { color: '#3b82f6' },
										},
									},
								],
							}"
						/>
					</div>
					<div
						v-else
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('No lesson data for this course.') }}
					</div>
				</div>

				<!-- Active learners over time -->
				<div class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
					<div class="flex items-center gap-3 mb-4 min-w-0">
						<h2
							class="flex-1 min-w-0 text-base font-semibold text-ink-gray-9 leading-snug truncate"
						>
							{{ __('Active learners over time') }}
						</h2>
						<div
							v-if="batchOptions.length"
							class="analytics-chart-filter-wrap shrink-0"
						>
							<FormControl
								v-model="selectedBatch"
								type="select"
								:options="batchOptions"
								class="analytics-chart-filter w-full"
								@update:modelValue="activeLearnersTrend.reload()"
							/>
						</div>
					</div>
					<p
						v-if="activeLearnersPeriodDescription"
						class="text-xs text-ink-gray-6 mb-3"
					>
						{{ activeLearnersPeriodDescription }}
					</p>
					<div
						v-if="activeLearnersTrend.loading || !activeLearnersTrend.fetched"
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('Loading chart...') }}
					</div>
					<div
						v-else-if="activeLearnersChartData.length"
						class="analytics-chart-area h-[300px] w-full max-w-full overflow-hidden"
					>
						<AxisChart
							:config="activeLearnersChartConfig"
						/>
					</div>
					<div
						v-else
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('No learner activity yet.') }}
					</div>
				</div>
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
				<!-- Course status breakdown -->
				<div class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
					<div class="flex items-center gap-3 mb-4 min-w-0">
						<h2
							class="flex-1 min-w-0 text-base font-semibold text-ink-gray-9 leading-snug truncate"
						>
							{{ __('Course status breakdown') }}
						</h2>
						<div
							v-if="batchOptions.length"
							class="analytics-chart-filter-wrap shrink-0"
						>
							<FormControl
								v-model="selectedBatchStatus"
								type="select"
								:options="batchOptions"
								class="analytics-chart-filter w-full"
								@update:modelValue="courseStatusBreakdown.reload()"
							/>
						</div>
					</div>
					<div
						v-if="courseStatusBreakdown.loading || !courseStatusBreakdown.fetched"
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('Loading chart...') }}
					</div>
					<div
						v-else-if="courseStatusBreakdown.data?.total > 0"
						class="analytics-chart-area h-[300px] w-full max-w-full overflow-hidden"
					>
						<ECharts :options="courseStatusChartOptions" />
					</div>
					<div
						v-else
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('No enrollment data yet.') }}
					</div>
				</div>

				<!-- Certifications issued over time -->
				<div class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
					<div class="flex items-center gap-3 mb-2 min-w-0">
						<h2
							class="flex-1 min-w-0 text-base font-semibold text-ink-gray-9 leading-snug truncate"
						>
							{{ __('Certifications issued over time') }}
						</h2>
						<div
							v-if="batchOptions.length"
							class="analytics-chart-filter-wrap shrink-0"
						>
							<FormControl
								v-model="selectedBatchCerts"
								type="select"
								:options="batchOptions"
								class="analytics-chart-filter w-full"
								@update:modelValue="certificationsTrend.reload()"
							/>
						</div>
					</div>
					<div
						v-if="certificationsTrend.fetched && certificationsSummary"
						class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-gray-6 mb-3"
					>
						<span>
							<span class="inline-block w-2 h-2 rounded-sm bg-green-600 mr-1" />
							{{ __('Certified') }} {{ certificationsSummary.certified }}
						</span>
						<span>
							<span class="inline-block w-2 h-2 rounded-sm bg-blue-500 mr-1" />
							{{ __('In progress') }} {{ certificationsSummary.in_progress }}
						</span>
						<span>
							<span class="inline-block w-2 h-2 rounded-sm bg-gray-400 mr-1" />
							{{ __('Not started') }} {{ certificationsSummary.not_started }}
						</span>
					</div>
					<div
						v-if="certificationsTrend.loading || !certificationsTrend.fetched"
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('Loading chart...') }}
					</div>
					<div
						v-else-if="certificationsChartData.length"
						class="analytics-chart-area h-[300px] w-full max-w-full overflow-hidden"
					>
						<AxisChart :config="certificationsChartConfig" />
					</div>
					<div
						v-else
						class="flex h-[300px] items-center justify-center text-sm text-ink-gray-6"
					>
						{{ __('No certification data yet.') }}
					</div>
				</div>
			</div>

			<!-- Learner progress -->
			<div class="border rounded-lg bg-surface-white p-4 mt-6 overflow-hidden min-w-0">
				<div class="flex flex-col sm:flex-row sm:items-center gap-3 mb-4 min-w-0">
					<h2 class="text-base font-semibold text-ink-gray-9 shrink-0">
						{{ __('Learner progress') }}
					</h2>
					<div class="flex flex-wrap items-center gap-2 sm:ml-auto">
						<div class="flex rounded-md border overflow-hidden text-xs">
							<button
								v-for="filter in statusFilters"
								:key="filter"
								type="button"
								class="px-3 py-1.5 transition-colors"
								:class="
									learnerStatusFilter === filter
										? 'bg-surface-gray-2 text-ink-gray-9 font-medium'
										: 'text-ink-gray-6 hover:bg-surface-gray-1'
								"
								@click="setLearnerStatusFilter(filter)"
							>
								{{ __(filter) }}
							</button>
						</div>
						<FormControl
							v-model="learnerSearch"
							type="text"
							:placeholder="__('Search by name')"
							class="learner-search-input w-36 sm:w-44 shrink-0"
							@input="onLearnerSearchInput"
						/>
						<Tooltip
							v-if="batchOptions.length"
							:text="selectedBatchLearnersLabel"
							placement="bottom"
						>
							<div class="analytics-chart-filter-wrap shrink-0">
								<FormControl
									v-model="selectedBatchLearners"
									type="select"
									:options="batchOptions"
									class="analytics-chart-filter w-full"
									@update:modelValue="onLearnerBatchChange"
								/>
							</div>
						</Tooltip>
					</div>
				</div>

				<div
					v-if="learnerProgress.loading"
					class="py-12 text-center text-sm text-ink-gray-6"
				>
					{{ __('Loading learners...') }}
				</div>
				<div
					v-else-if="learnerProgress.error"
					class="py-12 text-center text-sm text-ink-red-4"
				>
					{{
						learnerProgress.error?.messages?.[0] ||
						__('Failed to load learner progress.')
					}}
				</div>
				<div
					v-else-if="!learnerRows.length"
					class="py-12 text-center text-sm text-ink-gray-6"
				>
					{{ __('No learners match your search or filter.') }}
				</div>
				<div v-else>
					<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="border-b text-left text-ink-gray-6">
								<th class="py-2 pr-4 font-medium">{{ __('Learner') }}</th>
								<th
									v-if="isAllBatchesView"
									class="py-2 pr-4 font-medium"
								>
									{{ hasBatches ? __('Batch') : __('Course') }}
								</th>
								<th class="py-2 pr-4 font-medium">{{ __('Lessons') }}</th>
								<th class="py-2 pr-4 font-medium min-w-[140px]">
									{{ __('Progress') }}
								</th>
								<th class="py-2 pr-4 font-medium">{{ __('Quiz results') }}</th>
								<th class="py-2 pr-4 font-medium">
									{{ __('Assessments') }}
								</th>
								<th class="py-2 pr-4 font-medium">{{ __('Mock') }}</th>
								<th class="py-2 pr-4 font-medium">{{ __('Status') }}</th>
								<th class="py-2 font-medium">{{ __('Last active') }}</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in learnerRows"
								:key="row.batch ? `${row.member}-${row.batch}` : row.member"
								class="border-b border-surface-gray-2 last:border-0 cursor-pointer hover:bg-surface-gray-1 transition-colors"
								@click="openLearnerDetail(row)"
							>
								<td class="py-3 pr-4">
									<div class="flex items-center gap-2 min-w-[160px]">
										<Avatar
											:image="row.user_image"
											:label="row.full_name"
											size="sm"
										/>
										<span class="font-medium text-ink-gray-9 truncate">
											{{ row.full_name }}
										</span>
									</div>
								</td>
								<td
									v-if="isAllBatchesView"
									class="py-3 pr-4 text-ink-gray-7 whitespace-nowrap"
								>
									{{ row.batch_title }}
								</td>
								<td class="py-3 pr-4 text-ink-gray-7 whitespace-nowrap">
									{{ row.lessons_completed }}/{{ row.lessons_total }}
								</td>
								<td class="py-3 pr-4">
									<div class="flex items-center gap-2 min-w-[120px]">
										<ProgressBar
											:progress="row.progress"
											size="md"
											class="flex-1 min-w-[80px]"
										/>
										<span class="text-xs text-ink-gray-6 w-8 text-right">
											{{ row.progress }}%
										</span>
									</div>
								</td>
								<td class="py-3 pr-4 text-ink-gray-7 whitespace-nowrap">
									{{
										row.quiz_results !== null && row.quiz_results !== undefined
											? `${row.quiz_results}%`
											: '—'
									}}
								</td>
								<td class="py-3 pr-4 text-ink-gray-7 whitespace-nowrap">
									{{ row.assessment }}
								</td>
								<td class="py-3 pr-4 text-ink-gray-7 whitespace-nowrap">
									{{ row.mock }}
								</td>
								<td class="py-3 pr-4">
									<span
										class="inline-flex px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap"
										:class="statusClass(row.status_key)"
									>
										{{ row.status }}
									</span>
								</td>
								<td class="py-3 text-ink-gray-6 whitespace-nowrap">
									{{ row.last_active }}
								</td>
							</tr>
						</tbody>
					</table>
					</div>
					<div
						v-if="learnerTotalCount > 0"
						class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-4 pt-4 border-t border-surface-gray-2"
					>
						<p class="text-xs text-ink-gray-6">
							{{ learnerPaginationSummary }}
						</p>
						<div class="flex flex-wrap items-center gap-2">
							<FormControl
								v-model="learnerPageLength"
								type="select"
								:options="learnerPageLengthOptions"
								class="w-28 text-xs"
								@update:modelValue="onLearnerPageLengthChange"
							/>
							<Button
								variant="outline"
								:disabled="learnerPage <= 1 || learnerProgress.loading"
								@click="goToLearnerPage(learnerPage - 1)"
							>
								{{ __('Previous') }}
							</Button>
							<span class="text-xs text-ink-gray-6 px-1 tabular-nums">
								{{ __('Page {0} of {1}').format(learnerPage, learnerTotalPages) }}
							</span>
							<Button
								variant="outline"
								:disabled="
									learnerPage >= learnerTotalPages || learnerProgress.loading
								"
								@click="goToLearnerPage(learnerPage + 1)"
							>
								{{ __('Next') }}
							</Button>
						</div>
					</div>
				</div>
			</div>

			<div v-if="false" class="border rounded-lg bg-surface-white p-4 mt-4 overflow-hidden min-w-0">
				<div class="flex items-center gap-3 mb-4 min-w-0">
					<h2
						class="flex-1 min-w-0 text-base font-semibold text-ink-gray-9 leading-snug truncate"
					>
						{{ __('Lesson feedback') }}
					</h2>
					<Tooltip
						v-if="courseOptions.length"
						:text="selectedCourseFeedbackLabel"
						placement="bottom"
					>
						<div class="analytics-chart-filter-wrap shrink-0">
							<FormControl
								v-model="selectedCourseFeedback"
								type="select"
								:options="courseOptions"
								class="analytics-chart-filter w-full"
								@update:modelValue="lessonFeedback.reload()"
							/>
						</div>
					</Tooltip>
				</div>

				<div
					v-if="!courseOptions.length"
					class="py-8 text-center text-sm text-ink-gray-6"
				>
					{{ __('No courses available.') }}
				</div>
				<div
					v-else-if="lessonFeedback.loading"
					class="py-8 text-center text-sm text-ink-gray-6"
				>
					{{ __('Loading feedback...') }}
				</div>
				<div
					v-else-if="lessonFeedback.error"
					class="py-8 text-center text-sm text-ink-red-4"
				>
					{{
						lessonFeedback.error?.messages?.[0] ||
						__('Failed to load lesson feedback.')
					}}
				</div>
				<div
					v-else-if="!lessonFeedbackRows.length"
					class="py-8 text-center text-sm text-ink-gray-6"
				>
					{{ __('No lessons in this course.') }}
				</div>
				<div v-else>
					<p class="text-xs text-ink-gray-5 mb-4">
						{{
							__(
								'Thumbs up / down reactions from learners after each lesson (LMS Lesson Feedback).'
							)
						}}
					</p>
					<div
						class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-10 gap-y-6"
					>
						<div
							v-for="lesson in lessonFeedbackRows"
							:key="lesson.lesson"
							class="min-w-0"
						>
							<div
								class="text-sm font-medium text-ink-gray-9 mb-2 leading-snug line-clamp-2"
								:title="lesson.title"
							>
								{{ lesson.title }}
							</div>
							<div
								class="h-2 w-full rounded-sm overflow-hidden flex bg-surface-gray-2"
							>
								<template v-if="hasLessonFeedback(lesson)">
									<div
										class="bg-green-600 h-full shrink-0"
										:style="{
											width: `${lessonSatisfactionPercent(lesson)}%`,
										}"
									/>
									<div
										class="bg-red-500 h-full shrink-0"
										:style="{
											width: `${lessonDissatisfactionPercent(lesson)}%`,
										}"
									/>
								</template>
							</div>
							<div
								class="flex items-center justify-between mt-1.5 text-xs leading-none"
							>
								<span class="text-green-600 font-medium tabular-nums">
									+{{ lesson.yes_count }}
								</span>
								<span class="text-ink-gray-6 px-2 text-center">
									{{ lessonSatisfactionLabel(lesson) }}
								</span>
								<span class="text-red-600 font-medium tabular-nums">
									-{{ lesson.no_count }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<LearnerProgressDetailModal
			v-model="showLearnerDetail"
			:batch="selectedLearnerBatch"
			:member="selectedLearnerMember"
			@saved="learnerProgress.reload()"
		/>
	</div>
</template>

<script setup>
import {
	Avatar,
	AxisChart,
	Breadcrumbs,
	Button,
	createResource,
	ECharts,
	FormControl,
	Tooltip,
	usePageMeta,
} from 'frappe-ui'
import LearnerProgressDetailModal from '@/components/Modals/LearnerProgressDetailModal.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import { computed, onMounted, ref, watch, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '../stores/session'
import { usersStore } from '../stores/user'

const router = useRouter()
const { brand } = sessionStore()
const { userResource } = usersStore()

watchEffect(() => {
	if (userResource.data?.is_student) {
		router.replace({ name: 'Home' })
	}
})

const breadcrumbs = computed(() => [
	{
		label: __('Analytics dashboard'),
		route: { name: 'AnalyticsDashboard' },
	},
])

const overview = createResource({
	url: 'lms.lms.api.get_analytics_overview',
	cache: ['analyticsOverview'],
	auto: true,
})

const chartFilters = createResource({
	url: 'lms.lms.api.get_analytics_chart_filters',
	auto: true,
})

const selectedCourse = ref(null)
const selectedBatch = ref(null)
const selectedBatchStatus = ref(null)
const selectedBatchCerts = ref(null)
const selectedBatchLearners = ref(null)
const selectedCourseFeedback = ref(null)
const learnerStatusFilter = ref('All')
const learnerSearch = ref('')
const learnerPage = ref(1)
const learnerPageLength = ref(20)
const showLearnerDetail = ref(false)
const selectedLearnerMember = ref(null)
const selectedLearnerBatch = ref(null)
let learnerSearchDebounce = null
const statusFilters = ['All', 'Certified', 'In progress', 'Not started']
const ALL_FILTER = '__all__'
const learnerPageLengthOptions = [
	{ label: '10', value: 10 },
	{ label: '20', value: 20 },
	{ label: '50', value: 50 },
]

const courseOptions = computed(() => {
	if (!chartFilters.data?.courses?.length) return []
	return [
		{ label: __('All'), value: ALL_FILTER },
		...chartFilters.data.courses.map((course) => ({
			label: course.title,
			value: course.name,
		})),
	]
})

const batchOptions = computed(() => {
	const batches = chartFilters.data?.batches || []
	return [
		{ label: __('All'), value: ALL_FILTER },
		...batches.map((batch) => ({
			label: batch.title,
			value: batch.name,
		})),
	]
})

const hasBatches = computed(() => (chartFilters.data?.batches || []).length > 0)

const isAllBatchesView = computed(
	() => selectedBatchLearners.value === ALL_FILTER
)

const selectedCourseLabel = computed(() => {
	return (
		courseOptions.value.find((course) => course.value === selectedCourse.value)
			?.label || ''
	)
})

const selectedBatchLearnersLabel = computed(() => {
	return (
		batchOptions.value.find((batch) => batch.value === selectedBatchLearners.value)
			?.label || ''
	)
})

const selectedCourseFeedbackLabel = computed(() => {
	return (
		courseOptions.value.find((course) => course.value === selectedCourseFeedback.value)
			?.label || ''
	)
})

const lessonCompletion = createResource({
	url: 'lms.lms.api.get_analytics_lesson_completion',
	makeParams() {
		return { course: selectedCourse.value }
	},
})

const activeLearnersTrend = createResource({
	url: 'lms.lms.api.get_analytics_active_learners_trend',
	makeParams() {
		return { batch: selectedBatch.value, weeks: 8 }
	},
})

const courseStatusBreakdown = createResource({
	url: 'lms.lms.api.get_analytics_course_status_breakdown',
	makeParams() {
		return { batch: selectedBatchStatus.value }
	},
})

const certificationsTrend = createResource({
	url: 'lms.lms.api.get_analytics_certifications_trend',
	makeParams() {
		return { batch: selectedBatchCerts.value, months: 6 }
	},
})

const learnerProgress = createResource({
	url: 'lms.lms.api.get_analytics_learner_progress',
	makeParams() {
		if (!selectedBatchLearners.value) return null
		return {
			batch: selectedBatchLearners.value,
			status_filter: learnerStatusFilter.value,
			page: learnerPage.value,
			page_length: learnerPageLength.value,
			search: learnerSearch.value?.trim() || undefined,
		}
	},
	onError(error) {
		console.error('Learner progress failed:', error)
	},
})

const lessonFeedback = createResource({
	url: 'lms.lms.api.get_analytics_lesson_feedback',
	makeParams() {
		return { course: selectedCourseFeedback.value }
	},
})

function reloadLessonCompletion() {
	if (selectedCourse.value) {
		lessonCompletion.reload()
	}
}

function reloadActiveLearnersTrend() {
	if (selectedBatch.value) {
		activeLearnersTrend.reload()
	}
}

function reloadCourseStatusBreakdown() {
	if (selectedBatchStatus.value) {
		courseStatusBreakdown.reload()
	}
}

function reloadCertificationsTrend() {
	if (selectedBatchCerts.value) {
		certificationsTrend.reload()
	}
}

function reloadLearnerProgress() {
	if (!selectedBatchLearners.value) return
	learnerProgress.reload()
}

function reloadLessonFeedback() {
	if (selectedCourseFeedback.value) {
		lessonFeedback.reload()
	}
}

function resetLearnerPagination() {
	learnerPage.value = 1
}

function setLearnerStatusFilter(filter) {
	learnerStatusFilter.value = filter
	resetLearnerPagination()
	reloadLearnerProgress()
}

function onLearnerBatchChange() {
	learnerSearch.value = ''
	resetLearnerPagination()
	reloadLearnerProgress()
}

function onLearnerSearchInput() {
	if (learnerSearchDebounce) {
		clearTimeout(learnerSearchDebounce)
	}
	learnerSearchDebounce = setTimeout(() => {
		resetLearnerPagination()
		reloadLearnerProgress()
	}, 300)
}

function onLearnerPageLengthChange() {
	resetLearnerPagination()
	reloadLearnerProgress()
}

function goToLearnerPage(page) {
	if (page < 1) return
	learnerPage.value = page
	reloadLearnerProgress()
}

function openLearnerDetail(row) {
	const batch =
		row.batch ||
		(selectedBatchLearners.value !== ALL_FILTER ? selectedBatchLearners.value : null)
	if (!batch || !row?.member) return
	selectedLearnerBatch.value = batch
	selectedLearnerMember.value = row.member
	showLearnerDetail.value = true
}

function statusClass(statusKey) {
	if (statusKey === 'certified') {
		return 'text-green-700 bg-green-50'
	}
	if (statusKey === 'in_progress') {
		return 'text-blue-700 bg-blue-50'
	}
	return 'text-ink-gray-6 bg-surface-gray-2'
}

function hasLessonFeedback(lesson) {
	return (lesson.yes_count || 0) + (lesson.no_count || 0) > 0
}

function lessonSatisfactionPercent(lesson) {
	const total = (lesson.yes_count || 0) + (lesson.no_count || 0)
	if (!total) return 0
	return (lesson.yes_count / total) * 100
}

function lessonDissatisfactionPercent(lesson) {
	const total = (lesson.yes_count || 0) + (lesson.no_count || 0)
	if (!total) return 0
	return (lesson.no_count / total) * 100
}

function lessonSatisfactionLabel(lesson) {
	if (!hasLessonFeedback(lesson)) {
		return __('No feedback yet')
	}
	return `${lesson.satisfaction}% ${__('sat.')}`
}

function ensureValidSelection(current, options) {
	if (!options?.length) return null
	const validValues = options.map((option) => option.value)
	if (current && validValues.includes(current)) return current
	return options[0].value
}

function initChartFilters(data) {
	if (!data) return

	const courses = courseOptions.value

	if (courses.length) {
		selectedCourse.value = ensureValidSelection(selectedCourse.value, courses)
		selectedCourseFeedback.value = ensureValidSelection(
			selectedCourseFeedback.value,
			courses
		)
	}
	// Always default batch filters to "All" (works for course-only sites too)
	selectedBatch.value = ensureValidSelection(selectedBatch.value, batchOptions.value)
	selectedBatchStatus.value = ensureValidSelection(
		selectedBatchStatus.value,
		batchOptions.value
	)
	selectedBatchCerts.value = ensureValidSelection(
		selectedBatchCerts.value,
		batchOptions.value
	)
	selectedBatchLearners.value = ensureValidSelection(
		selectedBatchLearners.value,
		batchOptions.value
	)

	reloadLessonCompletion()
	reloadActiveLearnersTrend()
	reloadCourseStatusBreakdown()
	reloadCertificationsTrend()
	reloadLearnerProgress()
	reloadLessonFeedback()
}

watch(() => chartFilters.data, initChartFilters, { immediate: true })

watch(selectedCourse, (course, previous) => {
	if (course && course !== previous) {
		reloadLessonCompletion()
	}
})

watch(selectedCourseFeedback, (course, previous) => {
	if (course && course !== previous) {
		reloadLessonFeedback()
	}
})

watch(selectedBatchLearners, (batch, previous) => {
	if (batch && batch !== previous) {
		reloadLearnerProgress()
	}
})

watch(selectedBatch, (batch, previous) => {
	if (batch && batch !== previous) {
		reloadActiveLearnersTrend()
	}
})

watch(selectedBatchStatus, (batch, previous) => {
	if (batch && batch !== previous) {
		reloadCourseStatusBreakdown()
	}
})

watch(selectedBatchCerts, (batch, previous) => {
	if (batch && batch !== previous) {
		reloadCertificationsTrend()
	}
})

onMounted(() => {
	initChartFilters(chartFilters.data)
})

const lessonCompletionChartData = computed(() => {
	return (
		lessonCompletion.data?.lessons?.map((row) => ({
			label: row.label,
			completion: row.completion,
		})) ?? []
	)
})

const activeLearnersChartData = computed(() => {
	return activeLearnersTrend.data?.weeks ?? []
})

const activeLearnersPeriodDescription = computed(() => {
	return activeLearnersTrend.data?.period_description ?? ''
})

const activeLearnersWeekRangeByLabel = computed(() => {
	const lookup = {}
	for (const row of activeLearnersChartData.value) {
		if (row.week) {
			lookup[row.week] = row.week_range || row.week
		}
	}
	return lookup
})

const activeLearnersChartConfig = computed(() => {
	const weekRanges = activeLearnersWeekRangeByLabel.value

	return {
		data: activeLearnersChartData.value,
		xAxis: {
			key: 'week',
			title: __('Date range'),
			type: 'category',
			echartOptions: {
				axisLabel: {
					rotate: 35,
					fontSize: 11,
				},
			},
		},
		yAxis: {
			title: __('Learners'),
			echartOptions: {
				minInterval: 1,
				min: 0,
			},
		},
		series: [
			{
				name: 'learners',
				type: 'line',
				showDataPoints: true,
				echartOptions: {
					itemStyle: { color: '#16a34a' },
					lineStyle: { color: '#16a34a' },
					areaStyle: { color: 'rgba(22, 163, 74, 0.15)' },
				},
			},
		],
		echartOptions: {
			tooltip: {
				trigger: 'axis',
				formatter(params) {
					const point = Array.isArray(params) ? params[0] : params
					const label = point?.axisValue || point?.name || ''
					const range = weekRanges[label] || label
					const value = Array.isArray(point?.value)
						? point.value[1]
						: point?.value
					return `${range}<br/>${__('Active learners')}: ${value ?? 0}`
				},
			},
		},
	}
})

const COURSE_STATUS_COLORS = {
	completed: '#3b82f6',
	in_progress: '#16a34a',
	not_started: '#ef4444',
}

const courseStatusChartOptions = computed(() => {
	const segments = courseStatusBreakdown.data?.segments ?? []
	const total = courseStatusBreakdown.data?.total ?? 0

	const data = segments.map((segment) => ({
		name: segment.label,
		value: segment.value,
		itemStyle: {
			color: COURSE_STATUS_COLORS[segment.status_key] || '#9ca3af',
		},
	}))

	return {
		animation: true,
		animationDuration: 700,
		textStyle: { fontFamily: ['InterVar', 'sans-serif'] },
		series: [
			{
				type: 'pie',
				center: ['50%', '48%'],
				radius: ['40%', '70%'],
				label: { show: false },
				labelLine: { show: false },
				emphasis: { scaleSize: 5 },
				data,
			},
		],
		legend: {
			orient: 'horizontal',
			bottom: 0,
			left: 'center',
			show: true,
			type: 'scroll',
			itemGap: 12,
			formatter(name) {
				const segment = data.find((row) => row.name === name)
				const percentage =
					total > 0 ? ((segment?.value ?? 0) / total) * 100 : 0
				return `${name} (${percentage.toFixed(0)}%)`
			},
			textStyle: {
				padding: [0, 0, 0, -5],
				color: 'var(--ink-gray-8)',
			},
			icon: 'circle',
		},
		tooltip: {
			trigger: 'item',
			confine: true,
			appendToBody: false,
			formatter(params) {
				const value = params.value
				const percentage = total > 0 ? (value / total) * 100 : 0
				return `
					<div class="flex items-center justify-between gap-5">
						<div>${params.name}</div>
						<div class="font-bold">
							${value} (${percentage.toFixed(0)}%)
						</div>
					</div>
				`
			},
		},
	}
})

const certificationsChartData = computed(() => {
	return certificationsTrend.data?.months ?? []
})

const certificationsByMonth = computed(() => {
	const lookup = {}
	for (const row of certificationsChartData.value) {
		if (row.month) {
			lookup[row.month] = row
		}
	}
	return lookup
})

const certificationsChartConfig = computed(() => {
	const byMonth = certificationsByMonth.value

	return {
		data: certificationsChartData.value,
		xAxis: {
			key: 'month',
			title: __('Month'),
			type: 'category',
		},
		yAxis: {
			title: __('Learners'),
			echartOptions: {
				minInterval: 1,
				min: 0,
			},
		},
		series: [
			{
				name: 'certified',
				type: 'line',
				showDataPoints: true,
				echartOptions: {
					itemStyle: { color: '#16a34a' },
					lineStyle: { color: '#16a34a' },
				},
			},
			{
				name: 'in_progress',
				type: 'line',
				showDataPoints: true,
				echartOptions: {
					itemStyle: { color: '#3b82f6' },
					lineStyle: { color: '#3b82f6' },
				},
			},
			{
				name: 'not_started',
				type: 'line',
				showDataPoints: true,
				echartOptions: {
					itemStyle: { color: '#9ca3af' },
					lineStyle: { color: '#9ca3af' },
				},
			},
		],
		echartOptions: {
			legend: {
				show: false,
			},
			tooltip: {
				trigger: 'axis',
				confine: true,
				appendToBody: false,
				axisPointer: {
					type: 'line',
				},
				formatter(params) {
					const points = Array.isArray(params) ? params : [params]
					const label = points[0]?.axisValue || points[0]?.name || ''
					const row = byMonth[label] || {}
					const period = row.period || label

					const fromSeries = {}
					for (const point of points) {
						const key = point?.seriesName
						if (!key) continue
						const raw = Array.isArray(point.value)
							? point.value[1]
							: point.value
						fromSeries[key] = Number(raw ?? 0)
					}

					const certified = fromSeries.certified ?? Number(row.certified ?? 0)
					const inProgress =
						fromSeries.in_progress ?? Number(row.in_progress ?? 0)
					const notStarted =
						fromSeries.not_started ?? Number(row.not_started ?? 0)

					return `
						<div class="flex flex-col gap-1 min-w-[12rem]">
							<div class="font-medium">${period}</div>
							<div style="border-top: 1px solid var(--ink-gray-3); margin: 2px 0;"></div>
							<div class="flex items-center justify-between gap-5">
								<div>${__('Certified')}</div>
								<div>${certified}</div>
							</div>
							<div class="flex items-center justify-between gap-5">
								<div>${__('In progress')}</div>
								<div>${inProgress}</div>
							</div>
							<div class="flex items-center justify-between gap-5">
								<div>${__('Not started')}</div>
								<div>${notStarted}</div>
							</div>
							<div style="border-top: 1px solid var(--ink-gray-3); margin: 2px 0;"></div>
						</div>
					`
				},
			},
		},
	}
})

const certificationsSummary = computed(() => {
	return certificationsTrend.data?.summary ?? null
})

const learnerRows = computed(() => learnerProgress.data?.learners ?? [])

const learnerTotalCount = computed(
	() => learnerProgress.data?.total_count ?? 0
)

const learnerTotalPages = computed(() => {
	const total = learnerTotalCount.value
	const size = learnerPageLength.value || 20
	return Math.max(1, Math.ceil(total / size))
})

const learnerPaginationSummary = computed(() => {
	const total = learnerTotalCount.value
	if (!total) return ''

	const page = learnerProgress.data?.page || learnerPage.value
	const size = learnerProgress.data?.page_length || learnerPageLength.value
	const start = (page - 1) * size + 1
	const end = Math.min(page * size, total)

	return __('Showing {0}–{1} of {2} learners').format(start, end, total)
})

const lessonFeedbackRows = computed(() => lessonFeedback.data?.lessons ?? [])

const overviewCards = computed(() => {
	if (!overview.data) return []

	const data = overview.data
	return [
		{
			key: 'total_courses',
			label: 'Total courses',
			displayValue: data.total_courses?.value ?? 0,
			subtext: data.total_courses?.subtext ?? '',
		},
		{
			key: 'total_users',
			label: 'Total users',
			displayValue: data.total_users?.value ?? 0,
			subtext: data.total_users?.subtext ?? '',
		},
		{
			key: 'active_learners',
			label: 'Active learners',
			displayValue: data.active_learners?.value ?? 0,
			subtext: data.active_learners?.subtext ?? '',
		},
		{
			key: 'avg_completion',
			label: 'Avg completion',
			displayValue: `${data.avg_completion?.value ?? 0}%`,
			subtext: data.avg_completion?.subtext ?? '',
		},
		{
			key: 'certificates_issued',
			label: 'Certificates issued',
			displayValue: data.certificates_issued?.value ?? 0,
			subtext: data.certificates_issued?.subtext ?? '',
		},
	]
})

usePageMeta(() => ({
	title: __('Analytics dashboard'),
	icon: brand.favicon,
}))
</script>

<style scoped>
.analytics-chart-filter-wrap {
	width: 11rem;
	max-width: 42%;
	min-width: 0;
	overflow: hidden;
}

.learner-search-input :deep(.form-group) {
	margin-bottom: 0;
}

.analytics-chart-filter :deep(.form-group),
.analytics-chart-filter.space-y-1\.5 {
	margin-bottom: 0;
	width: 100%;
	min-width: 0;
	overflow: hidden;
}

.analytics-chart-filter :deep(.select-trigger-sizer) {
	display: none !important;
}

.analytics-chart-filter :deep([data-slot='trigger']) {
	display: flex !important;
	width: 100% !important;
	max-width: 100% !important;
	min-width: 0 !important;
	overflow: hidden !important;
}

.analytics-chart-filter :deep([data-slot='trigger'] .grid) {
	min-width: 0;
	flex: 1 1 0%;
	overflow: hidden;
}

.analytics-chart-filter :deep([data-slot='trigger'] [class*='truncate']) {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.analytics-chart-area :deep(div[dir='ltr']) {
	min-width: 0 !important;
	width: 100% !important;
	max-width: 100%;
}
</style>
