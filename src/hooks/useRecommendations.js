import { useQuery } from '@tanstack/react-query'
import { getJobRecommendations } from '../api/recommendations'
import { ApiError } from '../api/client'

/**
 * Normalizes the backend's two "nothing to show" shapes into one:
 * a 404 (no saved resumes at all) and a 200 with an empty array + message
 * (resume exists, no saved job descriptions yet) both become
 * `{ recommendations: [], ... }`, distinguished by `noResumes`.
 */
export function useRecommendations({ resumeId } = {}) {
  return useQuery({
    queryKey: ['recommendations', resumeId ?? 'latest'],
    queryFn: async () => {
      try {
        return await getJobRecommendations({ resumeId })
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return { recommendations: [], noResumes: true, message: error.message }
        }
        throw error
      }
    },
  })
}
