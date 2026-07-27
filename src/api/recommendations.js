import { apiRequest } from './client'

/**
 * @typedef {Object} JobRecommendation
 * @property {number} job_description_id
 * @property {string|null} title
 * @property {number} overall_match_score
 * @property {import('./matching').SkillMatch} skill_match
 * @property {import('./matching').ExperienceMatch} experience_match
 * @property {import('./matching').QualificationMatch} qualification_match
 * @property {import('./matching').GithubMatch} [github_match]
 *
 * @typedef {Object} JobRecommendationsResponse
 * @property {number} resume_id
 * @property {string} filename
 * @property {JobRecommendation[]} recommendations - already sorted desc by overall_match_score
 * @property {string} [message] - present when recommendations is empty (no saved job descriptions yet)
 * @property {string} [github_note]
 */

/**
 * @param {{resumeId?: number, githubUsername?: string}} [params]
 * @returns {Promise<JobRecommendationsResponse>}
 */
export function getJobRecommendations({ resumeId, githubUsername } = {}) {
  return apiRequest('/recommendations/jobs', {
    auth: true,
    query: { resume_id: resumeId, github_username: githubUsername },
  })
}
