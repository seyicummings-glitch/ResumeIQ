import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as subscriptionsApi from '../api/subscriptions'

export function useMySubscription() {
  return useQuery({ queryKey: ['subscription', 'me'], queryFn: subscriptionsApi.getMySubscription })
}

export function usePublicPlans() {
  return useQuery({ queryKey: ['subscription', 'plans'], queryFn: subscriptionsApi.getPublicPlans })
}

export function useAvailablePaymentMethods() {
  return useQuery({ queryKey: ['subscription', 'paymentMethods'], queryFn: subscriptionsApi.getAvailablePaymentMethods })
}

export function useCreditPackagesPublic() {
  return useQuery({ queryKey: ['subscription', 'creditPackages'], queryFn: subscriptionsApi.getCreditPackages })
}

export function useUpgradePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: subscriptionsApi.upgradePlan,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['subscription', 'me'] }),
  })
}

export function usePurchaseCredits() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: subscriptionsApi.purchaseCredits,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription', 'me'] })
      queryClient.invalidateQueries({ queryKey: ['subscription', 'transactions'] })
    },
  })
}

export function useMyTransactions(params) {
  return useQuery({ queryKey: ['subscription', 'transactions', params], queryFn: () => subscriptionsApi.getMyTransactions(params) })
}

export function useMyUsageHistory(params) {
  return useQuery({ queryKey: ['subscription', 'usageHistory', params], queryFn: () => subscriptionsApi.getMyUsageHistory(params) })
}
