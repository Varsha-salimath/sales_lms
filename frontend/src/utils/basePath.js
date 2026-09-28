export function getLmsBasePath() {
	const raw =
		typeof window !== 'undefined'
			? window.lms_path ?? window.boot?.lms_path
			: ''
	if (raw === undefined || raw === null || raw === false) {
		return ''
	}
	return String(raw).replace(/^\/+|\/+$/g, '')
}

export function getRouterHistoryBase() {
	const base = getLmsBasePath()
	return base ? `/${base}` : '/'
}

export function getLmsRoute(path = '') {
	const base = getLmsBasePath()
	const normalized = String(path || '').replace(/^\/+/, '')
	if (!base) {
		return normalized ? `/${normalized}` : '/dashboard'
	}
	if (!normalized) {
		return `/${base}/dashboard`
	}
	return `/${base}/${normalized}`
}
