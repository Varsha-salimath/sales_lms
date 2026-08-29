/**
 * SCORM 1.2 / 2004 CMI bridge for Genius player.
 * Attaches window.API and window.API_1484_11.
 *
 * Mid-lesson % is taken from cmi.progress_measure when present; otherwise
 * inferred from cmi.objectives.* completion and/or suspend_data payloads
 * (Articulate Rise often reports internal % without progress_measure).
 */

function parseTimeToSeconds(value) {
	if (value == null || value === '') return null
	if (typeof value === 'number' && !Number.isNaN(value)) return value

	const str = String(value).trim()
	const iso = str.match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$/i)
	if (iso) {
		const hours = parseFloat(iso[1] || 0)
		const minutes = parseFloat(iso[2] || 0)
		const seconds = parseFloat(iso[3] || 0)
		return hours * 3600 + minutes * 60 + seconds
	}

	const parts = str.split(':')
	if (parts.length >= 3) {
		const hours = parseFloat(parts[0]) || 0
		const minutes = parseFloat(parts[1]) || 0
		const seconds = parseFloat(parts[2]) || 0
		return hours * 3600 + minutes * 60 + seconds
	}

	const asNumber = parseFloat(str)
	return Number.isNaN(asNumber) ? null : asNumber
}

function normalizeProgressMeasure(value) {
	if (value == null || value === '') return null
	let n = parseFloat(value)
	if (Number.isNaN(n)) return null
	if (n > 1) n = n / 100
	return Math.min(1, Math.max(0, n))
}

function extractProgressFromSuspendData(raw) {
	if (!raw || typeof raw !== 'string') return null

	// Direct JSON
	try {
		const parsed = JSON.parse(raw)
		const fromObj = pickProgressFromObject(parsed)
		if (fromObj != null) return fromObj
	} catch {
		/* not plain JSON */
	}

	// Embedded JSON object inside LZW / packed strings
	const objectMatch = raw.match(/\{[\s\S]{8,8000}\}/)
	if (objectMatch) {
		try {
			const parsed = JSON.parse(objectMatch[0])
			const fromObj = pickProgressFromObject(parsed)
			if (fromObj != null) return fromObj
		} catch {
			/* ignore */
		}
	}

	// Common key=value / JSON fragments
	const patterns = [
		/"progress_measure"\s*:\s*([0-9.]+)/i,
		/"percentComplete"\s*:\s*([0-9.]+)/i,
		/"percent_complete"\s*:\s*([0-9.]+)/i,
		/"progress"\s*:\s*([0-9.]+)/i,
		/"completion"\s*:\s*([0-9.]+)/i,
		/"p"\s*:\s*([0-9.]+)/,
	]
	for (const re of patterns) {
		const m = raw.match(re)
		if (m) {
			const measure = normalizeProgressMeasure(m[1])
			if (measure != null) return measure
		}
	}

	// Visited/completed lesson flags: count true-like values in arrays
	const boolArray = raw.match(/\[(?:\s*(?:true|false|1|0)\s*,?){2,}\]/i)
	if (boolArray) {
		const flags = boolArray[0].match(/true|false|1|0/gi) || []
		if (flags.length >= 2) {
			const done = flags.filter((f) => /^(true|1)$/i.test(f)).length
			return Math.min(1, done / flags.length)
		}
	}

	return null
}

