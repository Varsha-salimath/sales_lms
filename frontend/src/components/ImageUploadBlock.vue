<template>
	<div
		class="lms-upload-image-block"
		:class="`lms-upload-image-block--align-${alignment}`"
		ref="rootRef"
	>
		<figure
			class="lms-upload-image-block__figure"
			:class="[figureClass, { 'lms-upload-image-block__figure--selected': selected && !readOnly }]"
			:style="figureStyle"
			@click.stop="onFigureClick"
		>
			<div class="lms-upload-image-block__inner" ref="innerRef">
				<img
					ref="imgRef"
					:src="fullSrc"
					:alt="altDisplay"
					class="lms-upload-image-block__img rounded-md border border-gray-200"
					:class="{ 'lms-upload-image-block__img--interactive': !readOnly }"
					:style="imgInlineStyle"
					loading="lazy"
					draggable="false"
					@load="onImgLoad"
					@click.stop="onImgClick"
				/>
				<template v-if="!readOnly && selected">
					<button
						v-for="h in handles"
						:key="h"
						type="button"
						class="lms-img-resize-handle"
						:class="`lms-img-resize-handle--${h}`"
						:data-handle="h"
						@pointerdown.stop.prevent="(e) => onResizePointerDown(e, h)"
					/>
				</template>
			</div>
			<figcaption
				v-if="captionText.trim()"
				class="lms-upload-image-block__caption text-sm text-gray-600 mt-1.5"
			>
				{{ captionText }}
			</figcaption>
		</figure>
		<Teleport to="body">
			<div
				v-if="!readOnly && selected"
				ref="panelRef"
				class="lms-image-inline-settings"
				:style="panelStyle"
				data-lms-image-settings-panel
				@mousedown.stop
				@click.stop
			>
			<p class="lms-image-inline-settings__title">{{ t('Image options') }}</p>
			<div class="lms-image-inline-settings__layout-btns" role="group" :aria-label="t('Image layout')">
				<button
					v-for="opt in layoutOptions"
					:key="opt.value"
					type="button"
					class="lms-image-inline-settings__layout-btn"
					:class="{ 'lms-image-inline-settings__layout-btn--active': alignment === opt.value }"
					@click="setAlignment(opt.value)"
				>
					{{ opt.label }}
				</button>
			</div>
			<label class="lms-image-inline-settings__label">{{ t('Image layout') }}</label>
			<select
				class="lms-image-inline-settings__field"
				:value="alignment"
				@change="onAlignChange"
			>
				<option value="block">{{ t('Full width') }}</option>
				<option value="center">{{ t('Centered') }}</option>
				<option value="float-left">{{ t('Float left') }}</option>
				<option value="float-right">{{ t('Float right') }}</option>
			</select>
			<label class="lms-image-inline-settings__label">{{ t('Spacing (px)') }}</label>
			<select
				class="lms-image-inline-settings__field"
				:value="String(textGapPx)"
				@change="onGapChange"
			>
				<option value="8">8</option>
				<option value="16">16</option>
				<option value="24">24</option>
			</select>
			<label class="lms-image-inline-settings__label">{{ t('Caption') }}</label>
			<input
				ref="captionInputRef"
				type="text"
				class="lms-image-inline-settings__field"
				v-model="captionDraft"
				autocomplete="off"
				@mousedown.stop
				@input="onCaptionInput"
			/>
			<label class="lms-image-inline-settings__label">{{ t('Alt text') }}</label>
			<input
				ref="altInputRef"
				type="text"
				class="lms-image-inline-settings__field"
				v-model="altDraft"
				autocomplete="off"
				@mousedown.stop
				@input="onAltInput"
			/>
			<button type="button" class="lms-image-inline-settings__btn" @click="onResetSize">
				{{ t('Reset to original size') }}
			</button>
			<p class="lms-image-inline-settings__hint">{{ layoutHint }}</p>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'

const MIN = 40

