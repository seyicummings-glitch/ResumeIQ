import { getToken } from '../auth/tokenStorage'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

/** Extracts a filename from a Content-Disposition header, falling back to a default. */
function filenameFromContentDisposition(header, fallback) {
  if (!header) return fallback
  const match = header.match(/filename="?([^";]+)"?/)
  return match ? match[1] : fallback
}

/** Triggers a real browser download for a blob via a temporary <a> element. */
function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

/** Generates a PDF report for an analysis (POST /documents/generate) and downloads it — the
 * "Download PDF report" action on Analysis History / Analysis Results. Generated fresh on
 * every call; nothing is saved server-side to browse or manage later. */
export async function generateDocument({ analysisId }) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const response = await fetch(`${API_BASE_URL}/documents/generate`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ analysis_id: analysisId }),
  })

  if (!response.ok) {
    let detail = null
    try {
      detail = await response.json()
    } catch {
      detail = null
    }
    const message = (detail && detail.detail) || 'Something went wrong. Please try again.'
    throw new Error(typeof message === 'string' ? message : 'Something went wrong. Please try again.')
  }

  const blob = await response.blob()
  const filename = filenameFromContentDisposition(response.headers.get('Content-Disposition'), 'analysis-report.pdf')
  triggerBlobDownload(blob, filename)
  return { filename }
}
