<template>
	<Dialog
		v-model="show"
		:options="{
			size: '3xl',
		}"
	>
		<template #body-title>
			<div
				v-if="detail.loading && !detail.data"
				class="text-base font-medium text-ink-gray-6"
			>
				{{ __('Loading learner...') }}
			</div>
			<div v-else-if="detail.data" class="flex items-start gap-3 min-w-0 pr-2">
				<Avatar
					:image="detail.data.user_image"
					:label="detail.data.full_name"
					size="lg"
				/>
				<div class="min-w-0">
					<h2 class="text-lg font-semibold text-ink-gray-9 truncate">
						{{ detail.data.full_name }}
					</h2>
					<p class="text-sm text-ink-gray-6 mt-0.5">
						{{
							__('{0}/{1} lessons • Last active: {2}').format(
								detail.data.lessons_completed,
								detail.data.lessons_total,
								detail.data.last_active
							)
						}}
					</p>
				</div>
			</div>
			<div v-else-if="detail.error" class="text-base font-medium text-ink-red-4">
				{{ __('Learner details') }}
			</div>
		</template>

		<template #body-content>
			<div
				v-if="detail.loading && !detail.data"
				class="flex items-center justify-center py-12"
			>
				<span class="text-sm text-ink-gray-6">{{ __('Loading learner...') }}</span>
			</div>

			<div v-else-if="detail.error" class="py-8 text-center text-sm text-ink-red-4">
				{{ detail.error?.messages?.[0] || __('Failed to load learner details.') }}
			</div>

			<div v-else-if="detail.data" class="max-h-[70vh] overflow-y-auto space-y-5">
				<div
					class="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-900"
				>
					{{ __('Instructor review - private, not visible to learner') }}
				</div>

				<div v-if="timeTracking.loading && !timeTracking.data" class="text-sm text-ink-gray-6">
					{{ __('Loading time tracking...') }}
				</div>
				<div v-else-if="timeTracking.data" class="space-y-4">
					<h3 class="text-sm font-semibold text-ink-gray-9">
						{{ __('Time on platform') }}
					</h3>
					<div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
						<div
							v-for="card in timeTracking.data.summary_cards"
							:key="card.key"
							class="rounded-lg border bg-surface-gray-1 px-4 py-3"
						>
							<div class="text-xs text-ink-gray-6 mb-1">{{ __(card.label) }}</div>
							<div class="text-lg font-semibold text-ink-gray-9 tabular-nums">
								{{ card.display }}
							</div>
							<div class="text-xs text-ink-gray-5 mt-0.5">{{ card.subtext }}</div>
						</div>
					</div>
					<ActivityHeatmap :user-id="props.member" />
				</div>

				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					<div class="rounded-lg border bg-surface-gray-1 px-4 py-3">
						<div class="text-xs text-ink-gray-6 mb-1">{{ __('Lessons done') }}</div>
						<div class="text-lg font-semibold text-ink-gray-9">
							{{ detail.data.lessons_completed }}/{{ detail.data.lessons_total }}
						</div>
					</div>
					<div class="rounded-lg border bg-surface-gray-1 px-4 py-3">
						<div class="text-xs text-ink-gray-6 mb-1">{{ __('Quiz avg') }}</div>
						<div class="text-lg font-semibold text-ink-gray-9">
							{{
								detail.data.quiz_average !== null &&
								detail.data.quiz_average !== undefined
									? `${detail.data.quiz_average}%`
									: '—'
							}}
						</div>
					</div>
				</div>

				<div>
					<label class="text-sm font-medium text-ink-gray-8 mb-1.5 block">
						{{ __('Instructor notes') }}
					</label>
					<FormControl
						v-model="instructorNotes"
						type="textarea"
						:rows="3"
						:placeholder="__('Add private notes for this learner...')"
						@blur="saveReview"
					/>
				</div>

				<div>
					<div class="flex items-center justify-between mb-2">
						<label class="text-sm font-medium text-ink-gray-8">
							{{ __('Mock result') }}
						</label>
						<Button variant="solid" size="sm" @click="openMockWizard()">
							{{ __('Add mock') }}
						</Button>
					</div>
					<div
						v-if="!detail.data.mock_assessments?.length"
						class="text-sm text-ink-gray-6 py-4 text-center border rounded-lg"
					>
						{{ __('No mock assessments yet.') }}
					</div>
					<div v-else class="space-y-2">
						<div
							v-for="mock in detail.data.mock_assessments"
							:key="mock.name"
							class="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-sm"
						>
							<div class="min-w-0">
								<div class="font-medium text-ink-gray-9 truncate">
									{{ mock.title }}
								</div>
								<div class="text-xs text-ink-gray-6 mt-0.5">
									{{ mock.submitted_on_display }}
									· {{ __(mock.status) }}
									<span v-if="mock.overall_rating">
										· {{ __('Rating') }}: {{ mock.overall_rating }}/5
									</span>
								</div>
							</div>
							<div class="flex flex-wrap items-center gap-2 shrink-0">
								<Button variant="outline" size="sm" @click="viewMock(mock.name)">
									{{ __('View') }}
								</Button>
								<Button
									v-if="mock.status === 'Draft'"
									variant="outline"
									size="sm"
									@click="editMock(mock.name)"
								>
									{{ __('Edit') }}
								</Button>
								<Button
									variant="outline"
									size="sm"
									:loading="togglingMock === mock.name"
									@click="toggleMockVisibility(mock)"
								>
									{{
										mock.status === 'Published'
											? __('Hide from learner')
											: __('Publish')
									}}
								</Button>
								<Button
									v-if="mock.status === 'Draft'"
									variant="outline"
									size="sm"
									theme="red"
									:loading="deletingMock === mock.name"
									@click.stop="confirmDeleteMock(mock)"
								>
									{{ __('Delete') }}
								</Button>
							</div>
						</div>
					</div>
				</div>

				<div>
					<label class="text-sm font-medium text-ink-gray-8 mb-2 block">
						{{ __('Assessment results') }}
					</label>
					<div
						v-if="!detail.data.assessments?.length"
						class="text-sm text-ink-gray-6 py-4 text-center border rounded-lg"
					>
						{{ __('No assessments in this batch yet.') }}
					</div>
					<div v-else class="space-y-2">
						<div
							v-for="item in detail.data.assessments"
							:key="`${item.assessment_type}-${item.assessment_name}`"
							class="flex items-center justify-between rounded-lg border px-3 py-2.5 text-sm"
						>
							<div class="min-w-0">
								<span
									class="inline-block text-xs font-medium px-1.5 py-0.5 rounded mr-2"
									:class="typeBadgeClass(item.type)"
								>
									{{ __(item.type) }}
								</span>
								<span class="text-ink-gray-9">{{ item.title }}</span>
							</div>
							<div class="flex items-center gap-2 shrink-0 ml-2">
								<span class="text-ink-gray-7 tabular-nums">
									{{ item.score_display }}
								</span>
								<span
									v-if="item.has_attempt"
									class="text-xs font-medium capitalize"
									:class="
										item.passed ? 'text-green-600' : 'text-red-600'
									"
								>
									{{ __(item.status_label) }}
								</span>
								<span v-else class="text-xs text-ink-gray-5">
									{{ __('Not attempted') }}
								</span>
								<Button
									v-if="item.has_attempt"
									variant="outline"
									size="sm"
									theme="red"
									:loading="
										resettingAssessment ===
										`${item.assessment_type}:${item.assessment_name}`
									"
									@click.stop="confirmResetAssessment(item)"
								>
									{{ __('Reset') }}
								</Button>
							</div>
						</div>
					</div>
				</div>

				<div>
					<label class="text-sm font-medium text-ink-gray-8 mb-1 block">
						{{ __('Add assessment after lesson') }}
					</label>
					<p class="text-xs text-ink-gray-6 mb-3">
						{{ __('Select type to attach after the most recent lesson:') }}
					</p>
					<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
						<button
							type="button"
							class="rounded-lg border-2 border-blue-200 bg-blue-50 px-4 py-4 text-left hover:bg-blue-100 transition-colors"
							@click="openAssessmentModal('LMS Quiz')"
						>
							<div class="text-sm font-semibold text-blue-800">
								{{ __('Quiz') }}
							</div>
							<div class="text-xs text-blue-700 mt-1">{{ __('Attach quiz') }}</div>
						</button>
						<button
							type="button"
							class="rounded-lg border-2 border-green-200 bg-green-50 px-4 py-4 text-left hover:bg-green-100 transition-colors"
							@click="openAssessmentModal('LMS Assignment')"
						>
							<div class="text-sm font-semibold text-green-800">
								{{ __('Assignment') }}
							</div>
							<div class="text-xs text-green-700 mt-1">
								{{ __('Attach assignment') }}
							</div>
						</button>
						<button
							type="button"
							class="rounded-lg border-2 border-purple-200 bg-purple-50 px-4 py-4 text-left hover:bg-purple-100 transition-colors"
							@click="openAssessmentModal('LMS Programming Exercise')"
						>
							<div class="text-sm font-semibold text-purple-800">
								{{ __('Programming') }}
							</div>
							<div class="text-xs text-purple-700 mt-1">
								{{ __('Attach exercise') }}
							</div>
						</button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>

	<AssessmentModal
		v-model="showAssessmentModal"
		:batch="batch"
		:initial-assessment-type="assessmentPresetType"
		@added="onAssessmentAdded"
	/>

	<MockAssessmentWizard
		v-model="showMockWizard"
		:batch="batch"
		:member="member"
		:edit-name="mockEditName"
		@saved="onMockSaved"
		@published="onMockSaved"
	/>

	<MockAssessmentViewModal
		v-model="showMockView"
		:mock-name="mockViewName"
		:batch="batch"
		:member="member"
	/>
