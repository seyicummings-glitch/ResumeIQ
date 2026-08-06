import { useMutation, useQuery } from '@tanstack/react-query'
import { getInterviewQuestions, sendInterviewMessage, saveInterviewSession } from '../api/interview'

export function useInterviewQuestions() {
  return useQuery({
    queryKey: ['interview', 'questions'],
    queryFn: getInterviewQuestions,
  })
}

export function useInterviewChat() {
  return useMutation({ mutationFn: sendInterviewMessage })
}

export function useSaveInterviewSession() {
  return useMutation({ mutationFn: saveInterviewSession })
}
