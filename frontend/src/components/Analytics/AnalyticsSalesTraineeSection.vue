<template>
	<div class="space-y-6">
		<div>
			<h2 class="text-base font-semibold text-ink-gray-9 mb-1">
				{{ __('Sales Trainees') }}
			</h2>
			<p class="text-xs text-ink-gray-6">
				{{ __('Onboarding, cohort, and payroll-eligibility status for third-party sales trainees.') }}
			</p>
		</div>

		<div class="flex flex-wrap gap-2">
			<input
				v-model="month"
				type="month"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				placeholder="Month"
			/>
			<input
				v-model="location"
				type="text"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				placeholder="Location"
			/>
			<input
				v-model="cohort"
				type="text"
				class="rounded-lg border px-2.5 py-1.5 text-sm"
				placeholder="Cohort"
			/>
		</div>

		<div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
			<div
				v-for="(label, key) in {
					in_training: __('In Training'),
					training_cleared: __('Training Cleared'),
					training_not_cleared: __('Training Not Cleared'),
					resigned: __('Resigned'),
					absconded: __('Absconded'),
					exited_churned: __('Exited/Churned'),
					payroll_eligible: __('Payroll Eligible'),
					open_payroll_cycles: __('Open Payroll Cycles'),
				}"
				:key="key"
				class="border rounded-lg bg-surface-white p-4"
			>
				<div class="text-2xl font-semibold text-ink-gray-9">{{ summary.data?.[key] ?? '—' }}</div>
				<div class="mt-1 text-xs text-ink-gray-6">{{ label }}</div>
			</div>
		</div>

		<Button @click="downloadExport">{{ __('Export Active Trainee Report') }}</Button>
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
