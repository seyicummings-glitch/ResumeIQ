import pytest

from app.models.models import User
from app.models.subscription_models import Plan, PlanLimit, Subscription, AiFeatureSetting, CreditBalance, CreditLedgerEntry
from app.services.feature_gate import (
    get_or_create_subscription,
    get_feature_setting,
    get_plan_limit,
    get_usage_count,
    _increment_usage,
    get_credit_balance,
    adjust_credits,
    get_feature_usage_summary,
    check_and_consume,
    FeatureAccessDenied,
)


def _user(db_session, email="user@example.com"):
    user = User(email=email, hashed_password="x", full_name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _plan(db_session, slug="free", name="Free"):
    plan = Plan(name=name, slug=slug, monthly_price_cents=0)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def _limit(db_session, plan_id, feature_key, daily=None, monthly=None):
    limit = PlanLimit(plan_id=plan_id, feature_key=feature_key, daily_limit=daily, monthly_limit=monthly)
    db_session.add(limit)
    db_session.commit()
    return limit


def _feature_setting(db_session, feature_key, is_paid=False, credit_cost=0, is_enabled=True):
    setting = AiFeatureSetting(
        feature_key=feature_key, feature_label=feature_key, is_paid=is_paid,
        credit_cost_per_use=credit_cost, is_enabled=is_enabled,
    )
    db_session.add(setting)
    db_session.commit()
    return setting


# --- get_or_create_subscription -----------------------------------------------

def test_get_or_create_subscription_creates_free_plan_subscription(db_session):
    _plan(db_session, slug="free", name="Free")
    user = _user(db_session)

    subscription = get_or_create_subscription(db_session, user)
    assert subscription is not None
    assert subscription.status == "active"

    free_plan = db_session.query(Plan).filter(Plan.slug == "free").first()
    assert subscription.plan_id == free_plan.id


def test_get_or_create_subscription_returns_existing_row(db_session):
    plan = _plan(db_session)
    user = _user(db_session)
    first = get_or_create_subscription(db_session, user)
    second = get_or_create_subscription(db_session, user)
    assert first.id == second.id
    assert db_session.query(Subscription).count() == 1


def test_get_or_create_subscription_returns_none_when_no_free_plan_seeded(db_session):
    user = _user(db_session)
    assert get_or_create_subscription(db_session, user) is None


# --- usage counters -------------------------------------------------------------

def test_increment_usage_creates_and_increments(db_session):
    user = _user(db_session)
    assert get_usage_count(db_session, user.id, "resume_analysis", "monthly", "2026-08") == 0
    _increment_usage(db_session, user.id, "resume_analysis", "monthly", "2026-08")
    _increment_usage(db_session, user.id, "resume_analysis", "monthly", "2026-08")
    assert get_usage_count(db_session, user.id, "resume_analysis", "monthly", "2026-08") == 2


def test_usage_counter_is_isolated_per_period_key(db_session):
    user = _user(db_session)
    _increment_usage(db_session, user.id, "resume_analysis", "monthly", "2026-08")
    assert get_usage_count(db_session, user.id, "resume_analysis", "monthly", "2026-09") == 0


# --- credits ----------------------------------------------------------------------

def test_adjust_credits_credits_and_debits(db_session):
    user = _user(db_session)
    assert get_credit_balance(db_session, user.id) == 0
    balance = adjust_credits(db_session, user.id, 100, reason="purchase")
    assert balance == 100
    balance = adjust_credits(db_session, user.id, -30, reason="usage", feature_key="ai_resume_builder")
    assert balance == 70
    assert get_credit_balance(db_session, user.id) == 70


def test_adjust_credits_raises_on_insufficient_balance(db_session):
    user = _user(db_session)
    adjust_credits(db_session, user.id, 10, reason="purchase")
    with pytest.raises(ValueError):
        adjust_credits(db_session, user.id, -20, reason="usage")
    assert get_credit_balance(db_session, user.id) == 10  # unchanged


def test_adjust_credits_writes_ledger_entry(db_session):
    user = _user(db_session)
    adjust_credits(db_session, user.id, 50, reason="purchase", reference_id=7)
    entry = db_session.query(CreditLedgerEntry).first()
    assert entry.delta == 50
    assert entry.reason == "purchase"
    assert entry.reference_id == "7"


# --- check_and_consume ---------------------------------------------------------

def test_check_and_consume_allows_and_counts_within_plan_limit(db_session):
    plan = _plan(db_session)
    _limit(db_session, plan.id, "resume_analysis", monthly=2)
    user = _user(db_session)

    result = check_and_consume(db_session, user, "resume_analysis")
    assert result["allowed"] is True
    assert result["usedVia"] == "plan"
    assert result["monthlyUsed"] == 1


def test_check_and_consume_denies_when_plan_limit_exhausted_and_feature_free(db_session):
    plan = _plan(db_session)
    _limit(db_session, plan.id, "resume_analysis", monthly=1)
    user = _user(db_session)

    check_and_consume(db_session, user, "resume_analysis")  # uses the 1 included use
    with pytest.raises(FeatureAccessDenied) as exc_info:
        check_and_consume(db_session, user, "resume_analysis")
    assert exc_info.value.payload["error"] == "limit_reached"
    assert exc_info.value.payload["canBuyCredits"] is False


def test_check_and_consume_falls_back_to_credits_when_paid_and_limit_exhausted(db_session):
    plan = _plan(db_session)
    _limit(db_session, plan.id, "ai_resume_builder", monthly=1)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=10)
    user = _user(db_session)
    adjust_credits(db_session, user.id, 25, reason="purchase")

    check_and_consume(db_session, user, "ai_resume_builder")  # uses the included use
    result = check_and_consume(db_session, user, "ai_resume_builder")  # falls through to credits
    assert result["usedVia"] == "credits"
    assert result["creditCost"] == 10
    assert result["creditBalance"] == 15
    assert get_credit_balance(db_session, user.id) == 15


