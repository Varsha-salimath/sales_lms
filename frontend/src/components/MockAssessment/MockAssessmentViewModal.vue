<template>
	<Dialog
		v-model="show"
		:options="{
			title: mockData?.title || __('Mock result'),
			size: '4xl',
		}"
	>
		<template #body-content>
			<div v-if="loading" class="py-8 text-center text-sm text-ink-gray-6">
				{{ __('Loading...') }}
			</div>
			<div v-else-if="mockData" class="max-h-[70vh] overflow-y-auto space-y-5">
				<div
					v-if="readOnly"
					class="rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-900"
				>
					{{
						__(
							'Your mock result is ready — reviewed by {0} on {1}.'
						).format(
							mockData.evaluator_name || mockData.instructor_name || __('Instructor'),
							mockData.published_on_display || '—'
						)
					}}
				</div>
				<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
					<div class="rounded-lg border bg-surface-gray-1 px-3 py-2">
						<div class="text-xs text-ink-gray-6">{{ __('Score') }}</div>
						<div class="text-lg font-semibold">
							{{
								mockData.assessment_score_percent != null
									? `${mockData.assessment_score_percent}%`
									: '—'
							}}
						</div>
					</div>
					<div class="rounded-lg border bg-surface-gray-1 px-3 py-2">
						<div class="text-xs text-ink-gray-6">{{ __('Overall rating') }}</div>
						<div class="text-lg font-semibold">
							{{
								mockData.overall_rating ? `${mockData.overall_rating}/5` : '—'
							}}
						</div>
					</div>
					<div class="rounded-lg border bg-surface-gray-1 px-3 py-2">
						<div class="text-xs text-ink-gray-6">{{ __('Attendance') }}</div>
						<div class="text-lg font-semibold">
							{{
								mockData.attendance_percent != null
									? `${mockData.attendance_percent}%`
									: '—'
							}}
						</div>
					</div>
					<div class="rounded-lg border bg-surface-gray-1 px-3 py-2">
						<div class="text-xs text-ink-gray-6">{{ __('Duration') }}</div>
						<div class="text-lg font-semibold">
							{{
								mockData.duration_minutes
									? `${mockData.duration_minutes} min`
									: '—'
							}}
						</div>
					</div>
				</div>

				<div
					v-for="section in mockData.evaluation_sections"
					:key="section.key"
					class="rounded-lg border p-4 space-y-2"
				>
					<div class="flex items-center justify-between">
						<h4 class="text-sm font-semibold text-ink-gray-9">{{ section.label }}</h4>
						<span v-if="section.rating" class="text-sm text-ink-gray-7">
							{{ __('Rating') }}: {{ section.rating }}/5
						</span>
					</div>
					<ul class="text-sm space-y-1">
						<li
							v-for="c in section.criteria"
							:key="c.key"
							:class="c.met ? 'text-green-700' : 'text-ink-gray-6'"
						>
							{{ c.met ? '✓' : '✗' }} {{ c.label }}
						</li>
					</ul>
					<p v-if="section.comment" class="text-sm text-ink-gray-7 italic">
						{{ section.comment }}
					</p>
				</div>

				<div class="rounded-lg border p-4 space-y-2">
					<h4 class="text-sm font-semibold">{{ __('Overall observation') }}</h4>
					<div v-if="mockData.strengths">
						<div class="text-xs font-medium text-ink-gray-6">{{ __('Strengths') }}</div>
						<p class="text-sm">{{ mockData.strengths }}</p>
					</div>
					<div v-if="mockData.areas_of_improvement">
						<div class="text-xs font-medium text-ink-gray-6">
							{{ __('Areas of improvement') }}
						</div>
						<p class="text-sm">{{ mockData.areas_of_improvement }}</p>
					</div>
					<div class="flex flex-wrap gap-3 text-sm">
						<span
							>{{ __('1:1 mentorship') }}:
							{{ mockData.needs_mentorship ? __('Yes') : __('No') }}</span
						>
						<span
							>{{ __('Re-mock') }}:
							{{ mockData.remock_needed ? __('Yes') : __('No') }}</span
						>
						<span
							>{{ __('Retraining') }}:
							{{ mockData.needs_retraining ? __('Yes') : __('No') }}</span
						>
					</div>
				</div>

				<a
					v-if="mockData.attachment"
					:href="getFileHref(mockData.attachment)"
					target="_blank"
					rel="noopener noreferrer"
					class="text-sm text-ink-blue-3 hover:underline"
				>
					{{ __('Download attachment') }}
				</a>

				<p v-if="readOnly" class="text-xs text-ink-gray-5 border-t pt-3">
					{{
						__(
							'This view is read-only. Contact your instructor if you have questions about your mock result.'
						)
					}}
				</p>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { getFileHref } from '@/utils/fileUrl'

const show = defineModel({ type: Boolean, default: false })
const props = defineProps({
	mockName: { type: String, default: null },
	batch: { type: String, default: null },
	member: { type: String, default: null },
	studentMode: { type: Boolean, default: false },
	readOnly: { type: Boolean, default: false },
})

const instructorDetail = createResource({
	url: 'lms.lms.mock_assessment_api.get_mock_assessment',
	makeParams() {
		if (!props.mockName || props.studentMode) return null
		return {
			name: props.mockName,
			batch: props.batch,
			member: props.member,
		}
	},
	auto: false,
})

const studentDetail = createResource({
	url: 'lms.lms.mock_assessment_api.get_student_mock_assessment',
	makeParams() {
		if (!props.mockName || !props.studentMode) return null
		return { name: props.mockName }
	},
	auto: false,
})

const loading = computed(
	() =>
		(props.studentMode ? studentDetail.loading : instructorDetail.loading) &&
		!mockData.value
)

const mockData = computed(() =>
	props.studentMode ? studentDetail.data : instructorDetail.data
)

watch(
	() => [show.value, props.mockName, props.studentMode],
	([visible, name]) => {
		if (!visible || !name) return
		if (props.studentMode) {
			studentDetail.reload()
		} else {
			instructorDetail.reload()
		}
	}
)
</script>