function pickProgressFromObject(obj, depth = 0) {
	if (!obj || typeof obj !== 'object' || depth > 4) return null

	const preferredKeys = [
		'progress_measure',
		'progressMeasure',
		'percentComplete',
		'percent_complete',
		'completionPercentage',
		'completion_percentage',
		'progress',
		'completion',
		'p',
	]
	for (const key of preferredKeys) {
		if (obj[key] != null) {
			const measure = normalizeProgressMeasure(obj[key])
			if (measure != null) return measure
		}
	}

	// Lesson/slide maps: { id: true/false } or { id: { completed: true } }
	const values = Object.values(obj)
	const boolish = values.filter(
		(v) => typeof v === 'boolean' || v === 0 || v === 1
	)
	if (boolish.length >= 2 && boolish.length === values.length) {
		const done = boolish.filter((v) => v === true || v === 1).length
		return Math.min(1, done / boolish.length)
	}

	const completedFlags = []
	for (const v of values) {
		if (v && typeof v === 'object') {
			if ('completed' in v || 'complete' in v || 'visited' in v) {
				completedFlags.push(!!(v.completed || v.complete || v.visited))
			}
		}
	}
	if (completedFlags.length >= 2) {
		const done = completedFlags.filter(Boolean).length
		return Math.min(1, done / completedFlags.length)
	}

	for (const v of values) {
		if (v && typeof v === 'object') {
			const nested = pickProgressFromObject(v, depth + 1)
			if (nested != null) return nested
		}
	}
	return null
}

