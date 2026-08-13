import { apiRequest } from './client'

/**
 * @typedef {Object} SkillMatch
 * @property {number} skill_score
 * @property {string[]} matched_skills
 * @property {string[]} missing_skills
 *
 * @typedef {Object} LatestScores
 * @property {number} overall_match_score
 * @property {SkillMatch} skill_match
 *
 * @typedef {Object} ResumeVersion
 * @property {number} id
 * @property {string} filename
 * @property {string|null} label
 * @property {number} version
 * @property {boolean} isActive
 * @property {string} uploadedAt
 * @property {string[]} skills
 * @property {LatestScores|null} latestScores
 * @property {number|null} latestAnalysisId
 * @property {number|null} latestJobDescriptionId
 * @property {string|null} latestJobTitle
 * @property {boolean} hasDownloadableFile
 */

function toResumeVersion(row) {
  return {
    id: row.id,
    filename: row.filename,
    label: row.label,
    version: row.version,
    isActive: row.is_active,
    uploadedAt: row.uploaded_at,
    skills: row.skills,
    latestScores: row.latest_scores,
    latestAnalysisId: row.latest_analysis_id,
    latestJobDescriptionId: row.latest_job_description_id,
    latestJobTitle: row.latest_job_title,
    hasDownloadableFile: row.has_downloadable_file,
  }
}

/** @returns {Promise<ResumeVersion[]>} */
export async function getResumeVersions() {
  const rows = await apiRequest('/resume/versions', { auth: true })
  return rows.map(toResumeVersion)
}

/**
 * @returns {Promise<{resumeA: ResumeVersion, resumeB: ResumeVersion, skillDiff: {resolved:string[], remaining:string[], added:string[]}|null}>}
 */
export async function compareResumeVersions({ aId, bId }) {
  const row = await apiRequest('/resume/versions/compare', {
    auth: true,
    query: { a: aId, b: bId },
  })
  return {
    resumeA: toResumeVersion(row.resume_a),
    resumeB: toResumeVersion(row.resume_b),
    skillDiff: row.skill_diff,
  }
}
