<template>
	<div style="display: none" />
</template>

<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import { call, createResource } from 'frappe-ui'
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import { usersStore } from '@/stores/user'

const { userResource } = usersStore()

let driverObj = null
let tourStarted = false

const STEP_DEFS = [
	{
		tourId: 'home',
		popover: {
			title: __('Welcome to the Sales LMS'),
			description: __(
				"This is Home — pick up where you left off and jump back into your courses. This quick tour takes about 30 seconds."
			),
		},
	},
	{
		tourId: 'curriculum',
		popover: {
			title: __('Curriculum'),
			description: __(
				'Browse courses here, and work through lessons and quizzes at your own pace.'
			),
		},
	},
	{
		tourId: 'certificates',
		popover: {
			title: __('Certificates & your profile'),
			description: __(
				'Earn certificates as you complete courses, and keep your profile up to date from the sidebar.'
			),
		},
	},
]

function waitForElement(selector, timeoutMs = 1500) {
	return new Promise((resolve) => {
		const start = Date.now()
		function check() {
			const el = document.querySelector(selector)
			if (el || Date.now() - start > timeoutMs) {
				resolve(el)
			} else {
				requestAnimationFrame(check)
			}
		}
		check()
	})
}

// Some layouts (mobile's bottom nav, a role-gated item) never render these
// sidebar anchors at all — fall back to a centered popover for that step
// instead of silently dropping it, so the tour still shows on every layout.
async function buildSteps() {
	const steps = []
	for (const def of STEP_DEFS) {
		const el = await waitForElement(`[data-tour-target="${def.tourId}"]`)
		steps.push(
			el
				? { element: el, popover: { ...def.popover, side: 'right', align: 'start' } }
				: { popover: def.popover }
		)
	}
	return steps
}

async function startTour() {
	if (tourStarted) return
	tourStarted = true

	driverObj = driver({
		showProgress: true,
		nextBtnText: __('Next'),
		prevBtnText: __('Back'),
		doneBtnText: __('Got it'),
		progressText: __('{{current}} of {{total}}'),
		steps: await buildSteps(),
		// Fires on completion, Escape, overlay click, or the close button —
		// any way the tour ends, not just "Done" — so it never silently
		// reappears on the next page load (see the old Dialog version's bug).
		onDestroyed: () => {
			call('lms.lms.app_welcome_tour.skip_app_welcome_tour')
		},
	})

	driverObj.drive()
}

const tourState = createResource({
	url: 'lms.lms.app_welcome_tour.get_app_welcome_tour_state',
	onSuccess(data) {
		if (!data?.skipped) {
			startTour()
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

onUnmounted(() => {
	driverObj?.destroy()
})
</script>
