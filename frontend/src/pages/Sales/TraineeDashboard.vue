<!-- frontend/src/pages/Sales/TraineeDashboard.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Trainee Dashboard</h1>
		<div class="grid grid-cols-3 gap-4 mb-6">
			<div class="border rounded p-4">
				<div class="text-2xl font-semibold">{{ inTraining.data ?? '—' }}</div>
				<div class="text-sm text-gray-500">In Training</div>
			</div>
			<div class="border rounded p-4">
				<div class="text-2xl font-semibold">{{ cleared.data ?? '—' }}</div>
				<div class="text-sm text-gray-500">Training Cleared</div>
			</div>
			<div class="border rounded p-4">
				<div class="text-2xl font-semibold">{{ exited.data ?? '—' }}</div>
				<div class="text-sm text-gray-500">Exited/Churned</div>
			</div>
		</div>
		<Button @click="downloadExport">Export Active Trainee Report</Button>
	</div>
</template>

<script setup>
import { createResource, call, Button } from 'frappe-ui'

const inTraining = createResource({
	url: 'frappe.client.get_count',
	params: { doctype: 'Sales Trainee', filters: { training_status: 'In Training' } },
	auto: true,
})
const cleared = createResource({
	url: 'frappe.client.get_count',
	params: { doctype: 'Sales Trainee', filters: { training_status: 'Training Cleared' } },
	auto: true,
})
const exited = createResource({
	url: 'frappe.client.get_count',
	params: { doctype: 'Sales Trainee', filters: { training_status: 'Exited/Churned' } },
	auto: true,
})

async function downloadExport() {
	const encoded = await call('lms.lms.trainee_reports.export_active_trainees_csv')
	const link = document.createElement('a')
	link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${encoded}`
	link.download = 'active-trainees.xlsx'
	link.click()
}
</script>
