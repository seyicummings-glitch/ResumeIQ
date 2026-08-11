"""Aggregation for the admin Dashboard (GET /admin/dashboard) — KPI tiles plus
30-day daily-series charts. Mirrors the query style already established in
app/routes/admin.py's older /admin/analytics endpoint (direct SQLAlchemy
aggregate queries against a live db: Session), since this data is inherently
DB-driven rather than something meaningful to compute from plain Python data.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import User, Resume, JobDescription, AnalysisResult
from app.models.interview_models import InterviewSession
from app.models.skill_assessment_models import SkillAssessmentAttempt
from app.models.roadmap_models import LearningRoadmap
from app.models.document_models import GeneratedDocument
from app.services.admin_analytics import compute_top_missing_skills

DASHBOARD_WINDOW_DAYS = 30


def _daily_series(db: Session, date_column, since: datetime, value_label: str) -> list[dict]:
    rows = (
        db.query(func.date(date_column).label("day"), func.count())
        .filter(date_column >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(day), value_label: count} for day, count in rows]


def compute_dashboard_summary(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    since_window = now - timedelta(days=DASHBOARD_WINDOW_DAYS)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users_today = db.query(func.count(User.id)).filter(User.last_login_at >= today_start).scalar() or 0
    new_users_this_month = db.query(func.count(User.id)).filter(User.created_at >= month_start).scalar() or 0
    total_resumes = db.query(func.count(Resume.id)).scalar() or 0
    total_analyses = db.query(func.count(AnalysisResult.id)).scalar() or 0
    total_ai_resume_builds = db.query(func.count(Resume.id)).filter(Resume.source == "ai_builder").scalar() or 0
    total_skill_assessments = db.query(func.count(SkillAssessmentAttempt.id)).scalar() or 0
    total_interview_sessions = db.query(func.count(InterviewSession.id)).scalar() or 0
    total_roadmaps = db.query(func.count(LearningRoadmap.id)).scalar() or 0
    total_documents = db.query(func.count(GeneratedDocument.id)).scalar() or 0
    avg_match_score = db.query(func.avg(AnalysisResult.match_percentage)).scalar()

    job_role_rows = (
        db.query(JobDescription.title, func.count(JobDescription.id))
        .filter(JobDescription.title.isnot(None), JobDescription.title != "")
        .group_by(JobDescription.title)
        .order_by(func.count(JobDescription.id).desc())
        .limit(10)
        .all()
    )
    most_requested_job_roles = [{"role": title, "count": count} for title, count in job_role_rows]

    recent_analyses = (
        db.query(AnalysisResult.result_json)
        .order_by(AnalysisResult.created_at.desc())
        .limit(200)
        .all()
    )
    most_common_missing_skills = compute_top_missing_skills([row[0] for row in recent_analyses], top_n=10)

    return {
        "kpis": {
            "totalUsers": total_users,
            "activeUsersToday": active_users_today,
            "newUsersThisMonth": new_users_this_month,
            "totalResumesUploaded": total_resumes,
            "totalAnalyses": total_analyses,
            "totalAiResumeBuilds": total_ai_resume_builds,
            "totalSkillAssessments": total_skill_assessments,
            "totalInterviewSessions": total_interview_sessions,
            "totalRoadmapsGenerated": total_roadmaps,
            "totalDocumentsGenerated": total_documents,
            # Populated starting Wave 3 once AiUsageEvent exists; null keeps the
            # tile visible-but-empty on the frontend rather than showing a fake 0.
            "aiRequestsToday": None,
            "averageMatchScore": round(avg_match_score) if avg_match_score is not None else 0,
        },
        "charts": {
            "userGrowth": _daily_series(db, User.created_at, since_window, "count"),
            "resumeUploadActivity": _daily_series(db, Resume.uploaded_at, since_window, "count"),
            "analysisActivity": _daily_series(db, AnalysisResult.created_at, since_window, "count"),
            "interviewActivity": _daily_series(db, InterviewSession.created_at, since_window, "count"),
            "skillAssessmentActivity": _daily_series(db, SkillAssessmentAttempt.created_at, since_window, "count"),
            "mostRequestedJobRoles": most_requested_job_roles,
            "mostCommonMissingSkills": most_common_missing_skills,
        },
    }
