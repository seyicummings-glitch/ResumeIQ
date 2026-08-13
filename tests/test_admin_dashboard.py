from datetime import datetime, timedelta, timezone

from app.models.models import User, Resume, JobDescription, AnalysisResult
from app.models.interview_models import InterviewSession
from app.models.skill_assessment_models import SkillAssessmentAttempt
from app.models.roadmap_models import LearningRoadmap
from app.models.analytics_models import AnalyticsEvent
from app.models.subscription_models import Plan, Subscription, Transaction
from app.services.admin_dashboard import compute_dashboard_summary
from app.routes import admin_dashboard as routes

# SQLite (used only for this in-memory test fixture) doesn't reliably populate
# server_default=func.now() columns the way Postgres does, so every row below
# sets its timestamp column explicitly rather than relying on the DB default.
NOW = datetime.now(timezone.utc)


def _user(db_session, email, last_login_at=None, created_at=None):
    user = User(
        email=email,
        hashed_password="x",
        full_name=email,
        last_login_at=last_login_at,
        created_at=created_at or NOW,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_kpis_count_users_resumes_analyses_and_ai_builds(db_session):
    active_user = _user(db_session, "active@example.com", last_login_at=NOW)
    _user(db_session, "stale@example.com", last_login_at=NOW - timedelta(days=5))

    db_session.add(Resume(user_id=active_user.id, filename="r1.pdf", source="upload", uploaded_at=NOW))
    db_session.add(Resume(user_id=active_user.id, filename="r2.pdf", source="ai_builder", uploaded_at=NOW))
    db_session.commit()

    summary = compute_dashboard_summary(db_session)
    kpis = summary["kpis"]

    assert kpis["totalUsers"] == 2
    assert kpis["activeUsersToday"] == 1
    assert kpis["totalResumesUploaded"] == 2
    assert kpis["totalAiResumeBuilds"] == 1
    assert kpis["aiRequestsToday"] is None  # not available until Wave 3's AiUsageEvent lands


def test_kpis_count_analyses_interviews_assessments_roadmaps_and_avg_score(db_session):
    user = _user(db_session, "user@example.com")
    resume = Resume(user_id=user.id, filename="r.pdf", uploaded_at=NOW)
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    jd = JobDescription(user_id=user.id, title="Backend Engineer", content="...", created_at=NOW)
    db_session.add(jd)
    db_session.commit()
    db_session.refresh(jd)

    db_session.add(AnalysisResult(user_id=user.id, resume_id=resume.id, job_description_id=jd.id, match_percentage=80, created_at=NOW))
    db_session.add(AnalysisResult(user_id=user.id, resume_id=resume.id, job_description_id=jd.id, match_percentage=60, created_at=NOW))
    db_session.add(InterviewSession(user_id=user.id, jd_title="Backend Engineer", created_at=NOW))
    db_session.add(SkillAssessmentAttempt(user_id=user.id, source="ai", technical_score=70, soft_score=80, overall_score=75, created_at=NOW))
    db_session.add(LearningRoadmap(user_id=user.id, source="ai", stages_json={}, created_at=NOW))
    db_session.commit()

    summary = compute_dashboard_summary(db_session)
    kpis = summary["kpis"]

    assert kpis["totalAnalyses"] == 2
    assert kpis["totalInterviewSessions"] == 1
    assert kpis["totalSkillAssessments"] == 1
    assert kpis["totalRoadmapsGenerated"] == 1
    assert kpis["averageMatchScore"] == 70


def test_most_requested_job_roles_ranked_by_count(db_session):
    user = _user(db_session, "user@example.com")
    db_session.add_all([
        JobDescription(user_id=user.id, title="Backend Engineer", content="...", created_at=NOW),
        JobDescription(user_id=user.id, title="Backend Engineer", content="...", created_at=NOW),
        JobDescription(user_id=user.id, title="Frontend Engineer", content="...", created_at=NOW),
    ])
    db_session.commit()

    summary = compute_dashboard_summary(db_session)
    roles = summary["charts"]["mostRequestedJobRoles"]

    assert roles[0] == {"role": "Backend Engineer", "count": 2}
    assert {"role": "Frontend Engineer", "count": 1} in roles


def test_dashboard_with_no_data_returns_zeroed_summary(db_session):
    summary = compute_dashboard_summary(db_session)
    kpis = summary["kpis"]

    assert kpis["totalUsers"] == 0
    assert kpis["averageMatchScore"] == 0
    assert summary["charts"]["mostRequestedJobRoles"] == []
    assert summary["charts"]["mostCommonMissingSkills"] == []


# --- Grouped analytics sections (real DB data, no hardcoded values) ----------

def _event(db_session, event_type, feature_name="resume_analyzer", user_id=None, metadata=None):
    event = AnalyticsEvent(user_id=user_id, event_type=event_type, feature_name=feature_name,
                            event_metadata=metadata or {}, created_at=NOW)
    db_session.add(event)
    db_session.commit()


def test_user_analytics_section(db_session):
    _user(db_session, "active@example.com", last_login_at=NOW, created_at=NOW)
    _user(db_session, "stale@example.com", last_login_at=NOW - timedelta(days=60), created_at=NOW - timedelta(days=60))

    summary = compute_dashboard_summary(db_session)
    section = summary["userAnalytics"]

    assert section["totalUsers"] == 2
    assert section["activeUsers"] == 1  # only the one logged in within 30 days
    assert section["newUsersToday"] == 1
    assert section["newUsersThisMonth"] == 1


def test_resume_analytics_section_combines_table_and_event_counts(db_session):
    user = _user(db_session, "user@example.com")
    db_session.add(Resume(user_id=user.id, filename="r1.pdf", source="upload", uploaded_at=NOW))
    db_session.add(Resume(user_id=user.id, filename="r2.pdf", source="upload", uploaded_at=NOW))
    db_session.commit()
    _event(db_session, "ats_score_generated", user_id=user.id)
    _event(db_session, "resume_downloaded", user_id=user.id)
    _event(db_session, "resume_downloaded", user_id=user.id)

    section = compute_dashboard_summary(db_session)["resumeAnalytics"]
    assert section["totalUploads"] == 2
    assert section["totalAtsReports"] == 1
    assert section["totalDownloads"] == 2


def test_ai_builder_analytics_section(db_session):
    user = _user(db_session, "user@example.com")
    db_session.add(Resume(user_id=user.id, filename="ai.pdf", source="ai_builder", uploaded_at=NOW))
    db_session.commit()
    _event(db_session, "ai_resume_saved", user_id=user.id)
    _event(db_session, "ai_resume_regenerated", user_id=user.id)
    _event(db_session, "ai_resume_downloaded", user_id=user.id)

    section = compute_dashboard_summary(db_session)["aiBuilderAnalytics"]
    assert section["totalBuilds"] == 1
    assert section["totalSaves"] == 1
    assert section["totalRegenerations"] == 1
    assert section["totalDownloads"] == 1


def test_interview_analytics_section(db_session):
    user = _user(db_session, "user@example.com")
    db_session.add(InterviewSession(user_id=user.id, jd_title="Backend Engineer", created_at=NOW))
    db_session.commit()
    _event(db_session, "voice_interview_started", user_id=user.id)
    _event(db_session, "text_interview_started", user_id=user.id)
    _event(db_session, "text_interview_started", user_id=user.id)
    _event(db_session, "interview_completed", user_id=user.id)

    section = compute_dashboard_summary(db_session)["interviewAnalytics"]
    assert section["totalInterviews"] == 1
    assert section["voiceInterviews"] == 1
    assert section["textInterviews"] == 2
    assert section["completedInterviews"] == 1


def test_learning_analytics_section_includes_most_viewed_resources(db_session):
    user = _user(db_session, "user@example.com")
    db_session.add(LearningRoadmap(user_id=user.id, source="ai", stages_json={}, created_at=NOW))
    db_session.commit()
    _event(db_session, "skill_viewed", user_id=user.id, metadata={"skill": "React"})
    _event(db_session, "skill_viewed", user_id=user.id, metadata={"skill": "React"})
    _event(db_session, "course_opened", user_id=user.id, metadata={"skill": "Docker"})
    _event(db_session, "youtube_resource_opened", user_id=user.id, metadata={"skill": "SEO"})

    section = compute_dashboard_summary(db_session)["learningAnalytics"]
    assert section["roadmapsGenerated"] == 1
    assert section["mostViewedSkills"][0] == {"value": "React", "count": 2}
    assert section["mostOpenedCourses"] == [{"value": "Docker", "count": 1}]
    assert section["mostOpenedYoutubeResources"] == [{"value": "SEO", "count": 1}]


def test_revenue_analytics_section_reads_real_subscription_tables(db_session):
    plan = Plan(name="Premium", slug="premium", monthly_price_cents=1999)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    user = _user(db_session, "subscriber@example.com")
    db_session.add(Subscription(user_id=user.id, plan_id=plan.id, status="active"))
    db_session.add(Transaction(user_id=user.id, plan_id=plan.id, amount_cents=1999, status="paid", created_at=NOW))
    db_session.add(Transaction(user_id=user.id, plan_id=plan.id, amount_cents=1999, status="failed", created_at=NOW))
    db_session.commit()

    section = compute_dashboard_summary(db_session)["revenueAnalytics"]
    assert section["activeSubscribers"] == 1
    assert section["monthlyRevenue"] == 19.99
    assert section["annualRevenue"] == 19.99
    assert section["failedPayments"] == 1


def test_revenue_analytics_section_is_honestly_zero_with_no_subscribers(db_session):
    section = compute_dashboard_summary(db_session)["revenueAnalytics"]
    assert section == {"activeSubscribers": 0, "monthlyRevenue": 0, "annualRevenue": 0, "failedPayments": 0}


def test_new_chart_series_present_in_response(db_session):
    charts = compute_dashboard_summary(db_session)["charts"]
    for key in (
        "userGrowthDaily", "userGrowthWeekly", "userGrowthMonthly", "platformUsage",
        "resumeActivity", "interviewStartedVsCompleted", "topSkillsViewed", "revenueTrend",
    ):
        assert key in charts


# --- Activity feed route ------------------------------------------------------

def test_activity_feed_route_returns_newest_first(db_session):
    admin = User(email="admin@example.com", hashed_password="x", role="admin", full_name="Admin")
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    user = _user(db_session, "jane@example.com")
    _event(db_session, "resume_uploaded", user_id=user.id)
    db_session.add(AnalyticsEvent(user_id=user.id, event_type="roadmap_generated", feature_name="learning_roadmap",
                                   created_at=NOW + timedelta(seconds=1)))
    db_session.commit()

    result = routes.get_activity_feed_route(limit=20, db=db_session, current_user=admin)
    activity = result["activity"]
    assert len(activity) == 2
    assert activity[0]["eventType"] == "roadmap_generated"