def test_check_and_consume_denies_with_insufficient_credits(db_session):
    plan = _plan(db_session)
    _limit(db_session, plan.id, "ai_resume_builder", monthly=0)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=10)
    user = _user(db_session)
    adjust_credits(db_session, user.id, 5, reason="purchase")

    with pytest.raises(FeatureAccessDenied) as exc_info:
        check_and_consume(db_session, user, "ai_resume_builder")
    assert exc_info.value.payload["error"] == "insufficient_credits"
    assert exc_info.value.payload["creditBalance"] == 5
    assert exc_info.value.payload["creditCost"] == 10
    assert exc_info.value.payload["canUpgrade"] is True
    assert exc_info.value.payload["canBuyCredits"] is True


def test_check_and_consume_allows_unlimited_when_limit_is_none(db_session):
    plan = _plan(db_session)
    _limit(db_session, plan.id, "learning_roadmap", monthly=None)
    user = _user(db_session)
    for _ in range(5):
        result = check_and_consume(db_session, user, "learning_roadmap")
        assert result["allowed"] is True


def test_check_and_consume_bypasses_everything_when_feature_disabled(db_session):
    plan = _plan(db_session)
    _limit(db_session, plan.id, "resume_analysis", monthly=0)
    _feature_setting(db_session, "resume_analysis", is_paid=True, credit_cost=999, is_enabled=False)
    user = _user(db_session)

    result = check_and_consume(db_session, user, "resume_analysis")
    assert result == {"allowed": True, "usedVia": "unrestricted", "reason": "gating_disabled"}


def test_check_and_consume_fails_open_when_no_free_plan_seeded(db_session):
    user = _user(db_session)
    result = check_and_consume(db_session, user, "resume_analysis")
    assert result == {"allowed": True, "usedVia": "unrestricted", "reason": "no_plan_configured"}


def test_check_and_consume_treats_missing_feature_setting_as_free(db_session):
    plan = _plan(db_session)
    _limit(db_session, plan.id, "resume_analysis", monthly=0)
    user = _user(db_session)
    # No AiFeatureSetting row exists at all for this feature.
    with pytest.raises(FeatureAccessDenied) as exc_info:
        check_and_consume(db_session, user, "resume_analysis")
    assert exc_info.value.payload["canBuyCredits"] is False


# --- get_feature_usage_summary --------------------------------------------------

def test_get_feature_usage_summary_reflects_plan_and_settings(db_session):
    plan = _plan(db_session, name="Premium", slug="premium")
    # get_or_create_subscription looks for slug "free" -- seed a free plan too so it's not None.
    _plan(db_session, slug="free_unused", name="unused")
    _limit(db_session, plan.id, "interview_practice", daily=2, monthly=50)
    _feature_setting(db_session, "interview_practice", is_paid=True, credit_cost=15)
    user = _user(db_session)

    subscription = Subscription(user_id=user.id, plan_id=plan.id, status="active")
    db_session.add(subscription)
    db_session.commit()

    summary = get_feature_usage_summary(db_session, user, "interview_practice")
    assert summary["isPaid"] is True
    assert summary["creditCostPerUse"] == 15
    assert summary["monthlyLimit"] == 50
    assert summary["dailyLimit"] == 2
    assert summary["planName"] == "Premium"
