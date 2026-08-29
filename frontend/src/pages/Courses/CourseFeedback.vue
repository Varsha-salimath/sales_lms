<template>
	<div class="min-h-screen px-4 py-6 sm:px-8" style="background: var(--genius-bg, #f8fafc)">
		<div class="mx-auto max-w-3xl">
			<div class="mb-6">
				<p class="text-xs font-semibold uppercase tracking-wide text-[color:var(--genius-primary)]">
					{{ __('Course Feedback') }}
				</p>
				<h1 class="mt-1 text-2xl font-semibold" style="color: var(--genius-navy) !important">
					{{ __('AI for Educators Webinar Feedback') }}
				</h1>
				<p class="mt-2 text-sm text-[color:var(--genius-muted)]">
					{{
						__(
							'Optional course feedback. It is not required to unlock your certificate.'
						)
					}}
				</p>
			</div>

			<div
				v-if="status.loading"
				class="rounded-2xl border bg-white p-8 text-center text-sm text-[color:var(--genius-muted)]"
			>
				{{ __('Loading…') }}
			</div>

			<div
				v-else-if="!status.data?.course_completed"
				class="rounded-2xl border bg-white p-8 text-center"
			>
				<p class="text-[color:var(--genius-ink)]">
					{{ __('Complete the course to 100% before submitting feedback.') }}
				</p>
				<router-link
					:to="{ name: 'GeniusScormPlayer', params: { courseName } }"
					class="mt-4 inline-flex rounded-xl px-4 py-2 text-sm font-semibold text-white"
					style="background: var(--genius-primary)"
				>
					{{ __('Continue Learning') }}
				</router-link>
			</div>

			<div
				v-else-if="submitted || status.data?.feedback_completed"
				class="overflow-hidden rounded-2xl border bg-white shadow-sm"
			>
				<div
					class="px-6 py-8 text-center text-white"
					style="background: linear-gradient(135deg, #1d4ed8, #0f172a)"
				>
					<div class="mx-auto mb-3 flex size-14 items-center justify-center rounded-full bg-white/15 text-2xl">
						✓
					</div>
					<h2 class="text-xl font-semibold text-white">
						{{ __('Thank you for your feedback.') }}
					</h2>
					<p class="mt-2 text-sm text-white/85">
						{{ __('Your certificate is now available.') }}
					</p>
				</div>
				<div class="flex flex-wrap items-center justify-center gap-3 px-6 py-6">
					<button
						type="button"
						class="rounded-xl px-5 py-2.5 text-sm font-semibold text-white"
						style="background: var(--genius-primary)"
						:disabled="!certificateName && issuing"
						@click="openCertificate"
					>
						{{ issuing ? __('Preparing…') : __('Download Certificate') }}
					</button>
					<router-link
						:to="{ name: 'CertifiedParticipants' }"
						class="rounded-xl border px-5 py-2.5 text-sm font-semibold text-[color:var(--genius-ink)]"
					>
						{{ __('My Certificates') }}
					</router-link>
				</div>
			</div>

			<form
				v-else
				class="space-y-5 rounded-2xl border bg-white p-5 shadow-sm sm:p-7"
				@submit.prevent="submitFeedback"
			>
				<div class="grid gap-4 sm:grid-cols-2">
					<label class="block text-sm">
						<span class="mb-1 block font-medium text-[color:var(--genius-ink)]">{{ __('Email') }}</span>
						<input
							v-model="form.learner_email"
							type="email"
							required
							readonly
							class="w-full rounded-xl border px-3 py-2.5 bg-surface-gray-1"
						/>
					</label>
					<label class="block text-sm">
						<span class="mb-1 block font-medium text-[color:var(--genius-ink)]">{{ __('Name') }}</span>
						<input
							v-model="form.learner_name"
							type="text"
							required
							readonly
							class="w-full rounded-xl border px-3 py-2.5 bg-surface-gray-1"
						/>
					</label>
				</div>

				<label class="block text-sm">
					<span class="mb-1 block font-medium text-[color:var(--genius-ink)]">{{ __('School Name') }}</span>
					<input
						v-model="form.school_name"
						type="text"
						required
						class="w-full rounded-xl border px-3 py-2.5"
						:placeholder="__('Enter your school name')"
					/>
				</label>

				<FieldGroup
					:label="__('Overall experience')"
					v-model="form.overall_rating"
					:options="ratingOptions"
					required
				/>
				<FieldGroup
					:label="__('Relevance to teaching needs')"
					v-model="form.relevance"
					:options="relevanceOptions"
					required
				/>
				<FieldGroup
					:label="__('Understanding of AI concepts')"
					v-model="form.understanding"
					:options="understandingOptions"
					required
				/>
				<FieldGroup
					:label="__('Most valuable topic')"
					v-model="form.valuable_topic"
					:options="topicOptions"
					required
				/>
				<FieldGroup
					:label="__('Confidence using AI tools')"
					v-model="form.confidence"
					:options="confidenceOptions"
					required
				/>
				<FieldGroup
					:label="__('Webinar easy to follow?')"
					v-model="form.followability"
					:options="followOptions"
					required
				/>
				<FieldGroup
					:label="__('Trainer delivery rating')"
					v-model="form.trainer_rating"
					:options="ratingOptions"
					required
				/>

				<label class="block text-sm">
					<span class="mb-1 block font-medium text-[color:var(--genius-ink)]">{{ __('Biggest takeaway') }}</span>
					<textarea
						v-model="form.takeaway"
						required
						rows="3"
						class="w-full rounded-xl border px-3 py-2.5"
					/>
				</label>

				<FieldGroup
					:label="__('Attend more AI sessions?')"
					v-model="form.future_training"
					:options="futureOptions"
					required
				/>
				<FieldGroup
					:label="__('Recommend to others?')"
					v-model="form.recommendation"
					:options="recommendOptions"
					required
				/>

				<label class="block text-sm">
					<span class="mb-1 block font-medium text-[color:var(--genius-ink)]">{{ __('Suggestions') }}</span>
					<textarea
						v-model="form.suggestions"
						rows="3"
						class="w-full rounded-xl border px-3 py-2.5"
					/>
				</label>

				<div class="flex flex-wrap items-center justify-between gap-3 pt-2">
					<p class="text-xs text-[color:var(--genius-muted)]">
						{{ __('Certificate unlocks after successful submission.') }}
					</p>
					<button
						type="submit"
						class="rounded-xl px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
						style="background: var(--genius-primary)"
						:disabled="submitting"
					>
						{{ submitting ? __('Submitting…') : __('Submit Feedback') }}
					</button>
				</div>
				<p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
			</form>
		</div>
	</div>
