import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAnalysisHistory, getAnalysisDetail } from '../api/history'
import { deleteAnalysis, compareAnalyses } from '../api/matching'

export function useAnalysisHistory() {
  return useQuery({ queryKey: ['analysisHistory'], queryFn: getAnalysisHistory })
}

export function useAnalysisDetail(id) {
  return useQuery({ queryKey: ['analysisHistory', id], queryFn: () => getAnalysisDetail(id), enabled: Boolean(id) })
}

export function useDeleteAnalysis() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteAnalysis,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysisHistory'] })
      queryClient.invalidateQueries({ queryKey: ['resumeVersions'] })
    },
  })
}

export function useCompareAnalyses(aId, bId) {
  return useQuery({
    queryKey: ['analysisHistory', 'compare', aId, bId],
    queryFn: () => compareAnalyses({ aId, bId }),
    enabled: Boolean(aId) && Boolean(bId) && aId !== bId,
  })
}
