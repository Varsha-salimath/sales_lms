<template>
	<Dialog
		v-model="show"
		:options="{
			title: isEdit ? __('Edit Learner Certification Report') : __('Add Learner Certification Report'),
			size: 'xl',
		}"
	>
		<template #body-content>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
				<FormControl
					v-if="isEdit && !selectedLearner && form.employee_name"
					:modelValue="form.employee_name"
					:label="__('Learner Name')"
					disabled
				/>
				<div class="sm:col-span-2">
					<Autocomplete
						v-model="selectedLearner"
						:options="learnerOptions"
						:label="isEdit && form.employee_name && !selectedLearner ? __('Link LMS learner') : __('Learner')"
						:placeholder="__('Search learner...')"
						:filterable="false"
						:readonly="isEdit && Boolean(record?.learner)"
						@update:query="onLearnerQuery"
					/>
				</div>
				<FormControl
					:modelValue="form.email"
					:label="__('Email ID')"
					:placeholder="__('Auto-populated')"
					disabled
				/>
				<FormControl
					v-model="form.location"
					type="select"
					:label="__('Location')"
					:options="locationSelectOptions"
				/>
				<FormControl
					v-if="form.location === NEW_LOCATION"
					v-model="form.newLocation"
					:label="__('New location')"
					:placeholder="__('Enter location')"
				/>
				<FormControl
					v-model="form.batch_start"
					type="date"
					:label="__('Batch Start')"
				/>
				<FormControl
					v-model="form.attendance_days"
					type="number"
					:label="__('Attendance')"
					min="0"
					step="1"
				/>
				<FormControl
					v-model="form.ai_mock_score"
					type="number"
					:label="__('AI Mock')"
					min="0"
					step="0.01"
				/>
				<FormControl
					v-model="form.audit_score"
					type="number"
					:label="__('Audit / 20')"
					min="0"
					max="20"
					step="0.01"
				/>
				<FormControl
					v-model="form.product_avg"
					type="number"
					:label="__('Product avg / 20')"
					min="0"
					max="20"
					step="0.01"
				/>
				<FormControl
					v-model="form.stage"
					type="select"
					:label="__('Stage')"
					:options="stageOptions"
				/>
			</div>
		</template>
		<template #actions="{ close }">
			<div class="flex justify-end gap-2">
				<Button variant="subtle" @click="close">
					{{ __('Cancel') }}
				</Button>
				<Button variant="solid" :loading="saving" @click="save(close)">
					{{ __('Save') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import { Button, Dialog, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const NEW_LOCATION = '__new__'

const show = defineModel({ type: Boolean, default: false })
const props = defineProps({
	record: { type: Object, default: null },
})
const emit = defineEmits(['saved'])

const saving = ref(false)
const learnerQuery = ref('')
const selectedLearner = ref(null)
let queryDebounce = null

const emptyForm = () => ({
	name: null,
	employee_name: '',
	email: '',
	location: '',
	newLocation: '',
	batch_start: '',
	attendance_days: '',
	ai_mock_score: '',
	audit_score: '',
	product_avg: '',
	stage: 'Not Started',
})

const form = ref(emptyForm())

const isEdit = computed(() => Boolean(props.record?.name))

const reportOptions = createResource({
	url: 'lms.lms.ojt_certification.get_ojt_report_options',
})

const learnerSearch = createResource({
	url: 'lms.lms.ojt_certification.search_ojt_learners',
	makeParams() {
		return { search: learnerQuery.value || undefined }
	},
})

const learnerOptions = computed(() => {
	const rows = learnerSearch.data || []
	const current = selectedLearner.value
	if (current?.value && !rows.some((row) => row.value === current.value)) {
		return [current, ...rows]
	}
	return rows
})

const locationSelectOptions = computed(() => {
	const items = reportOptions.data?.locations || []
	return [
		{ label: __('Select location'), value: '' },
		...items.map((item) => ({ label: item, value: item })),
		{ label: __('Add new location...'), value: NEW_LOCATION },
	]
})

const stageOptions = computed(() => {
	const items = reportOptions.data?.stages || [
		'Not Started',
		'Started',
		'Mock Completed',
		'Audit Completed',
		'Product Tests Completed',
	]
	return items.map((item) => ({ label: item, value: item }))
})

watch(show, (open) => {
	if (!open) return
	resetFromRecord()
	reportOptions.reload()
	learnerQuery.value = props.record?.employee_name || ''
	learnerSearch.reload()
})

watch(selectedLearner, (option) => {
	if (!option) {
		if (!isEdit.value) {
			form.value.email = ''
		}
		return
	}
	const selected =
		typeof option === 'string'
			? learnerOptions.value.find((row) => row.value === option)
			: option
	if (!selected) return
	form.value.email = selected.email || selected.description || ''
	if (!form.value.location && selected.city) {
		form.value.location = selected.city
	}
})

function resetFromRecord() {
	const row = props.record
	form.value = emptyForm()
	if (!row) {
		selectedLearner.value = null
		learnerQuery.value = ''
		return
	}
	form.value = {
		name: row.name,
		employee_name: row.employee_name || '',
		email: row.email || '',
		location: row.location || '',
		newLocation: '',
		batch_start: row.batch_start || '',
		attendance_days: valueOrEmpty(row.attendance_days),
		ai_mock_score: valueOrEmpty(row.ai_mock_score),
		audit_score: valueOrEmpty(row.audit_score),
		product_avg: valueOrEmpty(row.product_avg),
		stage: row.stage || 'Not Started',
	}
	selectedLearner.value = row.learner
		? {
				value: row.learner,
				label: row.employee_name || row.learner,
				description: row.email,
				email: row.email,
				city: row.location,
			}
		: null
}

function valueOrEmpty(value) {
	return value === null || value === undefined ? '' : value
}

function onLearnerQuery(query) {
	learnerQuery.value = query || ''
	if (queryDebounce) clearTimeout(queryDebounce)
	queryDebounce = setTimeout(() => learnerSearch.reload(), 250)
}

function selectedLearnerName() {
	const option = selectedLearner.value
	if (!option) return null
	return typeof option === 'string' ? option : option.value
}

function parseRequiredNumber(value, label, { min = 0, max = null, integer = false } = {}) {
	if (value === null || value === undefined || value === '') return null
	const number = Number(value)
	if (Number.isNaN(number)) {
		throw new Error(__('{0} must be a number').format(label))
	}
	if (integer && !Number.isInteger(number)) {
		throw new Error(__('{0} must be a whole number').format(label))
	}
	if (number < min) {
		throw new Error(__('{0} must be {1} or greater').format(label, min))
	}
	if (max !== null && number > max) {
		throw new Error(__('{0} must be {1} or less').format(label, max))
	}
	return number
}

async function save(close) {
	const learner = selectedLearnerName()
	if (!learner && !isEdit.value) {
		toast.error(__('Select a registered learner'))
		return
	}
	let attendance
	let aiMock
	let audit
	let productAvg
	try {
		attendance = parseRequiredNumber(form.value.attendance_days, __('Attendance'), {
			min: 0,
			integer: true,
		})
		aiMock = parseRequiredNumber(form.value.ai_mock_score, __('AI Mock'), { min: 0 })
		audit = parseRequiredNumber(form.value.audit_score, __('Audit / 20'), { min: 0, max: 20 })
		productAvg = parseRequiredNumber(form.value.product_avg, __('Product avg / 20'), {
			min: 0,
			max: 20,
		})
	} catch (error) {
		toast.error(error.message)
		return
	}

	const location =
		form.value.location === NEW_LOCATION
			? (form.value.newLocation || '').trim()
			: (form.value.location || '').trim()

	saving.value = true
	try {
		await call('lms.lms.ojt_certification.save_ojt_certification_report', {
			name: form.value.name || undefined,
			learner: learner || undefined,
			location: location || undefined,
			batch_start: form.value.batch_start || undefined,
			attendance_days: attendance,
			ai_mock_score: aiMock,
			audit_score: audit,
			product_avg: productAvg,
			stage: form.value.stage || undefined,
		})
		toast.success(isEdit.value ? __('Learner report updated') : __('Learner report added'))
		emit('saved')
		close()
	} catch (error) {
		toast.error(error?.messages?.[0] || error?.message || __('Unable to save learner report'))
	} finally {
		saving.value = false
	}
}
</script>