const props = defineProps({
	fileUrl: {
		type: String,
		required: true,
	},
	imageData: {
		type: Object,
		required: true,
	},
	readOnly: {
		type: Boolean,
		default: true,
	},
	onMetaChange: {
		type: Function,
		default: null,
	},
	onActivate: {
		type: Function,
		default: null,
	},
	onLayoutChange: {
		type: Function,
		default: null,
	},
	onResetSize: {
		type: Function,
		default: null,
	},
})

const handles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']
const rootRef = ref(null)
const panelRef = ref(null)
const captionInputRef = ref(null)
const altInputRef = ref(null)
const innerRef = ref(null)
const imgRef = ref(null)
const selected = ref(false)
const natural = ref({ w: 0, h: 0 })
const captionDraft = ref('')
const altDraft = ref('')

const t = (m) => (typeof window !== 'undefined' && window.__ ? window.__(m) : m)

const captionText = computed(() => String(props.imageData?.caption ?? ''))
const altText = computed(() => String(props.imageData?.alt ?? ''))
const alignment = computed(() => props.imageData?.alignment || 'block')
const textGapPx = computed(() => String(props.imageData?.text_gap ?? 16))

const layoutOptions = [
	{ value: 'block', label: 'Full' },
	{ value: 'center', label: 'Center' },
	{ value: 'float-left', label: 'Float L' },
	{ value: 'float-right', label: 'Float R' },
]

const panelStyle = ref({})

function updatePanelPosition() {
	const root = rootRef.value
	if (!root) return
	const rect = root.getBoundingClientRect()
	const panelW = 248
	const gap = 10
	const pad = 12
	const maxH = 420
	let left
	let top
	const align = alignment.value
	// Beside the image on full-width/center; below on float so we don't cover wrap text.
	if (align === 'float-left' || align === 'float-right') {
		left = rect.left
		top = rect.bottom + gap
	} else {
		const rightReserved = 340
		const maxRight = window.innerWidth - rightReserved
		left = rect.right + gap
		top = rect.top
		if (left + panelW > maxRight) {
			left = rect.left - panelW - gap
		}
	}
	if (left + panelW > window.innerWidth - pad) {
		left = window.innerWidth - panelW - pad
	}
	if (left < pad) left = pad
	if (top + maxH > window.innerHeight - pad) {
		top = Math.max(pad, window.innerHeight - maxH - pad)
	}
	panelStyle.value = {
		position: 'fixed',
		top: `${Math.round(top)}px`,
		left: `${Math.round(left)}px`,
		width: `${panelW}px`,
		zIndex: 10050,
		pointerEvents: 'auto',
	}
}

function isEventInsideImageUi(target) {
	if (!target || typeof target.closest !== 'function') return false
	if (target.closest?.('[data-lms-image-settings-panel]')) return true
	if (target.closest?.('.lms-upload-image-block__figure')) return true
	if (target.closest?.('.ce-toolbar')) return true
	return false
}

function deselectImage() {
	if (!selected.value) return
	selected.value = false
}

const layoutHint = computed(() => {
	switch (alignment.value) {
		case 'center':
			return t(
				'Centered: add Paragraph blocks above or below for text. Use Float left/right to wrap text beside the image.'
			)
		case 'float-left':
			return t('Text wraps on the right. Type in the paragraph below this image.')
		case 'float-right':
			return t(
				'Image on the right edge; spacing on the left is for wrapped text. Type in the paragraph below.'
			)
		default:
			return t('Full width fills the row. Drag blue handles to resize.')
	}
})

const fullSrc = computed(() => {
	const u = props.fileUrl || ''
	if (!u) return ''
	if (u.startsWith('http://') || u.startsWith('https://')) return encodeURI(u)
	return `${window.location.origin}${encodeURI(u)}`
})

const altDisplay = computed(() => altText.value.trim() || t('Lesson image'))

const figureClass = computed(() => {
	switch (alignment.value) {
		case 'center':
			return 'lms-upload-image-block__figure--center'
		case 'float-left':
		case 'float-right':
			return 'lms-upload-image-block__figure--in-float-column'
		default:
			return 'lms-upload-image-block__figure--block'
	}
})

