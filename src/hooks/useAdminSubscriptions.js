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
