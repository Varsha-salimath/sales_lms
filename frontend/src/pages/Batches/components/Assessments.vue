<template>
	<div>
		<div class="flex items-center justify-between mb-4">
			<div class="text-ink-gray-9 font-semibold">
				{{ __('Assessments') }}
			</div>
			<Button v-if="canAddAssessments()" @click="showModal = true">
				<template #prefix>
					<Plus class="h-4 w-4" />
				</template>
				{{ __('Add to batch') }}
			</Button>
		</div>

		<div v-if="assessments.loading" class="text-sm text-ink-gray-6 mb-4">
			{{ __('Loading assessments...') }}
		</div>

		<div v-if="liveFromCourse.length" class="mb-6">
			<div class="text-xs text-ink-gray-6 mb-2">
				{{
					__(
						'Live on courses — added from the course editor and turned on for this batch.'
					)
				}}
			</div>
			<div class="text-sm border rounded-lg overflow-hidden">
				<div
					v-for="row in liveFromCourse"
					:key="row.name"
					class="flex items-center justify-between gap-3 px-3 py-2 border-b last:border-b-0 hover:bg-surface-gray-2"
				>
					<router-link
						:to="getRowRoute(row)"
						class="flex-1 min-w-0"
					>
						<div class="font-medium text-ink-gray-9 truncate">
							{{ row.title }}
						</div>
						<div class="text-xs text-ink-gray-6">
							{{ getAssessmentTypeLabel(row.assessment_type) }}
							<span v-if="row.course_title"> · {{ row.course_title }}</span>
						</div>
					</router-link>
					<Badge theme="green" class="shrink-0">{{ __('Live') }}</Badge>
				</div>
			</div>
		</div>

		<div v-if="onBatch.length" class="text-sm">
			<div v-if="liveFromCourse.length" class="text-xs text-ink-gray-6 mb-2">
				{{ __('Added directly on this batch') }}
			</div>
			<ListView
				:columns="getAssessmentColumns()"
				:rows="onBatch"
				row-key="name"
				class="border rounded-lg"
				:options="{
					showTooltip: false,
					getRowRoute: (row) => getRowRoute(row),
					selectable: user.data?.is_student ? false : true,
				}"
			>
				<ListHeader
					class="mb-2 grid items-center gap-x-4 rounded-none rounded-t bg-surface-gray-2 p-2"
				>
					<ListHeaderItem :item="item" v-for="item in getAssessmentColumns()">
					</ListHeaderItem>
				</ListHeader>
				<ListRows>
					<ListRow
						:row="row"
						v-for="row in onBatch"
						class="!rounded-none"
					>
						<template #default="{ column, item }">
							<ListRowItem :item="row[column.key]" :align="column.align">
								<div v-if="column.key == 'assessment_type'">
									{{ getAssessmentTypeLabel(row[column.key]) }}
								</div>
								<div v-else-if="column.key == 'title'">
									{{ row[column.key] }}
								</div>
								<div v-else-if="isNaN(row[column.key])">
									<Badge :theme="getStatusTheme(row[column.key])">
										{{ row[column.key] }}
									</Badge>
								</div>
								<div v-else>
									{{ row[column.key] }}
								</div>
							</ListRowItem>
						</template>
					</ListRow>
				</ListRows>
				<ListSelectBanner class="!min-w-0">
					<template #actions="{ unselectAll, selections }">
						<div class="flex gap-2">
							<Button
								variant="ghost"
								@click="removeAssessments(selections, unselectAll)"
							>
								<Trash2 class="h-4 w-4 stroke-1.5" />
							</Button>
						</div>
					</template>
				</ListSelectBanner>
			</ListView>
		</div>

		<div
			v-if="
				!assessments.loading &&
				!liveFromCourse.length &&
				!onBatch.length
			"
			class="text-ink-gray-7 text-sm"
		>
			<p>{{ __('No assessments on this batch yet.') }}</p>
			<p class="mt-2 text-xs text-ink-gray-6">
				{{
					__(
						'Add assessments on a course (course Settings → Assessments) and turn them live for this batch, or use Add to batch below.'
					)
				}}
			</p>
		</div>
	</div>
	<AssessmentModal
		v-model="showModal"
		v-model:assessments="assessments"
		:batch="batchName"
		@added="assessments.reload()"
	/>
