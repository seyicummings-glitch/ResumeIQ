import { apiRequest } from './client'

/**
 * @typedef {Object} AssessmentQuestion
 * @property {number} id
 * @property {'technical'|'scenario'|'problem_solving'|'behavioral'} type
 * @property {'text'|'multiple_choice'} input_type
 * @property {string} category
 * @property {'beginner'|'intermediate'|'advanced'} [difficulty]
 * @property {string} question
 * @property {string[]} [options] - multiple_choice only
 * @property {number} [correct_index] - multiple_choice only
 * @property {string} [explanation] - multiple_choice only
 * @property {string} [tip] - multiple_choice only
 *
 * @typedef {Object} AssessmentBuild
 * @property {number|null} session_id
 * @property {'ai'|'fallback'|null} source
 * @property {AssessmentQuestion[]} questions
 * @property {string[]} detected_categories
 * @property {boolean} has_context
 * @property {string} [jd_title]
 *
 * @typedef {Object} CategoryBreakdownEntry
 * @property {string} category_key
 * @property {string} category_label
 * @property {number} pct
 *
 * @typedef {Object} QuestionFeedback
 * @property {number} question_id
 * @property {'technical'|'scenario'|'problem_solving'|'behavioral'} type
 * @property {string} category
 * @property {string} [difficulty]
 * @property {string} question
 * @property {string|null} answer
 * @property {number} score
 * @property {boolean} is_correct
 * @property {string} explanation
 * @property {string} correct_answer_or_improvement
 *
 * @typedef {Object} AssessmentResult
 * @property {number} technical_score
 * @property {number} soft_score
 * @property {number} overall_score
 * @property {number} correct_count
 * @property {number} total
 * @property {CategoryBreakdownEntry[]} category_breakdown
 * @property {QuestionFeedback[]} question_feedback
 * @property {'ai'|'fallback'} source
 * @property {number} attempt_id
 *
 * @typedef {Object} AssessmentAttempt
 * @property {number} id
 * @property {number} technical_score
 * @property {number} soft_score
 * @property {number} overall_score
 * @property {CategoryBreakdownEntry[]} category_breakdown
 * @property {'ai'|'fallback'} source
 * @property {string} created_at
 */

export const MIN_QUESTION_COUNT = 5
export const MAX_QUESTION_COUNT = 25
export const DEFAULT_QUESTION_COUNT = 15
export const QUESTION_COUNT_OPTIONS = [5, 10, 15, 20, 25]

/**
 * Builds a fresh, personalized assessment (technical, scenario-based,
 * problem-solving, and behavioral questions) from the user's latest saved
 * analysis. AI-generated and graded when a Gemini key is configured;
 * otherwise a randomized multiple-choice fallback bank.
 * @param {number} [questionCount] - total questions, 5-25 (default 15)
 * @returns {Promise<AssessmentBuild>}
 */
export function getAssessmentBuild(questionCount = DEFAULT_QUESTION_COUNT) {
  return apiRequest('/skill-assessment/build', { auth: true, query: { question_count: questionCount } })
}

/**
 * @typedef {Object} AssessmentAnswer
 * @property {number} questionId
 * @property {string} [answerText] - free-text questions
 * @property {number} [answerIndex] - multiple_choice questions
 *
 * Scores are always recomputed server-side from the session's stored rubric —
 * the client never sends a score or the correct answer directly.
 * @param {{sessionId: number, answers: AssessmentAnswer[]}} params
 * @returns {Promise<AssessmentResult>}
 */
export function submitAssessment({ sessionId, answers }) {
  return apiRequest('/skill-assessment/submit', {
    method: 'POST',
    auth: true,
    body: {
      session_id: sessionId,
      answers: answers.map(({ questionId, answerText, answerIndex }) => ({
        question_id: questionId,
        answer_text: answerText ?? null,
        answer_index: answerIndex ?? null,
      })),
    },
  })
}

/**
 * @returns {Promise<AssessmentAttempt[]>}
 */
export function getAssessmentHistory() {
  return apiRequest('/skill-assessment/history', { auth: true })
}
