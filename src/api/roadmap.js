import { apiRequest } from './client'

/**
 * @typedef {Object} RoadmapResource
 * @property {string} name
 * @property {'Course'|'Free'|'Book'|'Docs'|'Cert'|'Video'|'Article'|'Tutorial'} type
 * @property {string} provider
 *
 * @typedef {Object} RoadmapMilestones
 * @property {string} beginner
 * @property {string} intermediate
 * @property {string} advanced
 *
 * @typedef {Object} RoadmapQuizQuestion
 * @property {string} question
 * @property {string[]} options - exactly 4 options
 * @property {number} correct_index - 0-indexed
 * @property {string} explanation
 *
 * @typedef {Object} RoadmapTopic
 * @property {string} topic_key
 * @property {string} title
 * @property {string} why_it_matters
 * @property {string} current_gap - the candidate's specific gap for this topic
 * @property {string[]} learning_objectives
 * @property {RoadmapMilestones} milestones
 * @property {RoadmapResource[]} resources
 * @property {string[]} projects
 * @property {string[]} exercises
 * @property {RoadmapQuizQuestion[]} quiz
 * @property {number} estimated_hours
 * @property {'critical'|'high'|'medium'} priority
 * @property {boolean} done
 *
 * @typedef {Object} RoadmapStage
 * @property {'Foundation'|'Intermediate'|'Advanced'|'Job Ready'} stage
 * @property {string} description
 * @property {string} estimated_duration
 * @property {string} milestone
 * @property {RoadmapTopic[]} topics
 *
 * @typedef {Object} RoadmapStats
 * @property {number} total_hours
 * @property {number} done_count
 * @property {number} total_count
 *
 * @typedef {Object} Roadmap
 * @property {number} roadmap_id
 * @property {'ai'|'fallback'} source
 * @property {string|null} target_role
 * @property {string|null} industry
 * @property {RoadmapStage[]} stages
 * @property {string} created_at
 * @property {RoadmapStats} stats
 *
 * @typedef {Object} RoadmapResponse
 * @property {boolean} has_context
 * @property {Roadmap|null} roadmap
 */

/** @returns {Promise<RoadmapResponse>} */
export function getRoadmap() {
  return apiRequest('/roadmap', { auth: true })
}

/** Forces a brand-new roadmap to be generated, replacing the current one. @returns {Promise<RoadmapResponse>} */
export function regenerateRoadmap() {
  return apiRequest('/roadmap/regenerate', { method: 'POST', auth: true })
}

/**
 * @param {{topicKey: string}} params
 * @returns {Promise<{topic_key: string, completed: boolean}>}
 */
export function toggleRoadmapTopic({ topicKey }) {
  return apiRequest('/roadmap/topics/toggle', { method: 'POST', auth: true, body: { topic_key: topicKey } })
}

/**
 * Fire-and-forget analytics beacon for the Admin Dashboard's "most viewed skills /
 * most opened courses / most opened YouTube resources" — called when a user opens a
 * resource link or expands a topic, never awaited by the caller (a tracking failure
 * must never block or visibly affect the actual navigation/expand action).
 * @param {{resourceType: 'video'|'course'|'docs'|'skill', skillTitle: string, url?: string}} params
 */
export function trackRoadmapResourceClick({ resourceType, skillTitle, url }) {
  return apiRequest('/roadmap/track-resource-click', {
    method: 'POST',
    auth: true,
    body: { resource_type: resourceType, skill_title: skillTitle, url },
  }).catch(() => {})
}

