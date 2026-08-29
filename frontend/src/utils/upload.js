import AudioBlock from '@/components/AudioBlock.vue'
import VideoBlock from '@/components/VideoBlock.vue'
import ImageUploadBlock from '@/components/ImageUploadBlock.vue'
import SecurePdfViewer from '@/components/SecurePdfViewer.vue'
import UploadPlugin from '@/components/UploadPlugin.vue'
import { getLessonPdfContext } from '@/utils/lessonPdfContext'
import { h, createApp, reactive, ref } from 'vue'
import { Upload as UploadIcon } from 'lucide-vue-next'
import { createDialog } from '@/utils/dialogs'
import translationPlugin from '../translation'

export class Upload {
	constructor({ data, api, readOnly, block }) {
		// Plain objects do not notify Vue children when mutated from renderSettings();
		// reactive() keeps caption/alt/alignment edits in sync with ImageUploadBlock.
		const raw = data && typeof data === 'object' ? data : {}
		this.data = reactive(raw)
		this.api = api
		this.readOnly = readOnly
		this.block = block
		this._imageVueApp = null
		this._mountedMediaKey = null
		this._notifyTimer = null
		this.wrapper = null
		this._layoutRevision = ref(0)
		this._applyImageDefaults()
	}

	_clearImageDimensions() {
		delete this.data.img_width_px
		delete this.data.img_height_px
		delete this.data.img_width_pct
		this.data.lock_aspect = true
	}

	_bumpLayoutUpdate() {
		this._layoutRevision.value += 1
		this._syncCeBlockLayoutClass()
		requestAnimationFrame(() => this._syncCeBlockLayoutClass())
	}
	_selectImageBlock() {
		if (!this.block?.id || !this.api?.blocks) return false
		this.api.toolbar?.toggleBlockSettings?.(false)
		const idx = this.api.blocks.getBlockIndex(this.block.id)
		if (idx < 0) return false
		this.api.caret?.setToBlock?.(idx, 'start', 0)
		this.api.toolbar?.open?.()
		return true
	}

	_onImageLayoutChange(patch) {
		let needsLayoutSync = false
		let focusWrapParagraph = false

		if (patch.alignment !== undefined) {
			this.data.alignment = patch.alignment
			delete this.data.img_natural
			if (patch.alignment === 'block') this._clearImageDimensions()
			needsLayoutSync = true
			const a = patch.alignment
			if (a === 'float-left' || a === 'float-right') focusWrapParagraph = true
		}
		if (patch.text_gap !== undefined) {
			this.data.text_gap = parseInt(patch.text_gap, 10) || 16
			needsLayoutSync = true
		}

		const textOnly =
			(patch.caption !== undefined || patch.alt !== undefined) &&
			!needsLayoutSync
		if (patch.caption !== undefined) this.data.caption = patch.caption
		if (patch.alt !== undefined) this.data.alt = patch.alt

		if (needsLayoutSync) {
			this._bumpLayoutUpdate()
			if (focusWrapParagraph) {
				requestAnimationFrame(() => {
					this._syncCeBlockLayoutClass()
					this._ensureWrapParagraphAfter(true)
				})
			}
			this._scheduleNotifyChange()
		} else if (textOnly) {
			this._layoutRevision.value += 1
			this._scheduleTextNotifyChange()
		}
	}

	_scheduleTextNotifyChange() {
		if (this._textNotifyTimer) clearTimeout(this._textNotifyTimer)
		this._textNotifyTimer = setTimeout(() => {
			this._textNotifyTimer = null
			this.block?.dispatchChange?.()
		}, 400)
	}

	_onImageResetSize() {
		this._clearImageDimensions()
		this.data.img_natural = true
		this._bumpLayoutUpdate()
		this._scheduleNotifyChange()
	}

	_disposeVueApp() {
		if (this._imageVueApp) {
			try {
				this._imageVueApp.unmount()
			} catch {
			}
			this._imageVueApp = null
		}
		this._mountedMediaKey = null
	}

	_scheduleNotifyChange() {
		if (this._notifyTimer) clearTimeout(this._notifyTimer)
		this._notifyTimer = setTimeout(() => {
			this._notifyTimer = null
			this.block?.dispatchChange?.()
		}, 0)
	}

	_mediaKey(file) {
		if (!file?.file_url) return ''
		return `${file.file_type || ''}:${file.file_url}`
	}

	_applyImageDefaults() {
		if (!this._isImageBlock(this.data)) return
		if (!this.data.alignment) this.data.alignment = 'block'
		if (this.data.text_gap == null || this.data.text_gap === '')
			this.data.text_gap = 16
		if (this.data.caption == null) this.data.caption = ''
		if (this.data.alt == null) this.data.alt = ''
		if (this.data.lock_aspect === undefined) this.data.lock_aspect = true
	}

