import { apiRequest } from './client'
import { getToken } from '../auth/tokenStorage'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

/**
 * @typedef {Object} GeneratedDocument
 * @property {number} id
 * @property {string} name
 * @property {string} doc_type
 * @property {number|null} analysis_id
 * @property {number|null} size_kb
 * @property {string} created_at
 */

/** @returns {Promise<GeneratedDocument[]>} */
export function getDocuments() {
  return apiRequest('/documents', { auth: true })
}

export function deleteDocument(id) {
  return apiRequest(`/documents/${id}`, { method: 'DELETE', auth: true })
}

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

/** Raw authenticated fetch for binary PDF responses — apiRequest always JSON-parses the body, which doesn't work for file downloads. */
async function authedFetchBlob(path, { method = 'GET' } = {}) {
  const token = getToken()
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const response = await fetch(`${API_BASE_URL}${path}`, { method, headers })

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
  const filename = filenameFromContentDisposition(response.headers.get('Content-Disposition'), 'document.pdf')
  return { blob, filename }
}

/** Generates a PDF report for an analysis (POST /documents/generate), downloads it, and returns the response so callers can invalidate the documents list. */
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

/** Downloads an existing GeneratedDocument by id (GET /documents/{id}/download). */
export async function downloadDocument(id) {
  const { blob, filename } = await authedFetchBlob(`/documents/${id}/download`)
  triggerBlobDownload(blob, filename)
  return { filename }
}
