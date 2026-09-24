<!-- frontend/src/pages/Sales/TraineeList.vue -->
<template>
	<div class="p-6 max-w-5xl mx-auto">
		<h1 class="mb-4 text-xl font-semibold text-[color:var(--genius-navy)]">
			Trainees{{ cohortFilter ? ` — ${cohortFilter}` : '' }}
		</h1>
		<div class="genius-card rounded-2xl p-4 sm:p-5">
			<div class="overflow-x-auto">
				<table class="min-w-full text-left text-sm">
					<thead>
						<tr
							class="border-b text-[11px] uppercase tracking-wide text-[color:var(--genius-muted)]"
							style="border-color: var(--genius-border)"
						>
							<th class="pb-2 pr-3 font-medium">Name</th>
							<th class="pb-2 pr-3 font-medium">Email</th>
							<th class="pb-2 pr-3 font-medium">Status</th>
							<th class="pb-2 pr-3 font-medium">DOJ</th>
							<th class="pb-2 font-medium">Code</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="t in trainees.data"
							:key="t.name"
							class="border-b last:border-0"
							style="border-color: var(--genius-border)"
						>
							<td class="py-2.5 pr-3 font-medium text-[color:var(--genius-navy)]">
								{{ t.trainee_name }}
							</td>
							<td class="py-2.5 pr-3 text-xs text-[color:var(--genius-muted)]">
								{{ t.personal_email }}
							</td>
							<td class="py-2.5 pr-3">
								<span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="statusBadge(t.training_status)">
									{{ t.training_status }}
								</span>
							</td>
							<td class="py-2.5 pr-3 text-xs text-[color:var(--genius-muted)]">{{ t.date_of_joining }}</td>
							<td class="py-2.5 text-xs text-[color:var(--genius-muted)]">
								{{ t.employee_dummy_vendor_code || '—' }}
							</td>
						</tr>
					</tbody>
				</table>
				<div v-if="!trainees.loading && !trainees.data?.length" class="py-8 text-center text-sm text-[color:var(--genius-muted)]">
					No trainees yet.
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createListResource } from 'frappe-ui'

const STATUS_BADGES = {
	'In Training': 'bg-blue-50 text-blue-700',
	'Training Cleared': 'bg-green-50 text-green-700',
	'Training Not Cleared': 'bg-amber-50 text-amber-700',
	Resigned: 'bg-gray-100 text-gray-600',
	Absconded: 'bg-red-50 text-red-700',
	'Exited-Churned': 'bg-gray-100 text-gray-600',
}
function statusBadge(status) {
	return STATUS_BADGES[status] || 'bg-gray-100 text-gray-600'
}

const route = useRoute()
const cohortFilter = computed(() => route.query.cohort || '')

const trainees = createListResource({
	doctype: 'Sales Trainee',
	fields: ['name', 'trainee_name', 'personal_email', 'training_status', 'date_of_joining', 'employee_dummy_vendor_code'],
	filters: cohortFilter.value ? { cohort: cohortFilter.value } : {},
	auto: true,
	pageLength: 100,
})

// The list resource above is only evaluated once at setup. Because App.vue's
// <router-view /> has no :key on the route, navigating between query-only
// variants of this same route (e.g. /sales-trainees?cohort=A -> /sales-trainees)
// does not remount this component, so the filters must be kept in sync here.
watch(
	() => route.query.cohort,
	(cohort) => {
		trainees.update({
			filters: cohort ? { cohort } : {},
		})
		trainees.reload()
	}
)
</script>
