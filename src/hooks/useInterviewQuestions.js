import { useQuery } from '@tanstack/react-query'
import { getInterviewQuestions } from '../api/interview'

export function useInterviewQuestions() {
  return useQuery({
    queryKey: ['interview', 'questions'],
    queryFn: getInterviewQuestions,
  })
}
