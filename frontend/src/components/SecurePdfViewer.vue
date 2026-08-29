<template>
	<div
		ref="viewerRoot"
		class="secure-pdf-viewer mb-4 rounded-md border border-outline-gray-2 bg-surface-gray-1 overflow-hidden select-none"
		:style="{ height: `${height}px` }"
		@contextmenu.prevent
		@dragstart.prevent
		tabindex="0"
		@keydown="onKeydown"
	>
		<div
			class="flex flex-wrap items-center gap-2 border-b border-outline-gray-2 bg-surface-white px-3 py-2 text-sm"
		>
			<Button variant="ghost" size="sm" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">
				<template #icon>
					<ChevronLeft class="h-4 w-4" />
				</template>
			</Button>
			<span class="text-ink-gray-7 min-w-[4.5rem] text-center">
				{{ currentPage }} / {{ totalPages || '—' }}
			</span>
			<Button
				variant="ghost"
				size="sm"
				:disabled="!totalPages || currentPage >= totalPages"
				@click="goToPage(currentPage + 1)"
			>
				<template #icon>
					<ChevronRight class="h-4 w-4" />
				</template>
			</Button>

			<input
				v-if="totalPages"
				type="number"
				min="1"
				:max="totalPages"
				class="w-14 rounded border border-outline-gray-2 px-2 py-1 text-center text-sm"
				:value="currentPage"
				@change="onPageInput"
			/>

			<div class="mx-1 h-5 w-px bg-outline-gray-2" />

			<Button variant="ghost" size="sm" :disabled="scale <= 0.5" @click="setScale(scale - 0.25)">
				<template #icon>
					<Minus class="h-4 w-4" />
				</template>
			</Button>
			<span class="min-w-[3rem] text-center text-ink-gray-6">{{ Math.round(scale * 100) }}%</span>
			<Button variant="ghost" size="sm" :disabled="scale >= 3" @click="setScale(scale + 0.25)">
				<template #icon>
					<Plus class="h-4 w-4" />
				</template>
			</Button>

			<div class="flex-1" />

			<Button variant="ghost" size="sm" @click="toggleFullscreen">
				<template #icon>
					<Maximize2 class="h-4 w-4" />
				</template>
			</Button>
		</div>

		<div
			ref="scrollContainer"
			class="secure-pdf-scroll h-[calc(100%-3rem)] overflow-auto bg-surface-gray-2"
			@scroll="onScroll"
		>
			<div v-if="loading" class="flex h-full items-center justify-center text-ink-gray-6">
				{{ __('Loading document…') }}
			</div>
			<div v-else-if="error" class="flex h-full items-center justify-center px-4 text-center text-ink-red-3">
				{{ error }}
			</div>
			<div v-else class="flex flex-col items-center gap-4 py-4">
				<canvas
					v-for="page in totalPages"
					:key="page"
					:ref="(el) => setCanvasRef(page, el)"
					class="shadow-md bg-white max-w-full"
					@contextmenu.prevent
					@dragstart.prevent
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import * as pdfjsLib from 'pdfjs-dist'
import { ChevronLeft, ChevronRight, Maximize2, Minus, Plus } from 'lucide-vue-next'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getLessonPdfContext } from '@/utils/lessonPdfContext'
import {
	buildSecurePdfUrl,
	configurePdfWorker,
	fetchSecurePdfToken,
	getCsrfToken,
	PDFJS_WORKER_CDN,
} from '@/utils/securePdf'

const props = defineProps({
	fileUrl: { type: String, required: true },
	course: { type: String, default: null },
	lesson: { type: String, default: null },
	height: { type: Number, default: 700 },
})

const route = useRoute()

function getAccessContext() {
	const ctx = getLessonPdfContext()
	return {
		course: props.course || ctx.course || route.params?.courseName || null,
		lesson: props.lesson || ctx.lesson || null,
	}
}

const viewerRoot = ref(null)
const scrollContainer = ref(null)
const loading = ref(true)
const error = ref('')
const totalPages = ref(0)
const currentPage = ref(1)
const scale = ref(1)
const canvasRefs = ref({})

let pdfDoc = null
let renderTasks = {}
let pageHeights = []
let scrollRaf = null

function setCanvasRef(page, el) {
	if (el) {
		canvasRefs.value[page] = el
	} else {
		delete canvasRefs.value[page]
	}
}

function onKeydown(event) {
	if ((event.ctrlKey || event.metaKey) && ['p', 's', 'P', 'S'].includes(event.key)) {
		event.preventDefault()
	}
}

function onPageInput(event) {
	const page = parseInt(event.target.value, 10)
	if (!Number.isNaN(page)) goToPage(page)
}