</template>
<script setup>
import {
	ListView,
	ListRow,
	ListRows,
	ListHeader,
	ListHeaderItem,
	ListRowItem,
	ListSelectBanner,
	createResource,
	Button,
	Badge,
} from 'frappe-ui'
import { computed, inject, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AssessmentModal from '@/components/Modals/AssessmentModal.vue'
import { Plus, Trash2 } from 'lucide-vue-next'

const route = useRoute()

const user = inject('$user')
const showModal = ref(false)
const readOnlyMode = window.read_only_mode

const props = defineProps({
	batch: {
		type: String,
		default: '',
	},
	preloadLive: {
		type: Array,
		default: () => [],
	},
	rows: {
		type: Array,
	},
	columns: {
		type: Array,
	},
	options: {
		type: Object,
		default: () => ({
			selectable: true,
			totalCount: 0,
			rowCount: 0,
		}),
	},
})

const batchName = computed(
	() => props.batch || route.params.batchName || ''
)

const assessments = createResource({
	url: 'lms.lms.utils.get_assessments',
	makeParams() {
		return { batch: batchName.value }
	},
	auto: () => !!batchName.value,
})

watch(
	() => batchName.value,
	(name) => {
		if (name) {
			assessments.reload()
		}
	}
)

const liveFromCourse = computed(() => {
	const fromApi = (assessments.data || []).filter((row) => row && row.from_course)
	if (fromApi.length) {
		return fromApi
	}
	return (props.preloadLive || []).map((row) => ({
		...row,
		from_course: true,
	}))
})

const onBatch = computed(() =>
	(assessments.data || []).filter((row) => row && !row.from_course)
)

const deleteAssessments = createResource({
	url: 'lms.lms.api.delete_documents',
	makeParams(values) {
		return {
			doctype: 'LMS Assessment',
			documents: values.assessments,
		}
	},
})

const removeAssessments = (selections, unselectAll) => {
	deleteAssessments.submit(
		{ assessments: Array.from(selections) },
		{
			onSuccess(data) {
				assessments.reload()
				unselectAll()
			},
		}
	)
}

const getRowRoute = (row) => {
	if (row.assessment_type == 'LMS Assignment') {
		if (row.submission) {
			return {
				name: 'AssignmentSubmission',
				params: {
					assignmentID: row.assessment_name,
					submissionName: row.submission.name,
				},
			}
		} else {
			return {
				name: 'AssignmentSubmission',
				params: {
					assignmentID: row.assessment_name,
					submissionName: 'new',
				},
			}
		}
	} else if (row.assessment_type == 'LMS Programming Exercise') {
		if (row.submission) {
			return {
				name: 'ProgrammingExerciseSubmission',
				params: {
					exerciseID: row.assessment_name,
					submissionID: row.submission.name,
				},
			}
		} else {
			return {
				name: 'ProgrammingExerciseSubmission',
				params: {
					exerciseID: row.assessment_name,
					submissionID: 'new',
				},
			}
		}
	} else {
		return {
			name: 'QuizPage',
			params: {
				quizID: row.assessment_name,
			},
		}
	}
}

const canAddAssessments = () => {
	if (readOnlyMode) return false
	return user.data?.is_moderator || user.data?.is_evaluator
}

const getAssessmentColumns = () => {
	let columns = [
		{
			label: __('Assessment'),
			key: 'title',
		},
		{
			label: __('Type'),
			key: 'assessment_type',
			width: '10rem',
		},
	]

	if (!user.data?.is_moderator) {
		columns.push({
			label: __('Status/Percentage'),
			key: 'status',
			align: 'left',
			width: '10rem',
		})
	}
	return columns
}

const getStatusTheme = (status) => {
	if (status === 'Pass' || status === 'Passed') {
		return 'green'
	} else if (status === 'Not Graded') {
		return 'orange'
	} else {
		return 'red'
	}
}

const getAssessmentTypeLabel = (type) => {
	if (type == 'LMS Assignment') {
		return __('Assignment')
	} else if (type == 'LMS Quiz') {
		return __('Quiz')
	} else if (type == 'LMS Programming Exercise') {
		return __('Programming Exercise')
	}
}
</script>
