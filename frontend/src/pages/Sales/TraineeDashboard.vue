<!-- frontend/src/pages/Sales/TraineeDashboard.vue -->
<template>
	<div class="min-h-full w-full px-4 pb-8 pt-4 sm:px-6 lg:px-8">
		<h1 class="mb-4 text-xl font-semibold text-[color:var(--genius-navy)]">Trainee Dashboard</h1>
		<div class="genius-card mb-6 flex flex-wrap gap-2 rounded-2xl p-4 sm:p-5">
			<input
				v-model="month"
				type="month"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				style="border-color: var(--genius-border)"
				placeholder="Month"
			/>
			<input
				v-model="location"
				type="text"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				style="border-color: var(--genius-border)"
				placeholder="Location"
			/>
			<input
				v-model="cohort"
				type="text"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				style="border-color: var(--genius-border)"
				placeholder="Cohort"
			/>
		</div>
		<div class="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
			<div
				class="genius-card rounded-2xl p-4 sm:p-5"
				v-for="(label, key) in {
					in_training: 'In Training', training_cleared: 'Training Cleared',
					training_not_cleared: 'Training Not Cleared', resigned: 'Resigned',
					absconded: 'Absconded', exited_churned: 'Exited/Churned',
					payroll_eligible: 'Payroll Eligible', open_payroll_cycles: 'Open Payroll Cycles',
				}"
				:key="key"
			>
				<div class="text-2xl font-semibold text-[color:var(--genius-navy)]">{{ summary.data?.[key] ?? '—' }}</div>
				<div class="mt-1 text-xs text-[color:var(--genius-muted)]">{{ label }}</div>
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
	const encoded = await call('lms.lms.trainee_reports.export_active_trainees_csv', {
		cohort: cohort.value || undefined,
		location: location.value || undefined,
	})
	const link = document.createElement('a')
	link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${encoded}`
	link.download = 'active-trainees.xlsx'
	link.click()
}
</script>
