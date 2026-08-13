import { apiRequest } from './client'

/**
 * @typedef {Object} ContactInfo
 * @property {string} fullName
 * @property {string} email
 * @property {string} phone
 * @property {string} linkedin
 * @property {string} location
 * @property {string} portfolio
 *
 * @typedef {Object} ExperienceItem
 * @property {string} title
 * @property {string} company
 * @property {string} startDate
 * @property {string} endDate
 * @property {string[]} bullets - achievement-focused, quantified accomplishments
 *
 * @typedef {Object} EducationItem
 * @property {string} degree
 * @property {string} school
 * @property {string} date
 *
 * @typedef {Object} Skills
 * @property {string[]} technical - hard skills, tools, technologies, domain competencies
 * @property {string[]} soft - interpersonal/workplace skills
 *
 * @typedef {Object} ProjectItem
 * @property {string} name
 * @property {string} description
 * @property {string[]} technologies
 * @property {string[]} bullets - results achieved
 *
 * @typedef {Object} LanguageItem
 * @property {string} name
 * @property {string} proficiency
 *
 * @typedef {Object} EnhancedResumeResult
 * @property {string} title
 * @property {string} summary
 * @property {Skills} skills
 * @property {ExperienceItem[]} experience
 * @property {EducationItem[]} education
 * @property {string[]} certifications
 * @property {ProjectItem[]} projects
 * @property {LanguageItem[]} languages
 * @property {string[]} references
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
    portfolio: row?.portfolio || '',
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

function toSkills(row) {
  return { technical: row?.technical || [], soft: row?.soft || [] }
}

function toProjects(rows) {
  return (rows || []).map((project) => ({
    name: project.name || '', description: project.description || '',
    technologies: project.technologies || [], bullets: project.bullets || [],
  }))
}

function toLanguages(rows) {
  return (rows || []).map((lang) => ({ name: lang.name || '', proficiency: lang.proficiency || '' }))
}

function toEnhancedResumeResult(row) {
  return {
    title: row.title || '',
    summary: row.summary,
    skills: toSkills(row.skills),
    experience: toExperience(row.experience),
    education: toEducation(row.education),
    certifications: row.certifications || [],
    projects: toProjects(row.projects),
    languages: toLanguages(row.languages),
    references: row.references || [],
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
 * @property {Skills} skills
 * @property {ExperienceItem[]} experience
 * @property {EducationItem[]} education
 * @property {string[]} certifications
 * @property {ProjectItem[]} projects
 * @property {LanguageItem[]} languages
 * @property {string[]} references
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
 * @param {{conversation:BuilderChatMessage[], currentDraft: {title:string, summary:string, skills:Skills, experience:ExperienceItem[], education:EducationItem[], certifications:string[], projects:ProjectItem[], languages:LanguageItem[], references:string[]}, jdContent?:string, attachment?:BuilderChatAttachment|null}} params
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
      current_skills: {
        technical: currentDraft.skills?.technical || [],
        soft: currentDraft.skills?.soft || [],
      },
      current_experience: (currentDraft.experience || []).map((job) => ({
        title: job.title, company: job.company, start_date: job.startDate, end_date: job.endDate, bullets: job.bullets,
      })),
      current_education: (currentDraft.education || []).map((edu) => ({ degree: edu.degree, school: edu.school, date: edu.date })),
      current_certifications: currentDraft.certifications || [],
      current_projects: (currentDraft.projects || []).map((project) => ({
        name: project.name, description: project.description, technologies: project.technologies, bullets: project.bullets,
      })),
      current_languages: (currentDraft.languages || []).map((lang) => ({ name: lang.name, proficiency: lang.proficiency })),
      current_references: currentDraft.references || [],
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
    skills: toSkills(row.skills),
    experience: toExperience(row.experience),
    education: toEducation(row.education),
    certifications: row.certifications || [],
    projects: toProjects(row.projects),
    languages: toLanguages(row.languages),
    references: row.references || [],
    contact: toContact(row.contact),
    source: row.source,
  }
}

/**
 * Saves the chat-built draft as a new resume version. resumeId is optional — omit it when the
 * draft was built entirely from scratch through conversation with no prior uploaded resume.
 * @returns {Promise<{message:string, resumeId:number, version:number, label:string}>}
 */
export async function saveEnhancedResume({
  resumeId, title, summary, skills, experience, education, certifications, projects, languages, references,
}) {
  const row = await apiRequest('/resume-builder/save', {
    method: 'POST',
    auth: true,
    body: {
      resume_id: resumeId ?? undefined,
      title: title || '',
      summary,
      skills: { technical: skills?.technical || [], soft: skills?.soft || [] },
      experience: (experience || []).map((job) => ({
        title: job.title, company: job.company, start_date: job.startDate, end_date: job.endDate, bullets: job.bullets,
      })),
      education: (education || []).map((edu) => ({ degree: edu.degree, school: edu.school, date: edu.date })),
      certifications: certifications || [],
      projects: (projects || []).map((project) => ({
        name: project.name, description: project.description, technologies: project.technologies, bullets: project.bullets,
      })),
      languages: (languages || []).map((lang) => ({ name: lang.name, proficiency: lang.proficiency })),
      references: references || [],
    },
  })
  return {
    message: row.message,
    resumeId: row.resume_id,
    version: row.version,
    label: row.label,
  }
}
