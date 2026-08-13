import { apiRequest } from './client'

/**
 * @typedef {Object} CoachChatMessage
 * @property {'user'|'coach'} role
 * @property {string} content
 *
 * @typedef {Object} CoachChatReply
 * @property {string} reply
 * @property {'ai'|'fallback'} source
 */

/**
 * One turn of the AI Career Coach chat — the single persistent AI assistant available from
 * anywhere in the app. Always grounded in the user's whole account (resume, target role, skill
 * gaps, roadmap, latest skill assessment and mock interview results), not just whichever page
 * it was opened from. Optionally scoped further to a specific roadmap topic (topicKey).
 * @param {{conversation: CoachChatMessage[], topicKey?: string|null}} params
 * @returns {Promise<CoachChatReply>}
 */
export function sendCareerCoachMessage({ conversation, topicKey }) {
  return apiRequest('/career-coach/chat', {
    method: 'POST',
    auth: true,
    body: { conversation, topic_key: topicKey || null },
  })
}