export function createScormApiBridge({
	getProgress,
	saveProgress,
	courseRestartOnFailure = false,
	onComplete = null,
	onProgress = null,
}) {
	let isSuccessfullyCompleted = false
	let saveTimeout = null
	let pendingScore = null
	let pendingTotalTime = null
	let pendingProgressMeasure = null
	let lastSuspendData = ''
	let sessionAccumulated = 0
	let objectiveCount = null
	const objectives = new Map()

	const progressSnapshot = () => getProgress?.() || {}

	const measureFromObjectives = () => {
		const total =
			objectiveCount != null && objectiveCount > 0
				? objectiveCount
				: objectives.size
		if (!total) return null
		let completed = 0
		for (let i = 0; i < total; i++) {
			const obj = objectives.get(String(i)) || {}
			const status = String(obj.completion_status || obj.success_status || '').toLowerCase()
			const measure = normalizeProgressMeasure(obj.progress_measure)
			if (
				status === 'completed' ||
				status === 'passed' ||
				(measure != null && measure >= 1)
			) {
				completed += 1
			} else if (measure != null) {
				completed += measure
			}
		}
		return Math.min(1, completed / total)
	}

	const applyInferredMeasure = (measure, { forceSave = false } = {}) => {
		if (measure == null || Number.isNaN(measure)) return false
		const next = Math.min(1, Math.max(0, measure))
		const prev = pendingProgressMeasure
		// Never decrease mid-session progress (Rise may rewrite suspend_data)
		if (prev != null && next + 0.001 < prev && !isSuccessfullyCompleted) {
			return false
		}
		if (prev != null && Math.abs(prev - next) < 0.005 && !forceSave) {
			return false
		}
		pendingProgressMeasure = next
		if (next >= 0.999) {
			markComplete()
		} else {
			debouncedSaveProgress(buildDetails({ is_complete: false }))
		}
		return true
	}

	const refreshInferredProgress = ({ forceSave = false } = {}) => {
		if (isSuccessfullyCompleted) return
		if (pendingProgressMeasure != null && forceSave === false) {
			// Prefer explicit progress_measure already set; still allow objectives to raise it
		}
		const fromObjectives = measureFromObjectives()
		if (fromObjectives != null) {
			applyInferredMeasure(fromObjectives, { forceSave })
			return
		}
		const fromSuspend = extractProgressFromSuspendData(lastSuspendData)
		if (fromSuspend != null) {
			applyInferredMeasure(fromSuspend, { forceSave })
		}
	}

	const getDataFromLMS = (key) => {
		const progress = progressSnapshot()
		if (
			key === 'cmi.core.lesson_status' ||
			key === 'cmi.completion_status' ||
			key === 'cmi.success_status'
		) {
			if (progress.status === 'Complete') {
				if (key === 'cmi.success_status') return 'passed'
				if (key === 'cmi.completion_status') return 'completed'
				return 'passed'
			}
			if (key === 'cmi.success_status') return 'unknown'
			if (key === 'cmi.completion_status') return 'incomplete'
			return 'incomplete'
		}
		if (key === 'cmi.launch_data' || key === 'cmi.suspend_data') {
			return progress.scorm_content || ''
		}
		if (key === 'cmi.score.raw' || key === 'cmi.core.score.raw') {
			return progress.scorm_score != null ? String(progress.scorm_score) : ''
		}
		if (key === 'cmi.progress_measure') {
			if (progress.status === 'Complete') return '1'
			if (pendingProgressMeasure != null) return String(pendingProgressMeasure)
			return ''
		}
		if (
			key === 'cmi.total_time' ||
			key === 'cmi.core.total_time' ||
			key === 'cmi.session_time' ||
			key === 'cmi.core.session_time'
		) {
			return progress.scorm_total_time != null
				? String(progress.scorm_total_time)
				: ''
		}
		return ''
	}

	const buildDetails = (overrides = {}) => {
		const details = {
			is_complete: isSuccessfullyCompleted,
			scorm_content: isSuccessfullyCompleted ? '' : lastSuspendData,
			...overrides,
		}
		if (pendingScore != null) details.scorm_score = pendingScore
		if (pendingTotalTime != null) details.scorm_total_time = pendingTotalTime
		if (pendingProgressMeasure != null)
			details.progress_measure = pendingProgressMeasure
		return details
	}

	const flushSave = (scormDetails) => {
		clearTimeout(saveTimeout)
		saveProgress(scormDetails)
		onProgress?.(scormDetails)
	}

	const debouncedSaveProgress = (scormDetails) => {
		clearTimeout(saveTimeout)
		saveTimeout = setTimeout(() => {
			flushSave(scormDetails)
		}, 400)
	}

	const markComplete = () => {
		if (isSuccessfullyCompleted) return
		isSuccessfullyCompleted = true
		pendingProgressMeasure = 1
		const details = buildDetails({ is_complete: true, scorm_content: '' })
		flushSave(details)
		onComplete?.(details)
	}

	const handleObjectiveKey = (key, value) => {
		const countMatch = key.match(/^cmi\.objectives\._count$/i)
		if (countMatch) {
			const n = parseInt(value, 10)
			if (!Number.isNaN(n) && n >= 0) {
				objectiveCount = n
				refreshInferredProgress()
			}
			return true
		}

		const objMatch = key.match(
			/^cmi\.objectives\.(\d+)\.(completion_status|success_status|progress_measure)$/i
		)
		if (!objMatch) return false

		const idx = objMatch[1]
		const field = objMatch[2].toLowerCase()
		const current = objectives.get(idx) || {}
		current[field] = value
		objectives.set(idx, current)
		refreshInferredProgress()
		return true
	}

	const saveDataToLMS = (key, value) => {
		const lower = String(value || '').toLowerCase()

		const isLessonPassed =
			key === 'cmi.core.lesson_status' &&
			(lower === 'passed' || lower === 'completed')
		const isCompletionDone =
			key === 'cmi.completion_status' && lower === 'completed'
		const isSuccessPassed = key === 'cmi.success_status' && lower === 'passed'
		const shouldRestart =
			(key === 'cmi.core.lesson_status' && lower === 'failed') ||
			(key === 'cmi.completion_status' && lower === 'incomplete')

		if (handleObjectiveKey(key, value)) {
			return
		}

		if (key === 'cmi.score.raw' || key === 'cmi.core.score.raw') {
			const score = parseFloat(value)
			if (!Number.isNaN(score)) {
				pendingScore = score
				// Some packages put completion % into score.raw (0-100)
				if (score > 0 && score <= 100 && pendingProgressMeasure == null) {
					applyInferredMeasure(normalizeProgressMeasure(score))
				} else {
					debouncedSaveProgress(buildDetails({ is_complete: false }))
				}
			}
			return
		}

		if (key === 'cmi.progress_measure') {
			const measure = normalizeProgressMeasure(value)
			if (measure != null) {
				applyInferredMeasure(measure, { forceSave: true })
			}
			return
		}

		if (
			key === 'cmi.session_time' ||
			key === 'cmi.total_time' ||
			key === 'cmi.core.session_time' ||
			key === 'cmi.core.total_time'
		) {
			const seconds = parseTimeToSeconds(value)
			if (seconds != null) {
				pendingTotalTime = Math.max(pendingTotalTime || 0, seconds)
				sessionAccumulated = pendingTotalTime
				// Keep measure in payload when time commits
				refreshInferredProgress()
				debouncedSaveProgress(buildDetails({ is_complete: false }))
			}
			return
		}

		if (isLessonPassed || isCompletionDone || isSuccessPassed) {
			markComplete()
			return
		}

		if (shouldRestart && courseRestartOnFailure) {
			flushSave(buildDetails({ is_complete: false, scorm_content: '' }))
			return
		}

		if (key === 'cmi.suspend_data' && !isSuccessfullyCompleted) {
			lastSuspendData = value == null ? '' : String(value)
			const fromSuspend = extractProgressFromSuspendData(lastSuspendData)
			if (fromSuspend != null) {
				applyInferredMeasure(fromSuspend)
			} else {
				refreshInferredProgress()
				debouncedSaveProgress(
					buildDetails({ is_complete: false, scorm_content: lastSuspendData })
				)
			}
		}
	}

	const api1484 = {
		Initialize: () => 'true',
		Terminate: () => {
			refreshInferredProgress({ forceSave: true })
			if (!isSuccessfullyCompleted && pendingProgressMeasure >= 0.999) {
				markComplete()
			} else if (!isSuccessfullyCompleted) {
				flushSave(buildDetails({ is_complete: false }))
			}
			return 'true'
		},
		GetValue: (key) => getDataFromLMS(key),
		SetValue: (key, value) => {
			saveDataToLMS(key, value)
			return 'true'
		},
		Commit: () => {
			refreshInferredProgress({ forceSave: true })
			if (!isSuccessfullyCompleted) {
				flushSave(buildDetails({ is_complete: isSuccessfullyCompleted }))
			}
			return 'true'
		},
		GetLastError: () => '0',
		GetErrorString: () => '',
		GetDiagnostic: () => '',
	}

	const api12 = {
		LMSInitialize: () => 'true',
		LMSFinish: () => {
			api1484.Terminate()
			return 'true'
		},
		LMSGetValue: (key) => getDataFromLMS(key),
		LMSSetValue: (key, value) => {
			saveDataToLMS(key, value)
			return 'true'
		},
		LMSCommit: () => {
			api1484.Commit()
			return 'true'
		},
		LMSGetLastError: () => '0',
		LMSGetErrorString: () => '',
		LMSGetDiagnostic: () => '',
	}

	const attach = () => {
		window.API_1484_11 = api1484
		window.API = api12
	}

	const detach = () => {
		clearTimeout(saveTimeout)
		if (window.API_1484_11 === api1484) delete window.API_1484_11
		if (window.API === api12) delete window.API
	}

	const resetForLesson = () => {
		clearTimeout(saveTimeout)
		isSuccessfullyCompleted = false
		pendingScore = null
		pendingTotalTime = null
		pendingProgressMeasure = null
		lastSuspendData = ''
		sessionAccumulated = 0
		objectiveCount = null
		objectives.clear()
	}

	const markCompletedFromServer = (progress) => {
		if (progress?.status === 'Complete') {
			isSuccessfullyCompleted = true
			pendingProgressMeasure = 1
		} else if (progress?.progress_measure != null) {
			pendingProgressMeasure = normalizeProgressMeasure(
				progress.progress_measure
			)
		}
		if (progress?.scorm_content) {
			lastSuspendData = progress.scorm_content
			if (!isSuccessfullyCompleted && pendingProgressMeasure == null) {
				const inferred = extractProgressFromSuspendData(lastSuspendData)
				if (inferred != null) pendingProgressMeasure = inferred
			}
		}
		if (progress?.scorm_score != null) pendingScore = progress.scorm_score
		if (progress?.scorm_total_time != null)
			pendingTotalTime = progress.scorm_total_time
	}

	return {
		attach,
		detach,
		resetForLesson,
		markCompletedFromServer,
		getDataFromLMS,
		saveDataToLMS,
		getPendingProgressMeasure: () => pendingProgressMeasure,
	}
}
