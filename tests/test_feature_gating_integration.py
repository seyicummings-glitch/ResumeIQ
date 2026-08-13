"""Proves the Subscription & Credit Management gate is actually wired into
real feature routes, not just unit-tested in isolation in test_feature_gate.py.
Covers one representative endpoint per pattern (gate-at-start-of-a-session,
gate-at-a-single-action-endpoint) rather than exhaustively re-testing every
one of the ~7 call sites, since feature_gate.check_and_consume() itself is
already thoroughly covered."""
import pytest
from fastapi import HTTPException

from app.models.models import User, Resume
from app.models.subscription_models import Plan, PlanLimit
from app.routes import resume_builder as builder_routes
from app.routes import roadmap as roadmap_routes


def _user(db_session, email="user@example.com", target_role="Backend Engineer"):
    user = User(email=email, hashed_password="x", target_role=target_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _free_plan_with_limit(db_session, feature_key, monthly_limit):
    plan = Plan(name="Free", slug="free", monthly_price_cents=0)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    db_session.add(PlanLimit(plan_id=plan.id, feature_key=feature_key, monthly_limit=monthly_limit))
    db_session.commit()
    return plan


def test_ai_resume_builder_generate_denied_with_402_once_limit_exhausted(db_session):
    _free_plan_with_limit(db_session, "ai_resume_builder", monthly_limit=1)
    user = _user(db_session)
    resume = Resume(user_id=user.id, filename="r.pdf", raw_text="Some resume text", is_active=True)
    db_session.add(resume)
    db_session.commit()

    # First call succeeds (uses the one included use).
    builder_routes.generate_resume(db=db_session, current_user=user)

    # Second call is denied.
    with pytest.raises(HTTPException) as exc_info:
        builder_routes.generate_resume(db=db_session, current_user=user)
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "limit_reached"
    assert exc_info.value.detail["featureKey"] == "ai_resume_builder"


def test_roadmap_regenerate_denied_with_402_once_limit_exhausted(db_session):
    _free_plan_with_limit(db_session, "learning_roadmap", monthly_limit=1)
    user = _user(db_session)

    roadmap_routes.regenerate_roadmap(db=db_session, current_user=user)  # uses the 1 included use

    with pytest.raises(HTTPException) as exc_info:
        roadmap_routes.regenerate_roadmap(db=db_session, current_user=user)
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["featureKey"] == "learning_roadmap"


def test_gating_does_not_interfere_when_plan_allows_it(db_session):
    _free_plan_with_limit(db_session, "learning_roadmap", monthly_limit=5)
    user = _user(db_session)

    result = roadmap_routes.regenerate_roadmap(db=db_session, current_user=user)
    assert result["has_context"] is True
