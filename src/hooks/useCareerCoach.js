import { useMutation } from '@tanstack/react-query'
import { sendCareerCoachMessage } from '../api/careerCoach'

export function useCareerCoach() {
  return useMutation({ mutationFn: sendCareerCoachMessage })
}
