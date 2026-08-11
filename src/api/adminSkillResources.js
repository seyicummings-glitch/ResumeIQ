import { apiRequest } from './client'

export async function getSkillResourcesPage({ page = 1, pageSize = 20, search } = {}) {
  return apiRequest('/admin/skill-resources', { auth: true, query: { page, pageSize, search } })
}

export async function createSkillResource(fields) {
  return apiRequest('/admin/skill-resources', { method: 'POST', body: fields, auth: true })
}

export async function updateSkillResource(id, fields) {
  return apiRequest(`/admin/skill-resources/${id}`, { method: 'PATCH', body: fields, auth: true })
}

export async function deleteSkillResource(id) {
  return apiRequest(`/admin/skill-resources/${id}`, { method: 'DELETE', auth: true })
}
