import { apiRequest } from './client'

/**
 * @typedef {Object} SkillQuestion
 * @property {number} id
 * @property {string} category_key
 * @property {string} category_label
 * @property {'beginner'|'intermediate'|'advanced'} difficulty
 * @property {string} question
 * @property {string[]} options
 * @property {number} correct_index
 * @property {string} explanation
 * @property {string} tip
 *
 * @typedef {Object} SoftScenario
 * @property {string} category
 * @property {string} scenario
 *
 * @typedef {Object} AssessmentBuild
 * @property {SkillQuestion[]} questions
 * @property {SoftScenario[]} soft_scenarios
 * @property {string[]} detected_categories
 * @property {boolean} has_analysis
 *
 * @typedef {Object} CategoryBreakdownEntry
 * @property {string} category_key
 * @property {string} category_label
 * @property {number} correct
 * @property {number} total
 * @property {number} pct
 *
 * @typedef {Object} AssessmentResult
 * @property {number} technical_score
 * @property {number} soft_score
 * @property {number} overall_score
 * @property {number} correct_count
 * @property {number} total
 * @property {CategoryBreakdownEntry[]} category_breakdown
 * @property {number} attempt_id
 *
 * @typedef {Object} AssessmentAttempt
 * @property {number} id
 * @property {number} technical_score
 * @property {number} soft_score
 * @property {number} overall_score
 * @property {CategoryBreakdownEntry[]} category_breakdown
 * @property {string} created_at
 */

/**
 * Personalizes a technical question set + soft-skill scenarios from the user's
 * latest saved analysis (resume skills + missing skills).
 * @returns {Promise<AssessmentBuild>}
 */
export function getAssessmentBuild() {
  return apiRequest('/skill-assessment/build', { auth: true })
}

/**
 * Scores are always recomputed server-side from the question ids + answers — the
 * client never sends a score directly.
 * @param {{questionIds: number[], technicalAnswers: Object<string, number>, softAnswerTexts: string[]}} params
 * @returns {Promise<AssessmentResult>}
 */
export function submitAssessment({ questionIds, technicalAnswers, softAnswerTexts }) {
  return apiRequest('/skill-assessment/submit', {
    method: 'POST',
    auth: true,
    body: {
      question_ids: questionIds,
      technical_answers: technicalAnswers,
      soft_answer_texts: softAnswerTexts,
    },
  })
}

/**
 * @returns {Promise<AssessmentAttempt[]>}
 */
export function getAssessmentHistory() {
  return apiRequest('/skill-assessment/history', { auth: true })
}
