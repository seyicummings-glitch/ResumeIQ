import { apiRequest } from './client'
import { getMe } from './auth'

export function getProfile() {
  return getMe()
}

/**
 * @param {{fullName?: string, email?: string, phone?: string, location?: string,
 *   linkedinUrl?: string, githubUrl?: string, portfolioUrl?: string, targetRole?: string,
 *   industry?: string, experienceLevel?: string, careerGoals?: string}} fields
 */
export function updateProfile({
  fullName,
  email,
  phone,
  location,
  linkedinUrl,
  githubUrl,
  portfolioUrl,
  targetRole,
  industry,
  experienceLevel,
  careerGoals,
}) {
  return apiRequest('/auth/me', {
    method: 'PATCH',
    auth: true,
    body: {
      full_name: fullName,
      email,
      phone,
      location,
      linkedin_url: linkedinUrl,
      github_url: githubUrl,
      portfolio_url: portfolioUrl,
      target_role: targetRole,
      industry,
      experience_level: experienceLevel,
      career_goals: careerGoals,
    },
  })
}

/** @param {{currentPassword: string, newPassword: string}} fields */
export function changePassword({ currentPassword, newPassword }) {
  return apiRequest('/auth/change-password', {
    method: 'POST',
    auth: true,
    body: { current_password: currentPassword, new_password: newPassword },
  })
}
