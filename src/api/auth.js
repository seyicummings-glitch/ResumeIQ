import { apiRequest } from './client'

/**
 * @typedef {Object} User
 * @property {number} id
 * @property {string} email
 * @property {string|null} full_name
 * @property {string} role - "user" | "admin"
 * @property {string} created_at
 */

/** Doesn't log the user in — new accounts must verify their email first (see login()'s
 * 403 email_not_verified). `verification_token` is only present in the dev fallback
 * when the backend has no SMTP configured (no real email was sent).
 * @returns {Promise<{message: string, email: string, verification_token: string|null}>} */
export function register({ email, password, fullName }) {
  return apiRequest('/auth/register', {
    method: 'POST',
    body: { email, password, full_name: fullName || null },
  })
}

/** @returns {Promise<{message: string}>} */
export function verifyEmail(token) {
  return apiRequest('/auth/verify-email', { method: 'POST', body: { token } })
}

/** Same non-enumerating response whether the address doesn't exist or is already verified. */
export function resendVerification(email) {
  return apiRequest('/auth/resend-verification', { method: 'POST', body: { email } })
}

/** @returns {Promise<{access_token: string, token_type: string}>} */
export function login({ email, password }) {
  return apiRequest('/auth/login', { method: 'POST', body: { email, password } })
}

/** @returns {Promise<User>} */
export function getMe() {
  return apiRequest('/auth/me', { auth: true })
}

export function logout() {
  return apiRequest('/auth/logout', { method: 'POST', auth: true })
}

/** Backend has no email sending yet — response includes the raw reset_token directly. */
export function requestPasswordReset(email) {
  return apiRequest('/auth/password-reset/request', { method: 'POST', body: { email } })
}

export function confirmPasswordReset({ token, newPassword }) {
  return apiRequest('/auth/password-reset/confirm', {
    method: 'POST',
    body: { token, new_password: newPassword },
  })
}

/** Live check used by AdminRoute as defense-in-depth beyond the client-side role check. */
export function pingAdminOnly() {
  return apiRequest('/auth/admin-only', { auth: true })
}
