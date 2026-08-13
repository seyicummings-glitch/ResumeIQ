"""Proves the AI token-gating system is actually wired into real feature routes, not just
unit-tested in isolation in test_feature_gate.py. Covers one representative endpoint per pattern
(gate-at-start-of-a-session, gate-at-a-single-action-endpoint) rather than exhaustively
re-testing every one of the ~7 call sites, since feature_gate.check_and_consume() itself is
already thoroughly covered."""
import pytest
from fastapi import HTTPException

from app.models.models import User, Resume
from app.models.subscription_models import Plan, AiFeatureSetting
from app.routes import resume_builder as builder_routes
from app.routes import roadmap as roadmap_routes
from app.services.feature_gate import get_credit_balance


def _user(db_session, email="user@example.com", target_role="Backend Engineer"):
    user = User(email=email, hashed_password="x", target_role=target_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _give_tokens(db_session, user, amount):
    """Grants tokens as a purchase would, with last_free_refresh_at already stamped -- the same
    state a real account is in post-registration (grant_signup_credits always stamps it, even
    when the signup amount is 0). Without this, the free-plan periodic refresh would treat the
    account as "never refreshed" and add a surprise bonus the moment gating checks it."""
    from datetime import datetime, timezone
    from app.models.subscription_models import CreditBalance
    db_session.add(CreditBalance(user_id=user.id, balance=amount, last_free_refresh_at=datetime.now(timezone.utc)))
    db_session.commit()


def _free_plan(db_session):
    plan = Plan(name="Free", slug="free", monthly_price_cents=0)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def _paid_feature(db_session, feature_key, credit_cost):
    setting = AiFeatureSetting(feature_key=feature_key, feature_label=feature_key, is_paid=True, credit_cost_per_use=credit_cost)
    db_session.add(setting)
    db_session.commit()
    return setting


def test_ai_resume_builder_generate_denied_with_402_once_tokens_exhausted(db_session):
    _free_plan(db_session)
    _paid_feature(db_session, "ai_resume_builder", credit_cost=10)
    user = _user(db_session)
    resume = Resume(user_id=user.id, filename="r.pdf", raw_text="Some resume text", is_active=True)
    db_session.add(resume)
    db_session.commit()

    _give_tokens(db_session, user, 10)  # exactly enough for one use

    # First call succeeds (spends the only 10 tokens the account has).
    builder_routes.generate_resume(db=db_session, current_user=user)

    # Second call is denied -- balance is 0.
    with pytest.raises(HTTPException) as exc_info:
        builder_routes.generate_resume(db=db_session, current_user=user)
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "insufficient_credits"
    assert exc_info.value.detail["featureKey"] == "ai_resume_builder"


def test_roadmap_regenerate_denied_with_402_once_tokens_exhausted(db_session):
    _free_plan(db_session)
    _paid_feature(db_session, "learning_roadmap", credit_cost=10)
    user = _user(db_session)

    _give_tokens(db_session, user, 10)

    roadmap_routes.regenerate_roadmap(db=db_session, current_user=user)  # spends the 10 tokens

    with pytest.raises(HTTPException) as exc_info:
        roadmap_routes.regenerate_roadmap(db=db_session, current_user=user)
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["featureKey"] == "learning_roadmap"


def test_gating_does_not_interfere_when_feature_is_unmetered(db_session):
    _free_plan(db_session)  # learning_roadmap has no AiFeatureSetting row -> unmetered
    user = _user(db_session)

    result = roadmap_routes.regenerate_roadmap(db=db_session, current_user=user)
    assert result["has_context"] is True


def test_gating_does_not_interfere_when_balance_covers_the_cost(db_session):
    _free_plan(db_session)
    _paid_feature(db_session, "learning_roadmap", credit_cost=5)
    user = _user(db_session)

    _give_tokens(db_session, user, 50)

    result = roadmap_routes.regenerate_roadmap(db=db_session, current_user=user)
    assert result["has_context"] is True
    assert get_credit_balance(db_session, user.id) == 45
