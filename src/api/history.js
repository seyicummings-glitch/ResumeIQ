import { apiRequest } from './client'

function toHistoryRecord(row) {
  return {
    id: row.id,
    resumeFilename: row.resume_filename,
    jobTitle: row.job_description_title || 'Untitled job description',
    overallScore: row.match_result.overall_match_score,
    analyzedAt: row.created_at,
    skillMatch: row.match_result.skill_match,
    experienceMatch: row.match_result.experience_match,
    qualificationMatch: row.match_result.qualification_match,
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
