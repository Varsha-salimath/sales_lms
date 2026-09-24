<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="mb-2 text-xl font-semibold text-[color:var(--genius-navy)]">Mark Attendance</h1>
		<input
			v-model="date"
			type="date"
			class="mb-4 rounded-lg border px-2.5 py-1.5 text-sm"
			style="border-color: var(--genius-border)"
		/>
		<div class="genius-card rounded-2xl p-4 sm:p-5">
			<p v-if="existing.loading" class="mb-2 text-sm text-[color:var(--genius-muted)]">Loading existing attendance…</p>
			<div class="overflow-x-auto">
				<table class="min-w-full text-left text-sm">
					<thead>
						<tr
							class="border-b text-[11px] uppercase tracking-wide text-[color:var(--genius-muted)]"
							style="border-color: var(--genius-border)"
						>
							<th class="pb-2 pr-3 font-medium">Trainee</th>
							<th class="pb-2 pr-3 font-medium">Present</th>
							<th class="pb-2 pr-3 font-medium">Absent</th>
							<th class="pb-2 pr-3 font-medium">Leave</th>
							<th class="pb-2 font-medium">Holiday</th>
						</tr>
					</thead>
					<!-- renderKey forces the radios back in sync after a cancelled or failed change -->
					<tbody :key="renderKey">
						<tr
							v-for="t in trainees.data"
							:key="t.name"
							class="border-b last:border-0"
							style="border-color: var(--genius-border)"
						>
							<td class="py-2.5 pr-3 font-medium text-[color:var(--genius-navy)]">{{ t.trainee_name }}</td>
							<td class="py-2.5 pr-3" v-for="status in ['Present', 'Absent', 'Leave', 'Holiday']" :key="status">
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
				<div v-if="!trainees.loading && !trainees.data?.length" class="py-8 text-center text-sm text-[color:var(--genius-muted)]">
					No trainees currently in training.
				</div>
			</div>
		</div>
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
