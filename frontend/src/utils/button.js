import { h, createApp } from 'vue'
import { MousePointerClick } from 'lucide-vue-next'

export class ButtonBlock {
	constructor({ data, api, readOnly }) {
		this.data = {
			label: data.label || '',
			url: data.url || '',
			bgColor: data.bgColor || '#4F46E5',
			textColor: data.textColor || '#FFFFFF',
			newTab: data.newTab !== undefined ? data.newTab : true,
		}
		this.api = api
		this.readOnly = readOnly
		this.wrapper = null
	}

	static get toolbox() {
		const app = createApp({
			render: () =>
				h(MousePointerClick, {
					size: 18,
					strokeWidth: 1.5,
					color: 'black',
				}),
		})
		const div = document.createElement('div')
		app.mount(div)

		return {
			title: 'Button',
			icon: div.innerHTML,
		}
	}

	static get isReadOnlySupported() {
		return true
	}

	render() {
		this.wrapper = document.createElement('div')
		this.wrapper.classList.add('button-block')

		if (this.readOnly) {
			this._renderPreview()
		} else {
			this._renderEditor()
		}

		return this.wrapper
	}

	_renderPreview() {
		if (!this.data.label || !this.data.url) {
			this.wrapper.innerHTML = ''
			return
		}

		const link = document.createElement('a')
		link.href = this.data.url
		link.textContent = this.data.label
		link.rel = 'noopener noreferrer'
		if (this.data.newTab) {
			link.target = '_blank'
		}
		Object.assign(link.style, {
			display: 'inline-block',
			padding: '10px 24px',
			backgroundColor: this.data.bgColor,
			color: this.data.textColor,
			borderRadius: '8px',
			textDecoration: 'none',
			fontWeight: '600',
			fontSize: '14px',
			cursor: 'pointer',
			border: 'none',
			lineHeight: '1.4',
		})

		const container = document.createElement('div')
		container.style.margin = '12px 0'
		container.appendChild(link)
		this.wrapper.appendChild(container)
	}

