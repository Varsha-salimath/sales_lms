<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-2">Mark Attendance</h1>
		<input v-model="date" type="date" class="mb-4 border rounded px-2 py-1" />
		<table class="w-full text-left border-collapse">
			<thead>
				<tr class="border-b">
					<th class="py-2">Trainee</th>
					<th>Present</th>
					<th>Absent</th>
					<th>Leave</th>
					<th>Holiday</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="t in trainees.data" :key="t.name" class="border-b">
					<td class="py-2">{{ t.trainee_name }}</td>
					<td v-for="status in ['Present', 'Absent', 'Leave', 'Holiday']" :key="status">
						<input
							type="radio"
							:name="t.name"
							:checked="statusFor(t.name) === status"
							@change="setStatus(t.name, status)"
						/>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { call, createListResource } from 'frappe-ui'

const date = ref(new Date().toISOString().slice(0, 10))
const marked = ref({})

const trainees = createListResource({
	doctype: 'Sales Trainee',
	fields: ['name', 'trainee_name'],
	filters: { training_status: 'In Training' },
	auto: true,
	pageLength: 200,
})

function statusFor(trainee) {
	return marked.value[trainee]
}

async function setStatus(trainee, status) {
	marked.value[trainee] = status
	await call('lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance.mark_attendance', {
		trainee,
		attendance_date: date.value,
		status,
	})
}

watch(date, () => {
	marked.value = {}
})
</script>
