import { useMutation, useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import * as skillResourcesApi from '../api/adminSkillResources'

export function useAdminSkillResourcesPage(params) {
  return useQuery({
    queryKey: ['admin', 'skill-resources', params],
    queryFn: () => skillResourcesApi.getSkillResourcesPage(params),
    placeholderData: keepPreviousData,
  })
}

export function useCreateSkillResource() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (fields) => skillResourcesApi.createSkillResource(fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'skill-resources'] }),
  })
}

export function useUpdateSkillResource() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, fields }) => skillResourcesApi.updateSkillResource(id, fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'skill-resources'] }),
  })
}

export function useDeleteSkillResource() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id) => skillResourcesApi.deleteSkillResource(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'skill-resources'] }),
  })
}
