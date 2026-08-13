"""Aggregation for the admin Dashboard (GET /admin/dashboard) — KPI tiles,
grouped analytics sections, and chart series, all computed live against the
database on every request (no caching, no hardcoded values).

Two data sources are used deliberately, per metric:
  - A direct table count/aggregate where an authoritative table already
    exists (Resume, AnalysisResult, InterviewSession, LearningRoadmap,
    Subscription, Transaction, ...) — these are complete from the day the
    table itself was created, so they're strictly more accurate than an
    event count would be for anything tracked before analytics events
    existed.
  - An AnalyticsEvent count/aggregate (see app/services/analytics.py and
    app/services/analytics_reporting.py) for anything that has NO
    corresponding table column — resume downloads, AI-builder save/
    regenerate/download splits, voice-vs-text interview split, started-vs-
    completed funnels, and anything requiring metadata (most-viewed skills,
    most-opened courses/videos). These genuinely didn't exist as trackable
    metrics before the events system, so there's no historical gap to worry
    about.

Revenue Analytics queries Subscription/Transaction directly — real tables,
currently empty because no Stripe checkout/webhook integration exists yet in
this codebase (see app/services/stripe_client.py's forward-looking-only
helpers). This section will show real zeros until that wave is built, which
is correct: showing fabricated revenue numbers would violate the "never show
fake data" requirement just as badly as hardcoding would.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import User, Resume, JobDescription, AnalysisResult
from app.models.interview_models import InterviewSession
from app.models.skill_assessment_models import SkillAssessmentAttempt
from app.models.roadmap_models import LearningRoadmap
from app.models.document_models import GeneratedDocument
from app.models.subscription_models import Transaction
from app.services.subscription_admin import count_paid_active_subscribers
from app.services.admin_analytics import compute_top_missing_skills
from app.services.analytics import EVENT_TYPES
from app.services.analytics_reporting import (
    count_events,
    top_metadata_values,
    most_used_features,
    event_series,
    column_series,
    merge_series,
)

DASHBOARD_WINDOW_DAYS = 30
WEEKLY_CHART_WINDOW_DAYS = 84  # ~12 weeks
MONTHLY_CHART_WINDOW_DAYS = 365  # ~12 months
ACTIVE_USER_WINDOW_DAYS = 30


def _daily_series(db: Session, date_column, since: datetime, value_label: str) -> list[dict]:
    """Kept for the legacy flat `kpis`/`charts.*Activity` shape a couple of
    older frontend call sites still read — new charts use the richer
    column_series/event_series/merge_series helpers below instead."""
    rows = (
        db.query(func.date(date_column).label("day"), func.count())
        .filter(date_column >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(day), value_label: count} for day, count in rows]


def _time_bounds() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "now": now,
        "today_start": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "month_start": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        "year_start": now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
        "window_30d": now - timedelta(days=DASHBOARD_WINDOW_DAYS),
        "window_84d": now - timedelta(days=WEEKLY_CHART_WINDOW_DAYS),
        "window_365d": now - timedelta(days=MONTHLY_CHART_WINDOW_DAYS),
        "active_user_since": now - timedelta(days=ACTIVE_USER_WINDOW_DAYS),
    }


def _user_analytics(db: Session, bounds: dict) -> dict:
    return {
        "totalUsers": db.query(func.count(User.id)).scalar() or 0,
        "activeUsers": db.query(func.count(User.id)).filter(User.last_login_at >= bounds["active_user_since"]).scalar() or 0,
        "newUsersToday": db.query(func.count(User.id)).filter(User.created_at >= bounds["today_start"]).scalar() or 0,
        "newUsersThisMonth": db.query(func.count(User.id)).filter(User.created_at >= bounds["month_start"]).scalar() or 0,
    }


def _resume_analytics(db: Session) -> dict:
    return {
        "totalUploads": db.query(func.count(Resume.id)).filter(Resume.source == "upload").scalar() or 0,
        "totalAnalyses": db.query(func.count(AnalysisResult.id)).scalar() or 0,
        "totalAtsReports": count_events(db, EVENT_TYPES["ATS_SCORE_GENERATED"]),
        "totalDownloads": count_events(db, EVENT_TYPES["RESUME_DOWNLOADED"]),
    }


def _ai_builder_analytics(db: Session) -> dict:
    return {
        "totalBuilds": db.query(func.count(Resume.id)).filter(Resume.source == "ai_builder").scalar() or 0,
        "totalSaves": count_events(db, EVENT_TYPES["AI_RESUME_SAVED"]),
        "totalDownloads": count_events(db, EVENT_TYPES["AI_RESUME_DOWNLOADED"]),
        "totalRegenerations": count_events(db, EVENT_TYPES["AI_RESUME_REGENERATED"]),
    }


def _interview_analytics(db: Session) -> dict:
    return {
        "totalInterviews": db.query(func.count(InterviewSession.id)).scalar() or 0,
        "voiceInterviews": count_events(db, EVENT_TYPES["VOICE_INTERVIEW_STARTED"]),
        "textInterviews": count_events(db, EVENT_TYPES["TEXT_INTERVIEW_STARTED"]),
        "completedInterviews": count_events(db, EVENT_TYPES["INTERVIEW_COMPLETED"]),
    }


def _learning_analytics(db: Session) -> dict:
    return {
        "roadmapsGenerated": db.query(func.count(LearningRoadmap.id)).scalar() or 0,
        "mostViewedSkills": top_metadata_values(db, EVENT_TYPES["SKILL_VIEWED"], "skill", top_n=10),
        "mostOpenedCourses": top_metadata_values(db, EVENT_TYPES["COURSE_OPENED"], "skill", top_n=10),
        "mostOpenedYoutubeResources": top_metadata_values(db, EVENT_TYPES["YOUTUBE_RESOURCE_OPENED"], "skill", top_n=10),
    }


def _revenue_analytics(db: Session, bounds: dict) -> dict:
    monthly_cents = (
        db.query(func.sum(Transaction.amount_cents))
        .filter(Transaction.status == "paid", Transaction.created_at >= bounds["month_start"])
        .scalar() or 0
    )
    annual_cents = (
        db.query(func.sum(Transaction.amount_cents))
        .filter(Transaction.status == "paid", Transaction.created_at >= bounds["year_start"])
        .scalar() or 0
    )
    return {
        "activeSubscribers": count_paid_active_subscribers(db),
        "monthlyRevenue": round(monthly_cents / 100, 2),
        "annualRevenue": round(annual_cents / 100, 2),
        "failedPayments": db.query(func.count(Transaction.id)).filter(Transaction.status == "failed").scalar() or 0,
    }


def _revenue_trend(db: Session, since: datetime) -> list[dict]:
    rows = (
        db.query(Transaction.created_at, Transaction.amount_cents)
        .filter(Transaction.status == "paid", Transaction.created_at >= since)
        .all()
    )
    buckets: dict[str, int] = {}
    for created_at, amount_cents in rows:
        key = created_at.strftime("%Y-%m-%d")
        buckets[key] = buckets.get(key, 0) + amount_cents
    return [{"date": date, "revenue": round(cents / 100, 2)} for date, cents in sorted(buckets.items())]


def compute_dashboard_summary(db: Session) -> dict:
    bounds = _time_bounds()
    since_window = bounds["window_30d"]

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users_today = db.query(func.count(User.id)).filter(User.last_login_at >= bounds["today_start"]).scalar() or 0
    new_users_this_month = db.query(func.count(User.id)).filter(User.created_at >= bounds["month_start"]).scalar() or 0
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
        # Legacy flat shape — kept as-is so nothing else reading this response breaks;
        # the grouped sections below are the richer, spec'd replacement.
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
            "aiRequestsToday": None,
            "averageMatchScore": round(avg_match_score) if avg_match_score is not None else 0,
        },

        "userAnalytics": _user_analytics(db, bounds),
        "resumeAnalytics": _resume_analytics(db),
        "aiBuilderAnalytics": _ai_builder_analytics(db),
        "interviewAnalytics": _interview_analytics(db),
        "learningAnalytics": _learning_analytics(db),
        "revenueAnalytics": _revenue_analytics(db, bounds),

        "charts": {
            "userGrowth": _daily_series(db, User.created_at, since_window, "count"),
            "resumeUploadActivity": _daily_series(db, Resume.uploaded_at, since_window, "count"),
            "analysisActivity": _daily_series(db, AnalysisResult.created_at, since_window, "count"),
            "interviewActivity": _daily_series(db, InterviewSession.created_at, since_window, "count"),
            "skillAssessmentActivity": _daily_series(db, SkillAssessmentAttempt.created_at, since_window, "count"),
            "mostRequestedJobRoles": most_requested_job_roles,
            "mostCommonMissingSkills": most_common_missing_skills,

            # User growth at three granularities, per spec — weekly/monthly use a
            # wider lookback window than daily since a 30-day window would only ever
            # show ~1 monthly bucket.
            "userGrowthDaily": column_series(db, User.created_at, bounds["window_30d"], "day"),
            "userGrowthWeekly": column_series(db, User.created_at, bounds["window_84d"], "week"),
            "userGrowthMonthly": column_series(db, User.created_at, bounds["window_365d"], "month"),

            "platformUsage": most_used_features(db, since=since_window, top_n=10),

            "resumeActivity": merge_series({
                "uploads": event_series(db, EVENT_TYPES["RESUME_UPLOADED"], since_window),
                "analyses": event_series(db, EVENT_TYPES["RESUME_ANALYZED"], since_window),
                "downloads": event_series(db, EVENT_TYPES["RESUME_DOWNLOADED"], since_window),
            }),

            "interviewStartedVsCompleted": merge_series({
                "started": event_series(db, EVENT_TYPES["INTERVIEW_STARTED"], since_window),
                "completed": event_series(db, EVENT_TYPES["INTERVIEW_COMPLETED"], since_window),
            }),

            "topSkillsViewed": top_metadata_values(db, EVENT_TYPES["SKILL_VIEWED"], "skill", top_n=10, since=since_window),

            "revenueTrend": _revenue_trend(db, since_window),
        },
    }