const figureStyle = computed(() => {
	const gap = `${parseInt(textGapPx.value, 10) || 16}px`
	return { '--lms-img-text-gap': gap }
})

function maxContentWidth() {
	const inner = innerRef.value
	if (!inner?.isConnected) return 800
	const editor = inner.closest('.codex-editor')
	const redactor = inner.closest('.codex-editor__redactor')
	const editorW =
		editor?.getBoundingClientRect().width ||
		redactor?.getBoundingClientRect().width ||
		800
	const align = alignment.value
	if (align === 'float-left' || align === 'float-right') {
		const gap = parseInt(textGapPx.value, 10) || 16
		return Math.max(MIN, Math.floor(editorW * 0.5) - gap)
	}
	const host = inner.closest('.ce-block__content') || inner.parentElement
	return Math.max(MIN, host?.getBoundingClientRect().width || editorW)
}

function hasCustomImageSize(d) {
	const wp = d?.img_width_pct
	const wpx = d?.img_width_px
	return (
		(wp != null && wp !== '' && !Number.isNaN(Number(wp))) ||
		(wpx != null && wpx !== '' && Number(wpx) > 0)
	)
}

function applyNaturalImageStyle(st) {
	const nw = natural.value.w
	const cap = maxContentWidth()
	if (nw > 0) {
		st.width = `${Math.min(cap, nw)}px`
	} else {
		st.width = 'auto'
	}
	st.maxWidth = '100%'
	st.height = 'auto'
}

const imgInlineStyle = computed(() => {
	const d = props.imageData || {}
	const st = {
		maxWidth: '100%',
		boxSizing: 'border-box',
		display: 'block',
	}
	const wp = d.img_width_pct
	const wpx = d.img_width_px
	const hpx = d.img_height_px
	const lock = d.lock_aspect !== false
	const align = alignment.value

	if (d.img_natural && !hasCustomImageSize(d)) {
		applyNaturalImageStyle(st)
		return st
	}

	if (align === 'block' && !hasCustomImageSize(d)) {
		st.width = '100%'
		st.height = 'auto'
		return st
	}

	if (wp != null && wp !== '' && !Number.isNaN(Number(wp))) {
		const p = Math.min(100, Math.max(1, Number(wp)))
		st.width = `${p}%`
		st.height =
			hpx && Number(hpx) > 0 && !lock ? `${Number(hpx)}px` : 'auto'
		return st
	}
	if (wpx != null && Number(wpx) > 0) {
		const cap = maxContentWidth()
		st.width = `${Math.min(cap, Math.max(MIN, Number(wpx)))}px`
		if (hpx != null && Number(hpx) > 0 && !lock) {
			st.height = `${Math.max(MIN, Number(hpx))}px`
		} else {
			st.height = 'auto'
		}
		return st
	}
	if (alignment.value === 'float-left' || alignment.value === 'float-right') {
		st.width = 'auto'
		st.maxWidth = '100%'
		st.height = 'auto'
		return st
	}
	if (alignment.value === 'center') {
		st.marginInline = 'auto'
		if (wp != null && wp !== '' && !Number.isNaN(Number(wp))) {
			const p = Math.min(100, Math.max(1, Number(wp)))
			st.width = `${p}%`
			st.height =
				hpx && Number(hpx) > 0 && !lock ? `${Number(hpx)}px` : 'auto'
			return st
		}
		if (wpx != null && Number(wpx) > 0) {
			const cap = maxContentWidth()
			st.width = `${Math.min(cap, Math.max(MIN, Number(wpx)))}px`
			if (hpx != null && Number(hpx) > 0 && !lock) {
				st.height = `${Math.max(MIN, Number(hpx))}px`
			} else {
				st.height = 'auto'
			}
			return st
		}
		st.width = 'auto'
		st.maxWidth = '100%'
		st.height = 'auto'
		return st
	}
	st.width = '100%'
	st.height = 'auto'
	return st
})

function activateImage() {
	if (props.readOnly) return
	selected.value = true
	props.onActivate?.()
	nextTick(() => updatePanelPosition())
}

let panelPositionListener = null

