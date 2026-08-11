import { apiRequest } from './client'

export async function getPlansPage({ page = 1, pageSize = 20, search, status } = {}) {
  return apiRequest('/admin/subscriptions/plans', { auth: true, query: { page, pageSize, search, status } })
}

export async function createPlan(fields) {
  return apiRequest('/admin/subscriptions/plans', { method: 'POST', body: fields, auth: true })
}

export async function updatePlan(id, fields) {
  return apiRequest(`/admin/subscriptions/plans/${id}`, { method: 'PATCH', body: fields, auth: true })
}

export function setPlanStatus(id, isActive) {
  return apiRequest(`/admin/subscriptions/plans/${id}/status`, { method: 'PATCH', body: { isActive }, auth: true })
}

export async function deletePlan(id) {
  return apiRequest(`/admin/subscriptions/plans/${id}`, { method: 'DELETE', auth: true })
}

export async function getPlanLimits(id) {
  return apiRequest(`/admin/subscriptions/plans/${id}/limits`, { auth: true })
}

export async function updatePlanLimits(id, limits) {
  return apiRequest(`/admin/subscriptions/plans/${id}/limits`, { method: 'PUT', body: { limits }, auth: true })
}