</template>

<script setup>
import {
	Avatar,
	Button,
	Dialog,
	FormControl,
	createResource,
	toast,
} from 'frappe-ui'
import { getCurrentInstance, ref, watch } from 'vue'
import AssessmentModal from '@/components/Modals/AssessmentModal.vue'
import MockAssessmentWizard from '@/components/MockAssessment/MockAssessmentWizard.vue'
import MockAssessmentViewModal from '@/components/MockAssessment/MockAssessmentViewModal.vue'
import ActivityHeatmap from '@/components/Analytics/ActivityHeatmap.vue'

const show = defineModel({ type: Boolean, default: false })
const props = defineProps({
	batch: { type: String, default: null },
	member: { type: String, default: null },
})

const emit = defineEmits(['saved'])

const instructorNotes = ref('')
const showAssessmentModal = ref(false)
const assessmentPresetType = ref(null)
const showMockWizard = ref(false)
const showMockView = ref(false)
const mockEditName = ref(null)
const mockViewName = ref(null)
const togglingMock = ref(null)
const deletingMock = ref(null)
const resettingAssessment = ref(null)
const app = getCurrentInstance()
const $dialog = app?.appContext.config.globalProperties.$dialog

const detail = createResource({
	url: 'lms.lms.api.get_analytics_learner_detail',
	makeParams() {
		if (!props.batch || !props.member) return null
		return { batch: props.batch, member: props.member }
	},
})

