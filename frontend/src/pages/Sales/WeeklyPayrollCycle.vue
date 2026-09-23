<!-- frontend/src/pages/Sales/WeeklyPayrollCycle.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Weekly Payroll Cycles</h1>
		<table class="w-full text-left border-collapse mb-6">
			<thead>
				<tr class="border-b">
					<th class="py-2">Week</th>
					<th>Status</th>
					<th>Vendor Invoice</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="c in cycles.data" :key="c.name" class="border-b">
					<td class="py-2">{{ c.week_start }} – {{ c.week_end }}</td>
					<td>{{ c.status }}</td>
					<td>{{ c.vendor_invoice_amount || '—' }}</td>
					<td>
						<Button size="sm" @click="prepInputs(c.name)" v-if="c.status === 'Preparing'">Prepare Inputs</Button>
						<Button size="sm" @click="advance(c.name, nextStatus(c.status))" v-if="nextStatus(c.status)">
							Advance to {{ nextStatus(c.status) }}
						</Button>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { call, createListResource, Button } from 'frappe-ui'

const SEQUENCE = ['Preparing', 'Ready to Share', 'Shared with Vendor', 'Awaiting Invoice', 'Finance Validation', 'Closed']

const cycles = createListResource({
	doctype: 'Weekly Payroll Cycle',
	fields: ['name', 'week_start', 'week_end', 'status', 'vendor_invoice_amount'],
	auto: true,
	pageLength: 50,
})

function nextStatus(current) {
	const i = SEQUENCE.indexOf(current)
	return i >= 0 && i < SEQUENCE.length - 1 ? SEQUENCE[i + 1] : null
}

async function prepInputs(name) {
	await call('lms.lms.trainee_payroll.prepare_weekly_inputs', { cycle_name: name })
}

async function advance(name, newStatus) {
	await call('frappe.client.get_doc', { doctype: 'Weekly Payroll Cycle', name }).then(async (doc) => {
		await call('run_doc_method', { dt: 'Weekly Payroll Cycle', dn: name, method: 'advance_status', args: { new_status: newStatus } })
	})
	cycles.reload()
}
</script>
