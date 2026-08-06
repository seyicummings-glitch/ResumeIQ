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

/**
 * @typedef {Object} BuilderChatMessage
 * @property {'user'|'assistant'} role
 * @property {string} content
 *
 * @typedef {Object} BuilderChatReply
 * @property {string} reply
 * @property {string} summary
 * @property {string[]} experienceBullets
 * @property {string} skillsSection
 * @property {'ai'|'fallback'} source
 */

/**
 * One turn of conversational resume building/editing. Send the full transcript so far (not
 * including the reply being requested) plus the current draft, and get back the assistant's
 * reply and the updated draft — no server-side session, the frontend owns both. The backend
 * always grounds on whatever resume is currently active on the account (if any); uploading a
 * file mid-conversation makes it active, so the next turn picks it up automatically.
 * @param {{conversation:BuilderChatMessage[], currentSummary:string, currentExperienceBullets:string[], currentSkillsSection:string, jdContent?:string}} params
 * @returns {Promise<BuilderChatReply>}
 */
export async function chatAboutResume({ conversation, currentSummary, currentExperienceBullets, currentSkillsSection, jdContent }) {
  const row = await apiRequest('/resume-builder/chat', {
    method: 'POST',
    auth: true,
    body: {
      conversation,
      current_summary: currentSummary,
      current_experience_bullets: currentExperienceBullets,
      current_skills_section: currentSkillsSection,
      jd_content: jdContent || '',
    },
  })
  return {
    reply: row.reply,
    summary: row.summary,
    experienceBullets: row.experience_bullets,
    skillsSection: row.skills_section,
    source: row.source,
  }
}

/**
 * Saves the chat-built draft as a new resume version. resumeId is optional — omit it when the
 * draft was built entirely from scratch through conversation with no prior uploaded resume.
 * @returns {Promise<{message:string, resumeId:number, version:number, label:string}>}
 */
export async function saveEnhancedResume({ resumeId, summary, experienceBullets, skillsSection }) {
  const row = await apiRequest('/resume-builder/save', {
    method: 'POST',
    auth: true,
    body: {
      resume_id: resumeId ?? undefined,
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
