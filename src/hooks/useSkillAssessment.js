import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAssessmentBuild, getAssessmentHistory, submitAssessment, DEFAULT_QUESTION_COUNT } from '../api/skillAssessment'

export function useSkillAssessmentBuild(questionCount = DEFAULT_QUESTION_COUNT, options = {}) {
  return useQuery({
    queryKey: ['skillAssessment', 'build', questionCount],
    queryFn: () => getAssessmentBuild(questionCount),
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
