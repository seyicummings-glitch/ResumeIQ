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

/**
 * @typedef {Object} ConversationSummary
 * @property {number} id
 * @property {string|null} title
 * @property {string} createdAt
 * @property {string} updatedAt
 */

function toSummary(row) {
  return { id: row.id, title: row.title, createdAt: row.created_at, updatedAt: row.updated_at }
}

function toConversation(row) {
  return { ...toSummary(row), messages: row.messages || [], extra: row.extra ?? null }
}

/** History list for a kind that supports multiple conversations (currently just the AI Resume
 * Builder) — most recently updated first. Powers the history sidebar.
 * @param {'resume_builder'|'career_coach'} kind
 * @returns {Promise<ConversationSummary[]>}
 */
export async function listAiConversations(kind) {
  const { conversations } = await apiRequest(`/ai-conversations/${kind}/history`, { auth: true })
  return conversations.map(toSummary)
}

/** Starts a brand new, empty conversation — the "New Chat" action.
 * @param {'resume_builder'|'career_coach'} kind
 */
export async function createAiConversation(kind) {
  const row = await apiRequest(`/ai-conversations/${kind}/history`, { method: 'POST', auth: true })
  return toConversation(row)
}

/** Loads one specific past conversation by id — clicking into it from the history list.
 * @param {'resume_builder'|'career_coach'} kind
 */
export async function getAiConversationById(kind, conversationId) {
  const row = await apiRequest(`/ai-conversations/${kind}/history/${conversationId}`, { auth: true })
  return toConversation(row)
}

/** Saves the full current state of one specific conversation by id.
 * @param {'resume_builder'|'career_coach'} kind
 * @param {{messages: Array<Object>, extra?: Object|null}} state
 */
export async function saveAiConversationById(kind, conversationId, { messages, extra }) {
  const row = await apiRequest(`/ai-conversations/${kind}/history/${conversationId}`, {
    method: 'PUT',
    auth: true,
    body: { messages, extra: extra ?? null },
  })
  return toConversation(row)
}

/** Removes one specific conversation from the history list.
 * @param {'resume_builder'|'career_coach'} kind
 */
export function deleteAiConversationById(kind, conversationId) {
  return apiRequest(`/ai-conversations/${kind}/history/${conversationId}`, { method: 'DELETE', auth: true })
}
