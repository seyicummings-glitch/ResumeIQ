import { simulateLatency } from './sampleData/simulateLatency'
import { analysisHistorySample } from './sampleData/analysisHistory.sample'

// TODO: the backend has an AnalysisResult DB table but no route reads or
// writes it yet. Swap these two functions for real apiRequest('/analysis/...')
// calls once that endpoint exists — HistoryPage/HistoryDetailPage and
// useAnalysisHistory don't need to change at all.

/** @returns {Promise<typeof analysisHistorySample>} */
export async function getAnalysisHistory() {
  await simulateLatency()
  return analysisHistorySample
}

export async function getAnalysisDetail(id) {
  await simulateLatency()
  const record = analysisHistorySample.find((r) => r.id === id)
  if (!record) throw new Error('Analysis record not found.')
  return record
}
