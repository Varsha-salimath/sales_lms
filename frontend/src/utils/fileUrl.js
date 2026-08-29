export function getFileHref(url) {
	if (!url) return ''
	if (url.startsWith('http://') || url.startsWith('https://')) return url
	return `${window.location.origin}${encodeURI(url)}`
}