function bindPanelPositionListeners() {
	if (panelPositionListener) return
	panelPositionListener = () => updatePanelPosition()
	window.addEventListener('scroll', panelPositionListener, true)
	window.addEventListener('resize', panelPositionListener)
}

function unbindPanelPositionListeners() {
	if (!panelPositionListener) return
	window.removeEventListener('scroll', panelPositionListener, true)
	window.removeEventListener('resize', panelPositionListener)
	panelPositionListener = null
}

function onFigureClick(e) {
	if (props.readOnly) return
	if (
		selected.value &&
		!e.target.closest('.lms-img-resize-handle')
	) {
		deselectImage()
		return
	}
	activateImage()
}

function setAlignment(value) {
	props.onLayoutChange?.({ alignment: value })
}

function onAlignChange(e) {
	setAlignment(e.target.value)
}

function onGapChange(e) {
	props.onLayoutChange?.({ text_gap: e.target.value })
}

function syncDraftsFromProps() {
	const cap = document.activeElement === captionInputRef.value
	const alt = document.activeElement === altInputRef.value
	if (!cap) captionDraft.value = String(props.imageData?.caption ?? '')
	if (!alt) altDraft.value = String(props.imageData?.alt ?? '')
}

function onCaptionInput() {
	props.onLayoutChange?.({ caption: captionDraft.value })
}

function onAltInput() {
	props.onLayoutChange?.({ alt: altDraft.value })
}

function onResetSize() {
	props.onResetSize?.()
}

function onImgClick() {
	onFigureClick()
}

function onImgLoad() {
	const im = imgRef.value
	if (!im) return
	natural.value = { w: im.naturalWidth || 0, h: im.naturalHeight || 0 }
}

function emitMeta(patch) {
	props.onMetaChange?.(patch)
}

function onResizePointerDown(e, handle) {
	if (props.readOnly) return
	const im = imgRef.value
	if (!e.isPrimary || !im) return
	const rect = im.getBoundingClientRect()
	const l0 = rect.left
	const t0 = rect.top
	const r0 = rect.right
	const b0 = rect.bottom
	const p0x = e.clientX
	const p0y = e.clientY
	const maxW = maxContentWidth()
	const ratio =
		natural.value.w && natural.value.h
			? natural.value.w / natural.value.h
			: rect.width / Math.max(rect.height, 1)

	const onMove = (ev) => {
		if (!ev.isPrimary) return
		const dx = ev.clientX - p0x
		const dy = ev.clientY - p0y
		let l = l0
		let t = t0
		let r = r0
		let b = b0
		switch (handle) {
			case 'nw':
				l = l0 + dx
				t = t0 + dy
				break
			case 'n':
				t = t0 + dy
				break
			case 'ne':
				r = r0 + dx
				t = t0 + dy
				break
			case 'e':
				r = r0 + dx
				break
			case 'se':
				r = r0 + dx
				b = b0 + dy
				break
			case 's':
				b = b0 + dy
				break
			case 'sw':
				l = l0 + dx
				b = b0 + dy
				break
			case 'w':
				l = l0 + dx
				break
			default:
				return
		}
		let nw = Math.max(MIN, Math.min(maxW, r - l))
		let nh = Math.max(MIN, b - t)
		const shiftFree = ev.shiftKey
		const lock = props.imageData?.lock_aspect !== false
		if (lock && !shiftFree && ratio > 0) {
			if (handle === 'n' || handle === 's') {
				nw = nh * ratio
				nw = Math.min(maxW, Math.max(MIN, nw))
				nh = nw / ratio
			} else {
				nh = nw / ratio
				nh = Math.max(MIN, nh)
				nw = Math.min(maxW, Math.max(MIN, nh * ratio))
			}
		}
		if (lock && !shiftFree) {
			emitMeta({
				img_width_px: Math.round(nw),
				img_height_px: null,
				img_width_pct: null,
			})
		} else {
			emitMeta({
				img_width_px: Math.round(nw),
				img_height_px: Math.round(nh),
				img_width_pct: null,
			})
		}
	}

	const onUp = (ev) => {
		if (!ev.isPrimary) return
		document.removeEventListener('pointermove', onMove)
		document.removeEventListener('pointerup', onUp)
	}

	document.addEventListener('pointermove', onMove)
	document.addEventListener('pointerup', onUp)
}

