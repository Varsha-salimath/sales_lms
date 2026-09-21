<template>
	<div class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
		<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-3">
			<div>
				<h3 class="text-base font-semibold text-ink-gray-9">
					{{ __('Failed quizzes — blocked from next lesson') }}
				</h3>
				<p class="text-xs text-ink-gray-6 mt-0.5">
					{{
						__(
							'Learners who did not pass a batch quiz and are still locked on the next lesson.'
						)
					}}
				</p>
			</div>
			<FormControl
				v-if="batchOptions.length"
				v-model="selectedBatch"
				type="select"
				:options="batchOptions"
				class="analytics-chart-filter w-full sm:w-56 shrink-0"
				@update:modelValue="loadRows"
			/>
		</div>
		<div v-if="rows.loading" class="py-8 text-center text-sm text-ink-gray-6">
			{{ __('Loading...') }}
		</div>
		<div
			v-else-if="rows.error"
			class="py-8 text-center text-sm text-ink-red-4"
		>
			{{ rows.error?.messages?.[0] || __('Could not load learners.') }}
		</div>
		<div
			v-else-if="!(rows.data?.rows || []).length"
			class="py-8 text-center text-sm text-ink-gray-6"
		>
			{{ __('No blocked learners found for this filter.') }}
		</div>
		<div v-else class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b text-left text-xs text-ink-gray-6">
						<th class="py-2 pe-3">{{ __('Learner') }}</th>
						<th class="py-2 pe-3">{{ __('Batch') }}</th>
						<th class="py-2 pe-3">{{ __('Quiz') }}</th>
						<th class="py-2 pe-3">{{ __('Score') }}</th>
						<th class="py-2">{{ __('Pass mark') }}</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in rows.data.rows"
						:key="`${row.member}-${row.quiz}`"
						class="border-b border-outline-gray-1"
					>
						<td class="py-2 pe-3">
							<div class="font-medium text-ink-gray-9">{{ row.full_name }}</div>
							<div class="text-xs text-ink-gray-5">{{ row.email }}</div>
						</td>
						<td class="py-2 pe-3 whitespace-nowrap">{{ row.batch_title }}</td>
						<td class="py-2 pe-3">{{ row.quiz_title }}</td>
						<td class="py-2 pe-3 tabular-nums">{{ row.score_display }}</td>
						<td class="py-2 tabular-nums">{{ row.passing_percentage }}%</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { FormControl, createResource } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
	batches: {
		type: Array,
		default: () => [],
	},
})

const selectedBatch = ref('__all__')

const batchOptions = computed(() => [
	{ label: __('All batches'), value: '__all__' },
	...(props.batches || []).map((batch) => ({
		label: batch.title || batch.name,
		value: batch.name,
	})),
])

const rows = createResource({
	url: 'lms.lms.api.get_failed_quiz_blocked_learners',
	makeParams() {
		return { batch: selectedBatch.value, page: 1, page_length: 100 }
	},
})

const loadRows = () => rows.reload()

onMounted(() => loadRows())
</script>
