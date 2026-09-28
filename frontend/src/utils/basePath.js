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
	const configured = getLmsBasePath()
	if (!configured) {
		return '/'
	}
	// Canonical LMS URLs are at site root (/analytics). If boot still has legacy
	// lms_path but the browser path has no /lms prefix, mount the router at /.
	if (typeof window !== 'undefined') {
		const path = window.location.pathname || '/'
		const prefix = `/${configured}`
		if (path !== prefix && !path.startsWith(`${prefix}/`)) {
			return '/'
		}
	}
	return `/${configured}`
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
