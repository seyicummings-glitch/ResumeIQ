import { apiRequest } from './client'

/**
 * @typedef {Object} EnhancedResumeResult
 * @property {string} summary
 * @property {string[]} experienceBullets
 * @property {string} skillsSection
 * @property {'ai'|'fallback'} source
 * @property {string|undefined} overallAssessment - present on fallback responses
 * @property {number} resumeId - the source resume this was generated from
 */

function toEnhancedResumeResult(row) {
  return {
    summary: row.summary,
    experienceBullets: row.experience_bullets,
    skillsSection: row.skills_section,
    source: row.source,
    overallAssessment: row.overall_assessment,
    resumeId: row.resume_id,
  }
}

/** @returns {Promise<EnhancedResumeResult>} */
export async function generateEnhancedResume() {
  const row = await apiRequest('/resume-builder/generate', { method: 'POST', auth: true })
  return toEnhancedResumeResult(row)
}

/** @returns {Promise<{message:string, resumeId:number, version:number, label:string}>} */
export async function saveEnhancedResume({ resumeId, summary, experienceBullets, skillsSection }) {
  const row = await apiRequest('/resume-builder/save', {
    method: 'POST',
    auth: true,
    body: {
      resume_id: resumeId,
      summary,
      experience_bullets: experienceBullets,
      skills_section: skillsSection,
    },
  })
  return {
    message: row.message,
    resumeId: row.resume_id,
    version: row.version,
    label: row.label,
  }
}
