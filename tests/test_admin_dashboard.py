from datetime import datetime, timedelta, timezone

from app.models.models import User, Resume, JobDescription, AnalysisResult
from app.models.interview_models import InterviewSession
from app.models.skill_assessment_models import SkillAssessmentAttempt
from app.models.roadmap_models import LearningRoadmap
from app.services.admin_dashboard import compute_dashboard_summary

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
