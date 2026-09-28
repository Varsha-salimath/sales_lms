<template>
	<div class="mx-auto max-w-3xl px-4 pb-8 pt-4 sm:px-6 lg:px-8">
		<h1 class="mb-4 text-2xl font-semibold text-[color:var(--genius-navy)]">Ops Checklist</h1>

		<div v-if="tourState.data && !tourState.data.skipped" class="genius-card mt-4 p-4">
			<p class="text-p-base">
				{{ tourCopy }}
			</p>
			<Button variant="subtle" class="mt-3" @click="skipTour">Skip</Button>
		</div>

		<div v-if="checklist.loading" class="mt-6 text-p-base text-gray-500">Loading…</div>

		<div v-else-if="checklist.error" class="genius-card mt-6 p-4 text-p-base text-red-600">
			Couldn't load your checklist. Try reloading the page.
		</div>

		<div v-else class="mt-6 flex flex-col gap-3">
			<div v-if="items.length === 0" class="genius-card p-4 text-p-base text-gray-600">
				Nothing pending — you're all caught up.
			</div>
			<!-- A section that failed server-side (spec §4) comes back as a plain item with
			     action_route: null — render it as a static error card, not a broken router-link. -->
			<template v-for="item in pendingItems" :key="item.key">
				<router-link
					:to="item.action_route"
					class="genius-card flex items-center justify-between p-4"
				>
					<span class="text-p-base">{{ item.title }}</span>
				</router-link>
			</template>
			<div
				v-for="item in erroredItems"
				:key="item.key"
				class="genius-card p-4 text-p-base text-red-600"
			>
				{{ item.title }}
			</div>

			<div v-if="summary" class="genius-card mt-2 p-4">
				<h2 class="text-lg font-medium">Trainee status summary</h2>
				<dl class="mt-2 grid grid-cols-2 gap-2 text-p-sm">
					<template v-for="(value, key) in displaySummary" :key="key">
						<dt class="text-gray-500">{{ key }}</dt>
						<dd class="font-medium">{{ value }}</dd>
					</template>
				</dl>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource, call, Button } from 'frappe-ui'
import { usersStore } from '@/stores/user'

const { userResource } = usersStore()

const tourState = createResource({
	url: 'lms.lms.ops_checklist.get_ops_checklist_tour_state',
	auto: true,
})

const checklist = createResource({
	url: 'lms.lms.ops_checklist.get_ops_checklist',
	auto: true,
})

const items = computed(() => checklist.data?.items || [])
const pendingItems = computed(() => items.value.filter((item) => item.action_route))
const erroredItems = computed(() => items.value.filter((item) => !item.action_route))
const summary = computed(() => checklist.data?.summary || null)
const displaySummary = computed(() => {
	if (!summary.value) return {}
	const { total, ...rest } = summary.value
	return { total, ...rest }
})

const tourCopy = computed(() => {
	const roles = userResource.data?.roles || []
	if (roles.includes('Sales Training Finance')) {
		return "This is your Ops Checklist — it lists payroll cycles that still need to be closed before month-end, so you never miss the vendor's invoicing window."
	}
	if (roles.includes('Sales Trainee Manager')) {
		return 'This is your Ops Checklist — it lists your own trainees with unmarked attendance for today, so you never fall behind on OJT tracking.'
	}
	if (roles.includes('Sales Training Leadership')) {
		return 'This is your Ops Checklist — a read-only summary of trainee status across the program.'
	}
	return 'This is your Ops Checklist — it lists cohorts with unmarked attendance, un-cleared trainees, and the next payroll-export deadline, so nothing in the SOP slips.'
})

function skipTour() {
	call('lms.lms.ops_checklist.skip_ops_checklist_tour').then(() => {
		tourState.reload()
	})
}
</script>
