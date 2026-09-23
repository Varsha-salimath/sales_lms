<!-- frontend/src/pages/Sales/TraineeDashboard.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Trainee Dashboard</h1>
		<div class="flex gap-2 mb-4">
			<input v-model="month" type="month" class="border rounded px-2 py-1" placeholder="Month" />
			<input v-model="location" type="text" class="border rounded px-2 py-1" placeholder="Location" />
			<input v-model="cohort" type="text" class="border rounded px-2 py-1" placeholder="Cohort" />
		</div>
		<div class="grid grid-cols-4 gap-4 mb-6">
			<div class="border rounded p-4" v-for="(label, key) in {
				in_training: 'In Training', training_cleared: 'Training Cleared',
				training_not_cleared: 'Training Not Cleared', resigned: 'Resigned',
				absconded: 'Absconded', exited_churned: 'Exited/Churned',
				payroll_eligible: 'Payroll Eligible', open_payroll_cycles: 'Open Payroll Cycles',
			}" :key="key">
				<div class="text-2xl font-semibold">{{ summary.data?.[key] ?? '—' }}</div>
				<div class="text-sm text-gray-500">{{ label }}</div>
			</div>
		</div>
		<Button @click="downloadExport">Export Active Trainee Report</Button>
	</div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { createResource, call, Button } from 'frappe-ui'

const month = ref('')
const location = ref('')
const cohort = ref('')

const summary = createResource({
	url: 'lms.lms.trainee_dashboard.get_dashboard_summary',
	params: { month: month.value, location: location.value, cohort: cohort.value },
	auto: true,
})

watch([month, location, cohort], () => {
	summary.update({ params: { month: month.value, location: location.value, cohort: cohort.value } })
	summary.reload()
})

async function downloadExport() {
	const encoded = await call('lms.lms.trainee_reports.export_active_trainees_csv')
	const link = document.createElement('a')
	link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${encoded}`
	link.download = 'active-trainees.xlsx'
	link.click()
}
</script>
