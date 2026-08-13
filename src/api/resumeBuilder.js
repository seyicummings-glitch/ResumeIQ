import { apiRequest } from './client'

/**
 * @typedef {Object} ContactInfo
 * @property {string} fullName
 * @property {string} email
 * @property {string} phone
 * @property {string} linkedin
 * @property {string} location
 *
 * @typedef {Object} ExperienceItem
 * @property {string} title
 * @property {string} company
 * @property {string} startDate
 * @property {string} endDate
 * @property {string[]} bullets
 *
 * @typedef {Object} EducationItem
 * @property {string} degree
 * @property {string} school
 * @property {string} date
 *
 * @typedef {Object} EnhancedResumeResult
 * @property {string} title
 * @property {string} summary
 * @property {string[]} skills
 * @property {ExperienceItem[]} experience
 * @property {EducationItem[]} education
 * @property {string[]} certifications
 * @property {ContactInfo} contact - real profile contact info, never AI-generated
 * @property {'ai'|'fallback'} source
 * @property {string|undefined} overallAssessment - present on fallback responses
 * @property {number} resumeId - the source resume this was generated from
 */

function toContact(row) {
  return {
    fullName: row?.full_name || '',
    email: row?.email || '',
    phone: row?.phone || '',
    linkedin: row?.linkedin || '',
    location: row?.location || '',
  }
}

function toExperience(rows) {
  return (rows || []).map((job) => ({
    title: job.title || '', company: job.company || '',
    startDate: job.start_date || '', endDate: job.end_date || '',
    bullets: job.bullets || [],
  }))
}

function toEducation(rows) {
  return (rows || []).map((edu) => ({ degree: edu.degree || '', school: edu.school || '', date: edu.date || '' }))
}

function toEnhancedResumeResult(row) {
  return {
    title: row.title || '',
    summary: row.summary,
    skills: row.skills || [],
    experience: toExperience(row.experience),
    education: toEducation(row.education),
    certifications: row.certifications || [],
    contact: toContact(row.contact),
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
 * @property {string} title
 * @property {string} summary
 * @property {string[]} skills
 * @property {ExperienceItem[]} experience
 * @property {EducationItem[]} education
 * @property {string[]} certifications
 * @property {ContactInfo} contact
 * @property {'ai'|'fallback'} source
 */

/**
 * One turn of conversational resume building/editing. Send the full transcript so far (not
 * including the reply being requested) plus the current draft, and get back the assistant's
 * reply and the updated draft — no server-side session, the frontend owns both. The backend
 * always grounds on whatever resume is currently active on the account (if any); uploading a
 * file mid-conversation makes it active, so the next turn picks it up automatically. Contact
 * info always comes back sourced from the user's real profile, never from the AI.
 * @typedef {Object} BuilderChatAttachment
 * @property {string} filename
 * @property {string} mimeType
 * @property {string} dataBase64
 *
 * @param {{conversation:BuilderChatMessage[], currentDraft: {title:string, summary:string, skills:string[], experience:ExperienceItem[], education:EducationItem[], certifications:string[]}, jdContent?:string, attachment?:BuilderChatAttachment|null}} params
 * @returns {Promise<BuilderChatReply>}
 */
export async function chatAboutResume({ conversation, currentDraft, jdContent, attachment }) {
  const row = await apiRequest('/resume-builder/chat', {
    method: 'POST',
    auth: true,
    body: {
      conversation,
      current_title: currentDraft.title || '',
      current_summary: currentDraft.summary || '',
      current_skills: currentDraft.skills || [],
      current_experience: (currentDraft.experience || []).map((job) => ({
        title: job.title, company: job.company, start_date: job.startDate, end_date: job.endDate, bullets: job.bullets,
      })),
      current_education: (currentDraft.education || []).map((edu) => ({ degree: edu.degree, school: edu.school, date: edu.date })),
      current_certifications: currentDraft.certifications || [],
      jd_content: jdContent || '',
      attachment: attachment
        ? { filename: attachment.filename, mime_type: attachment.mimeType, data_base64: attachment.dataBase64 }
        : null,
    },
  })
  return {
    reply: row.reply,
    title: row.title || '',
    summary: row.summary,
    skills: row.skills || [],
    experience: toExperience(row.experience),
    education: toEducation(row.education),
    certifications: row.certifications || [],
    contact: toContact(row.contact),
    source: row.source,
  }
}

/**
 * Saves the chat-built draft as a new resume version. resumeId is optional — omit it when the
 * draft was built entirely from scratch through conversation with no prior uploaded resume.
 * @returns {Promise<{message:string, resumeId:number, version:number, label:string}>}
 */
export async function saveEnhancedResume({ resumeId, title, summary, skills, experience, education, certifications }) {
  const row = await apiRequest('/resume-builder/save', {
    method: 'POST',
    auth: true,
    body: {
      resume_id: resumeId ?? undefined,
      title: title || '',
      summary,
      skills: skills || [],
      experience: (experience || []).map((job) => ({
        title: job.title, company: job.company, start_date: job.startDate, end_date: job.endDate, bullets: job.bullets,
      })),
      education: (education || []).map((edu) => ({ degree: edu.degree, school: edu.school, date: edu.date })),
      certifications: certifications || [],
    },
  })
  return {
    message: row.message,
    resumeId: row.resume_id,
    version: row.version,
    label: row.label,
  }
}
