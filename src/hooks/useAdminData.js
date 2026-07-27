import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as adminApi from '../api/admin'

export function useAdminUsers() {
  return useQuery({ queryKey: ['admin', 'users'], queryFn: adminApi.getUsers })
}

export function useSetUserStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }) => adminApi.setUserStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, fields }) => adminApi.updateUser(id, fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useAdminReports() {
  return useQuery({ queryKey: ['admin', 'reports'], queryFn: adminApi.getReports })
}

export function useUpdateReportStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }) => adminApi.updateReportStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'reports'] }),
  })
}

export function useAdminAnalytics() {
  return useQuery({ queryKey: ['admin', 'analytics'], queryFn: adminApi.getAnalytics })
}

export function useAdminSettings() {
  return useQuery({ queryKey: ['admin', 'settings'], queryFn: adminApi.getSettings })
}

export function useUpdateAdminSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: adminApi.updateSettings,
    onSuccess: (data) => queryClient.setQueryData(['admin', 'settings'], data),
  })
}
