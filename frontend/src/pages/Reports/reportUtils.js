// Shared bits for the learner reports (colour bands follow the student PTM report).

export const BAND_STYLES = {
	excellent: { label: 'Excellent', bg: '#8ADB9F', soft: '#E7F8EC', text: '#0B5A24', dot: '#35C759' },
	good: { label: 'Good', bg: '#C9F0D4', soft: '#F0FBF3', text: '#146C31', dot: '#027BFF' },
	average: { label: 'Average', bg: '#FFE8B3', soft: '#FFF8E6', text: '#8A5A00', dot: '#FFAB00' },
	needs_improvement: { label: 'Needs Improvement', bg: '#FFD4D4', soft: '#FFF1F1', text: '#B42323', dot: '#F03E3E' },
}

export const BAND_ORDER = ['excellent', 'good', 'average', 'needs_improvement']

export const BAND_RULES = '≥90% Excellent · 80–90% Good · 60–80% Average · <60% Needs Improvement'

export function bandStyle(band) {
	return BAND_STYLES[band] || { label: '—', bg: '#F2F2F2', soft: '#F7F7F7', text: '#85878A', dot: '#CECFD0' }
}

export function fmt(value, digits = 1) {
	if (value === null || value === undefined || value === '') return '—'
	const n = Number(value)
	if (Number.isNaN(n)) return String(value)
	return Number.isInteger(n) ? String(n) : n.toFixed(digits)
}

export function fmtPct(value) {
	return value === null || value === undefined ? '—' : `${fmt(value)}%`
}

export function fmtDuration(seconds) {
	if (seconds === null || seconds === undefined) return '—'
	const h = Math.floor(seconds / 3600)
	const m = Math.floor((seconds % 3600) / 60)
	return h ? `${h}h ${m}m` : `${m}m`
}

export function fmtDate(value) {
	if (!value) return '—'
	const d = new Date(value)
	if (Number.isNaN(d.getTime())) return String(value)
	return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function initials(name) {
	return (name || '?')
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0].toUpperCase())
		.join('')
}

export function managerName(email) {
	if (!email) return '—'
	const local = String(email).split('@')[0]
	return local
		.split(/[._]/)
		.filter(Boolean)
		.map((p) => p[0].toUpperCase() + p.slice(1))
		.join(' ')
}
