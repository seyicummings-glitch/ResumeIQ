"""Shared feature-key vocabulary for plan limits and usage tracking — the
single source of truth both admin_subscriptions.py (limit configuration) and
usage_tracker.py (Wave 4) key off of, so the two can never drift apart."""

FEATURE_KEYS = [
    "resume_analysis",
    "ai_resume_builder",
    "interview_practice",
    "skill_assessment",
    "learning_roadmap",
    "documents",
    "github_analysis",
    "ai_chat",
]

FEATURE_LABELS = {
    "resume_analysis": "Resume Analysis",
    "ai_resume_builder": "AI Resume Builder",
    "interview_practice": "Interview Practice",
    "skill_assessment": "Skill Assessments",
    "learning_roadmap": "Learning Roadmaps",
    "documents": "Documents",
    "github_analysis": "GitHub Analysis",
    "ai_chat": "AI Chat",
}
