import { useQuery } from '@tanstack/react-query'
import { getResumeVersions, compareResumeVersions } from '../api/resumeVersions'

export function useResumeVersions() {
  return useQuery({ queryKey: ['resumeVersions'], queryFn: getResumeVersions })
}

export function useCompareResumeVersions(aId, bId) {
  return useQuery({
    queryKey: ['resumeVersions', 'compare', aId, bId],
    queryFn: () => compareResumeVersions({ aId, bId }),
    enabled: Boolean(aId) && Boolean(bId) && aId !== bId,
  })
}
