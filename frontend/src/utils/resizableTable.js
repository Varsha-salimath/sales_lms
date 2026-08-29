/**
 * Editor.js table tool with column (fr) and row (min-height) drag resize.
 * Extends @editorjs/table; persists colWidths (relative fr weights) and rowHeights (min-height px).
 */
import BaseTable from '@editorjs/table'

const MIN_COL_PX = 40
const MIN_ROW_PX = 24
const CSS = {
	wrapper: 'tc-wrap',
	table: 'tc-table',
	row: 'tc-row',
	cell: 'tc-cell',
}

function equalWeights(n) {
	return Array.from({ length: n }, () => 1)
}

export default class ResizableTable extends BaseTable {
	constructor(opts) {
		super(opts)
		const d = opts.data || {}
		this.block = opts.block
		this.data.colWidths = Array.isArray(d.colWidths) ? [...d.colWidths] : null
		this.data.rowHeights = Array.isArray(d.rowHeights) ? [...d.rowHeights] : null
		this._disposeResize = null
		this._mo = null
		this._colResizeActiveIndex = null
		this._rowResizeActiveIndex = null
		this._resizeLayer = null
	}

	save() {
		this._teardownResizeUi()
		const out = this._collectTableData()
		if (!this.readOnly) {
			requestAnimationFrame(() => this._installResizeUi())
		}
		return out
	}
	_collectTableData() {
		const tableEl = this._getTableEl()
		const content = []
		if (tableEl) {
			tableEl.querySelectorAll(`.${CSS.row}`).forEach((row) => {
				const cells = Array.from(row.querySelectorAll(`.${CSS.cell}`))
				if (!cells.every((cell) => !cell.textContent.trim())) {
					content.push(cells.map((cell) => cell.innerHTML))
				}
			})
		}
		const out = {
			withHeadings: !!this.data.withHeadings,
			stretched: !!this.data.stretched,
			content,
		}
		if (Array.isArray(this.data.colWidths) && this.data.colWidths.length) {
			const first = this.data.colWidths[0]
			const uniform = this.data.colWidths.every(
				(x) => Math.abs(x - first) < 1e-4
			)
			if (!uniform) out.colWidths = [...this.data.colWidths]
		}
		if (
			Array.isArray(this.data.rowHeights) &&
			this.data.rowHeights.some((h) => Number(h) > 0)
		) {
			out.rowHeights = [...this.data.rowHeights]
		}
		return out
	}

	_rowCount() {
		const tableEl = this._getTableEl()
		if (!tableEl) return 0
		return tableEl.querySelectorAll(`.${CSS.row}`).length
	}

	renderSettings() {
		const wrap = document.createElement('div')
		if (this.readOnly) return wrap
		const btn = document.createElement('button')
		btn.type = 'button'
		btn.textContent = 'Reset row heights'
		btn.className =
			'w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm font-medium text-ink-gray-8 hover:bg-surface-gray-2'
		btn.addEventListener('click', (e) => {
			e.preventDefault()
			this._resetAllRowHeights()
		})
		wrap.appendChild(btn)
		return wrap
	}

	_resetAllRowHeights() {
		const engine = this._getEngine()
		if (!engine) return
		const n = this._rowCount()
		this.data.rowHeights = Array(n).fill(0)
		for (let i = 1; i <= n; i++) {
			this._setRowMinHeight(engine.getRow(i), 0)
		}
		this.block?.dispatchChange?.()
		const layer = this._resizeLayer
		const tableEl = this._getTableEl()
		if (layer && tableEl) {
			this._renderResizeHandles(layer, tableEl, engine)
		}
	}

	rendered() {
		if (typeof super.rendered === 'function') super.rendered()
		this._syncDimensionsFromData()
		if (!this.readOnly) {
			requestAnimationFrame(() => this._installResizeUi())
		} else {
			this._teardownResizeUi()
		}
	}

	destroy() {
		this._teardownResizeUi()
		super.destroy()
	}

	_getEngine() {
		return this.table
	}

	_getTableEl() {
		return this._getEngine()?.table ?? null
	}
	_getWrapperEl() {
		return this._getEngine()?.wrapper ?? null
	}

