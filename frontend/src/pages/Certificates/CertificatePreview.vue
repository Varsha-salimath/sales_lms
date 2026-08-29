<template>
	<div class="min-h-screen bg-surface-gray-2 px-4 py-6 sm:px-8">
		<div class="mx-auto flex max-w-6xl flex-col gap-4">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div>
					<h1 class="text-xl font-semibold text-ink-gray-9">
						{{ __('Certificate of Completion') }}
					</h1>
					<p class="mt-1 text-sm text-ink-gray-6">
						{{ preview.data?.learner_full_name }}
						<span v-if="preview.data?.completion_date">
							· {{ preview.data.completion_date }}
						</span>
					</p>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					<Button variant="subtle" @click="zoomOut">{{ __('Zoom out') }}</Button>
					<span class="min-w-12 text-center text-sm text-ink-gray-7">
						{{ Math.round(zoom * 100) }}%
					</span>
					<Button variant="subtle" @click="zoomIn">{{ __('Zoom in') }}</Button>
					<Button variant="subtle" @click="resetZoom">{{ __('Fit') }}</Button>
					<Button
						variant="solid"
						:loading="false"
						@click="downloadPdf"
					>
						{{ __('Download PDF') }}
					</Button>
					<Button variant="outline" @click="downloadPng">
						{{ __('Download PNG') }}
					</Button>
				</div>
			</div>

			<div
				class="overflow-auto rounded-2xl border border-outline-gray-2 bg-surface-white p-4 shadow-sm"
				style="min-height: 70vh"
			>
				<div
					v-if="preview.loading"
					class="flex h-[60vh] items-center justify-center text-ink-gray-6"
				>
					{{ __('Loading certificate…') }}
				</div>
				<div
					v-else-if="preview.error"
					class="flex h-[60vh] items-center justify-center text-red-600"
				>
					{{ __('Unable to load certificate.') }}
				</div>
				<div v-else class="flex justify-center">
					<img
						:src="imageSrc"
						:alt="__('Certificate')"
						class="max-w-none rounded shadow-md origin-top transition-transform duration-200"
						:style="{
							width: `${baseWidth * zoom}px`,
							height: 'auto',
						}"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Button, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const zoom = ref(1)
const baseWidth = 960

const preview = createResource({
	url: 'lms.lms.doctype.lms_certificate.lms_certificate.get_certificate_preview',
	auto: false,
})

watch(
	() => route.params.certificateName,
	(name) => {
		if (name) {
			preview.submit({ name })
		}
	},
	{ immediate: true }
)

const imageSrc = computed(() => {
	const b64 = preview.data?.png_base64
	return b64 ? `data:image/png;base64,${b64}` : ''
})

const zoomIn = () => {
	zoom.value = Math.min(2.5, Number((zoom.value + 0.1).toFixed(2)))
}
const zoomOut = () => {
	zoom.value = Math.max(0.4, Number((zoom.value - 0.1).toFixed(2)))
}
const resetZoom = () => {
	zoom.value = 1
}

const downloadPdf = () => {
	const url = preview.data?.pdf_url
	if (url) window.open(url, '_blank')
}
const downloadPng = () => {
	const url = preview.data?.png_url
	if (url) window.open(url, '_blank')
}
</script>
