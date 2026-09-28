<template>
	<Dialog v-model="showTour" :options="{ size: 'lg' }">
		<template #body>
			<div class="p-6">
				<div class="flex items-start justify-between">
					<h2 class="text-lg font-semibold text-ink-gray-9">{{ currentStep.title }}</h2>
					<button
						class="text-ink-gray-5 hover:text-ink-gray-8"
						@click="finishTour"
					>
						{{ __('Skip') }}
					</button>
				</div>
				<p class="mt-3 text-p-base text-ink-gray-7">{{ currentStep.body }}</p>

				<div class="mt-6 flex items-center justify-between">
					<div class="flex gap-1.5">
						<span
							v-for="(step, index) in steps"
							:key="index"
							class="h-1.5 w-1.5 rounded-full"
							:class="index === stepIndex ? 'bg-ink-gray-9' : 'bg-ink-gray-4'"
						/>
					</div>
					<div class="flex gap-2">
						<Button v-if="stepIndex > 0" variant="subtle" @click="stepIndex--">
							{{ __('Back') }}
						</Button>
						<Button v-if="!isLastStep" variant="solid" @click="stepIndex++">
							{{ __('Next') }}
						</Button>
						<Button v-else variant="solid" @click="finishTour">
							{{ __('Got it') }}
						</Button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Button, Dialog, call, createResource } from 'frappe-ui'
import { usersStore } from '@/stores/user'

const { userResource } = usersStore()

const SALES_TRAINING_ROLES = [
	'Sales Training Team',
	'Sales Trainee Manager',
	'Sales Training Finance',
	'Sales Training Leadership',
]

const isSalesTrainingStaff = computed(() => {
	const roles = userResource.data?.roles || []
	return SALES_TRAINING_ROLES.some((r) => roles.includes(r))
})

const steps = computed(() => {
	const base = [
		{
			title: __('Welcome to the Sales LMS'),
			body: __(
				"Here's a quick look at what you can do here — this takes about 30 seconds."
			),
		},
		{
			title: __('Courses & curriculum'),
			body: __(
				'Browse courses under Curriculum, work through lessons and quizzes, and pick up where you left off from Home.'
			),
		},
	]
	if (isSalesTrainingStaff.value) {
		base.push({
			title: __('Sales training tools'),
			body: __(
				'Under Sales Trainees, manage trainees and cohorts, mark weekly attendance, and track payroll cycles.'
			),
		})
	}
	base.push({
		title: __('Certificates & your profile'),
		body: __(
			'Earn certificates as you complete courses, and keep your profile up to date from the sidebar.'
		),
	})
	return base
})

const stepIndex = ref(0)
const currentStep = computed(() => steps.value[stepIndex.value])
const isLastStep = computed(() => stepIndex.value === steps.value.length - 1)

const showTour = ref(false)

const tourState = createResource({
	url: 'lms.lms.app_welcome_tour.get_app_welcome_tour_state',
	onSuccess(data) {
		if (!data?.skipped) {
			showTour.value = true
		}
	},
})

onMounted(() => {
	if (userResource.data) {
		tourState.fetch()
	}
})

watch(
	() => userResource.data,
	(data) => {
		if (data && !tourState.data) {
			tourState.fetch()
		}
	}
)

// The dialog can also close via an outside click or Escape, not just our
// buttons — record the skip whenever it closes, however that happened, so
// it never silently reappears on the next page load.
watch(showTour, (isOpen, wasOpen) => {
	if (wasOpen && !isOpen) {
		call('lms.lms.app_welcome_tour.skip_app_welcome_tour')
	}
})

function finishTour() {
	showTour.value = false
}
</script>
