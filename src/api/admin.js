import { apiRequest } from './client'

export async function getDashboard() {
  return apiRequest('/admin/dashboard', { auth: true })
}

export async function getActivityFeed(limit = 20) {
  return apiRequest('/admin/dashboard/activity-feed', { auth: true, query: { limit } })
}

export async function getUsersPage({ page = 1, pageSize = 20, search, status, role } = {}) {
  return apiRequest('/admin/users', { auth: true, query: { page, pageSize, search, status, role } })
}

export async function getUserDetail(id) {
  return apiRequest(`/admin/users/${id}`, { auth: true })
}

export async function updateUser(id, fields) {
  return apiRequest(`/admin/users/${id}`, { method: 'PATCH', body: fields, auth: true })
}

export function setUserStatus(id, status) {
  return apiRequest(`/admin/users/${id}/status`, { method: 'PATCH', body: { status }, auth: true })
}

export async function deleteUser(id) {
  return apiRequest(`/admin/users/${id}`, { method: 'DELETE', auth: true })
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
