import { getLmsRoute } from '@/utils/basePath'

export function getCertificatePreviewPath(certificateName) {
	return getLmsRoute(`certificate/${encodeURIComponent(certificateName)}`)
}

export function openCertificatePreview(certificate) {
	const name = typeof certificate === 'string' ? certificate : certificate?.name
	if (!name) return
	window.open(getCertificatePreviewPath(name), '_blank')
}