	_isImageBlock(file) {
		if (!file?.file_url) return false
		const t = (file.file_type || '').toLowerCase()
		// File API / Frappe often use MIME types (image/jpeg), not just extensions.
		if (t.startsWith('image/')) return true
		if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'image'].includes(t))
			return true
		return /\.(png|jpe?g|gif|webp|svg|bmp)(\?|#|$)/i.test(file.file_url)
	}

	_getCeBlock() {
		const holder = this.block?.holder
		if (!holder) return null
		return holder.classList?.contains('ce-block')
			? holder
			: holder.closest('.ce-block')
	}

	_clearCeBlockLayoutClass() {
		const el = this._getCeBlock()
		if (!el) return
		el.style.removeProperty('--lms-img-ce-gap')
		el.classList.remove(
			'ce-block--lms-float-start',
			'ce-block--lms-float-end',
			'ce-block--lms-center',
			'ce-block--lms-block'
		)
	}

	_syncCeBlockLayoutClass() {
		this._clearCeBlockLayoutClass()
		const el = this._getCeBlock()
		if (!el || !this._isImageBlock(this.data)) return
		const a = this.data.alignment || 'block'
		const gap = `${Number(this.data.text_gap) || 16}px`
		el.style.removeProperty('width')
		el.style.removeProperty('max-width')
		if (a === 'float-left') {
			el.classList.add('ce-block--lms-float-start')
			el.style.setProperty('--lms-img-ce-gap', gap)
		} else if (a === 'float-right') {
			el.classList.add('ce-block--lms-float-end')
			el.style.setProperty('--lms-img-ce-gap', gap)
		} else if (a === 'center') {
			el.classList.add('ce-block--lms-center')
			el.style.removeProperty('float')
		} else if (a === 'block') {
			el.classList.add('ce-block--lms-block')
			el.style.removeProperty('float')
		}
	}

	_ensureWrapParagraphAfter(focus = true) {
		if (this.readOnly || !this.api?.blocks || !this.block?.id) return
		const align = this.data.alignment
		if (align !== 'float-left' && align !== 'float-right') return

		const idx = this.api.blocks.getBlockIndex(this.block.id)
		if (idx < 0) return

		const next = this.api.blocks.getBlockByIndex(idx + 1)
		if (!next || next.name !== 'paragraph') {
			this.api.blocks.insert('paragraph', { text: '' }, {}, idx + 1, focus)
			return
		}
		if (focus && this.api.caret) {
			requestAnimationFrame(() => {
				this.api.caret.setToBlock(idx + 1, 'start', 0)
			})
		}
	}

	rendered() {
		if (this._isImageBlock(this.data)) {
			requestAnimationFrame(() => {
				this._syncCeBlockLayoutClass()
				const a = this.data.alignment
				if (a === 'float-left' || a === 'float-right') {
					this._ensureWrapParagraphAfter(false)
				}
			})
		}
	}

	destroy() {
		if (this._notifyTimer) clearTimeout(this._notifyTimer)
		if (this._textNotifyTimer) clearTimeout(this._textNotifyTimer)
		this._clearCeBlockLayoutClass()
		this._disposeVueApp()
		this.wrapper = null
	}

	static get toolbox() {
		const app = createApp({
			render: () =>
				h(UploadIcon, { size: 18, strokeWidth: 1.5, color: 'black' }),
		})

		const div = document.createElement('div')
		app.mount(div)

		return {
			title: 'Upload',
			icon: div.innerHTML,
		}
	}

	static get isReadOnlySupported() {
		return true
	}

	_hintPanel(className, text) {
		const el = document.createElement('div')
		el.className = `ce-settings__lms-image-layout px-3 py-3 font-sans text-sm text-ink-gray-5 ${className}`
		el.textContent = text
		return el
	}

	renderSettings() {
		const empty = document.createElement('div')
		if (this.readOnly) return empty
		if (!this.data?.file_url) {
			return this._hintPanel('', 'Upload a file first.')
		}
		if (!this._isImageBlock(this.data)) {
			return this._hintPanel(
				'',
				'Layout options apply to images only. Click the image to edit layout.'
			)
		}
		return this._hintPanel(
			'',
			'Click the image to change layout, caption, and alt text. Use Move up / Delete below.'
		)
	}

	render() {
		if (!this.wrapper) {
			this.wrapper = document.createElement('div')
		}

		if (this.data && this.data.file_url) {
			this.renderFile(this.data)
		} else {
			this.renderFileUploader()
		}

		return this.wrapper
	}

	_mountImageVue(file) {
		const key = this._mediaKey(file)
		if (this._imageVueApp && this._mountedMediaKey === key) {
			requestAnimationFrame(() => this._syncCeBlockLayoutClass())
			return
		}
		this._disposeVueApp()
		this.wrapper.innerHTML = ''
		this._applyImageDefaults()
		const self = this
		const layoutRevision = this._layoutRevision
		const app = createApp({
			name: 'LmsImageUploadRoot',
			setup() {
				return () => {
					layoutRevision.value
					const d = self.data
					void d.alignment
					void d.img_width_px
					void d.img_height_px
					void d.img_width_pct
					void d.img_natural
					void d.caption
					void d.alt
					return h(ImageUploadBlock, {
						fileUrl: file.file_url,
						imageData: d,
						readOnly: self.readOnly,
						onActivate: () => {
							self._selectImageBlock()
						},
						onLayoutChange: (patch) => {
							self._onImageLayoutChange(patch)
						},
						onResetSize: () => {
							self._onImageResetSize()
						},
						onMetaChange: (patch) => {
							Object.assign(self.data, patch)
							delete self.data.img_natural
							self._syncCeBlockLayoutClass()
							self._scheduleNotifyChange()
						},
					})
				}
			},
		})
		app.use(translationPlugin)
		app.mount(this.wrapper)
		this._imageVueApp = app
		this._mountedMediaKey = key
		requestAnimationFrame(() => this._syncCeBlockLayoutClass())
	}

	renderFile(file) {
		const key = this._mediaKey(file)
		const sameMedia = key && key === this._mountedMediaKey

		if (!this._isImageBlock(file)) {
			if (!sameMedia) this._disposeVueApp()
			this._clearCeBlockLayoutClass()
		}

		if (this.isVideo(file.file_type)) {
			if (sameMedia && this._imageVueApp) return
			this._disposeVueApp()
			this.wrapper.innerHTML = ''
			const app = createApp(VideoBlock, {
				file: file.file_url,
				readOnly: this.readOnly,
				quizzes: file.quizzes || [],
				saveQuizzes: (quizzes) => {
					if (this.readOnly) return
					this.data.quizzes = quizzes
				},
			})
			app.use(translationPlugin)
			app.config.globalProperties.$dialog = createDialog
			app.mount(this.wrapper)
			this._mountedMediaKey = key
			return
		}
		if (this.isAudio(file.file_type)) {
			if (sameMedia && this._imageVueApp) return
			this._disposeVueApp()
			this.wrapper.innerHTML = ''
			const app = createApp(AudioBlock, {
				file: file.file_url,
			})
			app.mount(this.wrapper)
			this._mountedMediaKey = key
			return
		}
		if (this._isPdf(file.file_type)) {
			this._mountSecurePdf(file, key)
			return
		}
		if (file.file_type == 'DOCX' || file.file_url?.endsWith('.docx')) {
			this._disposeVueApp()
			this._mountedMediaKey = key
			const fullUrl = `${window.location.origin}${encodeURI(file.file_url)}`
			this.wrapper.innerHTML = `<iframe src="https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fullUrl)}" width='100%' height='700px' class="mb-4" frameborder="0"></iframe>`
			return
		}
		if (this._isImageBlock(file)) {
			this._mountImageVue(file)
			return
		}
		this._disposeVueApp()
		this._mountedMediaKey = key
		this.wrapper.innerHTML = `<img class="mb-4" src=${encodeURI(file.file_url)} width='100%'>`
	}

	renderFileUploader() {
		this._disposeVueApp()
		this.wrapper.innerHTML = ''
		const app = createApp(UploadPlugin, {
			onFileUploaded: (file) => {
				this.data.file_url = file.file_url
				this.data.file_type = file.file_type
				this.renderFile(file)
			},
		})
		app.use(translationPlugin)
		app.mount(this.wrapper)
	}

	validate(savedData) {
		if (!savedData.file_url || !savedData.file_type) {
			return false
		}
		return true
	}

	save(blockContent) {
		const base = {
			file_url: this.data.file_url,
			file_type: this.data.file_type,
			quizzes: this.data.quizzes || [],
		}
		if (this._isImageBlock(this.data)) {
			return {
				...base,
				alignment: this.data.alignment || 'block',
				text_gap: this.data.text_gap ?? 16,
				caption: this.data.caption || '',
				alt: this.data.alt || '',
				img_width_px: this.data.img_width_px ?? null,
				img_height_px: this.data.img_height_px ?? null,
				img_width_pct: this.data.img_width_pct ?? null,
				lock_aspect: this.data.lock_aspect !== false,
			}
		}
		return base
	}

	isVideo(type) {
		return ['mov', 'mp4', 'avi', 'mkv', 'webm'].includes(type.toLowerCase())
	}

	isAudio(type) {
		return ['mp3', 'wav', 'ogg'].includes(type.toLowerCase())
	}

	_isPdf(type) {
		return type?.toUpperCase() === 'PDF'
	}

	_mountSecurePdf(file, key) {
		if (key === this._mountedMediaKey && this._imageVueApp) return
		this._disposeVueApp()
		this.wrapper.innerHTML = ''
		const { course, lesson } = getLessonPdfContext()
		const app = createApp(SecurePdfViewer, {
			fileUrl: file.file_url,
			course,
			lesson,
		})
		app.use(translationPlugin)
		app.mount(this.wrapper)
		this._imageVueApp = app
		this._mountedMediaKey = key
	}
}
