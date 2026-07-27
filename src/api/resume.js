import { apiRequest, toFormData } from './client'

export const ALLOWED_RESUME_EXTENSIONS = ['.pdf', '.docx']
export const MAX_RESUME_FILE_SIZE_MB = 10

/**
 * @typedef {Object} ContactInfo
 * @property {string|null} email
 * @property {string|null} phone
 * @property {string|null} linkedin
 *
 * @typedef {Object} StructuredResume
 * @property {ContactInfo} contact_info
 * @property {string} summary
 * @property {string[]} skills
 * @property {string} experience
 * @property {string} education
 * @property {string} certifications
 * @property {string} projects
 *
 * @typedef {Object} AtsSubScore
 * @property {number} contact_score
 * @property {number} section_score
 * @property {number} skills_score
 * @property {number} skills_count
 * @property {number} extraction_score
 * @property {number} character_count
 * @property {number} format_score
 * @property {string} file_extension
 *
 * @typedef {Object} AtsResult
 * @property {number} overall_ats_score - 0-100
 * @property {{contact_score:number, issues:string[]}} contact_completeness
 * @property {{section_score:number, issues:string[]}} section_completeness
 * @property {{skills_score:number, skills_count:number, issues:string[]}} skills_detected
 * @property {{extraction_score:number, character_count:number, issues:string[]}} text_extraction_health
 * @property {{format_score:number, file_extension:string, issues:string[]}} file_format_risk
 * @property {string[]} issues - combined issue list across all sub-scores
 *
 * @typedef {Object} AiSuggestion
 * @property {string} category
 * @property {string} issue
 * @property {string} suggestion
 *
 * @typedef {Object} AiSuggestionsResult
 * @property {string} overall_assessment
 * @property {AiSuggestion[]} suggestions
 * @property {'ai'|'fallback'} source
 *
 * @typedef {Object} SavedResume
 * @property {number} id
 * @property {number} user_id
 * @property {string} filename
 * @property {string} raw_text
 * @property {string} skills - comma-separated
 * @property {string} experience
 * @property {string} education
 * @property {string} certifications
 * @property {string} projects
 * @property {string} uploaded_at
 */

/** @returns {Promise<{filename:string, extracted_text_preview:string, character_count:number}>} */
export function uploadResume(file) {
  return apiRequest('/resume/upload', { method: 'POST', body: toFormData({ file }) })
}

/** @returns {Promise<{filename:string, structured_data:StructuredResume}>} */
export function structureResume(file) {
  return apiRequest('/resume/structure', { method: 'POST', body: toFormData({ file }) })
}

/** @returns {Promise<{filename:string, ats_result:AtsResult}>} */
export function getAtsScore(file) {
  return apiRequest('/resume/ats-score', { method: 'POST', body: toFormData({ file }) })
}

/** @returns {Promise<{filename:string, ai_suggestions:AiSuggestionsResult}>} */
export function getAiSuggestions(file, jobDescription) {
  return apiRequest('/resume/ai-suggestions', {
    method: 'POST',
    body: toFormData({ file, job_description: jobDescription || undefined }),
  })
}

/** @returns {Promise<{message:string, resume_id:number, filename:string, uploaded_at:string}>} */
export function saveResume(file) {
  return apiRequest('/resume/save', { method: 'POST', auth: true, body: toFormData({ file }) })
}

/** @returns {Promise<SavedResume[]>} */
export function getMyResumes() {
  return apiRequest('/resume/my-resumes', { auth: true })
}
