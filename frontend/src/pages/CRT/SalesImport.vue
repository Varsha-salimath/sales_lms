<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<header class="border-b bg-white" style="border-color: #d7e4f7">
			<div class="mx-auto flex max-w-3xl items-center justify-between px-5 py-3">
				<router-link :to="{ name: 'GeniusCourseDetail', params: { courseName: 'sales-crt' } }" class="text-sm font-semibold" style="color: #0075ff">
					← {{ __('CRT course') }}
				</router-link>
			</div>
		</header>

		<div class="mx-auto max-w-3xl px-5 pt-10">
			<p class="text-xs font-semibold uppercase tracking-[0.22em]" style="color: #0075ff">
				Admin
			</p>
			<h1 class="mt-2 text-3xl font-semibold tracking-tight text-[color:var(--il-ink)]">
				Import CRT Excel
			</h1>
			<p class="mt-3 text-sm leading-6 text-[color:var(--il-muted)]">
				Reads the CRT schedule workbook, validates required columns, then creates/updates the Sales CRT course, chapters, lessons, and schedule pages. Re-import is safe (idempotent).
			</p>

			<div class="sales-card mt-8 p-6">
				<div
					class="flex h-36 flex-col items-center justify-center rounded-2xl border border-dashed bg-[#f4f8ff]"
					style="border-color: #9cc4ff"
					@dragover.prevent
					@drop.prevent="uploadFile"
				>
					<input
						ref="fileInput"
						type="file"
						class="hidden"
						accept=".xlsx,.xls"
						@change="uploadFile"
					/>
					<div v-if="!uploading && !fileDoc" class="text-center">
						<p class="text-sm font-medium text-[color:var(--il-ink)]">
							Drop CRT Schedule.xlsx here, or
							<button class="font-semibold" style="color: #0075ff" @click="fileInput?.click()">
								browse
							</button>
						</p>
					</div>
					<p v-else-if="uploading" class="text-sm text-[color:var(--il-muted)]">Uploading… {{ uploadProgress }}%</p>
					<p v-else class="text-sm font-medium">{{ fileDoc.file_name || fileDoc.name }}</p>
				</div>

				<div class="mt-5 flex flex-wrap gap-3">
					<button
						class="rounded-full border px-4 py-2 text-sm font-semibold disabled:opacity-40"
						style="border-color: #9cc4ff; color: #0075ff"
						:disabled="!canRun"
						@click="runPreview"
					>
						Dry-run preview
					</button>
					<button
						class="rounded-full px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
						style="background: #0075ff"
						:disabled="!canRun"
						@click="runImport"
					>
						Import into Frappe
					</button>
					<button
						class="rounded-full border px-4 py-2 text-sm font-semibold text-[color:var(--il-ink)]"
						style="border-color: #d7e4f7"
						@click="runBundled('preview')"
					>
						Preview bundled Excel
					</button>
					<button
						class="rounded-full border px-4 py-2 text-sm font-semibold text-[color:var(--il-ink)]"
						style="border-color: #d7e4f7"
						@click="runBundled('import')"
					>
						Import bundled Excel
					</button>
				</div>
			</div>

			<div v-if="error" class="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
				{{ error }}
			</div>

			<div v-if="preview" class="sales-card mt-6 p-6">
				<div class="flex items-center justify-between">
					<h2 class="text-lg font-semibold">{{ preview.sheet }} · {{ preview.session_count }} sessions / {{ preview.day_count }} days</h2>
					<span class="text-xs text-[color:var(--il-muted)]">{{ result?.import_log || preview.import_log }}</span>
				</div>
				<div class="mt-4 space-y-4">
					<div v-for="day in preview.days" :key="day.day_number">
						<div class="text-sm font-semibold" style="color: #0075ff">
							{{ day.day_label }} · {{ day.session_count }}
						</div>
						<ul class="mt-2 space-y-1 text-sm text-[color:var(--il-muted)]">
							<li v-for="s in day.sessions" :key="s.session_key">
								{{ s.time_label || '—' }} — {{ s.topic }}
								<span class="text-xs uppercase">[{{ s.session_type }}]</span>
							</li>
						</ul>
					</div>
				</div>
				<p v-if="result && !result.dry_run" class="mt-4 text-sm font-medium text-emerald-700">
					Imported. Created {{ result.sessions_created }}, updated {{ result.sessions_updated }}, removed {{ result.sessions_removed }}.
				</p>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { call, FileUploadHandler, toast } from 'frappe-ui'

const fileInput = ref(null)
const fileDoc = ref(null)
const uploading = ref(false)
const uploaded = ref(0)
const total = ref(0)
const preview = ref(null)
const result = ref(null)
const error = ref('')
const busy = ref(false)

const uploadProgress = computed(() => {
	if (!total.value) return 0
	return Math.floor((uploaded.value / total.value) * 100)
})
const canRun = computed(() => !!fileDoc.value && !busy.value)

const extractFile = (e) => e.target?.files?.[0] || e.dataTransfer?.files?.[0] || null

const uploadFile = (e) => {
	const file = extractFile(e)
	if (!file) return
	const ext = file.name.split('.').pop()?.toLowerCase()
	if (!['xlsx', 'xls'].includes(ext)) {
		toast.error('Upload a .xlsx CRT schedule workbook.')
		return
	}
	error.value = ''
	const uploader = new FileUploadHandler()
	uploader.on('start', () => {
		uploading.value = true
	})
	uploader.on('progress', (data) => {
		uploaded.value = data.uploaded
		total.value = data.total
	})
	uploader.on('finish', () => {
		uploading.value = false
	})
	uploader
		.upload(file, { private: 1 })
		.then((data) => {
			fileDoc.value = data
			toast.success('Workbook uploaded')
		})
		.catch((err) => {
			uploading.value = false
			error.value = err?.message || 'Upload failed'
			toast.error(error.value)
		})
}

const runPreview = async () => {
	busy.value = true
	error.value = ''
	try {
		preview.value = await call('lms.lms.sales_crt.preview_import', {
			file_name: fileDoc.value.name,
			file_url: fileDoc.value.file_url,
		})
		result.value = { dry_run: 1, import_log: preview.value.import_log }
		toast.success('Dry-run complete')
	} catch (err) {
		error.value = err?.messages?.[0] || err?.message || 'Preview failed'
		toast.error(error.value)
	} finally {
		busy.value = false
	}
}

const runImport = async () => {
	busy.value = true
	error.value = ''
	try {
		const data = await call('lms.lms.sales_crt.import_schedule', {
			file_name: fileDoc.value.name,
			file_url: fileDoc.value.file_url,
		})
		result.value = data
		preview.value = data.preview || preview.value
		toast.success('CRT schedule imported')
	} catch (err) {
		error.value = err?.messages?.[0] || err?.message || 'Import failed'
		toast.error(error.value)
	} finally {
		busy.value = false
	}
}

const runBundled = async (mode) => {
	busy.value = true
	error.value = ''
	try {
		const method =
			mode === 'import' ? 'lms.lms.sales_crt.import_schedule' : 'lms.lms.sales_crt.preview_import'
		const data = await call(method, { use_bundled: 1 })
		if (mode === 'import') {
			result.value = data
			preview.value = data.preview
			toast.success('Bundled CRT schedule imported')
		} else {
			preview.value = data
			result.value = { dry_run: 1, import_log: data.import_log }
			toast.success('Bundled dry-run complete')
		}
	} catch (err) {
		error.value = err?.messages?.[0] || err?.message || 'Bundled import failed'
		toast.error(error.value)
	} finally {
		busy.value = false
	}
}
</script>
