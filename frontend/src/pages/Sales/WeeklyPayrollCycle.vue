<!-- frontend/src/pages/Sales/WeeklyPayrollCycle.vue -->
<template>
	<div class="min-h-full w-full px-4 pb-8 pt-4 sm:px-6 lg:px-8">
		<h1 class="mb-4 text-xl font-semibold text-[color:var(--genius-navy)]">Weekly Payroll Cycles</h1>
		<div class="genius-card rounded-2xl p-4 sm:p-5">
			<div class="overflow-x-auto">
				<table class="min-w-full text-left text-sm">
					<thead>
						<tr
							class="border-b text-[11px] uppercase tracking-wide text-[color:var(--genius-muted)]"
							style="border-color: var(--genius-border)"
						>
							<th class="pb-2 pr-3 font-medium">Week</th>
							<th class="pb-2 pr-3 font-medium">Status</th>
							<th class="pb-2 pr-3 font-medium">Vendor Invoice</th>
							<th class="pb-2 font-medium"></th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="c in cycles.data"
							:key="c.name"
							class="border-b last:border-0"
							style="border-color: var(--genius-border)"
						>
							<td class="py-2.5 pr-3 font-medium text-[color:var(--genius-navy)]">
								{{ c.week_start }} – {{ c.week_end }}
							</td>
							<td class="py-2.5 pr-3">
								<span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="statusBadge(c.status)">
									{{ c.status }}
								</span>
							</td>
							<td class="py-2.5 pr-3 text-xs text-[color:var(--genius-muted)]">
								{{ c.vendor_invoice_amount || '—' }}
							</td>
							<td class="py-2.5">
								<div class="flex gap-2">
									<Button size="sm" :loading="busy === c.name" @click="prepInputs(c.name)" v-if="c.status === 'Preparing'">
										Prepare Inputs
									</Button>
									<Button size="sm" :loading="busy === c.name" @click="advance(c.name, nextStatus(c.status))" v-if="nextStatus(c.status)">
										Advance to {{ nextStatus(c.status) }}
									</Button>
									<Button size="sm" :loading="busy === c.name" @click="exportReconciliation(c.name)" v-if="canExportFinance">
										Export reconciliation
									</Button>
								</div>
							</td>
						</tr>
					</tbody>
				</table>
				<div v-if="!cycles.loading && !cycles.data?.length" class="py-8 text-center text-sm text-[color:var(--genius-muted)]">
					No payroll cycles yet.
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { call, createListResource, Button } from 'frappe-ui'
import { usersStore } from '@/stores/user'

const { userResource } = usersStore()
const canExportFinance = computed(() => (userResource?.data?.roles || []).includes('Sales Training Finance'))

const SEQUENCE = ['Preparing', 'Ready to Share', 'Shared with Vendor', 'Awaiting Invoice', 'Finance Validation', 'Closed']
const STATUS_BADGES = {
	Preparing: 'bg-gray-100 text-gray-600',
	'Ready to Share': 'bg-blue-50 text-blue-700',
	'Shared with Vendor': 'bg-blue-50 text-blue-700',
	'Awaiting Invoice': 'bg-amber-50 text-amber-700',
	'Finance Validation': 'bg-amber-50 text-amber-700',
	Closed: 'bg-green-50 text-green-700',
}
const busy = ref(null)

const cycles = createListResource({
	doctype: 'Weekly Payroll Cycle',
	fields: ['name', 'week_start', 'week_end', 'status', 'vendor_invoice_amount'],
	auto: true,
	pageLength: 50,
})

function statusBadge(status) {
	return STATUS_BADGES[status] || 'bg-gray-100 text-gray-600'
}

function nextStatus(current) {
	const i = SEQUENCE.indexOf(current)
	return i >= 0 && i < SEQUENCE.length - 1 ? SEQUENCE[i + 1] : null
}

async function prepInputs(name) {
	busy.value = name
	try {
		await call('lms.lms.trainee_payroll.prepare_weekly_inputs', { cycle_name: name })
	} finally {
		busy.value = null
	}
}

async function advance(name, newStatus) {
	busy.value = name
	try {
		await call('run_doc_method', { dt: 'Weekly Payroll Cycle', dn: name, method: 'advance_status', args: { new_status: newStatus } })
		cycles.reload()
	} finally {
		busy.value = null
	}
}

async function exportReconciliation(name) {
	busy.value = name
	try {
		const encoded = await call('lms.lms.trainee_reports.export_finance_reconciliation_report', { cycle_name: name })
		const link = document.createElement('a')
		link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${encoded}`
		link.download = `finance-reconciliation-${name}.xlsx`
		link.click()
	} finally {
		busy.value = null
	}
}
</script>
