import { apiRequest } from './client'

function toHistoryRecord(row) {
  return {
    id: row.id,
    resumeId: row.resume_id,
    resumeFilename: row.resume_filename,
    jobDescriptionId: row.job_description_id,
    jobTitle: row.job_description_title || 'Untitled job description',
    overallScore: row.match_result.overall_match_score,
    overallExplanation: row.match_result.overall_explanation || null,
    analyzedAt: row.created_at,
    skillMatch: row.match_result.skill_match,
    experienceMatch: row.match_result.experience_match,
    qualificationMatch: row.match_result.qualification_match,
    // Only present on analyses saved after ATS/keyword/writing enrichment shipped —
    // older saved analyses won't have these, so callers must handle null.
    atsResult: row.match_result.ats_result || null,
    keywordAnalysis: row.match_result.keyword_analysis || null,
    writingResult: row.match_result.writing_result || null,
    hiringReadinessScore: row.match_result.hiring_readiness_score ?? null,
    hiringReadinessExplanation: row.match_result.hiring_readiness_explanation || null,
  }
}

export async function getAnalysisHistory() {
  const rows = await apiRequest('/matching/history', { auth: true })
  return rows.map(toHistoryRecord)
}

export async function getAnalysisDetail(id) {
  const row = await apiRequest(`/matching/${id}`, { auth: true })
  return toHistoryRecord(row)
}
