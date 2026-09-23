<template>
	<div class="p-6 max-w-3xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Bulk Onboard Sales Trainees</h1>
		<input ref="fileInput" type="file" accept=".csv" class="mb-4" @change="onFileSelected" />
		<div class="flex gap-2 mb-4">
			<Button :loading="busy" @click="runImport(true)">Validate (dry run)</Button>
			<Button :loading="busy" variant="solid" :disabled="!preview?.ok" @click="runImport(false)">
				Import
			</Button>
		</div>
		<div v-if="error" class="text-red-600 mb-4">{{ error }}</div>
		<div v-if="preview">
			<p v-if="preview.ok" class="text-green-700">
				Looks good — {{ rows.length }} rows ready to import.
			</p>
			<ul v-else class="text-red-600 list-disc pl-5">
				<li v-for="(e, i) in preview.errors" :key="i">{{ e }}</li>
			</ul>
		</div>
		<div v-if="result" class="mt-4">
			<p class="text-green-700">
				Created {{ result.created }}, updated {{ result.updated }}.
			</p>
			<ul v-if="result.errors?.length" class="text-red-600 list-disc pl-5">
				<li v-for="(e, i) in result.errors" :key="i">{{ e }}</li>
			</ul>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { call, Button } from 'frappe-ui'

const fileInput = ref(null)
const rows = ref([])
const preview = ref(null)
const result = ref(null)
const error = ref('')
const busy = ref(false)

function onFileSelected(e) {
	const file = e.target.files[0]
	if (!file) return
	const reader = new FileReader()
	reader.onload = () => {
		rows.value = parseCsv(reader.result)
	}
	reader.readAsText(file)
}

function parseCsv(text) {
	const [headerLine, ...lines] = text.trim().split('\n')
	const headers = headerLine.split(',').map((h) => h.trim())
	return lines
		.filter((l) => l.trim())
		.map((line) => {
			const values = line.split(',')
			return Object.fromEntries(headers.map((h, i) => [h, (values[i] || '').trim()]))
		})
}

async function runImport(dryRun) {
	error.value = ''
	busy.value = true
	try {
		const response = await call('lms.lms.sales_trainee_import.import_sales_trainees', {
			rows: rows.value,
			dry_run: dryRun,
		})
		if (dryRun) {
			preview.value = response
		} else {
			result.value = response
		}
	} catch (err) {
		error.value = err?.messages?.[0] || err?.message || 'Import failed'
	} finally {
		busy.value = false
	}
}
</script>
