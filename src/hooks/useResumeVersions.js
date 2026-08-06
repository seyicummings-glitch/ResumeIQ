import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getResumeVersions, compareResumeVersions } from '../api/resumeVersions'
import { deleteResume, downloadResumeFile } from '../api/resume'

export function useResumeVersions() {
  return useQuery({ queryKey: ['resumeVersions'], queryFn: getResumeVersions })
}

export function useDeleteResume() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteResume,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumeVersions'] })
      queryClient.invalidateQueries({ queryKey: ['analysisHistory'] })
    },
  })
}

/** Deletes several resumes at once (existing per-resume DELETE, called in parallel). A
 * partial failure still deletes the ones that succeeded — the caller is told how many failed. */
export function useBulkDeleteResumes() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (resumeIds) => {
      const results = await Promise.allSettled(resumeIds.map((id) => deleteResume(id)))
      const failed = results.filter((result) => result.status === 'rejected').length
      return { total: resumeIds.length, failed }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumeVersions'] })
      queryClient.invalidateQueries({ queryKey: ['analysisHistory'] })
    },
  })
}

export function useDownloadResume() {
  return useMutation({
    mutationFn: ({ resumeId, filename }) => downloadResumeFile(resumeId, filename),
  })
}

export function useCompareResumeVersions(aId, bId) {
  return useQuery({
    queryKey: ['resumeVersions', 'compare', aId, bId],
    queryFn: () => compareResumeVersions({ aId, bId }),
    enabled: Boolean(aId) && Boolean(bId) && aId !== bId,
  })
}