	_syncResizeLayerBox(layer, wrapperEl, tableEl) {
		if (!layer || !wrapperEl || !tableEl) return
		const tableRect = tableEl.getBoundingClientRect()
		const wrapRect = wrapperEl.getBoundingClientRect()
		layer.style.left = `${tableRect.left - wrapRect.left}px`
		layer.style.top = `${tableRect.top - wrapRect.top}px`
		layer.style.width = `${tableRect.width}px`
		layer.style.height = `${tableRect.height}px`
	}

	_normalizeColWeights() {
		const engine = this._getEngine()
		const tableEl = this._getTableEl()
		if (!engine || !tableEl) return
		const n = engine.numberOfColumns
		if (!n) return
		let w = this.data.colWidths
		if (!Array.isArray(w) || w.length === 0) {
			w = equalWeights(n)
		} else if (w.length < n) {
			w = [...w, ...equalWeights(n - w.length)]
		} else if (w.length > n) {
			w = w.slice(0, n)
		}
		this.data.colWidths = w.map((x) => Math.max(0.0001, Number(x) || 0.0001))
	}

	_applyColumnTemplate() {
		const engine = this._getEngine()
		const tableEl = this._getTableEl()
		if (!engine || !tableEl) return
		this._normalizeColWeights()
		const w = this.data.colWidths
		const tpl = w.map((wt) => `minmax(${MIN_COL_PX}px, ${wt}fr)`).join(' ')
		tableEl.querySelectorAll(`.${CSS.row}`).forEach((row) => {
			row.style.gridTemplateColumns = tpl
		})
	}

	_getNaturalRowHeight(rowEl) {
		if (!rowEl) return MIN_ROW_PX
		const tableEl = rowEl.closest(`.${CSS.table}`)
		const width = rowEl.getBoundingClientRect().width || tableEl?.offsetWidth
		if (!width) return MIN_ROW_PX

		const clone = rowEl.cloneNode(true)
		clone.style.cssText = [
			'position:absolute',
			'left:-10000px',
			'top:0',
			'visibility:hidden',
			'pointer-events:none',
			'height:auto',
			'min-height:0',
			`width:${width}px`,
		].join(';')
		;(tableEl || rowEl.parentElement).appendChild(clone)
		const h = clone.getBoundingClientRect().height
		clone.remove()
		return Math.max(MIN_ROW_PX, Math.ceil(h))
	}

	_setRowMinHeight(rowEl, px) {
		if (!rowEl) return
		if (px == null || px <= 0) {
			rowEl.style.removeProperty('min-height')
			rowEl.style.removeProperty('height')
		} else {
			rowEl.style.minHeight = `${Math.max(MIN_ROW_PX, px)}px`
			rowEl.style.removeProperty('height')
		}
	}

	_applyRowHeights() {
		const engine = this._getEngine()
		const tableEl = this._getTableEl()
		if (!engine || !tableEl) return
		if (!Array.isArray(this.data.rowHeights)) return
		const n = this._rowCount()
		while (this.data.rowHeights.length < n) this.data.rowHeights.push(0)
		if (this.data.rowHeights.length > n) this.data.rowHeights.length = n
		const rh = this.data.rowHeights
		const dragging = this._rowResizeActiveIndex != null

		for (let i = 1; i <= n; i++) {
			const row = engine.getRow(i)
			if (!row) continue
			const h = rh[i - 1]
			if (h != null && Number(h) > 0) {
				const px = Math.max(MIN_ROW_PX, Number(h))
				if (!dragging) {
					const natural = this._getNaturalRowHeight(row)
					if (px <= natural + 2) {
						this._setRowMinHeight(row, 0)
						rh[i - 1] = 0
						continue
					}
				}
				this._setRowMinHeight(row, px)
			} else {
				this._setRowMinHeight(row, 0)
			}
		}
	}

	_syncDimensionsFromData() {
		this._normalizeColWeights()
		this._applyColumnTemplate()
		this._applyRowHeights()
	}

