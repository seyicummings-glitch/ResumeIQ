import { apiRequest, toFormData } from './client'

export const ALLOWED_JD_FILE_EXTENSIONS = ['.pdf', '.docx', '.txt']

/**
 * @typedef {Object} JobDescriptionAnalysis
 * @property {string[]} required_skills
 * @property {string} experience_level - e.g. "3+ years" or "Not specified"
 * @property {string[]} qualifications
 * @property {string[]} keywords
 *
 * @typedef {Object} ParsedJobDescription
 * @property {'text'|'file'|'url'} source
 * @property {string} [filename]
 * @property {string} [url]
 * @property {string} [extracted_text_preview]
 * @property {JobDescriptionAnalysis} job_description_analysis
 *
 * @typedef {Object} SavedJobDescription
 * @property {number} id
 * @property {string|null} title
 * @property {string} content
 * @property {string} created_at
 */

/** @returns {Promise<ParsedJobDescription>} */
export function parseText(content) {
  return apiRequest('/job-description/parse', { method: 'POST', body: { content } })
}

/** @returns {Promise<ParsedJobDescription>} */
export function parseFile(file) {
  return apiRequest('/job-description/parse-file', { method: 'POST', body: toFormData({ file }) })
}

/** @returns {Promise<ParsedJobDescription>} */
export function parseUrl(url) {
  return apiRequest('/job-description/parse-url', { method: 'POST', body: { url } })
}

/** @returns {Promise<SavedJobDescription>} */
export function saveJobDescription({ title, content }) {
  return apiRequest('/job-description/save', {
    method: 'POST',
    auth: true,
    body: { title: title || null, content },
  })
}

/** @returns {Promise<SavedJobDescription[]>} */
export function getMyJobDescriptions() {
  return apiRequest('/job-description/my-job-descriptions', { auth: true })
}
