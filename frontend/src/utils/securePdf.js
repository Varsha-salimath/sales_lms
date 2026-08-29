import { call } from 'frappe-ui'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorkerBundled from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
export const PDFJS_DIST_VERSION = '4.10.38'

export const PDFJS_WORKER_CDN = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS_DIST_VERSION}/build/pdf.worker.min.mjs`

let pdfWorkerReady = null

export async function configurePdfWorker() {
	if (pdfWorkerReady) {
		return pdfWorkerReady
	}

	pdfWorkerReady = (async () => {
		const bundled =
			typeof pdfjsWorkerBundled === 'string' ? pdfjsWorkerBundled : ''
		if (bundled && !bundled.includes('__VITE_ASSET__')) {
			try {
				const res = await fetch(bundled, { method: 'HEAD' })
				const ct = res.headers.get('content-type') || ''
				if (res.ok && /javascript|ecmascript/i.test(ct)) {
					pdfjsLib.GlobalWorkerOptions.workerSrc = bundled
					return bundled
				}
			} catch {
			}
		}
		pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CDN
		return PDFJS_WORKER_CDN
	})()

	return pdfWorkerReady
}

export function getCsrfToken() {
	return (
		window.csrf_token ||
		document.cookie
			.split('; ')
			.find((c) => c.startsWith('csrf_token='))
			?.split('=')[1]
	)
}

export async function fetchSecurePdfToken(fileUrl, { course, lesson } = {}) {
	const result = await call('lms.lms.pdf_security.get_secure_pdf_token', {
		file_url: fileUrl,
		course: course || undefined,
		lesson: lesson || undefined,
	})
	return result
}

export function buildSecurePdfUrl(token) {
	return `/api/method/lms.lms.pdf_security.serve_secure_pdf?token=${encodeURIComponent(token)}`
}
