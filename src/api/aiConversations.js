import { apiRequest } from './client'

/**
 * @typedef {Object} AiConversationState
 * @property {Array<Object>} messages
 * @property {Object|null} extra - feature-specific extra state (e.g. the Resume Builder's draft)
 * @property {string|null} updated_at
 */

/** Loads the saved conversation for this account — so opening the AI Resume Builder or Career
 * Coach on a different browser/device picks up where it left off instead of starting blank.
 * @param {'resume_builder'|'career_coach'} kind
 * @returns {Promise<AiConversationState>}
 */
export function getAiConversation(kind) {
  return apiRequest(`/ai-conversations/${kind}`, { auth: true })
}

/** Upserts the full current state of a conversation.
 * @param {'resume_builder'|'career_coach'} kind
 * @param {{messages: Array<Object>, extra?: Object|null}} state
 * @returns {Promise<AiConversationState>}
 */
export function saveAiConversation(kind, { messages, extra }) {
  return apiRequest(`/ai-conversations/${kind}`, {
    method: 'PUT',
    auth: true,
    body: { messages, extra: extra ?? null },
  })
}

/** @param {'resume_builder'|'career_coach'} kind */
export function clearAiConversation(kind) {
  return apiRequest(`/ai-conversations/${kind}`, { method: 'DELETE', auth: true })
}
