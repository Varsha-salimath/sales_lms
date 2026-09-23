<!-- frontend/src/pages/Sales/TraineeList.vue -->
<template>
	<div class="p-6 max-w-5xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Trainees{{ cohortFilter ? ` — ${cohortFilter}` : '' }}</h1>
		<table class="w-full text-left border-collapse">
			<thead>
				<tr class="border-b">
					<th class="py-2">Name</th>
					<th>Email</th>
					<th>Status</th>
					<th>DOJ</th>
					<th>Code</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="t in trainees.data" :key="t.name" class="border-b">
					<td class="py-2">{{ t.trainee_name }}</td>
					<td>{{ t.personal_email }}</td>
					<td>{{ t.training_status }}</td>
					<td>{{ t.date_of_joining }}</td>
					<td>{{ t.employee_dummy_vendor_code || '—' }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createListResource } from 'frappe-ui'

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
