import { apiRequest, toFormData } from './client'

/**
 * @typedef {Object} SkillMatch
 * @property {number} skill_score
 * @property {string[]} matched_skills
 * @property {string[]} missing_skills
 *
 * @typedef {Object} ExperienceMatch
 * @property {number} experience_score
 * @property {number} [required_years]
 * @property {number} [candidate_years_found]
 * @property {string} [note]
 *
 * @typedef {Object} QualificationMatch
 * @property {number} qualification_score
 * @property {string[]} [matched_qualifications]
 * @property {string} [note]
 *
 * @typedef {Object} GithubMatch
 * @property {number} github_bonus_score
 * @property {string[]} matched_languages
 *
 * @typedef {Object} MatchResult
 * @property {number} overall_match_score - 0-100. Weighted: skills 50%/experience 30%/qualifications 20% (or 45/25/15/15 with a GitHub bonus)
 * @property {SkillMatch} skill_match
 * @property {ExperienceMatch} experience_match
 * @property {QualificationMatch} qualification_match
 * @property {GithubMatch} [github_match] - only present if a GitHub username was supplied
 *
 * @typedef {Object} MatchAnalysis
 * @property {string} filename
 * @property {string[]} resume_skills_found
 * @property {import('./jobDescription').JobDescriptionAnalysis} job_description_analysis
 * @property {{matched_keywords:string[], missing_keywords:string[], keyword_frequency:Object<string,number>}} keyword_analysis
 * @property {MatchResult} match_result
 * @property {string} [github_note]
 */

/**
 * No auth required by the backend for this endpoint.
 * @param {{file: File, jobDescription: string, githubUsername?: string}} params
 * @returns {Promise<MatchAnalysis>}
 */
export function analyzeMatch({ file, jobDescription, githubUsername }) {
  return apiRequest('/matching/analyze', {
    method: 'POST',
    body: toFormData({ file, job_description: jobDescription, github_username: githubUsername || undefined }),
  })
}
