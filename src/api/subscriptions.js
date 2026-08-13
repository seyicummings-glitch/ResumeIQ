import { apiRequest } from './client'

export async function getMySubscription() {
  return apiRequest('/subscriptions/me', { auth: true })
}

export async function getPublicPlans() {
  return apiRequest('/subscriptions/plans')
}

export async function getAvailablePaymentMethods() {
  return apiRequest('/subscriptions/payment-methods')
}

export async function upgradePlan({ planId, billingCycle, paymentMethod }) {
  return apiRequest('/subscriptions/upgrade', {
    method: 'POST', auth: true, body: { planId, billingCycle, paymentMethod },
  })
}

export async function getCreditPackages() {
  return apiRequest('/subscriptions/credit-packages')
}

export async function purchaseCredits({ packageId, paymentMethod }) {
  return apiRequest('/subscriptions/credits/purchase', {
    method: 'POST', auth: true, body: { packageId, paymentMethod },
  })
}

export async function getMyTransactions({ page = 1, pageSize = 20 } = {}) {
  return apiRequest('/subscriptions/transactions', { auth: true, query: { page, pageSize } })
}

export async function getMyUsageHistory({ page = 1, pageSize = 20 } = {}) {
  return apiRequest('/subscriptions/usage-history', { auth: true, query: { page, pageSize } })
}
