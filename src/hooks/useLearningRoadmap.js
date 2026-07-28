import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getRoadmap, toggleRoadmapItem } from '../api/roadmap'

export function useLearningRoadmap() {
  return useQuery({
    queryKey: ['roadmap'],
    queryFn: getRoadmap,
  })
}

export function useToggleRoadmapItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: toggleRoadmapItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roadmap'] })
    },
  })
}
