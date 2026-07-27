import { apiRequest } from './client'

/**
 * @typedef {Object} GithubRepo
 * @property {string} name
 * @property {string|null} description
 * @property {string|null} language
 * @property {number} stars
 * @property {number} forks
 * @property {string} url
 * @property {string} updated_at
 *
 * @typedef {Object} GithubAnalysis
 * @property {{username:string, name:string|null, bio:string|null, public_repos:number, followers:number, profile_url:string}} profile
 * @property {GithubRepo[]} repositories
 * @property {string[]} languages_used
 * @property {number} repo_count_analyzed
 */

/** Accepts a plain username or a full github.com profile URL. @returns {Promise<GithubAnalysis>} */
export function analyzeGithubProfile(usernameOrUrl) {
  return apiRequest('/github/analyze', { method: 'POST', body: { username_or_url: usernameOrUrl } })
}
