<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-2">Mark Attendance</h1>
		<input v-model="date" type="date" class="mb-4 border rounded px-2 py-1" />
		<p v-if="existing.loading" class="text-sm text-ink-gray-5 mb-2">Loading existing attendance…</p>
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
			<!-- renderKey forces the radios back in sync after a cancelled or failed change -->
			<tbody :key="renderKey">
				<tr v-for="t in trainees.data" :key="t.name" class="border-b">
					<td class="py-2">{{ t.trainee_name }}</td>
					<td v-for="status in ['Present', 'Absent', 'Leave', 'Holiday']" :key="status">
						<input
							type="radio"
							:name="t.name"
							:checked="statusFor(t.name) === status"
							:disabled="existing.loading"
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
import { call, createListResource, toast } from 'frappe-ui'

const date = ref(new Date().toISOString().slice(0, 10))
const marked = ref({})
const renderKey = ref(0)

const trainees = createListResource({
	doctype: 'Sales Trainee',
	fields: ['name', 'trainee_name'],
	filters: { training_status: 'In Training' },
	auto: true,
	pageLength: 200,
})

// What is already on record for the selected date (manual or Zoom), so staff see it
// and a change to it is treated as a correction.
const existing = createListResource({
	doctype: 'Sales Trainee Attendance',
	fields: ['trainee', 'status'],
	filters: { attendance_date: date.value },
	auto: true,
	pageLength: 1000,
	onSuccess(rows) {
		marked.value = Object.fromEntries(rows.map((r) => [r.trainee, r.status]))
		renderKey.value++
	},
})

function statusFor(trainee) {
	return marked.value[trainee]
}

function revert(trainee, previous) {
	if (previous === undefined) delete marked.value[trainee]
	else marked.value[trainee] = previous
	renderKey.value++
}

async function setStatus(trainee, status) {
	const previous = marked.value[trainee]
	let reason
	if (previous && previous !== status) {
		// Changing a recorded day is a correction: the server requires a reason and audit-logs it.
		reason = window.prompt(`Change ${previous} to ${status}. Reason for the correction:`)
		if (!reason || !reason.trim()) {
			revert(trainee, previous)
			return
		}
	}
	marked.value[trainee] = status
	try {
		await call('lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance.mark_attendance', {
			trainee,
			attendance_date: date.value,
			status,
			reason,
		})
	} catch (e) {
		revert(trainee, previous)
		toast.error(e?.messages?.[0] || 'Could not save attendance.')
	}
}

watch(date, (value) => {
	marked.value = {}
	existing.update({ filters: { attendance_date: value } })
	existing.reload()
})
</script>
