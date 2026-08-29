<template>
	<div class="mt-7 mb-10">
		<h2 class="mb-3 text-lg font-semibold text-ink-gray-9">
			{{ __('Mock results') }}
		</h2>
		<div v-if="mocks.loading" class="text-sm text-ink-gray-6">
			{{ __('Loading...') }}
		</div>
		<div
			v-else-if="!mocks.data?.length"
			class="text-sm italic text-ink-gray-5"
		>
			{{ __('No published mock results yet.') }}
		</div>
		<div v-else class="space-y-3">
			<button
				v-for="mock in mocks.data"
				:key="mock.name"
				type="button"
				class="w-full text-left rounded-lg border px-4 py-3 hover:bg-surface-gray-1 transition-colors"
				@click="openMock(mock.name)"
			>
				<div class="font-medium text-ink-gray-9">{{ mock.title }}</div>
				<div class="text-xs text-ink-gray-6 mt-1">
					<span v-if="mock.published_on_display">{{ mock.published_on_display }}</span>
					<span v-if="mock.overall_rating">
						· {{ __('Rating') }}: {{ mock.overall_rating }}/5
					</span>
					<span v-if="mock.assessment_score_percent != null">
						· {{ mock.assessment_score_percent }}%
					</span>
				</div>
			</button>
		</div>
		<p class="text-xs text-ink-gray-5 mt-6 border-t pt-4">
			{{
				__(
					'This section is read-only. Contact your instructor if you have questions about your mock results.'
				)
			}}
		</p>
	</div>

	<MockAssessmentViewModal
		v-model="showDetail"
		:mock-name="selectedMock"
		student-mode
		read-only
	/>
</template>

<script setup>
import { createResource } from 'frappe-ui'
import { inject, onMounted, ref } from 'vue'
import MockAssessmentViewModal from '@/components/MockAssessment/MockAssessmentViewModal.vue'

const $user = inject('$user')
const showDetail = ref(false)
const selectedMock = ref(null)

const mocks = createResource({
	url: 'lms.lms.mock_assessment_api.get_student_mock_assessments',
	auto: false,
})

onMounted(() => {
	if ($user.data) mocks.reload()
})

function openMock(name) {
	selectedMock.value = name
	showDetail.value = true
}
</script>
