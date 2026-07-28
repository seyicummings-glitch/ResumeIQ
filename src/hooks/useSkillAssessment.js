import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAssessmentBuild, getAssessmentHistory, submitAssessment } from '../api/skillAssessment'

export function useSkillAssessmentBuild(options = {}) {
  return useQuery({
    queryKey: ['skillAssessment', 'build'],
    queryFn: getAssessmentBuild,
    ...options,
  })
}

export function useSubmitSkillAssessment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: submitAssessment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skillAssessment', 'history'] })
    },
  })
}

export function useSkillAssessmentHistory() {
  return useQuery({ queryKey: ['skillAssessment', 'history'], queryFn: getAssessmentHistory })
}