function onDocPointerDown(ev) {
	if (props.readOnly || !selected.value) return
	if (isEventInsideImageUi(ev.target)) return
	deselectImage()
}

function onEditorPointerDown(ev) {
	if (props.readOnly || !selected.value) return
	const root = rootRef.value
	if (!root) return
	const editor = root.closest('.codex-editor')
	if (!editor?.contains(ev.target)) return
	if (isEventInsideImageUi(ev.target)) return
	const myBlock = root.closest('.ce-block')
	const clickBlock = ev.target.closest?.('.ce-block')
	if (clickBlock && myBlock && clickBlock !== myBlock) {
		deselectImage()
	}
}

function onDocKeyDown(ev) {
	if (props.readOnly || !selected.value) return
	if (ev.key === 'Escape') {
		ev.preventDefault()
		deselectImage()
	}
}

watch(selected, (on) => {
	if (on) {
		nextTick(() => {
			updatePanelPosition()
			bindPanelPositionListeners()
		})
	} else {
		unbindPanelPositionListeners()
	}
})

watch(alignment, () => {
	if (selected.value) nextTick(() => updatePanelPosition())
})

watch(
	() => [props.imageData?.caption, props.imageData?.alt],
	() => syncDraftsFromProps()
)

watch(
	() => props.readOnly,
	(ro) => {
		if (ro) selected.value = false
	}
)

let editorEl = null

onMounted(() => {
	syncDraftsFromProps()
	document.addEventListener('pointerdown', onDocPointerDown, true)
	document.addEventListener('keydown', onDocKeyDown, true)
	editorEl = rootRef.value?.closest('.codex-editor') || null
	editorEl?.addEventListener('mousedown', onEditorPointerDown, true)
})

onBeforeUnmount(() => {
	document.removeEventListener('pointerdown', onDocPointerDown, true)
	document.removeEventListener('keydown', onDocKeyDown, true)
	editorEl?.removeEventListener('mousedown', onEditorPointerDown, true)
	editorEl = null
	unbindPanelPositionListeners()
})
</script>

<style scoped>
.lms-upload-image-block {
	position: relative;
	z-index: 1;
}

.lms-image-inline-settings {
	padding: 0.75rem;
	border-radius: 0.5rem;
	border: 1px solid theme('colors.gray.200');
	background: white;
	box-shadow: 0 8px 24px rgb(0 0 0 / 0.15);
	font-size: 0.875rem;
	max-height: min(70vh, 420px);
	overflow-y: auto;
	pointer-events: auto;
}

.lms-image-inline-settings__layout-btns {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 0.35rem;
	margin-bottom: 0.5rem;
}

.lms-image-inline-settings__layout-btn {
	padding: 0.35rem 0.5rem;
	border-radius: 0.375rem;
	border: 1px solid theme('colors.gray.200');
	background: theme('colors.gray.50');
	font-size: 0.6875rem;
	font-weight: 500;
	cursor: pointer;
}

.lms-image-inline-settings__layout-btn--active {
	border-color: theme('colors.blue.500');
	background: theme('colors.blue.50');
	color: theme('colors.blue.700');
}

.lms-image-inline-settings__layout-btn:hover {
	background: theme('colors.gray.100');
}

.lms-image-inline-settings__title {
	margin: 0 0 0.5rem;
	font-size: 0.75rem;
	font-weight: 600;
	color: theme('colors.gray.700');
}

.lms-image-inline-settings__label {
	display: block;
	margin: 0.5rem 0 0.25rem;
	font-size: 0.6875rem;
	font-weight: 500;
	color: theme('colors.gray.500');
}

.lms-image-inline-settings__field {
	display: block;
	width: 100%;
	min-height: 2rem;
	margin-bottom: 0.125rem;
	padding: 0.375rem 0.5rem;
	border-radius: 0.375rem;
	border: 1px solid theme('colors.gray.200');
	font-size: 0.8125rem;
}

