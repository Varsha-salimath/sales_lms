<!-- frontend/src/pages/Sales/TraineeCohortList.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="mb-4 text-xl font-semibold text-[color:var(--genius-navy)]">Trainee Cohorts</h1>
		<div class="genius-card rounded-2xl p-4 sm:p-5">
			<div class="overflow-x-auto">
				<table class="min-w-full text-left text-sm">
					<thead>
						<tr
							class="border-b text-[11px] uppercase tracking-wide text-[color:var(--genius-muted)]"
							style="border-color: var(--genius-border)"
						>
							<th class="pb-2 pr-3 font-medium">Cohort</th>
							<th class="pb-2 pr-3 font-medium">Location</th>
							<th class="pb-2 pr-3 font-medium">Start Date</th>
							<th class="pb-2 font-medium">Trainer</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="c in cohorts.data"
							:key="c.name"
							class="border-b last:border-0"
							style="border-color: var(--genius-border)"
						>
							<td class="py-2.5 pr-3">
								<router-link
									:to="{ name: 'TraineeList', query: { cohort: c.name } }"
									class="font-medium text-[color:var(--genius-blue)] hover:underline"
								>
									{{ c.cohort_name }}
								</router-link>
							</td>
							<td class="py-2.5 pr-3 text-xs text-[color:var(--genius-muted)]">{{ c.location }}</td>
							<td class="py-2.5 pr-3 text-xs text-[color:var(--genius-muted)]">{{ c.start_date }}</td>
							<td class="py-2.5 text-xs text-[color:var(--genius-muted)]">{{ c.trainer }}</td>
						</tr>
					</tbody>
				</table>
				<div v-if="!cohorts.loading && !cohorts.data?.length" class="py-8 text-center text-sm text-[color:var(--genius-muted)]">
					No cohorts yet.
				</div>
			</div>
		</div>
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