const timeTracking = createResource({
	url: 'lms.tracking.get_user_summary',
	makeParams() {
		if (!props.member) return null
		return { user_id: props.member }
	},
})

const saveResource = createResource({
	url: 'lms.lms.api.save_analytics_learner_review',
	makeParams(values = {}) {
		return {
			batch: props.batch,
			member: props.member,
			instructor_notes: instructorNotes.value,
			...values,
		}
	},
})

function loadDetail() {
	if (!props.batch || !props.member) return
	detail.reload()
	timeTracking.reload()
}

watch(
	() => [show.value, props.batch, props.member],
	([visible]) => {
		if (visible && props.batch && props.member) {
			loadDetail()
		}
	}
)

watch(
	() => detail.data,
	(data) => {
		if (!data) return
		instructorNotes.value = data.instructor_notes || ''
	},
	{ immediate: true }
)

function saveReview() {
	if (!props.batch || !props.member) return
	saveResource.submit(
		{},
		{
			onSuccess() {
				emit('saved')
			},
			onError(err) {
				toast.error(err?.messages?.[0] || __('Could not save review.'))
			},
		}
	)
}

watch(showMockWizard, (open) => {
	if (!open) mockEditName.value = null
})

function openMockWizard(name = null) {
	mockEditName.value = name
	showMockWizard.value = true
}

function editMock(name) {
	openMockWizard(name)
}

function viewMock(name) {
	mockViewName.value = name
	showMockView.value = true
}

function onMockSaved() {
	loadDetail()
	emit('saved')
}

