import { useQuery } from '@tanstack/react-query'
import { getAnalysisHistory, getAnalysisDetail } from '../api/history'

export function useAnalysisHistory() {
  return useQuery({ queryKey: ['analysisHistory'], queryFn: getAnalysisHistory })
}

export function useAnalysisDetail(id) {
  return useQuery({ queryKey: ['analysisHistory', id], queryFn: () => getAnalysisDetail(id), enabled: Boolean(id) })
}
