<template>
	<div class="il-page min-h-full pb-16">
		<div class="mx-auto max-w-3xl">
			<header class="hi-hero mt-4">
				<div class="relative z-[1]">
					<p class="text-sm font-medium text-white/75">{{ __('Before Day 1') }}</p>
					<h1 class="mt-1 text-2xl font-semibold text-white sm:text-[1.75rem]">{{ __('Hello ILians 👋') }}</h1>
					<p class="mt-1.5 max-w-lg text-sm leading-6 text-white/80">
						{{ __('Tell us a little about yourself. It takes about 2 minutes, and Day 1 of your training opens as soon as you submit.') }}
					</p>
				</div>
			</header>

			<div v-if="form.loading && !form.data" class="mt-6 h-96 animate-pulse rounded-3xl bg-[#e6e7e8]" />
			<div v-else-if="form.error" class="il-card mt-6 p-8 text-center text-sm text-[color:var(--il-error-50)]">
				{{ form.error.messages?.[0] || __('Could not load the form.') }}
			</div>

			<form v-else-if="form.data" class="mt-6 space-y-6" novalidate @submit.prevent="submit">
				<div v-if="form.data.submitted" class="hi-done">
					<CheckCircle2 class="h-5 w-5 shrink-0" />
					<span>{{ __('You have already submitted this. You can update your answers below.') }}</span>
				</div>

				<!-- About you -->
				<section class="il-card p-5 sm:p-6">
					<h2 class="hi-h2">{{ __('About you') }}</h2>
					<div class="hi-grid">
						<Field :label="__('First name')" required :error="errors.first_name">
							<input v-model.trim="v.first_name" class="hi-input" autocomplete="given-name" />
						</Field>
						<Field :label="__('Last name')">
							<input v-model.trim="v.last_name" class="hi-input" autocomplete="family-name" />
						</Field>
						<Field :label="__('Email')">
							<input :value="form.data.email" class="hi-input" disabled />
						</Field>
						<Field :label="__('Employee code')">
							<input v-model.trim="v.employee_code" class="hi-input" :placeholder="__('If you have one')" />
						</Field>
						<Field :label="__('Contact number')" required :error="errors.phone">
							<input v-model.trim="v.phone" class="hi-input" inputmode="tel" autocomplete="tel" placeholder="98XXXXXXXX" />
						</Field>
						<Field :label="__('Alternate contact number')" required :error="errors.alternate_phone">
							<input v-model.trim="v.alternate_phone" class="hi-input" inputmode="tel" placeholder="98XXXXXXXX" />
						</Field>
					</div>
				</section>

				<!-- Joining -->
				<section class="il-card p-5 sm:p-6">
					<h2 class="hi-h2">{{ __('Your joining') }}</h2>
					<div class="hi-grid">
						<Field :label="__('Joining date')" required :error="errors.joining_date">
							<input v-model="v.joining_date" type="date" class="hi-input" />
						</Field>
						<Field :label="__('Training Manager')" required :error="errors.team_lead">
							<select v-model="v.team_lead" class="hi-input">
								<option value="" disabled>{{ __('Pick your Training Manager') }}</option>
								<option v-for="t in options.team_leads" :key="t.value" :value="t.value">{{ t.label }}</option>
							</select>
						</Field>
						<Field :label="__('AC name')" required :error="errors.ac_name">
							<input v-model.trim="v.ac_name" class="hi-input" />
						</Field>
						<Field :label="__('AC official email')" required :error="errors.ac_email">
							<input v-model.trim="v.ac_email" type="email" class="hi-input" placeholder="name@infinitylearn.com" />
						</Field>
					</div>
				</section>

				<!-- Where you're from -->
				<section class="il-card p-5 sm:p-6">
					<h2 class="hi-h2">{{ __('Where you’re from') }}</h2>
					<div class="hi-grid">
						<Field :label="__('Home state')" required :error="errors.home_state">
							<select v-model="v.home_state" class="hi-input">
								<option value="" disabled>{{ __('Pick a state') }}</option>
								<option v-for="s in options.states" :key="s" :value="s">{{ s }}</option>
							</select>
						</Field>
						<Field :label="__('City')">
							<input v-model.trim="v.city" class="hi-input" />
						</Field>
						<Field :label="__('Primary language')" required :error="errors.primary_language">
							<select v-model="v.primary_language" class="hi-input">
								<option value="" disabled>{{ __('Pick a language') }}</option>
								<option v-for="l in options.languages" :key="l" :value="l">{{ l }}</option>
								<option value="Other">{{ __('Other') }}</option>
							</select>
						</Field>
						<Field :label="__('Distance from office')" required :error="errors.distance_from_office">
							<Chips v-model="v.distance_from_office" :items="options.distance" />
						</Field>
						<Field class="sm:col-span-2" :label="__('Other languages you speak fluently')" required :error="errors.other_languages">
							<div class="flex flex-wrap gap-2">
								<button
									v-for="l in options.languages.filter((x) => x !== v.primary_language)"
									:key="l"
									type="button"
									class="hi-chip"
									:class="{ 'is-on': otherLanguages.includes(l) }"
									@click="toggleLanguage(l)"
								>
									{{ l }}
								</button>
								<button type="button" class="hi-chip" :class="{ 'is-on': otherLanguages.includes('None') }" @click="setNoOther">
									{{ __('None') }}
								</button>
							</div>
						</Field>
					</div>
				</section>

				<!-- Experience -->
				<section class="il-card p-5 sm:p-6">
					<h2 class="hi-h2">{{ __('Experience') }}</h2>
					<div class="hi-grid">
						<Field class="sm:col-span-2" :label="__('Experience (in months)')" required :error="errors.experience">
							<Chips v-model="v.experience" :items="options.experience" />
						</Field>
						<Field class="sm:col-span-2" :label="__('Name of previous company')" required :error="errors.previous_company">
							<input v-model.trim="v.previous_company" class="hi-input" :placeholder="v.experience === 'Fresher' ? __('Write “Fresher” if this is your first job') : ''" />
						</Field>
						<Field :label="__('EdTech experience')" required :error="errors.edtech_experience">
							<Chips v-model="v.edtech_experience" :items="['Yes', 'No']" />
						</Field>
						<Field v-if="v.edtech_experience === 'Yes'" :label="__('Last EdTech company')" required :error="errors.last_edtech_company">
							<input v-model.trim="v.last_edtech_company" class="hi-input" />
						</Field>
					</div>
				</section>

				<div class="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
					<p class="text-xs text-[color:var(--il-muted)]">{{ __('Fields marked * are required.') }}</p>
					<button type="submit" class="il-btn il-btn-primary !h-12 !px-8" :disabled="saving">
						{{ saving ? __('Submitting…') : form.data.submitted ? __('Update answers') : __('Submit and start Day 1') }}
					</button>
				</div>
			</form>
		</div>
	</div>
