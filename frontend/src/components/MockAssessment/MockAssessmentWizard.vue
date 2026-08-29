<template>
	<Dialog
		v-model="show"
		:options="{
			title: wizardTitle,
			size: '4xl',
		}"
	>
		<template #body-content>
			<div v-if="options.loading" class="py-8 text-center text-sm text-ink-gray-6">
				{{ __('Loading...') }}
			</div>
			<div v-else class="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
				<div class="flex items-center gap-2 text-xs text-ink-gray-6">
					<span
						v-for="(label, idx) in stepLabels"
						:key="idx"
						class="px-2 py-1 rounded"
						:class="
							idx === step
								? 'bg-blue-100 text-blue-800 font-medium'
								: idx < step
									? 'text-ink-gray-7'
									: 'text-ink-gray-5'
						"
					>
						{{ idx + 1 }}. {{ label }}
					</span>
				</div>

				<!-- Step 0: Title -->
				<div v-show="step === 0" class="space-y-3">
					<FormControl
						v-model="form.title"
						type="text"
						:label="__('Mock title')"
						:placeholder="__('e.g. Grade 1 Mock, Python VIVA — May 2026')"
						:required="true"
					/>
					<p class="text-xs text-ink-gray-6">
						{{
							__(
								'Enter a unique title for this learner. Nothing is saved until you click Save draft or Submit and publish on the last step.'
							)
						}}
					</p>
				</div>

				<!-- Step 1: General -->
				<div v-show="step === 1" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					<FormControl
						v-model="form.instructor_name"
						type="text"
						:label="__('Instructor name')"
					/>
					<FormControl
						v-model="form.mock_date"
						type="date"
						:label="__('Date of mock')"
					/>
					<FormControl
						v-model="form.batch_brand"
						type="text"
						:label="__('Batch / school brand')"
					/>
					<FormControl
						v-model="form.grade_observed"
						type="select"
						:options="gradeOptions"
						:label="__('Grade observed')"
					/>
					<FormControl
						v-model="form.evaluator_name"
						type="text"
						:label="__('Evaluator name')"
					/>
					<FormControl
						v-model="form.duration_minutes"
						type="select"
						:options="durationOptions"
						:label="__('Duration of mock')"
					/>
					<FormControl
						v-model="form.topic_observed"
						type="text"
						:label="__('Topic observed')"
					/>
					<FormControl
						v-model="form.assessment_type"
						type="select"
						:options="typeOptions"
						:label="__('Type of assessment')"
					/>
					<FormControl
						:modelValue="percentDisplay(form.attendance_percent)"
						type="text"
						inputmode="decimal"
						:label="__('Attendance percentage')"
						:placeholder="__('0–100')"
						@update:modelValue="(v) => setPercentField('attendance_percent', v)"
					/>
					<FormControl
						:modelValue="percentDisplay(form.assessment_score_percent)"
						type="text"
						inputmode="decimal"
						:label="__('Assessment score (%)')"
						:placeholder="__('0–100')"
						@update:modelValue="(v) => setPercentField('assessment_score_percent', v)"
					/>
				</div>

				<!-- Step 2: All evaluation sections -->
				<div v-show="step === 2" class="space-y-5">
					<div
						v-for="(section, sIdx) in form.evaluation_sections"
						:key="section.key"
						class="rounded-lg border p-4 space-y-3"
					>
						<div>
							<h4 class="text-sm font-semibold text-ink-gray-9">
								{{ section.label }}
							</h4>
							<p class="text-xs text-ink-gray-6 mt-0.5">
								{{ sectionDescriptions[section.key] }}
							</p>
						</div>
						<div>
							<label class="text-xs text-ink-gray-6 mb-1 block">
								{{ __('Rating (1–5)') }}
							</label>
							<div class="flex gap-2">
								<button
									v-for="n in 5"
									:key="n"
									type="button"
									class="w-8 h-8 rounded border text-sm font-medium"
									:class="
										section.rating === n
											? 'bg-blue-600 text-white border-blue-600'
											: 'bg-surface-white text-ink-gray-7'
									"
									@click="section.rating = n"
								>
									{{ n }}
								</button>
							</div>
						</div>
						<div class="space-y-2">
							<label
								v-for="(criterion, cIdx) in section.criteria"
								:key="criterion.key"
								class="flex items-center gap-2 text-sm cursor-pointer"
							>
								<input
									type="checkbox"
									v-model="form.evaluation_sections[sIdx].criteria[cIdx].met"
									class="rounded"
								/>
								<span>{{ criterion.label }}</span>
							</label>
						</div>
						<FormControl
							v-model="form.evaluation_sections[sIdx].comment"
							type="textarea"
							:rows="2"
							:label="__('Comment')"
						/>
					</div>
				</div>

				<!-- Step 3: Overall -->
				<div v-show="step === 3" class="space-y-4">
					<div>
						<label class="text-xs text-ink-gray-6 mb-1 block">
							{{ __('Overall rating (1–5)') }}
						</label>
						<div class="flex gap-2">
							<button
								v-for="n in 5"
								:key="n"
								type="button"
								class="w-8 h-8 rounded border text-sm font-medium"
								:class="
									form.overall_rating === n
										? 'bg-blue-600 text-white border-blue-600'
										: 'bg-surface-white text-ink-gray-7'
								"
								@click="form.overall_rating = n"
							>
								{{ n }}
							</button>
						</div>
					</div>
					<FormControl
						v-model="form.strengths"
						type="textarea"
						:rows="3"
						:label="__('Strengths identified')"
					/>
					<FormControl
						v-model="form.areas_of_improvement"
						type="textarea"
						:rows="3"
						:label="__('Areas of improvement')"
					/>
					<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
						<label class="flex items-center gap-2 text-sm">
							<input type="checkbox" v-model="form.needs_mentorship" class="rounded" />
							{{ __('Needs 1:1 mentorship') }}
						</label>
						<label class="flex items-center gap-2 text-sm">
							<input type="checkbox" v-model="form.remock_needed" class="rounded" />
							{{ __('Re-mock needed') }}
						</label>
						<label class="flex items-center gap-2 text-sm">
							<input type="checkbox" v-model="form.needs_retraining" class="rounded" />
							{{ __('Needs retraining') }}
						</label>
					</div>
					<div>
						<label class="text-sm font-medium text-ink-gray-8 mb-1.5 block">
							{{ __('Attachment (optional)') }}
						</label>
						<FileUploader
							:fileTypes="['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx']"
							@success="onAttachmentUploaded"
						>
							<template v-slot="{ openFileSelector, uploading }">
								<Button
									variant="outline"
									:loading="uploading"
									@click="openFileSelector"
								>
									{{ form.attachment ? __('Replace file') : __('Upload file') }}
								</Button>
							</template>
						</FileUploader>
						<div v-if="form.attachment" class="flex items-center gap-3 mt-2">
							<a
								:href="getFileHref(form.attachment)"
								target="_blank"
								class="text-xs text-ink-blue-3 hover:underline"
							>
								{{ __('View attachment') }}
							</a>
							<button
								type="button"
								class="text-xs text-ink-red-3 hover:underline"
								@click="removeAttachment"
							>
								{{ __('Remove') }}
							</button>
						</div>
					</div>
				</div>

				<!-- Step 4: Confirm -->
				<div v-show="step === 4" class="rounded-lg border bg-surface-gray-1 p-4 text-sm space-y-2">
					<p>
						<strong>{{ __('Title') }}:</strong> {{ form.title }}
					</p>
					<p v-if="form.mock_date">
						<strong>{{ __('Date') }}:</strong> {{ form.mock_date }}
					</p>
					<p v-if="form.overall_rating">
						<strong>{{ __('Overall rating') }}:</strong> {{ form.overall_rating }}/5
					</p>
					<p class="text-ink-gray-6">
						{{
							__(
								'Save as draft to continue later, or submit and publish to make this visible to the learner immediately.'
							)
						}}
					</p>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex flex-wrap justify-between w-full gap-2">
				<Button v-if="step > 0" variant="outline" @click="step -= 1">
					{{ __('Back') }}
				</Button>
				<div v-else />
				<div class="flex flex-wrap gap-2 ml-auto">
					<Button variant="outline" @click="show = false">{{ __('Cancel') }}</Button>
					<Button v-if="step < 4" variant="solid" :loading="saving" @click="nextStep">
						{{ __('Next') }}
					</Button>
					<template v-else>
						<Button variant="outline" :loading="saving" @click="submit(false)">
							{{ __('Save draft') }}
						</Button>
						<Button variant="solid" :loading="saving" @click="submit(true)">
							{{ __('Submit and publish') }}
						</Button>
					</template>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import {
	Button,
	Dialog,
	FileUploader,
	FormControl,
	call,
	createResource,
	toast,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { getFileHref } from '@/utils/fileUrl'

const show = defineModel({ type: Boolean, default: false })
const props = defineProps({
	batch: { type: String, required: true },
	member: { type: String, required: true },
	editName: { type: String, default: null },
})

const emit = defineEmits(['saved', 'published'])

const step = ref(0)
const saving = ref(false)
const docName = ref(null)

const stepLabels = [
	__('Title'),
	__('Details'),
	__('Evaluation'),
	__('Overall'),
	__('Submit'),
]

const sectionDescriptions = {
	technical_efficacy: __(
		'Tool usage, debugging ability, syntax accuracy, and handling technical queries.'
	),
	curriculum_knowledge: __(
		'Session objectives, curriculum alignment, theoretical accuracy, and topic connection.'
	),
	session_delivery: __(
		'Use of examples, analogies, application-based questions, and engagement.'
	),
	communication_skill: __(
		'Language clarity, pace, two-way communication, and patience with learners.'
	),
	time_management: __(
		'Coverage within time, balance of theory/practical, avoiding diversions, and session structure.'
	),
}

const emptyForm = () => ({
	title: '',
	instructor_name: '',
	mock_date: '',
	batch_brand: '',
	grade_observed: '',
	evaluator_name: '',
	duration_minutes: '',
	topic_observed: '',
	assessment_type: 'Mock',
	attendance_percent: null,
	assessment_score_percent: null,
	evaluation_sections: [],
	overall_rating: null,
	strengths: '',
	areas_of_improvement: '',
	needs_mentorship: false,
	remock_needed: false,
	needs_retraining: false,
	attachment: '',
})

const form = ref(emptyForm())

const options = createResource({
	url: 'lms.lms.mock_assessment_api.get_mock_assessment_form_options',
	auto: false,
})

const gradeOptions = computed(() =>
	(options.data?.grade_options || []).map((g) => ({ label: g, value: g }))
)
const durationOptions = computed(() =>
	(options.data?.duration_options || []).map((d) => ({
		label: `${d} ${__('min')}`,
		value: d,
	}))
)
const typeOptions = computed(() =>
	(options.data?.assessment_type_options || []).map((t) => ({ label: t, value: t }))
)

const wizardTitle = computed(() =>
	props.editName ? __('Edit mock assessment') : __('Add mock assessment')
)

watch(show, async (open) => {
	if (!open) return
	step.value = 0
	docName.value = props.editName
	await options.reload()
	if (!form.value.evaluation_sections?.length) {
		form.value.evaluation_sections = JSON.parse(
			JSON.stringify(options.data?.default_sections || [])
		)
	}
	if (props.editName) {
		await loadExisting(props.editName)
	} else {
		form.value = emptyForm()
		form.value.evaluation_sections = JSON.parse(
			JSON.stringify(options.data?.default_sections || [])
		)
	}
})

async function loadExisting(name) {
	const d = await call('lms.lms.mock_assessment_api.get_mock_assessment', {
		name,
		batch: props.batch,
		member: props.member,
	})
	if (!d) return
	docName.value = d.name
	form.value = {
		title: d.title || '',
		instructor_name: d.instructor_name || '',
		mock_date: d.mock_date || '',
		batch_brand: d.batch_brand || '',
		grade_observed: d.grade_observed || '',
		evaluator_name: d.evaluator_name || '',
		duration_minutes: d.duration_minutes || '',
		topic_observed: d.topic_observed || '',
		assessment_type: d.assessment_type || 'Mock',
		attendance_percent: d.attendance_percent,
		assessment_score_percent: d.assessment_score_percent,
		evaluation_sections: d.evaluation_sections || [],
		overall_rating: d.overall_rating,
		strengths: d.strengths || '',
		areas_of_improvement: d.areas_of_improvement || '',
		needs_mentorship: !!d.needs_mentorship,
		remock_needed: !!d.remock_needed,
		needs_retraining: !!d.needs_retraining,
		attachment: d.attachment || '',
	}
}

function onAttachmentUploaded(file) {
	form.value.attachment = file.file_url
}

function removeAttachment() {
	form.value.attachment = ''
}

function percentDisplay(value) {
	if (value === null || value === undefined || value === '') return ''
	return String(value)
}

function setPercentField(field, value) {
	if (value === '' || value === null || value === undefined) {
		form.value[field] = null
		return
	}
	const raw = String(value).trim()
	if (!/^(\d+(\.\d{0,2})?|\d+\.)$/.test(raw)) return

	const num = Number(raw.endsWith('.') ? raw.slice(0, -1) : raw)
	if (Number.isNaN(num) || num < 0 || num > 100) return

	form.value[field] = num
}

function validatePercentFields() {
	const fields = [
		{ key: 'attendance_percent', label: __('Attendance percentage') },
		{ key: 'assessment_score_percent', label: __('Assessment score (%)') },
	]
	for (const { key, label } of fields) {
		const value = form.value[key]
		if (value === null || value === '' || value === undefined) continue
		const num = Number(value)
		if (Number.isNaN(num) || num < 0 || num > 100) {
			toast.error(__('{0} must be between 0 and 100.').format(label))
			return false
		}
	}
	return true
}

async function persistDraft() {
	const result = await call('lms.lms.mock_assessment_api.save_mock_assessment', {
		batch: props.batch,
		member: props.member,
		name: docName.value,
		data: form.value,
	})
	docName.value = result?.name || docName.value
	return docName.value
}

async function nextStep() {
	if (step.value === 0 && !form.value.title?.trim()) {
		toast.error(__('Please enter a mock title.'))
		return
	}
	if (step.value === 1 && !validatePercentFields()) {
		return
	}
	step.value += 1
}

async function submit(publish) {
	if (!form.value.title?.trim()) {
		toast.error(__('Please enter a mock title.'))
		return
	}
	if (!validatePercentFields()) {
		return
	}
	saving.value = true
	try {
		const name = await persistDraft()
		if (publish && name) {
			await call('lms.lms.mock_assessment_api.publish_mock_assessment', {
				name,
				batch: props.batch,
				member: props.member,
			})
			toast.success(__('Mock published. Learner can see it now.'))
			emit('published')
		} else {
			toast.success(__('Draft saved.'))
			emit('saved')
		}
		show.value = false
	} catch (err) {
		toast.error(err?.messages?.[0] || __('Could not save mock assessment.'))
	} finally {
		saving.value = false
	}
}
</script>
