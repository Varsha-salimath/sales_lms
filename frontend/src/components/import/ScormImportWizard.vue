<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Import SCORM Course'),
			size: 'lg',
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-p-base">
				<p class="text-sm text-ink-gray-6">
					{{
						__(
							'Upload a SCORM 1.2 or SCORM 2004 ZIP. Genius will create a published course with SCORM chapters.'
						)
					}}
				</p>
				<FormControl
					v-model="courseTitle"
					:label="__('Course title (optional)')"
					:placeholder="__('Use title from manifest')"
				/>
				<FormControl
					v-model="courseName"
					:label="__('Course ID / slug (optional)')"
					:placeholder="__('e.g. intel-ai-foundations')"
				/>
				<div
					v-if="!zip"
					@dragover.prevent
					@drop.prevent="(e) => uploadFile(e)"
					class="flex h-[140px] flex-col items-center justify-center rounded-md border border-dashed border-outline-gray-3 bg-surface-gray-1"
				>
					<div v-if="!uploading" class="w-4/5 text-center">
						<UploadCloud class="mx-auto mb-2.5 size-6 stroke-1.5 text-ink-gray-6" />
						<input
							ref="fileInput"
							type="file"
							class="hidden"
							accept=".zip"
							@change="(e) => uploadFile(e)"
						/>
						<div class="leading-5 text-ink-gray-9">
							{{ __('Drag and drop a SCORM ZIP, or') }}
							<span
								class="cursor-pointer font-semibold hover:underline"
								@click="openFileSelector"
							>
								{{ __('browse') }}
							</span>
						</div>
					</div>
					<div v-else class="w-fit rounded-md border bg-surface-white p-2">
						<div class="space-y-2">
							<div class="font-medium">{{ uploadingFile?.name }}</div>
							<div class="text-ink-gray-6">
								{{ convertToMB(uploaded) }} of {{ convertToMB(total) }}
							</div>
						</div>
						<div class="mt-3 h-1 w-full rounded-full bg-surface-gray-1">
							<div
								class="h-1 rounded-full bg-surface-gray-7 transition-all duration-500"
								:style="`width: ${uploadProgress}%`"
							/>
						</div>
					</div>
				</div>
				<div
					v-else
					class="flex h-[120px] items-center justify-center rounded-md border border-dashed border-outline-gray-3 bg-surface-gray-1"
				>
					<div
						class="mx-5 flex w-fit items-center justify-between gap-x-4 rounded-md border bg-surface-white p-2"
					>
						<div class="space-y-1">
							<div class="font-medium leading-5 text-ink-gray-9">
								{{ zip.file_name || zip.name }}
							</div>
							<div v-if="zip.file_size" class="text-ink-gray-6">
								{{ convertToMB(zip.file_size) }}
							</div>
						</div>
						<Trash2
							class="size-4 cursor-pointer stroke-1.5 text-ink-red-3"
							@click="deleteFile"
						/>
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button variant="subtle" @click="show = false">{{ __('Cancel') }}</Button>
				<Button variant="solid" :loading="importing" @click="runImport">
					{{ __('Import SCORM') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Button, call, Dialog, FileUploadHandler, FormControl, toast } from 'frappe-ui'
import { computed, ref } from 'vue'
import { Trash2, UploadCloud } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const show = defineModel({ type: Boolean, required: true })
const fileInput = ref(null)
const zip = ref(null)
const uploaded = ref(0)
const total = ref(0)
const uploading = ref(false)
const uploadingFile = ref(null)
const importing = ref(false)
const courseTitle = ref('')
const courseName = ref('')
const router = useRouter()

const uploadProgress = computed(() => {
	if (total.value === 0) return 0
	return Math.floor((uploaded.value / total.value) * 100)
})

const openFileSelector = () => fileInput.value?.click()

const extractFile = (e) => {
	const inputFiles = e.target?.files
	const dt = e.dataTransfer?.files
	return inputFiles?.[0] || dt?.[0] || null
}

const uploadFile = (e) => {
	const file = extractFile(e)
	if (!file) return
	const extension = file.name.split('.').pop()?.toLowerCase()
	if (extension !== 'zip') {
		toast.error(__('Please upload a valid ZIP file.'))
		return
	}

	uploadingFile.value = file
	const uploader = new FileUploadHandler()
	uploader.on('start', () => {
		uploading.value = true
	})
	uploader.on('progress', (data) => {
		uploaded.value = data.uploaded
		total.value = data.total
	})
	uploader.on('error', () => {
		uploading.value = false
		toast.error(__('File upload failed. Please try again.'))
	})
	uploader.on('finish', () => {
		uploading.value = false
	})
	uploader
		.upload(file, { private: 1 })
		.then((data) => {
			zip.value = data
		})
		.catch(() => {
			uploading.value = false
			uploadingFile.value = null
			toast.error(__('File upload failed. Please try again.'))
		})
}

const deleteFile = () => {
	zip.value = null
}

const convertToMB = (bytes) => ((bytes || 0) / 1024 / 1024).toFixed(2) + ' MB'

const runImport = () => {
	if (!zip.value?.name) {
		toast.error(__('Upload a SCORM ZIP first.'))
		return
	}
	importing.value = true
	call('lms.lms.api.import_scorm_course', {
		file_name: zip.value.name,
		course_title: courseTitle.value || null,
		course_name: courseName.value || null,
		publish: 1,
	})
		.then((data) => {
			toast.success(__('SCORM course imported successfully'))
			show.value = false
			deleteFile()
			courseTitle.value = ''
			courseName.value = ''
			router.push({
				name: 'GeniusCourseDetail',
				params: { courseName: data.name },
			})
		})
		.catch((error) => {
			toast.error(error.messages?.[0] || error.message || __('Import failed'))
		})
		.finally(() => {
			importing.value = false
		})
}
</script>
