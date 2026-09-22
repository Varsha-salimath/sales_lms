<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Import attendance & calling metrics'),
			size: '3xl',
		}"
	>
		<template #body-content>
			<p class="mb-3 text-xs text-ink-gray-6">
				{{
					__(
						'CSV columns: email, batch_start, attendance_days, dc, cc, talk_time, booked, catered. Only existing OJT Certification Metric rows are updated.'
					)
				}}
			</p>
			<input
				ref="fileInput"
				type="file"
				accept=".csv,text/csv"
				class="hidden"
				@change="onFileChange"
			/>
			<Button variant="outline" @click="fileInput?.click()">
				{{ csvFileName || __('Choose CSV file') }}
			</Button>
			<div v-if="preview.loading" class="mt-4 text-sm text-ink-gray-6">
				{{ __('Validating...') }}
			</div>
			<div v-else-if="preview.data" class="mt-4 space-y-3">
				<div
					v-for="warning in preview.data.warnings || []"
					:key="warning"
					class="rounded-md border border-outline-orange-1 bg-surface-orange-1 px-3 py-2 text-xs text-ink-orange-3"
				>
					{{ warning }}
				</div>
				<div
					v-for="err in preview.data.errors || []"
					:key="`${err.row}-${err.email}`"
					class="rounded-md border border-outline-red-1 bg-surface-red-1 px-3 py-2 text-xs text-ink-red-3"
				>
					{{ __('Row') }} {{ err.row }} ({{ err.email }}):
					{{ err.messages?.join(' ') }}
				</div>
				<p class="text-sm text-ink-gray-7">
					{{ __('Ready to import') }}: {{ preview.data.valid_count || 0 }} /
					{{ preview.data.total_rows || 0 }}
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button @click="show = false">{{ __('Close') }}</Button>
				<Button
					variant="solid"
					:loading="importing"
					:disabled="!preview.data?.valid_count || preview.data?.errors?.length"
					@click="runImport"
				>
					{{ __('Import') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog, call, createResource, toast } from 'frappe-ui'
import { ref, watch } from 'vue'

const show = defineModel({ type: Boolean, default: false })
const fileInput = ref(null)
const csvText = ref('')
const csvFileName = ref('')
const importing = ref(false)

const preview = createResource({
	url: 'lms.lms.ojt_certification.preview_attendance_metrics_csv',
	makeParams() {
		return { file_content: csvText.value }
	},
})

watch(csvText, (value) => {
	if (value) preview.reload()
})

const onFileChange = (event) => {
	const file = event.target.files?.[0]
	if (!file) return
	csvFileName.value = file.name
	const reader = new FileReader()
	reader.onload = () => {
		csvText.value = String(reader.result || '')
	}
	reader.readAsText(file)
}

const runImport = async () => {
	if (!csvText.value) return
	importing.value = true
	try {
		const result = await call('lms.lms.ojt_certification.import_attendance_metrics_csv', {
			file_content: csvText.value,
		})
		toast.success(`${__('Updated')} ${result.updated || 0} ${__('learner rows.')}`)
		show.value = false
		csvText.value = ''
		csvFileName.value = ''
		preview.reset()
	} catch (err) {
		toast.error(err.messages?.[0] || err.message || __('Import failed'))
	} finally {
		importing.value = false
	}
}
</script>