	_renderEditor() {
		this.wrapper.innerHTML = ''

		const form = document.createElement('div')
		Object.assign(form.style, {
			border: '1px solid #E5E7EB',
			borderRadius: '8px',
			padding: '16px',
			marginBottom: '8px',
			backgroundColor: '#F9FAFB',
		})

		form.innerHTML = `
			<div style="display:flex; align-items:center; gap:8px; margin-bottom:12px; font-weight:600; font-size:14px; color:#374151;">
				<span>Button Block</span>
			</div>

			<div style="margin-bottom:10px;">
				<label style="display:block; font-size:12px; font-weight:500; color:#6B7280; margin-bottom:4px;">Button Label</label>
				<input type="text" class="btn-label-input" value="${this._esc(this.data.label)}"
					placeholder="e.g. Submit, Next Step, Download"
					style="width:100%; padding:8px 10px; border:1px solid #D1D5DB; border-radius:6px; font-size:14px; outline:none;" />
			</div>

			<div style="margin-bottom:10px;">
				<label style="display:block; font-size:12px; font-weight:500; color:#6B7280; margin-bottom:4px;">Button URL</label>
				<input type="url" class="btn-url-input" value="${this._esc(this.data.url)}"
					placeholder="https://example.com"
					style="width:100%; padding:8px 10px; border:1px solid #D1D5DB; border-radius:6px; font-size:14px; outline:none;" />
				<span class="btn-url-error" style="color:#EF4444; font-size:12px; display:none; margin-top:2px;">Please enter a valid URL</span>
			</div>

			<div style="display:flex; gap:16px; margin-bottom:10px; flex-wrap:wrap;">
				<div>
					<label style="display:block; font-size:12px; font-weight:500; color:#6B7280; margin-bottom:4px;">Background Colour</label>
					<input type="color" class="btn-bg-input" value="${this.data.bgColor}"
						style="width:48px; height:36px; border:1px solid #D1D5DB; border-radius:6px; cursor:pointer; padding:2px;" />
				</div>
				<div>
					<label style="display:block; font-size:12px; font-weight:500; color:#6B7280; margin-bottom:4px;">Text Colour</label>
					<input type="color" class="btn-text-input" value="${this.data.textColor}"
						style="width:48px; height:36px; border:1px solid #D1D5DB; border-radius:6px; cursor:pointer; padding:2px;" />
				</div>
			</div>

			<div style="margin-bottom:12px;">
				<label style="display:block; font-size:12px; font-weight:500; color:#6B7280; margin-bottom:4px;">Open in</label>
				<div style="display:flex; gap:16px;">
					<label style="display:flex; align-items:center; gap:4px; font-size:13px; cursor:pointer;">
						<input type="radio" name="btn-target-${this.api.blocks.getCurrentBlockIndex()}" class="btn-target-new" value="true" ${this.data.newTab ? 'checked' : ''} />
						New Tab
					</label>
					<label style="display:flex; align-items:center; gap:4px; font-size:13px; cursor:pointer;">
						<input type="radio" name="btn-target-${this.api.blocks.getCurrentBlockIndex()}" class="btn-target-same" value="false" ${!this.data.newTab ? 'checked' : ''} />
						Same Tab
					</label>
				</div>
			</div>

			<div class="btn-preview-area" style="padding:12px; background:#fff; border:1px dashed #D1D5DB; border-radius:6px; text-align:left;">
				<span style="font-size:11px; color:#9CA3AF; display:block; margin-bottom:8px;">Preview</span>
				<a class="btn-preview-link" href="javascript:void(0)"
					style="display:inline-block; padding:10px 24px; background-color:${this.data.bgColor}; color:${this.data.textColor}; border-radius:8px; text-decoration:none; font-weight:600; font-size:14px; cursor:default; line-height:1.4;">
					${this._esc(this.data.label) || 'Button'}
				</a>
			</div>
		`

		this.wrapper.appendChild(form)

		const labelInput = form.querySelector('.btn-label-input')
		const urlInput = form.querySelector('.btn-url-input')
		const bgInput = form.querySelector('.btn-bg-input')
		const textInput = form.querySelector('.btn-text-input')
		const targetNew = form.querySelector('.btn-target-new')
		const targetSame = form.querySelector('.btn-target-same')
		const preview = form.querySelector('.btn-preview-link')
		const urlError = form.querySelector('.btn-url-error')

		const updatePreview = () => {
			preview.textContent = this.data.label || 'Button'
			preview.style.backgroundColor = this.data.bgColor
			preview.style.color = this.data.textColor
		}

		labelInput.addEventListener('input', (e) => {
			this.data.label = e.target.value
			updatePreview()
		})

		urlInput.addEventListener('input', (e) => {
			this.data.url = e.target.value
			urlError.style.display = this._isValidUrl(this.data.url)
				? 'none'
				: 'block'
		})

		bgInput.addEventListener('input', (e) => {
			this.data.bgColor = e.target.value
			updatePreview()
		})

		textInput.addEventListener('input', (e) => {
			this.data.textColor = e.target.value
			updatePreview()
		})

		targetNew.addEventListener('change', () => {
			this.data.newTab = true
		})
		targetSame.addEventListener('change', () => {
			this.data.newTab = false
		})
	}

	validate(savedData) {
		if (!savedData.label || !savedData.label.trim()) return false
		if (!savedData.url || !this._isValidUrl(savedData.url)) return false
		return true
	}

	save() {
		return {
			label: this.data.label,
			url: this.data.url,
			bgColor: this.data.bgColor,
			textColor: this.data.textColor,
			newTab: this.data.newTab,
		}
	}

	_isValidUrl(string) {
		if (!string) return false
		try {
			const url = new URL(string)
			return ['http:', 'https:', 'mailto:'].includes(url.protocol)
		} catch {
			return false
		}
	}

	_esc(str) {
		if (!str) return ''
		const div = document.createElement('div')
		div.textContent = str
		return div.innerHTML
	}
}
