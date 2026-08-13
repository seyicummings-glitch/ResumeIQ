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

// --- AI feature settings ------------------------------------------------------

export async function getFeatureSettings() {
  return apiRequest('/admin/subscriptions/feature-settings', { auth: true })
}

export async function updateFeatureSetting(featureKey, fields) {
  return apiRequest(`/admin/subscriptions/feature-settings/${featureKey}`, { method: 'PUT', body: fields, auth: true })
}

// --- Credit packages -----------------------------------------------------------

export async function getCreditPackages() {
  return apiRequest('/admin/subscriptions/credit-packages', { auth: true })
}

export async function createCreditPackage(fields) {
  return apiRequest('/admin/subscriptions/credit-packages', { method: 'POST', body: fields, auth: true })
}

export async function updateCreditPackage(id, fields) {
  return apiRequest(`/admin/subscriptions/credit-packages/${id}`, { method: 'PATCH', body: fields, auth: true })
}

export function setCreditPackageStatus(id, isActive) {
  return apiRequest(`/admin/subscriptions/credit-packages/${id}/status`, { method: 'PATCH', body: { isActive }, auth: true })
}

export async function deleteCreditPackage(id) {
  return apiRequest(`/admin/subscriptions/credit-packages/${id}`, { method: 'DELETE', auth: true })
}

// --- Payment methods -------------------------------------------------------------

export async function getPaymentMethods() {
  return apiRequest('/admin/subscriptions/payment-methods', { auth: true })
}

export function setPaymentMethodStatus(methodKey, isEnabled) {
  return apiRequest(`/admin/subscriptions/payment-methods/${methodKey}/status`, { method: 'PATCH', body: { isEnabled }, auth: true })
}

// --- Subscribers & transactions -----------------------------------------------------

export async function getSubscribersPage({ page = 1, pageSize = 20, planId, status } = {}) {
  return apiRequest('/admin/subscriptions/subscribers', { auth: true, query: { page, pageSize, planId, status } })
}

export async function getTransactionsPage({ page = 1, pageSize = 20, status, kind } = {}) {
  return apiRequest('/admin/subscriptions/transactions', { auth: true, query: { page, pageSize, status, kind } })
}

export async function getSubscriptionAnalytics() {
  return apiRequest('/admin/subscriptions/analytics', { auth: true })
}
