<!-- frontend/src/pages/Sales/TraineeCohortList.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Trainee Cohorts</h1>
		<table class="w-full text-left border-collapse">
			<thead>
				<tr class="border-b">
					<th class="py-2">Cohort</th>
					<th>Location</th>
					<th>Start Date</th>
					<th>Trainer</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="c in cohorts.data" :key="c.name" class="border-b">
					<td class="py-2">
						<router-link :to="{ name: 'TraineeList', query: { cohort: c.name } }">
							{{ c.cohort_name }}
						</router-link>
					</td>
					<td>{{ c.location }}</td>
					<td>{{ c.start_date }}</td>
					<td>{{ c.trainer }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { createListResource } from 'frappe-ui'

const cohorts = createListResource({
	doctype: 'Sales Trainee Cohort',
	fields: ['name', 'cohort_name', 'location', 'start_date', 'trainer'],
	auto: true,
	pageLength: 100,
})
</script>