const toggleResource = createResource({
	url: 'lms.lms.mock_assessment_api.toggle_mock_assessment_visibility',
	makeParams(values = {}) {
		return {
			name: values.name,
			batch: props.batch,
			member: props.member,
		}
	},
})

function toggleMockVisibility(mock) {
	if (!props.batch || !props.member) return
	togglingMock.value = mock.name
	toggleResource.submit(
		{ name: mock.name },
		{
			onSuccess() {
				togglingMock.value = null
				toast.success(
					mock.status === 'Published'
						? __('Mock hidden from learner')
						: __('Mock published')
				)
				loadDetail()
				emit('saved')
			},
			onError(err) {
				togglingMock.value = null
				toast.error(err?.messages?.[0] || __('Could not update visibility.'))
			},
		}
	)
}

const deleteMockResource = createResource({
	url: 'lms.lms.mock_assessment_api.delete_mock_assessment',
	makeParams(values = {}) {
		return {
			name: values.name,
			batch: props.batch,
			member: props.member,
		}
	},
})

function confirmDeleteMock(mock) {
	const message = __('This permanently removes "{0}". This cannot be undone.').format(
		mock.title
	)
	if (!$dialog) {
		if (window.confirm(`${__('Delete mock assessment?')}\n\n${message}`)) {
			deleteMock(mock)
		}
		return
	}
	$dialog({
		title: __('Delete mock assessment?'),
		message,
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					close()
					deleteMock(mock)
				},
			},
		],
	})
}

function deleteMock(mock) {
	if (!props.batch || !props.member) return
	deletingMock.value = mock.name
	deleteMockResource.submit(
		{ name: mock.name },
		{
			onSuccess() {
				deletingMock.value = null
				toast.success(__('Mock assessment deleted'))
				loadDetail()
				emit('saved')
			},
			onError(err) {
				deletingMock.value = null
				toast.error(err?.messages?.[0] || __('Could not delete mock assessment.'))
			},
		}
	)
}

function openAssessmentModal(type) {
	assessmentPresetType.value = type
	showAssessmentModal.value = true
}

function onAssessmentAdded() {
	loadDetail()
}

const resetAssessmentResource = createResource({
	url: 'lms.lms.api.reset_learner_assessment_attempt',
	makeParams(values = {}) {
		return {
			batch: props.batch,
			member: props.member,
			assessment_type: values.assessment_type,
			assessment_name: values.assessment_name,
		}
	},
})

function assessmentResetKey(item) {
	return `${item.assessment_type}:${item.assessment_name}`
}

function assessmentResetLabel(item) {
	if (item.type === 'Assignment') return __('assignment')
	if (item.type === 'Programming') return __('programming exercise')
	return __('quiz')
}

function confirmResetAssessment(item) {
	const attempts = item.attempt_count || 1
	const label = assessmentResetLabel(item)
	const message = __(
		'This will delete {0} attempt(s) for "{1}". The learner can submit this {2} again and the new result will be counted.'
	).format(attempts, item.title, label)
	if (!$dialog) {
		if (
			window.confirm(
				`${__('Reset assessment for this learner?')}\n\n${message}`
			)
		) {
			resetAssessment(item)
		}
		return
	}
	$dialog({
		title: __('Reset assessment for this learner?'),
		message,
		actions: [
			{
				label: __('Reset'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					close()
					resetAssessment(item)
				},
			},
		],
	})
}

function resetAssessment(item) {
	if (!props.batch || !props.member || !item?.assessment_name) return
	resettingAssessment.value = assessmentResetKey(item)
	resetAssessmentResource.submit(
		{
			assessment_type: item.assessment_type,
			assessment_name: item.assessment_name,
		},
		{
			onSuccess() {
				resettingAssessment.value = null
				toast.success(
					__('Assessment attempt reset. The learner can try again now.')
				)
				loadDetail()
				emit('saved')
			},
			onError(err) {
				resettingAssessment.value = null
				toast.error(
					err?.messages?.[0] || __('Could not reset assessment attempt.')
				)
			},
		}
	)
}

function typeBadgeClass(type) {
	if (type === 'Quiz') return 'bg-blue-100 text-blue-800'
	if (type === 'Assignment') return 'bg-green-100 text-green-800'
	return 'bg-purple-100 text-purple-800'
}
</script>