</template>

<script setup>
import { createResource, call, toast } from 'frappe-ui'
import { computed, defineComponent, h, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { openCertificatePreview } from '@/utils/certificate'

const FieldGroup = defineComponent({
	name: 'FieldGroup',
	props: {
		label: String,
		modelValue: [String, Number],
		options: { type: Array, default: () => [] },
		required: Boolean,
	},
	emits: ['update:modelValue'],
	setup(props, { emit }) {
		return () =>
			h('fieldset', { class: 'block text-sm' }, [
				h(
					'legend',
					{ class: 'mb-2 font-medium text-[color:var(--genius-ink)]' },
					props.label
				),
				h(
					'div',
					{ class: 'flex flex-wrap gap-2' },
					props.options.map((opt) =>
						h(
							'button',
							{
								type: 'button',
								class: [
									'rounded-full border px-3 py-1.5 text-sm transition',
									String(props.modelValue) === String(opt)
										? 'border-transparent text-white'
										: 'border-[color:var(--genius-border)] text-[color:var(--genius-ink)]',
								],
								style:
									String(props.modelValue) === String(opt)
										? { background: 'var(--genius-primary)' }
										: {},
								onClick: () => emit('update:modelValue', opt),
							},
							String(opt)
						)
					)
				),
			])
	},
})

const route = useRoute()
const router = useRouter()
const courseName = computed(() => route.params.courseName)
const submitted = ref(false)
const submitting = ref(false)
const issuing = ref(false)
const errorMsg = ref('')
const certificateName = ref(null)

const form = reactive({
	learner_email: '',
	learner_name: '',
	school_name: '',
	overall_rating: '',
	relevance: '',
	understanding: '',
	valuable_topic: '',
	confidence: '',
	followability: '',
	trainer_rating: '',
	takeaway: '',
	future_training: '',
	recommendation: '',
	suggestions: '',
})

const ratingOptions = ['1', '2', '3', '4', '5']
const relevanceOptions = ['Very relevant', 'Relevant', 'Somewhat relevant', 'Not relevant']
const understandingOptions = ['Very well', 'Well', 'Somewhat', 'Not clearly']
const topicOptions = [
	'Introduction to AI',
	'Generative AI',
	'Prompt writing',
	'AI tools',
	'Ethical use of AI',
]
const confidenceOptions = ['Very confident', 'Confident', 'Somewhat confident', 'Not confident']
const followOptions = ['Yes completely', 'Mostly', 'Somewhat', 'No']
const futureOptions = ['Yes', 'Maybe', 'No']
const recommendOptions = ['Definitely', 'Probably', 'Maybe', 'No']

const status = createResource({
	url: 'lms.lms.doctype.lms_course_feedback.lms_course_feedback.get_feedback_status',
	auto: false,
	onSuccess(data) {
		form.learner_email = data.learner_email
		form.learner_name = data.learner_name
		certificateName.value = data.certificate?.name || null
	},
})

watch(
	courseName,
	(name) => {
		if (name) status.submit({ course: name })
	},
	{ immediate: true }
)

const submitFeedback = async () => {
	errorMsg.value = ''
	submitting.value = true
	try {
		const res = await call(
			'lms.lms.doctype.lms_course_feedback.lms_course_feedback.submit_course_feedback',
			{
				course: courseName.value,
				feedback: { ...form },
			}
		)
		certificateName.value = res?.certificate?.name || null
		submitted.value = true
		await status.reload()
		toast.success(__('Feedback submitted successfully'))
	} catch (e) {
		errorMsg.value =
			e?.messages?.[0] || e?.message || __('Unable to submit feedback. Please try again.')
	} finally {
		submitting.value = false
	}
}

const openCertificate = async () => {
	if (certificateName.value) {
		openCertificatePreview(certificateName.value)
		return
	}
	issuing.value = true
	try {
		const cert = await call(
			'lms.lms.doctype.lms_certificate.lms_certificate.create_certificate',
			{ course: courseName.value }
		)
		certificateName.value = cert?.name
		if (cert?.name) openCertificatePreview(cert.name)
	} catch (e) {
		toast.error(
			e?.messages?.[0] || e?.message || __('Certificate is not ready yet.')
		)
	} finally {
		issuing.value = false
	}
}
</script>
