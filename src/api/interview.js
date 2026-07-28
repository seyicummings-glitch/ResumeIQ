import { apiRequest } from './client'

/**
 * @typedef {Object} InterviewQuestion
 * @property {number} id
 * @property {'Behavioral'|'Technical'|'System Design'|'Role-Specific'} category
 * @property {'Easy'|'Medium'|'Hard'} difficulty
 * @property {string} question
 * @property {string} tip
 * @property {string} sample_answer
 * @property {string} relevance
 *
 * @typedef {Object} InterviewQuestionsResult
 * @property {InterviewQuestion[]} questions
 * @property {boolean} has_analysis
 * @property {string} [jd_title]
 */

/** @returns {Promise<InterviewQuestionsResult>} */
export function getInterviewQuestions() {
  return apiRequest('/interview/questions', { auth: true })
}
