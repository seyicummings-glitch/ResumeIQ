import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getRoadmap, regenerateRoadmap, toggleRoadmapTopic } from '../api/roadmap'

export function useLearningRoadmap() {
  return useQuery({
    queryKey: ['roadmap'],
    queryFn: getRoadmap,
  })
}

export function useRegenerateRoadmap() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: regenerateRoadmap,
    onSuccess: (data) => {
      queryClient.setQueryData(['roadmap'], data)
    },
  })
}

export function useToggleRoadmapTopic() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: toggleRoadmapTopic,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roadmap'] })
    },
  })
}
