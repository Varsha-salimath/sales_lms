<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Bulk enroll'),
			size: '3xl',
		}"
	>
		<template #body-content>
			<p class="mb-2 text-sm text-ink-gray-7">
				{{
					__(
						'Upload the Batch Upload sheet (CSV). New learners get an account, team assignment, optional Training Manager line, and enrollment in this batch.'
					)
				}}
			</p>
			<p class="mb-4 text-xs text-ink-gray-5">
				{{
					__(
						'Columns: Batch Start, Employee Name, Email ID, Locations, Training Manager. In Google Sheets use File → Download → Comma Separated Values (.csv). Do not upload .xlsx.'
					)
				}}
			</p>

			<div class="mb-4 flex flex-wrap gap-2">
				<Button variant="outline" size="sm" @click="downloadTemplate">
					{{ __('Download template') }}
				</Button>
				<input
					ref="fileInput"
					type="file"
					accept=".csv,text/csv,text/plain"
					class="hidden"
					@change="onFileChange"
				/>
				<Button variant="outline" size="sm" @click="fileInput?.click()">
					{{ fileName || __('Choose CSV file') }}
				</Button>
			</div>

			<div class="mb-4 space-y-3 rounded-lg border bg-surface-gray-1 p-3 text-sm">
				<label class="flex items-center gap-2">
					<input v-model="options.send_welcome" type="checkbox" class="rounded" />
					<span>{{ __('Send welcome email to new accounts') }}</span>
				</label>
				<label class="flex items-center gap-2">
					<input v-model="options.assign_training_manager" type="checkbox" class="rounded" />
					<span>{{ __('Assign Training Manager reporting line') }}</span>
				</label>
				<p class="text-xs text-ink-gray-5">
					{{
						__(
							'Batch enrollment confirmation email is sent automatically when each learner is enrolled (if email is configured on the batch).'
						)
					}}
				</p>
			</div>

			<div v-if="validating" class="text-sm text-ink-gray-6">
				{{ __('Validating...') }}
			</div>

			<template v-else-if="previewResult">
				<div
					v-for="(warning, idx) in previewResult.warnings || []"
					:key="'w-' + idx"
					class="mb-2 rounded-md border border-outline-orange-1 bg-surface-orange-1 px-3 py-2 text-xs text-ink-orange-3"
				>
					{{ warning }}
				</div>
				<div
					v-for="err in previewResult.errors || []"
					:key="`${err.row}-${err.email}`"
					class="mb-2 rounded-md border border-outline-red-1 bg-surface-red-1 px-3 py-2 text-xs text-ink-red-3"
				>
					{{ __('Row') }} {{ err.row }} ({{ err.email }}):
					{{ err.messages?.join(' ') }}
				</div>
				<p class="mb-3 text-sm font-medium text-ink-gray-8">
					{{ __('To enroll') }}: {{ previewResult.valid_count ?? 0 }} /
					{{ previewResult.total_rows ?? 0 }}
					<span v-if="previewResult.skip_count" class="font-normal text-ink-gray-6">
						({{ previewResult.skip_count }} {{ __('already enrolled — skipped') }})
					</span>
				</p>
				<div
					v-if="previewResult.preview?.length"
					class="max-h-48 overflow-y-auto rounded border text-xs"
				>
					<table class="w-full">
						<thead class="sticky top-0 bg-surface-gray-2 text-left text-ink-gray-6">
							<tr>
								<th class="p-2">{{ __('Email') }}</th>
								<th class="p-2">{{ __('Name') }}</th>
								<th class="p-2">{{ __('Status') }}</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in previewResult.preview"
								:key="row.row"
								class="border-t border-surface-gray-2"
							>
								<td class="p-2">{{ row.email }}</td>
								<td class="p-2">{{ row.employee_name }}</td>
								<td class="p-2 capitalize">{{ statusLabel(row.status) }}</td>
							</tr>
						</tbody>
					</table>
				</div>
			</template>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button @click="show = false">{{ __('Close') }}</Button>
				<Button
					variant="solid"
					:loading="importing"
					:disabled="!canRunImport"
					@click="runImport"
				>
					{{ __('Enroll learners') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog, call, toast } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

const show = defineModel({ type: Boolean, default: false })

const props = defineProps({
	batchName: {
		type: String,
		required: true,
	},
})

const emit = defineEmits(['success'])

const fileInput = ref(null)
const fileName = ref('')
const csvText = ref('')
const validating = ref(false)
const importing = ref(false)
const previewResult = ref(null)

const options = reactive({
	send_welcome: true,
	assign_training_manager: true,
})

const canRunImport = computed(() => {
	if (!csvText.value || !previewResult.value) return false
	if ((previewResult.value.errors?.length ?? 0) > 0) return false
	const toEnroll = previewResult.value.valid_count ?? 0
	const skipped = previewResult.value.skip_count ?? 0
	return toEnroll > 0 || skipped > 0
})

watch(show, (open) => {
	if (!open) {
		csvText.value = ''
		fileName.value = ''
		previewResult.value = null
	}
})

watch(
	() => options.assign_training_manager,
	() => {
		if (csvText.value) validateFile()
	}
)

function statusLabel(status) {
	if (status === 'will_create') return __('New account + enroll')
	if (status === 'will_enroll') return __('Enroll')
	if (status === 'already_enrolled') return __('Already enrolled')
	return status
}

async function downloadTemplate() {
	try {
		const csv = await call('lms.lms.batch_enrollment_bulk.get_batch_upload_template_csv', {
			batch: props.batchName,
		})
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
		const link = document.createElement('a')
		link.href = URL.createObjectURL(blob)
		link.download = 'batch-upload-template.csv'
		link.click()
		URL.revokeObjectURL(link.href)
	} catch (err) {
		toast.error(err.messages?.[0] || err.message || __('Could not download template'))
	}
}

async function validateFile() {
	if (!csvText.value) return
	validating.value = true
	try {
		previewResult.value = await call(
			'lms.lms.batch_enrollment_bulk.preview_batch_enrollment_upload',
			{
				batch: props.batchName,
				file_content: csvText.value,
				options: JSON.stringify(options),
			}
		)
	} catch (err) {
		previewResult.value = null
		toast.error(err.messages?.[0] || err.message || __('Validation failed'))
	} finally {
		validating.value = false
	}
}

function onFileChange(event) {
	const file = event.target.files?.[0]
	if (!file) return
	const lower = file.name.toLowerCase()
	if (lower.endsWith('.xlsx') || lower.endsWith('.xls')) {
		toast.error(
			__(
				'Please save the sheet as CSV (File → Download → Comma Separated Values) and upload the .csv file.'
			)
		)
		event.target.value = ''
		return
	}
	fileName.value = file.name
	const reader = new FileReader()
	reader.onload = () => {
		csvText.value = String(reader.result || '')
		validateFile()
	}
	reader.readAsText(file)
	event.target.value = ''
}

async function runImport() {
	if (!csvText.value) return
	importing.value = true
	try {
		const result = await call('lms.lms.batch_enrollment_bulk.commit_batch_enrollment_upload', {
			batch: props.batchName,
			file_content: csvText.value,
			options: JSON.stringify(options),
		})
		const enrolled = result.enrolled ?? 0
		const skipped = result.skipped ?? 0
		if (enrolled === 0 && skipped > 0 && !(result.failed?.length)) {
			toast.success(__('All {0} learner(s) were already in this batch.').format(skipped))
		} else {
			const parts = [
				enrolled ? __('{0} enrolled').format(enrolled) : null,
				result.created ? __('{0} new accounts').format(result.created) : null,
				skipped ? __('{0} already enrolled').format(skipped) : null,
			].filter(Boolean)
			toast.success(parts.join(' · ') || __('Bulk enroll finished'))
		}
		if (result.failed?.length) {
			toast.error(
				__('{0} row(s) failed. Check Training Manager emails and team mapping.').format(
					result.failed.length
				)
			)
		}
		emit('success')
		show.value = false
	} catch (err) {
		toast.error(err.messages?.[0] || err.message || __('Bulk enroll failed'))
	} finally {
		importing.value = false
	}
}
</script>