</template>

<script setup>
import { computed, h, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { call, createResource, toast } from 'frappe-ui'
import { CheckCircle2 } from 'lucide-vue-next'

const router = useRouter()
const saving = ref(false)
const errors = reactive({})
const v = reactive({
	first_name: '',
	last_name: '',
	employee_code: '',
	joining_date: '',
	ac_name: '',
	ac_email: '',
	team_lead: '',
	phone: '',
	alternate_phone: '',
	distance_from_office: '',
	home_state: '',
	city: '',
	primary_language: '',
	other_languages: '',
	experience: '',
	previous_company: '',
	edtech_experience: '',
	last_edtech_company: '',
})

const form = createResource({
	url: 'lms.lms.hello_ilians.get_form',
	auto: true,
	onSuccess(data) {
		for (const k of Object.keys(v)) if (data.values?.[k] != null) v[k] = data.values[k]
		if (v.last_edtech_company === 'No EdTech Experience') v.last_edtech_company = ''
	},
})
const options = computed(() => form.data?.options || { team_leads: [], experience: [], distance: [], languages: [], states: [] })

const otherLanguages = computed(() =>
	String(v.other_languages || '')
		.split(',')
		.map((x) => x.trim())
		.filter(Boolean)
)
function toggleLanguage(l) {
	const list = otherLanguages.value.filter((x) => x !== 'None')
	const i = list.indexOf(l)
	if (i >= 0) list.splice(i, 1)
	else list.push(l)
	v.other_languages = list.join(', ')
}
function setNoOther() {
	v.other_languages = otherLanguages.value.includes('None') ? '' : 'None'
}

const REQUIRED = {
	first_name: __('Enter your first name'),
	phone: __('Enter your contact number'),
	alternate_phone: __('Enter an alternate number'),
	joining_date: __('Pick your joining date'),
	team_lead: __('Pick your Training Manager'),
	ac_name: __('Enter your AC’s name'),
	ac_email: __('Enter your AC’s email'),
	home_state: __('Pick your home state'),
	primary_language: __('Pick your primary language'),
	distance_from_office: __('Pick a distance'),
	other_languages: __('Pick at least one, or None'),
	experience: __('Pick your experience'),
	previous_company: __('Enter your previous company'),
	edtech_experience: __('Pick Yes or No'),
}

function validate() {
	for (const k of Object.keys(errors)) delete errors[k]
	for (const [k, msg] of Object.entries(REQUIRED)) if (!String(v[k] || '').trim()) errors[k] = msg
	const phone = /^[+\d][\d\s-]{7,}$/
	if (v.phone && !phone.test(v.phone)) errors.phone = __('Enter a valid number')
	if (v.alternate_phone && !phone.test(v.alternate_phone)) errors.alternate_phone = __('Enter a valid number')
	if (v.ac_email && !/.+@.+\..+/.test(v.ac_email)) errors.ac_email = __('Enter a valid email')
	if (v.edtech_experience === 'Yes' && !v.last_edtech_company) errors.last_edtech_company = __('Enter the company name')
	return !Object.keys(errors).length
}

async function submit() {
	if (!validate()) {
		toast.error(__('Please fill the highlighted fields.'))
		requestAnimationFrame(() => document.querySelector('.hi-error')?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
		return
	}
	saving.value = true
	try {
		await call('lms.lms.hello_ilians.submit_form', { values: { ...v } })
		toast.success(__('Thanks! Day 1 is open.'))
		router.push('/dashboard')
	} catch (e) {
		toast.error(e?.messages?.[0] || __('Could not submit. Please try again.'))
	} finally {
		saving.value = false
	}
}

// Label + control + error message.
const Field = (props, { slots }) =>
	h('div', { class: ['hi-field', props.class] }, [
		h('span', { class: 'hi-label' }, [props.label, props.required ? h('span', { class: 'text-[#D12B2B]' }, ' *') : null]),
		slots.default?.(),
		props.error ? h('span', { class: 'hi-error' }, props.error) : null,
	])
Field.props = ['label', 'required', 'error', 'class']

// Single-choice pill buttons.
const Chips = (props, { emit }) =>
	h(
		'div',
		{ class: 'flex flex-wrap gap-2', role: 'radiogroup' },
		props.items.map((item) =>
			h(
				'button',
				{
					type: 'button',
					role: 'radio',
					'aria-checked': props.modelValue === item,
					class: ['hi-chip', { 'is-on': props.modelValue === item }],
					onClick: () => emit('update:modelValue', item),
				},
				item
			)
		)
	)
Chips.props = ['modelValue', 'items']
Chips.emits = ['update:modelValue']
</script>

<style scoped>
.hi-hero {
	position: relative;
	overflow: hidden;
	border-radius: 24px;
	padding: 1.75rem;
	background: var(--il-promo);
}

.hi-hero::after {
	content: '';
	position: absolute;
	right: -4rem;
	top: -4rem;
	width: 16rem;
	height: 16rem;
	border-radius: 999px;
	background: radial-gradient(circle, rgba(2, 123, 255, 0.55) 0%, rgba(2, 123, 255, 0) 70%);
}

.hi-h2 {
	margin-bottom: 1rem;
	color: var(--il-ink);
	font-size: 1.0625rem;
	font-weight: 600;
}

.hi-grid {
	display: grid;
	gap: 1rem 1.25rem;
}

@media (min-width: 640px) {
	.hi-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}

:deep(.hi-field) {
	display: flex;
	flex-direction: column;
	gap: 0.4rem;
}

:deep(.hi-label) {
	color: var(--il-ink);
	font-size: 0.8125rem;
	font-weight: 500;
}

:deep(.hi-error) {
	color: #d12b2b;
	font-size: 0.75rem;
}

.hi-input {
	height: 2.75rem;
	width: 100%;
	border: 1px solid var(--il-neutral-90);
	border-radius: 12px;
	padding: 0 0.85rem;
	background-color: #fff;
	color: var(--il-ink);
	font-size: 0.9375rem;
	box-shadow: none;
}

.hi-input:focus {
	border-color: var(--il-primary-50);
	box-shadow: 0 0 0 3px rgba(2, 123, 255, 0.12);
	outline: none;
}

.hi-input:disabled {
	background: var(--il-neutral-95);
	color: var(--il-muted);
}

:deep(.hi-chip) {
	min-height: 2.4rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 999px;
	padding: 0 1rem;
	background: #fff;
	color: var(--il-ink);
	font-size: 0.875rem;
	transition: all 0.12s ease;
}

:deep(.hi-chip:hover) {
	border-color: var(--il-primary-50);
}

:deep(.hi-chip.is-on) {
	border-color: var(--il-primary-50);
	background: var(--il-primary-50);
	color: #fff;
}

.hi-done {
	display: flex;
	align-items: center;
	gap: 0.6rem;
	border-radius: 16px;
	padding: 0.8rem 1rem;
	background: var(--il-success-95);
	color: var(--il-success-50);
	font-size: 0.875rem;
}
</style>
