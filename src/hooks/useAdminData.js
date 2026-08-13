import { useMutation, useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import * as adminApi from '../api/admin'

// 20s: real-time-enough for an admin dashboard without hammering the backend --
// see the "Real-Time Updates" requirement (polling, not WebSockets, per the
// architecture note in AdminDashboardPage.jsx).
const DASHBOARD_POLL_INTERVAL_MS = 20_000

export function useAdminDashboard() {
  return useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: adminApi.getDashboard,
    refetchInterval: DASHBOARD_POLL_INTERVAL_MS,
  })
}

export function useAdminActivityFeed(limit = 20) {
  return useQuery({
    queryKey: ['admin', 'activityFeed', limit],
    queryFn: () => adminApi.getActivityFeed(limit),
    refetchInterval: DASHBOARD_POLL_INTERVAL_MS,
  })
}

export function useAdminUsersPage(params) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => adminApi.getUsersPage(params),
    placeholderData: keepPreviousData,
  })
}

export function useAdminUserDetail(id) {
  return useQuery({
    queryKey: ['admin', 'users', 'detail', id],
    queryFn: () => adminApi.getUserDetail(id),
    enabled: id != null,
  })
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

export function useDeleteUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id) => adminApi.deleteUser(id),
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
