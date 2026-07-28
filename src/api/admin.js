import { apiRequest } from './client'

export async function getUsers() {
  return apiRequest('/admin/users', { auth: true })
}

export async function updateUser(id, fields) {
  return apiRequest(`/admin/users/${id}`, { method: 'PATCH', body: fields, auth: true })
}

export function setUserStatus(id, status) {
  return apiRequest(`/admin/users/${id}/status`, { method: 'PATCH', body: { status }, auth: true })
}

export async function getReports() {
  return apiRequest('/admin/reports', { auth: true })
}

export async function updateReportStatus(id, status) {
  return apiRequest(`/admin/reports/${id}/status`, { method: 'PATCH', body: { status }, auth: true })
}

export async function getAnalytics() {
  return apiRequest('/admin/analytics', { auth: true })
}

export async function getSettings() {
  return apiRequest('/admin/settings', { auth: true })
}

export async function updateSettings(fields) {
  return apiRequest('/admin/settings', { method: 'PUT', body: fields, auth: true })
}