.lms-image-inline-settings__btn {
	display: block;
	width: 100%;
	margin-top: 0.5rem;
	padding: 0.5rem 0.75rem;
	border-radius: 0.375rem;
	border: 1px solid theme('colors.gray.200');
	background: theme('colors.gray.50');
	font-size: 0.8125rem;
	font-weight: 500;
	cursor: pointer;
}

.lms-image-inline-settings__btn:hover {
	background: theme('colors.gray.100');
}

.lms-image-inline-settings__hint {
	margin: 0.5rem 0 0;
	font-size: 0.6875rem;
	line-height: 1.4;
	color: theme('colors.gray.500');
}


.lms-upload-image-block__figure {
	margin: 0;
	position: relative;
	cursor: pointer;
}

.lms-upload-image-block__inner {
	position: relative;
	display: inline-block;
	max-width: 100%;
	vertical-align: top;
}

.lms-upload-image-block__figure--block .lms-upload-image-block__inner {
	display: block;
	width: 100%;
}

/* Float / center: inner must hug the image width so resize handles stay on the image, not the column edge */
.lms-upload-image-block__figure--in-float-column .lms-upload-image-block__inner {
	display: block;
	width: fit-content;
	max-width: 100%;
}

.lms-upload-image-block__figure--center {
	display: flex;
	flex-direction: column;
	align-items: center;
	width: 100%;
}

.lms-upload-image-block__figure--center .lms-upload-image-block__inner {
	display: block;
	margin-inline: auto;
	max-width: 100%;
	width: fit-content;
}

.lms-upload-image-block__img--interactive {
	cursor: pointer;
}

.lms-upload-image-block__figure--block .lms-upload-image-block__img {
	display: block;
	width: 100%;
	height: auto;
}

.lms-upload-image-block__figure--in-float-column .lms-upload-image-block__img {
	display: block;
	width: auto;
	max-width: 100%;
	height: auto;
}

.lms-upload-image-block__figure--center .lms-upload-image-block__img {
	display: block;
	max-width: 100%;
	height: auto;
	margin-inline: auto;
}

.lms-upload-image-block__caption {
	display: block;
	width: 100%;
	max-width: 100%;
	word-break: break-word;
	line-height: 1.4;
}

.lms-upload-image-block__figure--in-float-column .lms-upload-image-block__caption,
.lms-upload-image-block__figure--center .lms-upload-image-block__caption {
	max-width: 100%;
}

.lms-upload-image-block__figure--selected .lms-upload-image-block__img {
	outline: 2px solid theme('colors.blue.500');
	outline-offset: 2px;
}

.lms-img-resize-handle {
	position: absolute;
	width: 10px;
	height: 10px;
	padding: 0;
	margin: 0;
	border: 2px solid theme('colors.blue.500');
	background: white;
	border-radius: 2px;
	z-index: 4;
	box-sizing: border-box;
	touch-action: none;
}

.lms-img-resize-handle--nw {
	top: -5px;
	left: -5px;
	cursor: nwse-resize;
}
.lms-img-resize-handle--n {
	top: -5px;
	left: 50%;
	transform: translateX(-50%);
	cursor: ns-resize;
}
.lms-img-resize-handle--ne {
	top: -5px;
	right: -5px;
	cursor: nesw-resize;
}
.lms-img-resize-handle--e {
	top: 50%;
	right: -5px;
	transform: translateY(-50%);
	cursor: ew-resize;
}
.lms-img-resize-handle--se {
	bottom: -5px;
	right: -5px;
	cursor: nwse-resize;
}
.lms-img-resize-handle--s {
	bottom: -5px;
	left: 50%;
	transform: translateX(-50%);
	cursor: ns-resize;
}
.lms-img-resize-handle--sw {
	bottom: -5px;
	left: -5px;
	cursor: nesw-resize;
}
.lms-img-resize-handle--w {
	top: 50%;
	left: -5px;
	transform: translateY(-50%);
	cursor: ew-resize;
}
</style>
