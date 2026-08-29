<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Grant Access'),
			size: 'lg',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick: saveAssignments,
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<div class="text-sm text-ink-gray-6">
					{{ recording?.title }}
				</div>
				<p class="text-xs text-ink-gray-5">
					{{
						__(
							'Only learners you select below can watch this recording in their Library.'
						)
					}}
				</p>
				<p v-if="recording?.batch_title" class="text-xs text-ink-gray-5">
					{{
						__(
							'Learners enrolled in {0}. Use the search box to filter this list.'
						).format(recording.batch_title)
					}}
				</p>

				<FormControl
					v-model="search"
					type="text"
					:label="__('Search learners')"
					:placeholder="__('Search by name or email')"
				/>

				<div
					v-if="loadingStudents"
					class="text-sm text-ink-gray-5 py-2"
				>
					{{ __('Loading learners...') }}
				</div>

				<div
					v-else-if="!batchStudents.length"
					class="rounded-lg border border-dashed px-4 py-3 text-sm text-ink-gray-5"
				>
					{{ __('No learners are enrolled in this batch yet.') }}
				</div>

				<div
					v-else
					class="rounded-lg border bg-surface-gray-1 max-h-56 overflow-y-auto"
				>
					<label
						class="flex items-center gap-2.5 px-3 py-2.5 border-b bg-surface-white sticky top-0 cursor-pointer"
					>
						<input
							type="checkbox"
							class="rounded"
							:checked="allFilteredSelected"
							:indeterminate.prop="someFilteredSelected"
							@change="toggleSelectAll"
						/>
						<span class="text-sm font-medium text-ink-gray-8">
							{{ __('Select all') }}
							<span
								v-if="search.trim()"
								class="font-normal text-ink-gray-5"
							>
								({{ __('filtered') }})
							</span>
						</span>
						<span class="ms-auto text-xs text-ink-gray-5">
							{{
								__('{0} selected').format(selectedStudents.length)
							}}
						</span>
					</label>

					<label
						v-for="student in filteredStudents"
						:key="student.value"
						class="flex items-start gap-2.5 px-3 py-2.5 border-b last:border-b-0 cursor-pointer hover:bg-surface-white"
					>
						<input
							type="checkbox"
							class="rounded mt-0.5"
							:checked="selectedStudents.includes(student.value)"
							@change="toggleStudent(student.value)"
						/>
						<div class="min-w-0">
							<div class="text-sm font-medium text-ink-gray-8 truncate">
								{{ student.label }}
							</div>
							<div class="text-xs text-ink-gray-5 truncate">
								{{ student.value }}
							</div>
						</div>
					</label>

					<div
						v-if="search.trim() && !filteredStudents.length"
						class="px-3 py-4 text-sm text-ink-gray-5 text-center"
					>
						{{ __('No learners match your search.') }}
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, FormControl, call, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const show = defineModel()
const props = defineProps({
	recording: {
		type: Object,
		default: null,
	},
})

const emit = defineEmits(['saved'])
const selectedStudents = ref([])
const batchStudents = ref([])
const loadingStudents = ref(false)
const search = ref('')

const filteredStudents = computed(() => {
	const query = search.value.trim().toLowerCase()
	if (!query) return batchStudents.value
	return batchStudents.value.filter((student) => {
		const haystack = `${student.label} ${student.value}`.toLowerCase()
		return haystack.includes(query)
	})
})

const allFilteredSelected = computed(() => {
	if (!filteredStudents.value.length) return false
	return filteredStudents.value.every((student) =>
		selectedStudents.value.includes(student.value)
	)
})

const someFilteredSelected = computed(() => {
	if (!filteredStudents.value.length) return false
	const selectedCount = filteredStudents.value.filter((student) =>
		selectedStudents.value.includes(student.value)
	).length
	return selectedCount > 0 && selectedCount < filteredStudents.value.length
})

const loadBatchStudents = async () => {
	if (!props.recording?.batch) {
		batchStudents.value = []
		return
	}
	loadingStudents.value = true
	try {
		const rows = await call('lms.lms.library_api.search_batch_students', {
			batch: props.recording.batch,
			txt: '',
			page_length: 100,
		})
		batchStudents.value = rows || []
	} catch (error) {
		batchStudents.value = []
	} finally {
		loadingStudents.value = false
	}
}

const loadAssignments = async () => {
	if (!props.recording?.name) return
	try {
		const rows = await call(
			'lms.lms.library_api.get_recording_assignment_details',
			{ recording: props.recording.name }
		)
		selectedStudents.value = (rows || []).map((row) => row.member)
	} catch (error) {
		selectedStudents.value = []
	}
}

const loadModalData = async () => {
	search.value = ''
	await Promise.all([loadBatchStudents(), loadAssignments()])
}

watch(
	() => [show.value, props.recording?.name],
	([isOpen]) => {
		if (isOpen) loadModalData()
	}
)

const toggleStudent = (member) => {
	if (selectedStudents.value.includes(member)) {
		selectedStudents.value = selectedStudents.value.filter((v) => v !== member)
		return
	}
	selectedStudents.value = [...selectedStudents.value, member]
}

const toggleSelectAll = (event) => {
	const checked = event.target.checked
	const filteredValues = filteredStudents.value.map((student) => student.value)

	if (checked) {
		selectedStudents.value = [
			...new Set([...selectedStudents.value, ...filteredValues]),
		]
		return
	}

	selectedStudents.value = selectedStudents.value.filter(
		(member) => !filteredValues.includes(member)
	)
}

const saveAssignments = async (close) => {
	if (!props.recording?.name) return
	try {
		await call('lms.lms.library_api.assign_recording_students', {
			recording: props.recording.name,
			members: selectedStudents.value,
		})
		toast.success(__('Access updated successfully.'))
		emit('saved')
		close()
	} catch (error) {
		toast.error(error?.messages?.[0] || __('Failed to update access.'))
	}
}
</script>
