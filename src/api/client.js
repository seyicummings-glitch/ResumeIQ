import { getToken, clearToken } from '../auth/tokenStorage'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export class ApiError extends Error {
  constructor(status, message, detail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

let unauthorizedHandler = null

/** Wired up once by AuthContext so any 401 anywhere in the app clears the session and redirects, without every page having to handle it. */
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

let featureLimitHandler = null

/** Wired up once by UpgradeModalProvider so any gated AI feature hitting its token limit (402,
 * see app/services/feature_gate.py) opens the upgrade modal automatically, without every page
 * having to catch it individually. Called with the FeatureAccessDenied payload. */
export function setFeatureLimitHandler(handler) {
  featureLimitHandler = handler
}

let balanceChangedHandler = null

/** Wired up once by UpgradeModalProvider so the token balance badge refreshes right after any
 * gated AI feature successfully spends tokens — without threading query invalidation through
 * every individual feature hook. */
export function setBalanceChangedHandler(handler) {
  balanceChangedHandler = handler
}

// Path prefixes whose successful, non-GET requests may have just spent tokens (see the
// matching check_and_consume() call sites in the backend's app/routes/*.py).
const GATED_PATH_PREFIXES = [
  '/resume-builder', '/matching', '/interview', '/skill-assessment', '/roadmap', '/documents', '/career-coach',
]

function extractErrorMessage(detail) {
  if (!detail) return 'Something went wrong. Please try again.'
  if (typeof detail === 'string') return detail
  // FastAPI validation errors: [{ loc, msg, type }, ...]
  if (Array.isArray(detail)) return detail.map((d) => d.msg).filter(Boolean).join(' ')
  return 'Something went wrong. Please try again.'
}

function buildUrl(path, query) {
  let url = `${API_BASE_URL}${path}`
  if (query) {
    const params = new URLSearchParams()
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, value)
    })
    const qs = params.toString()
    if (qs) url += `?${qs}`
  }
  return url
}

/**
 * Shared fetch wrapper used by every api/* module.
 * @param {string} path - route path, e.g. '/auth/login'
 * @param {Object} [options]
 * @param {string} [options.method]
 * @param {any} [options.body] - a FormData instance is sent as multipart as-is; anything else is JSON-encoded
 * @param {boolean} [options.auth] - attach the stored bearer token
 * @param {Object} [options.query] - query string params
 * @param {AbortSignal} [options.signal]
 */
export async function apiRequest(path, { method = 'GET', body, auth = false, query, signal } = {}) {
  const headers = {}
  let requestBody

  if (body instanceof FormData) {
    requestBody = body
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    requestBody = JSON.stringify(body)
  }

  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  let response
  try {
    response = await fetch(buildUrl(path, query), { method, headers, body: requestBody, signal })
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.', null)
  }

  if (response.status === 204) return null

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    // A 401 on the login/register forms themselves means "wrong credentials," not "your session expired."
    const isCredentialsCheck = path === '/auth/login' || path === '/auth/register'
    if (response.status === 401 && !isCredentialsCheck) {
      clearToken()
      unauthorizedHandler?.()
    }
    if (response.status === 402) {
      featureLimitHandler?.(data?.detail)
    }
    throw new ApiError(response.status, extractErrorMessage(data?.detail), data?.detail)
  }

  if (method !== 'GET' && GATED_PATH_PREFIXES.some((prefix) => path.startsWith(prefix))) {
    balanceChangedHandler?.()
  }

  return data
}

/**
 * Like apiRequest, but for endpoints that return a raw binary body (e.g. audio) instead of
 * JSON — a plain <audio src="..."> can't attach an Authorization header, so protected binary
 * downloads need to go through fetch + an object URL instead.
 * @param {string} path
 * @param {{auth?: boolean, signal?: AbortSignal}} [options]
 * @returns {Promise<Blob>}
 */
export async function apiRequestBlob(path, { auth = false, signal } = {}) {
  const headers = {}
  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  let response
  try {
    response = await fetch(buildUrl(path), { headers, signal })
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.', null)
  }

  if (!response.ok) {
    let detail = null
    try {
      detail = (await response.json())?.detail
    } catch {
      detail = null
    }
    if (response.status === 401) {
      clearToken()
      unauthorizedHandler?.()
    }
    throw new ApiError(response.status, extractErrorMessage(detail), detail)
  }

  return response.blob()
}

/** Triggers a real browser download for a blob via a temporary, invisible <a> element. */
export function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

/** Builds a FormData body from a plain object, skipping undefined/null values. File/Blob values are appended as files, everything else as strings. */
export function toFormData(fields) {
  const formData = new FormData()
  Object.entries(fields).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    formData.append(key, value)
  })
  return formData
}
