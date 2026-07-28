import { useMutation, useQueryClient } from '@tanstack/react-query'
import { generateEnhancedResume, saveEnhancedResume } from '../api/resumeBuilder'

export function useGenerateEnhancedResume() {
  return useMutation({
    mutationFn: generateEnhancedResume,
  })
}

export function useSaveEnhancedResume() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: saveEnhancedResume,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] })
      queryClient.invalidateQueries({ queryKey: ['resumeVersions'] })
    },
  })
}
