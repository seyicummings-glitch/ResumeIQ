import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiRequest, apiRequestBlob, ApiError, setUnauthorizedHandler, toFormData } from './client'
import { clearToken, setToken } from '../auth/tokenStorage'

function mockFetchOnce({ status = 200, body = null } = {}) {
  const text = body === null ? '' : JSON.stringify(body)
  global.fetch = vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    text: () => Promise.resolve(text),
  })
}

describe('apiRequest', () => {
  beforeEach(() => {
    clearToken()
    setUnauthorizedHandler(null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends a GET with no body by default', async () => {
    mockFetchOnce({ body: { ok: true } })
    const result = await apiRequest('/health')
    expect(result).toEqual({ ok: true })
    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toBe('/api/health')
    expect(options.method).toBe('GET')
    expect(options.body).toBeUndefined()
  })

  it('JSON-encodes a plain object body and sets Content-Type', async () => {
    mockFetchOnce({ body: { id: 1 } })
    await apiRequest('/resume-builder/chat', { method: 'POST', body: { conversation: [] } })
    const [, options] = global.fetch.mock.calls[0]
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(options.body).toBe(JSON.stringify({ conversation: [] }))
  })

  it('sends a FormData body as-is without a Content-Type header', async () => {
    mockFetchOnce({ body: { ok: true } })
    const formData = toFormData({ file: 'not-a-real-file' })
    await apiRequest('/resume/save', { method: 'POST', body: formData })
    const [, options] = global.fetch.mock.calls[0]
    expect(options.body).toBe(formData)
    expect(options.headers['Content-Type']).toBeUndefined()
  })

  it('attaches the bearer token when auth is true and a token is stored', async () => {
    setToken('test-token')
    mockFetchOnce({ body: {} })
    await apiRequest('/resume/my-resumes', { auth: true })
    const [, options] = global.fetch.mock.calls[0]
    expect(options.headers['Authorization']).toBe('Bearer test-token')
  })

  it('omits the Authorization header when auth is true but no token is stored', async () => {
    mockFetchOnce({ body: {} })
    await apiRequest('/resume/my-resumes', { auth: true })
    const [, options] = global.fetch.mock.calls[0]
    expect(options.headers['Authorization']).toBeUndefined()
  })

  it('builds a query string, skipping undefined/null/empty values', async () => {
    mockFetchOnce({ body: {} })
    await apiRequest('/resume/versions/compare', { query: { a: 1, b: 2, c: undefined, d: null, e: '' } })
    const [url] = global.fetch.mock.calls[0]
    expect(url).toBe('/api/resume/versions/compare?a=1&b=2')
  })

  it('returns null for a 204 response without reading the body', async () => {
    mockFetchOnce({ status: 204 })
    const result = await apiRequest('/some/route', { method: 'DELETE' })
    expect(result).toBeNull()
  })

  it('throws an ApiError with the string detail on a non-OK response', async () => {
    mockFetchOnce({ status: 404, body: { detail: 'Resume not found.' } })
    await expect(apiRequest('/resume/1')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'Resume not found.',
    })
  })

  it('joins FastAPI validation-error arrays into one message', async () => {
    mockFetchOnce({
      status: 422,
      body: { detail: [{ loc: ['body', 'email'], msg: 'field required', type: 'value_error' }] },
    })
    await expect(apiRequest('/auth/register', { method: 'POST', body: {} })).rejects.toMatchObject({
      message: 'field required',
    })
  })

  it('falls back to a generic message when there is no detail', async () => {
    mockFetchOnce({ status: 500, body: null })
    await expect(apiRequest('/resume/1')).rejects.toMatchObject({
      message: 'Something went wrong. Please try again.',
    })
  })

  it('wraps a network failure in an ApiError with status 0', async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(apiRequest('/health')).rejects.toBeInstanceOf(ApiError)
    await expect(apiRequest('/health')).rejects.toMatchObject({ status: 0 })
  })

  it('clears the token and calls the unauthorized handler on a 401 outside login/register', async () => {
    setToken('stale-token')
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    mockFetchOnce({ status: 401, body: { detail: 'Session expired.' } })

    await expect(apiRequest('/resume/my-resumes', { auth: true })).rejects.toBeInstanceOf(ApiError)
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('does not treat a 401 on /auth/login as a session expiry', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    mockFetchOnce({ status: 401, body: { detail: 'Incorrect email or password.' } })

    await expect(apiRequest('/auth/login', { method: 'POST', body: {} })).rejects.toBeInstanceOf(ApiError)
    expect(handler).not.toHaveBeenCalled()
  })
})

describe('apiRequestBlob', () => {
  beforeEach(() => {
    clearToken()
    setUnauthorizedHandler(null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('attaches the bearer token and returns the response as a Blob', async () => {
    setToken('test-token')
    const fakeBlob = new Blob(['audio-bytes'], { type: 'audio/webm' })
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(fakeBlob),
    })

    const result = await apiRequestBlob('/interview/sessions/1/audio', { auth: true })

    expect(result).toBe(fakeBlob)
    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toBe('/api/interview/sessions/1/audio')
    expect(options.headers['Authorization']).toBe('Bearer test-token')
  })

  it('throws an ApiError with the parsed detail on a non-OK response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Recording not found.' }),
    })

    await expect(apiRequestBlob('/interview/sessions/1/audio', { auth: true })).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'Recording not found.',
    })
  })

  it('falls back to a generic message when the error body is not valid JSON', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('not json')),
    })

    await expect(apiRequestBlob('/interview/sessions/1/audio')).rejects.toMatchObject({
      message: 'Something went wrong. Please try again.',
    })
  })

  it('wraps a network failure in an ApiError with status 0', async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(apiRequestBlob('/interview/sessions/1/audio')).rejects.toMatchObject({ status: 0 })
  })
})

describe('toFormData', () => {
  it('skips undefined and null values', () => {
    const formData = toFormData({ a: 'x', b: undefined, c: null, d: 0 })
    expect(formData.has('a')).toBe(true)
    expect(formData.has('b')).toBe(false)
    expect(formData.has('c')).toBe(false)
    expect(formData.get('d')).toBe('0')
  })
})
