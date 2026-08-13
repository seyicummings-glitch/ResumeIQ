"""Shared feature-key vocabulary for plan limits and usage tracking — the
single source of truth admin_subscriptions.py (limit configuration),
feature_gate.py (usage tracking/gating enforcement), and subscriptions.py
(user-facing usage display) all key off of, so none of them can drift apart.

Note: github_analysis's only route (/github/analyze) is fully anonymous —
no authenticated variant exists in this codebase, so it's registered here
for admin-configurability/forward-compat but feature_gate.check_and_consume()
is never actually called for it today (there's no logged-in user to gate)."""

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
