<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Add an assessment'),
			size: 'md',
			actions: [
				{
					label: __('Submit'),
					variant: 'solid',
					onClick: (close) => addAssessment(close),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="assessmentTitle"
					type="text"
					:label="__('Title')"
					:placeholder="__('Name shown to students on this course')"
					:required="true"
				/>
				<FormControl
					type="select"
					:options="assessmentTypes"
					v-model="assessmentType"
					:label="__('Type')"
					placeholder=" "
					@update:modelValue="onTypeChange"
				/>
				<Link
					v-if="assessmentType"
					v-model="assessment"
					:doctype="assessmentType"
					:label="__('Assessment')"
					:placeholder="__('Select or create')"
					@change="onAssessmentSelected"
					:onCreate="
						(value, close) => {
							close()
							openCreatePage()
						}
					"
				/>
				<div v-if="course && courseBatches.data?.length" class="space-y-2">
					<label class="block text-xs text-ink-gray-5">
						{{ __('Make live for batches') }}
					</label>
					<div class="space-y-2 max-h-40 overflow-y-auto border rounded-md p-2">
						<label
							v-for="batch in courseBatches.data"
							:key="batch.name"
							class="flex items-center gap-2 text-sm cursor-pointer"
						>
							<input
								type="checkbox"
								:value="batch.name"
								v-model="selectedBatches"
								class="rounded border-outline-gray-3"
							/>
							<span>{{ batch.title }}</span>
						</label>
					</div>
					<p class="text-xs text-ink-gray-6">
						{{
							__(
								'Unchecked batches stay hidden. You can change this later from the course outline.'
							)
						}}
					</p>
				</div>
				<div
					v-else-if="course && courseBatches.fetched && !courseBatches.data?.length"
					class="text-xs text-ink-gray-6"
				>
					{{
						__(
							'No batches include this course yet. Add the course to a batch first, then you can go live per batch.'
						)
					}}
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Link from '@/components/Controls/Link.vue'
import { getServerErrorMessage } from '@/utils'

const show = defineModel()
const assessmentType = ref(null)
const assessment = ref(null)
const assessmentTitle = ref('')
const selectedBatches = ref([])
const assessments = defineModel('assessments')
const router = useRouter()

const props = defineProps({
	batch: {
		type: String,
		default: null,
	},
	course: {
		type: String,
		default: null,
	},
	initialAssessmentType: {
		type: String,
		default: null,
	},
})

const emit = defineEmits(['added'])

const courseBatches = createResource({
	url: 'lms.lms.utils.get_course_assessment_batches',
	makeParams() {
		return { course: props.course }
	},
	auto: false,
})

watch(show, (open) => {
	if (open) {
		assessmentType.value = props.initialAssessmentType || null
		assessment.value = null
		assessmentTitle.value = ''
		selectedBatches.value = []
		if (props.course) {
			courseBatches.reload()
		}
	}
})

const assessmentResource = createResource({
	url: 'frappe.client.insert',
	makeParams() {
		const parent = props.course || props.batch
		const parenttype = props.course ? 'LMS Course' : 'LMS Batch'

		return {
			doc: {
				doctype: 'LMS Assessment',
				parent,
				parenttype,
				parentfield: 'assessment',
				assessment_type: assessmentType.value,
				assessment_name: assessment.value,
				display_title: assessmentTitle.value?.trim() || null,
			},
		}
	},
})

const onTypeChange = () => {
	assessment.value = null
}

const onAssessmentSelected = async () => {
	if (!assessment.value || assessmentTitle.value?.trim()) return

	try {
		const title = await call('frappe.client.get_value', {
			doctype: assessmentType.value,
			filters: { name: assessment.value },
			fieldname: 'title',
		})
		if (title?.message?.title) {
			assessmentTitle.value = title.message.title
		}
	} catch {
		// keep manual title
	}
}

const openCreatePage = () => {
	show.value = false
	if (assessmentType.value === 'LMS Quiz') {
		router.push({ name: 'Quizzes', query: { new: 'true' } })
	} else if (assessmentType.value === 'LMS Assignment') {
		router.push({ name: 'Assignments', query: { new: 'true' } })
	} else if (assessmentType.value === 'LMS Programming Exercise') {
		router.push({ name: 'ProgrammingExercises', query: { new: 'true' } })
	}
}

const isDuplicateAssessment = () => {
	const rows = assessments.value?.data || []
	return rows.some(
		(row) =>
			row.assessment_type === assessmentType.value &&
			row.assessment_name === assessment.value
	)
}

const addAssessment = async (close) => {
	if (!props.course && !props.batch) {
		toast.error(__('Save the course or batch before adding assessments.'))
		return
	}
	if (!assessmentType.value || !assessment.value) {
		toast.error(__('Please select an assessment type and assessment.'))
		return
	}
	if (!assessmentTitle.value?.trim()) {
		toast.error(__('Please enter a title for this assessment.'))
		return
	}
	if (isDuplicateAssessment()) {
		const label = assessmentTitle.value?.trim() || assessment.value
		toast.error(
			__(
				'"{0}" is already added to this {1}. Check the list below or pick a different assessment.'
			).format(label, props.course ? __('course') : __('batch'))
		)
		return
	}

	assessmentResource.submit(
		{},
		{
			async onSuccess(data) {
				const courseAssessmentName = data?.name
				if (
					props.course &&
					selectedBatches.value.length &&
					courseAssessmentName
				) {
					for (const batch of selectedBatches.value) {
						try {
							await call('lms.lms.api.set_course_assessment_visibility', {
								course_assessment: courseAssessmentName,
								batch,
								is_visible: 1,
							})
						} catch (error) {
							toast.error(
								getServerErrorMessage(
									error,
									__(
										'Assessment was added but could not be made live for this batch. You can toggle visibility in the list below.'
									)
								)
							)
						}
					}
				}
				try {
					await assessments.value?.reload?.()
				} catch {
				}
				emit('added')
				toast.success(__('Assessment added successfully'))
				close()
			},
			onError(error) {
				const message = getServerErrorMessage(
					error,
					__('Could not add this assessment. Please try again.')
				)
				if (message.toLowerCase().includes('already been added')) {
					toast.error(
						__(
							'This assessment is already on the course. It is listed in the Assessments section below.'
						)
					)
					return
				}
				toast.error(message)
			},
		}
	)
}

const assessmentTypes = computed(() => {
	return [
		{ label: 'Quiz', value: 'LMS Quiz' },
		{ label: 'Assignment', value: 'LMS Assignment' },
		{ label: 'Programming Exercise', value: 'LMS Programming Exercise' },
	]
})
</script>
