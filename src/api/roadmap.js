import { apiRequest } from './client'

/**
 * @typedef {Object} RoadmapItem
 * @property {string} skill
 * @property {'Course'|'Project'|'Cert'} type
 * @property {string} provider
 * @property {string} duration
 * @property {'critical'|'high'|'medium'} importance
 * @property {string[]} resources
 * @property {boolean} done
 *
 * @typedef {Object} RoadmapPhase
 * @property {string} phase
 * @property {string} timeframe
 * @property {RoadmapItem[]} items
 *
 * @typedef {Object} RoadmapStats
 * @property {number} total_hours
 * @property {number} done_count
 * @property {number} total_count
 *
 * @typedef {Object} RoadmapResult
 * @property {RoadmapPhase[]} phases
 * @property {boolean} has_gaps
 * @property {RoadmapStats} [stats]
 */

/** @returns {Promise<RoadmapResult>} */
export function getRoadmap() {
  return apiRequest('/roadmap', { auth: true })
}

/**
 * @param {{skill: string}} params
 * @returns {Promise<{skill: string, completed: boolean}>}
 */
export function toggleRoadmapItem({ skill }) {
  return apiRequest('/roadmap/toggle', { method: 'POST', auth: true, body: { skill } })
}