	_teardownResizeUi() {
		if (this._disposeResize) {
			this._disposeResize()
			this._disposeResize = null
		}
		if (this._mo) {
			this._mo.disconnect()
			this._mo = null
		}
		const wrapperEl = this._getWrapperEl()
		if (wrapperEl) {
			wrapperEl
				.querySelectorAll('.lms-table-resize-layer')
				.forEach((n) => n.remove())
		}
		this._resizeLayer = null
		this._colResizeActiveIndex = null
		this._rowResizeActiveIndex = null
	}

	_installResizeUi() {
		this._teardownResizeUi()
		const tableEl = this._getTableEl()
		const wrapperEl = this._getWrapperEl()
		const engine = this._getEngine()
		if (!tableEl || !wrapperEl || !engine || this.readOnly) return

		const layer = document.createElement('div')
		layer.className = 'lms-table-resize-layer'
		layer.style.cssText =
			'position:absolute;pointer-events:none;z-index:3;overflow:visible;'
		wrapperEl.appendChild(layer)
		this._resizeLayer = layer

		const refresh = () => {
			this._normalizeColWeights()
			this._applyColumnTemplate()
			this._applyRowHeights()
			this._syncResizeLayerBox(layer, wrapperEl, tableEl)
			this._renderResizeHandles(layer, tableEl, engine)
		}

		let debounceTimer = null
		const scheduleRefresh = () => {
			if (this._rowResizeActiveIndex != null) return
			clearTimeout(debounceTimer)
			debounceTimer = setTimeout(() => {
				debounceTimer = null
				requestAnimationFrame(refresh)
			}, 150)
		}

		this._mo = new MutationObserver(() => scheduleRefresh())
		this._mo.observe(tableEl, { childList: true, subtree: true })

		const onWin = () => refresh()
		window.addEventListener('resize', onWin)
		refresh()

		this._disposeResize = () => {
			clearTimeout(debounceTimer)
			window.removeEventListener('resize', onWin)
		}
	}

	_renderResizeHandles(layer, tableEl, engine) {
		if (!layer || !tableEl || !engine) return
		layer.innerHTML = ''
		const rect = tableEl.getBoundingClientRect()
		if (!rect.width) return

		const nCols = engine.numberOfColumns
		const nRows = this._rowCount()

		for (let i = 1; i < nCols; i++) {
			const c1 = engine.getCell(1, i)
			if (!c1) continue
			const r = c1.getBoundingClientRect()
			const x = r.right - tableEl.getBoundingClientRect().left
			const h = document.createElement('div')
			h.className = 'lms-table-col-resizer'
			h.style.pointerEvents = 'auto'
			h.dataset.colIndex = String(i)
			h.style.top = '0'
			h.style.height = `${rect.height}px`
			h.style.left = `${x - 3}px`
			h.style.width = '6px'
			h.addEventListener('pointerdown', (e) =>
				this._onColResizePointerDown(e, i, tableEl, engine)
			)
			if (this._colResizeActiveIndex === i) {
				h.classList.add('lms-table-resizer--active')
			}
			layer.appendChild(h)
		}

		for (let r = 1; r <= nRows; r++) {
			const rowEl = engine.getRow(r)
			if (!rowEl) continue
			const br = rowEl.getBoundingClientRect()
			const tr = tableEl.getBoundingClientRect()
			const y = br.bottom - tr.top
			const el = document.createElement('div')
			el.className = 'lms-table-row-resizer'
			el.style.pointerEvents = 'auto'
			el.dataset.rowIndex = String(r)
			el.style.left = '0'
			el.style.width = `${rect.width}px`
			el.style.top = `${y - 3}px`
			el.style.height = '6px'
			el.title = 'Drag to resize row · Double-click to reset'
			el.addEventListener('pointerdown', (e) =>
				this._onRowResizePointerDown(e, r, engine)
			)
			el.addEventListener('dblclick', (e) => {
				e.preventDefault()
				e.stopPropagation()
				if (!Array.isArray(this.data.rowHeights)) return
				this.data.rowHeights[r - 1] = 0
				this._setRowMinHeight(rowEl, 0)
				this.block?.dispatchChange?.()
				this._renderResizeHandles(layer, tableEl, engine)
			})
			if (this._rowResizeActiveIndex === r) {
				el.classList.add('lms-table-resizer--active')
			}
			layer.appendChild(el)
		}
	}

