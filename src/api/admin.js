import { simulateLatency } from './sampleData/simulateLatency'
import { adminUsersSample } from './sampleData/adminUsers.sample'
import { adminReportsSample } from './sampleData/adminReports.sample'
import { adminAnalyticsSample } from './sampleData/adminAnalytics.sample'
import { adminSettingsSample } from './sampleData/adminSettings.sample'

// TODO: no /admin/* endpoints exist on the backend yet (only the example
// GET /auth/admin-only route). These functions read/write a localStorage
// copy of the sample data so edits/deactivations feel real across a
// session. Swap each function body for a real apiRequest call once the
// backend adds admin endpoints — AdminUsersPage/AdminReportsPage/etc. and
// their hooks call these functions and don't need to change.

const USERS_KEY = 'resumeiq_admin_users_sample'
const REPORTS_KEY = 'resumeiq_admin_reports_sample'
const SETTINGS_KEY = 'resumeiq_admin_settings_sample'

function readStore(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function writeStore(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

export async function getUsers() {
  await simulateLatency()
  return readStore(USERS_KEY, adminUsersSample)
}

export async function updateUser(id, fields) {
  await simulateLatency()
  const users = readStore(USERS_KEY, adminUsersSample)
  const next = users.map((u) => (u.id === id ? { ...u, ...fields } : u))
  writeStore(USERS_KEY, next)
  return next.find((u) => u.id === id)
}

export function setUserStatus(id, status) {
  return updateUser(id, { status })
}

export async function getReports() {
  await simulateLatency()
  return readStore(REPORTS_KEY, adminReportsSample)
}

export async function updateReportStatus(id, status) {
  await simulateLatency()
  const reports = readStore(REPORTS_KEY, adminReportsSample)
  const next = reports.map((r) => (r.id === id ? { ...r, status } : r))
  writeStore(REPORTS_KEY, next)
  return next.find((r) => r.id === id)
}

export async function getAnalytics() {
  await simulateLatency()
  return adminAnalyticsSample
}

export async function getSettings() {
  await simulateLatency()
  return readStore(SETTINGS_KEY, adminSettingsSample)
}

export async function updateSettings(fields) {
  await simulateLatency()
  const current = readStore(SETTINGS_KEY, adminSettingsSample)
  const next = { ...current, ...fields }
  writeStore(SETTINGS_KEY, next)
  return next
}
