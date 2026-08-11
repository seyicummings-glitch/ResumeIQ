// Mirrors app/services/subscription_limits.py's FEATURE_KEYS/FEATURE_LABELS —
// kept as a small independent duplication (frontend/backend repos don't share
// code) rather than fetched from the API, since this list changes rarely.
export const FEATURE_KEYS = [
  'resume_analysis',
  'ai_resume_builder',
  'interview_practice',
  'skill_assessment',
  'learning_roadmap',
  'documents',
  'github_analysis',
  'ai_chat',
]

export const FEATURE_LABELS = {
  resume_analysis: 'Resume Analysis',
  ai_resume_builder: 'AI Resume Builder',
  interview_practice: 'Interview Practice',
  skill_assessment: 'Skill Assessments',
  learning_roadmap: 'Learning Roadmaps',
  documents: 'Documents',
  github_analysis: 'GitHub Analysis',
  ai_chat: 'AI Chat',
}