	_onColResizePointerDown(e, leftColIndex, tableEl, engine) {
		if (e.button !== 0) return
		e.preventDefault()
		e.stopPropagation()
		this._normalizeColWeights()
		const W = Math.max(tableEl.getBoundingClientRect().width, 1)
		const weights = [...this.data.colWidths]
		const sumFr = weights.reduce((a, b) => a + b, 0)
		const startPx = weights.map((fr) => (fr / sumFr) * W)
		const i = leftColIndex - 1
		const startX = e.clientX
		this._colResizeActiveIndex = leftColIndex

		const finish = () => {
			this._colResizeActiveIndex = null
			document.removeEventListener('pointermove', onMove)
			document.removeEventListener('pointerup', finish)
			document.removeEventListener('pointercancel', finish)
			const layer = this._resizeLayer
			if (layer) this._renderResizeHandles(layer, tableEl, engine)
		}

		const onMove = (ev) => {
			const dx = ev.clientX - startX
			const px = [...startPx]
			const S = startPx[i] + startPx[i + 1]
			let a = startPx[i] + dx
			let b = S - a
			if (a < MIN_COL_PX) {
				a = MIN_COL_PX
				b = S - a
			}
			if (b < MIN_COL_PX) {
				b = MIN_COL_PX
				a = S - b
			}
			px[i] = a
			px[i + 1] = b
			this.data.colWidths = px.map((p) => Math.max(MIN_COL_PX, p))
			this._applyColumnTemplate()
			this.block?.dispatchChange?.()
			const layer = this._resizeLayer
			if (layer) this._renderResizeHandles(layer, tableEl, engine)
		}
		document.addEventListener('pointermove', onMove)
		document.addEventListener('pointerup', finish)
		document.addEventListener('pointercancel', finish)
	}

	_onRowResizePointerDown(e, rowIndex, engine) {
		if (e.button !== 0) return
		e.preventDefault()
		e.stopPropagation()
		const n = this._rowCount()
		if (!Array.isArray(this.data.rowHeights)) this.data.rowHeights = Array(n).fill(0)
		if (this.data.rowHeights.length < n) {
			this.data.rowHeights = [
				...this.data.rowHeights,
				...Array(n - this.data.rowHeights.length).fill(0),
			]
		}
		const rowEl = engine.getRow(rowIndex)
		if (!rowEl) return
		const startY = e.clientY
		const naturalMin = this._getNaturalRowHeight(rowEl)
		const prevMin =
			parseFloat(rowEl.style.minHeight) ||
			rowEl.getBoundingClientRect().height ||
			naturalMin
		this._rowResizeActiveIndex = rowIndex
		const idx = rowIndex - 1

		const finish = () => {
			this._rowResizeActiveIndex = null
			document.removeEventListener('pointermove', onMove)
			document.removeEventListener('pointerup', finish)
			document.removeEventListener('pointercancel', finish)
			const tableEl = this._getTableEl()
			const layer = this._resizeLayer
			if (layer && tableEl) this._renderResizeHandles(layer, tableEl, engine)
			this._applyRowHeights()
		}

		const onMove = (ev) => {
			const dy = ev.clientY - startY
			const next = Math.max(MIN_ROW_PX, prevMin + dy)
			if (next <= naturalMin + 2) {
				this.data.rowHeights[idx] = 0
				this._setRowMinHeight(rowEl, 0)
			} else {
				const px = Math.round(next)
				this.data.rowHeights[idx] = px
				this._setRowMinHeight(rowEl, px)
			}
			this.block?.dispatchChange?.()
			const tableEl = this._getTableEl()
			const layer = this._resizeLayer
			if (layer && tableEl) this._renderResizeHandles(layer, tableEl, engine)
		}
		document.addEventListener('pointermove', onMove)
		document.addEventListener('pointerup', finish)
		document.addEventListener('pointercancel', finish)
	}
}
