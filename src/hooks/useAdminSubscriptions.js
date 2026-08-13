import { useMutation, useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import * as adminSubscriptionsApi from '../api/adminSubscriptions'

export function useAdminPlansPage(params) {
  return useQuery({
    queryKey: ['admin', 'subscriptions', 'plans', params],
    queryFn: () => adminSubscriptionsApi.getPlansPage(params),
    placeholderData: keepPreviousData,
  })
}

export function useCreatePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (fields) => adminSubscriptionsApi.createPlan(fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'plans'] }),
  })
}

export function useUpdatePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, fields }) => adminSubscriptionsApi.updatePlan(id, fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'plans'] }),
  })
}

export function useSetPlanStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isActive }) => adminSubscriptionsApi.setPlanStatus(id, isActive),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'plans'] }),
  })
}

export function useDeletePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id) => adminSubscriptionsApi.deletePlan(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'plans'] }),
  })
}

export function usePlanLimits(planId) {
  return useQuery({
    queryKey: ['admin', 'subscriptions', 'plans', planId, 'limits'],
    queryFn: () => adminSubscriptionsApi.getPlanLimits(planId),
    enabled: planId != null,
  })
}

export function useUpdatePlanLimits() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, limits }) => adminSubscriptionsApi.updatePlanLimits(id, limits),
    onSuccess: (_, { id }) => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'plans', id, 'limits'] }),
  })
}

// --- AI feature settings ------------------------------------------------------

export function useFeatureSettings() {
  return useQuery({ queryKey: ['admin', 'subscriptions', 'featureSettings'], queryFn: adminSubscriptionsApi.getFeatureSettings })
}

export function useUpdateFeatureSetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ featureKey, fields }) => adminSubscriptionsApi.updateFeatureSetting(featureKey, fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'featureSettings'] }),
  })
}

// --- Credit packages -----------------------------------------------------------

export function useCreditPackages() {
  return useQuery({ queryKey: ['admin', 'subscriptions', 'creditPackages'], queryFn: adminSubscriptionsApi.getCreditPackages })
}

export function useCreateCreditPackage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (fields) => adminSubscriptionsApi.createCreditPackage(fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'creditPackages'] }),
  })
}

export function useUpdateCreditPackage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, fields }) => adminSubscriptionsApi.updateCreditPackage(id, fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'creditPackages'] }),
  })
}

export function useSetCreditPackageStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isActive }) => adminSubscriptionsApi.setCreditPackageStatus(id, isActive),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'creditPackages'] }),
  })
}

export function useDeleteCreditPackage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id) => adminSubscriptionsApi.deleteCreditPackage(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'creditPackages'] }),
  })
}

// --- Payment methods -------------------------------------------------------------

export function usePaymentMethods() {
  return useQuery({ queryKey: ['admin', 'subscriptions', 'paymentMethods'], queryFn: adminSubscriptionsApi.getPaymentMethods })
}

export function useSetPaymentMethodStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ methodKey, isEnabled }) => adminSubscriptionsApi.setPaymentMethodStatus(methodKey, isEnabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscriptions', 'paymentMethods'] }),
  })
}

// --- Subscribers, transactions, analytics ---------------------------------------

export function useAdminSubscribersPage(params) {
  return useQuery({
    queryKey: ['admin', 'subscriptions', 'subscribers', params],
    queryFn: () => adminSubscriptionsApi.getSubscribersPage(params),
    placeholderData: keepPreviousData,
  })
}

export function useAdminTransactionsPage(params) {
  return useQuery({
    queryKey: ['admin', 'subscriptions', 'transactions', params],
    queryFn: () => adminSubscriptionsApi.getTransactionsPage(params),
    placeholderData: keepPreviousData,
  })
}

export function useSubscriptionAnalytics() {
  return useQuery({ queryKey: ['admin', 'subscriptions', 'analytics'], queryFn: adminSubscriptionsApi.getSubscriptionAnalytics })
}
