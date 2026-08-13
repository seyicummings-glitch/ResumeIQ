"""
Consolidated "everything we know about this user's career journey" — resume, target job,
skill gaps, roadmap progress, latest skill-assessment and interview results. Built for the
Career Coach (app/services/career_coach_ai.py) so it can answer with real, specific knowledge
of the user's whole account instead of generic advice scoped to whichever single feature they
happened to open it from. Pure read/assembly — no FastAPI imports, so it's easy to reuse from
any future route that wants the same "who is this user, career-wise" snapshot.
"""
from sqlalchemy.orm import Session
from app.models.models import User, Resume, JobDescription
from app.models.roadmap_models import LearningRoadmap
from app.models.skill_assessment_models import SkillAssessmentAttempt
from app.models.interview_models import InterviewSession
from app.services.analysis_store import get_latest_analysis
from app.services.resume_structurer import extract_skills_list


def _skill_assessment_summary(db: Session, user_id: int) -> str | None:
    attempt = (
        db.query(SkillAssessmentAttempt)
        .filter(SkillAssessmentAttempt.user_id == user_id)
        .order_by(SkillAssessmentAttempt.created_at.desc())
        .first()
    )
    if not attempt:
        return None

    breakdown = attempt.category_breakdown or []
    weak = sorted(breakdown, key=lambda item: item.get("pct", 0))[:3]
    weak_text = ", ".join(f"{item.get('category_label', item.get('category_key'))} ({item.get('pct', 0)}%)" for item in weak)
    return (
        f"Technical score: {attempt.technical_score}/100, soft-skill score: {attempt.soft_score}/100. "
        f"Weakest areas: {weak_text or 'none recorded'}."
    )


def _interview_summary(db: Session, user_id: int) -> str | None:
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.desc())
        .first()
    )
    if not session or not session.feedback_json:
        return None

    areas = session.feedback_json.get("areas_to_improve") or []
    if not areas:
        return None
    return "Areas to improve from the most recent mock interview: " + "; ".join(areas[:4])


def _roadmap_summary(roadmap: LearningRoadmap | None) -> str:
    """A compact stage/topic outline (not the full content) — enough for the coach to know
    where the user is in their plan without spending the whole context budget on it."""
    if not roadmap:
        return ""
    lines = []
    for stage in roadmap.stages_json:
        topic_titles = ", ".join(t["title"] for t in stage["topics"])
        lines.append(f"- {stage['stage']}: {topic_titles}")
    return "\n".join(lines)


def get_user_career_context(db: Session, user: User) -> dict:
    """One snapshot of the user's whole career journey on this platform: their latest saved
    resume/job match, target role, skill gaps, roadmap progress, and how their last skill
    assessment and mock interview went. `roadmap` is the raw ORM row (or None) so callers can
    also look up a specific topic within it; everything else is already prompt-ready text."""
    analysis = get_latest_analysis(db, user.id)

    resume_text = ""
    resume_skills: list[str] = []
    missing_skills: list[str] = []
    jd_title = ""
    jd_content = ""

    if analysis:
        resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
        resume_text = resume.raw_text or "" if resume else ""
        resume_skills = extract_skills_list(resume.skills or "") if resume else []
        missing_skills = (analysis.result_json or {}).get("skill_match", {}).get("missing_skills", []) or []
        jd = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()
        if jd:
            jd_title = jd.title or ""
            jd_content = jd.content or ""

    roadmap = (
        db.query(LearningRoadmap)
        .filter(LearningRoadmap.user_id == user.id)
        .order_by(LearningRoadmap.created_at.desc())
        .first()
    )

    return {
        "target_role": user.target_role or "",
        "industry": user.industry or "",
        "experience_level": user.experience_level or "",
        "resume_text": resume_text,
        "resume_skills": resume_skills,
        "missing_skills": missing_skills,
        "jd_title": jd_title,
        "jd_content": jd_content,
        "roadmap": roadmap,
        "roadmap_summary": _roadmap_summary(roadmap),
        "skill_assessment_summary": _skill_assessment_summary(db, user.id),
        "interview_summary": _interview_summary(db, user.id),
    }


def find_roadmap_topic(roadmap: LearningRoadmap | None, topic_key: str | None) -> dict | None:
    if not roadmap or not topic_key:
        return None
    for stage in roadmap.stages_json:
        for topic in stage["topics"]:
            if topic.get("topic_key") == topic_key:
                return topic
    return None


def topic_context_text(topic: dict) -> str:
    return (
        f"Title: {topic['title']}\n"
        f"Why it matters: {topic['why_it_matters']}\n"
        f"Current gap: {topic.get('current_gap', '')}\n"
        f"Learning objectives: {'; '.join(topic.get('learning_objectives', []))}"
    )