function setScale(next) {
	scale.value = Math.min(3, Math.max(0.5, next))
	renderAllPages()
}

function goToPage(page) {
	if (!totalPages.value) return
	const target = Math.min(totalPages.value, Math.max(1, page))
	currentPage.value = target
	const canvas = canvasRefs.value[target]
	if (canvas && scrollContainer.value) {
		scrollContainer.value.scrollTo({
			top: canvas.offsetTop - 16,
			behavior: 'smooth',
		})
	}
}

function onScroll() {
	if (!scrollContainer.value || !totalPages.value) return
	if (scrollRaf) cancelAnimationFrame(scrollRaf)
	scrollRaf = requestAnimationFrame(() => {
		const scrollTop = scrollContainer.value.scrollTop + 80
		let page = 1
		for (let i = 0; i < pageHeights.length; i++) {
			if (scrollTop >= pageHeights[i]) page = i + 1
		}
		currentPage.value = page
	})
}

function toggleFullscreen() {
	const el = viewerRoot.value
	if (!el) return
	if (!document.fullscreenElement) {
		el.requestFullscreen?.()
	} else {
		document.exitFullscreen?.()
	}
}

function isPdfWorkerError(err) {
	const msg = String(err?.message || err?.messages?.[0] || '')
	return /worker|pdf\.worker|Failed to fetch dynamically imported module/i.test(msg)
}

async function openPdfDocument(url) {
	const loadingTask = pdfjsLib.getDocument({
		url,
		withCredentials: true,
		httpHeaders: {
			'X-Frappe-CSRF-Token': getCsrfToken(),
		},
	})
	return loadingTask.promise
}

async function loadPdf() {
	loading.value = true
	error.value = ''
	canvasRefs.value = {}
	renderTasks = {}
	try {
		await configurePdfWorker()
		const { course, lesson } = getAccessContext()
		const { token } = await fetchSecurePdfToken(props.fileUrl, {
			course,
			lesson,
		})
		const url = buildSecurePdfUrl(token)
		try {
			pdfDoc = await openPdfDocument(url)
		} catch (err) {
			if (isPdfWorkerError(err)) {
				pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CDN
				pdfDoc = await openPdfDocument(url)
			} else {
				throw err
			}
		}
		totalPages.value = pdfDoc.numPages
		loading.value = false
		await nextTick()
		await renderAllPages()
	} catch (err) {
		error.value = err?.messages?.[0] || err?.message || __('Unable to load document.')
		loading.value = false
	}
}

async function renderAllPages() {
	if (!pdfDoc || !totalPages.value) return

	await nextTick()
	pageHeights = []
	let offset = 0

	for (let pageNum = 1; pageNum <= totalPages.value; pageNum++) {
		let canvas = canvasRefs.value[pageNum]
		if (!canvas) {
			await nextTick()
			canvas = canvasRefs.value[pageNum]
		}
		if (!canvas) continue

		if (renderTasks[pageNum]) {
			try {
				renderTasks[pageNum].cancel()
			} catch {
			}
		}

		const page = await pdfDoc.getPage(pageNum)
		const viewport = page.getViewport({ scale: scale.value })
		const context = canvas.getContext('2d')
		if (!context) continue

		const outputScale = window.devicePixelRatio || 1
		canvas.width = Math.floor(viewport.width * outputScale)
		canvas.height = Math.floor(viewport.height * outputScale)
		canvas.style.width = `${viewport.width}px`
		canvas.style.height = `${viewport.height}px`
		context.setTransform(outputScale, 0, 0, outputScale, 0, 0)

		pageHeights.push(offset)
		offset += viewport.height + 16

		const task = page.render({ canvasContext: context, viewport })
		renderTasks[pageNum] = task
		await task.promise
	}
}

onMounted(() => {
	loadPdf()
})

onBeforeUnmount(() => {
	Object.values(renderTasks).forEach((task) => {
		try {
			task?.cancel?.()
		} catch {
		}
	})
	pdfDoc?.destroy?.()
})

watch(
	() => [props.fileUrl, props.course, props.lesson],
	() => {
		pdfDoc?.destroy?.()
		pdfDoc = null
		totalPages.value = 0
		canvasRefs.value = {}
		loadPdf()
	},
)
</script>

<style scoped>
.secure-pdf-viewer :deep(canvas) {
	-webkit-user-drag: none;
	user-select: none;
	pointer-events: auto;
}

.secure-pdf-scroll {
	-webkit-user-select: none;
	user-select: none;
}

@media print {
	.secure-pdf-viewer,
	.secure-pdf-viewer * {
		display: none !important;
		visibility: hidden !important;
	}
}
</style>
