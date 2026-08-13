from datetime import datetime, timedelta, timezone

import pytest

from app.models.models import User
from app.models.admin_models import AppSetting
from app.models.subscription_models import Plan, Subscription, AiFeatureSetting, CreditBalance, CreditLedgerEntry
from app.services.feature_gate import (
    get_or_create_subscription,
    get_feature_setting,
    get_usage_count,
    _increment_usage,
    get_credit_balance,
    adjust_credits,
    grant_signup_credits,
    next_free_refresh_at,
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


def _plan(db_session, slug="free", name="Free", monthly_credits=0):
    plan = Plan(name=name, slug=slug, monthly_price_cents=0, monthly_credits=monthly_credits)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def _feature_setting(db_session, feature_key, is_paid=False, credit_cost=0, is_enabled=True):
    setting = AiFeatureSetting(
        feature_key=feature_key, feature_label=feature_key, is_paid=is_paid,
        credit_cost_per_use=credit_cost, is_enabled=is_enabled,
    )
    db_session.add(setting)
    db_session.commit()
    return setting


def _app_settings(db_session, free_signup_credits=100, free_credit_refresh_hours=720):
    row = AppSetting(free_signup_credits=free_signup_credits, free_credit_refresh_hours=free_credit_refresh_hours)
    db_session.add(row)
    db_session.commit()
    return row


def _give_tokens(db_session, user, amount):
    """Grants tokens as a purchase would, with last_free_refresh_at already stamped -- the same
    state a real account is in post-registration. Without this, a plain adjust_credits() call
    leaves last_free_refresh_at unset, and the free-plan periodic refresh (correctly) treats
    that as "never refreshed" and adds a surprise bonus the moment gating checks it -- exactly
    what grant_signup_credits() exists to prevent for real accounts."""
    balance_row = db_session.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
    if not balance_row:
        balance_row = CreditBalance(user_id=user.id, balance=0)
        db_session.add(balance_row)
        db_session.flush()
    balance_row.last_free_refresh_at = datetime.now(timezone.utc)
    db_session.commit()
    adjust_credits(db_session, user.id, amount, reason="purchase")


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
    _plan(db_session)
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


# --- credits/tokens ----------------------------------------------------------------

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


# --- signup grant ----------------------------------------------------------------

def test_grant_signup_credits_uses_admin_configured_amount(db_session):
    _app_settings(db_session, free_signup_credits=250)
    user = _user(db_session)

    grant_signup_credits(db_session, user)

    assert get_credit_balance(db_session, user.id) == 250
    entry = db_session.query(CreditLedgerEntry).filter(CreditLedgerEntry.reason == "signup_grant").first()
    assert entry.delta == 250
    balance_row = db_session.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
    assert balance_row.last_free_refresh_at is not None


def test_grant_signup_credits_uses_default_when_no_settings_row(db_session):
    user = _user(db_session)
    grant_signup_credits(db_session, user)
    assert get_credit_balance(db_session, user.id) == 100  # DEFAULT_FREE_SIGNUP_CREDITS


def test_grant_signup_credits_is_a_noop_when_admin_sets_zero(db_session):
    _app_settings(db_session, free_signup_credits=0)
    user = _user(db_session)
    grant_signup_credits(db_session, user)
    assert get_credit_balance(db_session, user.id) == 0
    assert db_session.query(CreditLedgerEntry).count() == 0


# --- check_and_consume: unmetered / disabled features --------------------------

def test_check_and_consume_allows_unmetered_feature_without_touching_balance(db_session):
    _feature_setting(db_session, "resume_analysis", is_paid=False)
    user = _user(db_session)

    result = check_and_consume(db_session, user, "resume_analysis")
    assert result == {"allowed": True, "usedVia": "unrestricted", "reason": "free_feature"}
    assert get_credit_balance(db_session, user.id) == 0
    assert get_usage_count(db_session, user.id, "resume_analysis", "monthly", datetime.now(timezone.utc).strftime("%Y-%m")) == 1


def test_check_and_consume_treats_missing_feature_setting_as_unmetered(db_session):
    user = _user(db_session)
    # No AiFeatureSetting row exists at all for this feature.
    result = check_and_consume(db_session, user, "resume_analysis")
    assert result["allowed"] is True
    assert result["usedVia"] == "unrestricted"


def test_check_and_consume_bypasses_everything_when_feature_disabled(db_session):
    _feature_setting(db_session, "resume_analysis", is_paid=True, credit_cost=999, is_enabled=False)
    user = _user(db_session)

    result = check_and_consume(db_session, user, "resume_analysis")
    assert result == {"allowed": True, "usedVia": "unrestricted", "reason": "gating_disabled"}


def test_check_and_consume_zero_cost_paid_feature_is_treated_as_unmetered(db_session):
    _feature_setting(db_session, "resume_analysis", is_paid=True, credit_cost=0)
    user = _user(db_session)
    result = check_and_consume(db_session, user, "resume_analysis")
    assert result["usedVia"] == "unrestricted"


def test_check_and_consume_fails_open_when_no_free_plan_seeded(db_session):
    _feature_setting(db_session, "resume_analysis", is_paid=True, credit_cost=10)
    user = _user(db_session)
    result = check_and_consume(db_session, user, "resume_analysis")
    assert result == {"allowed": True, "usedVia": "unrestricted", "reason": "no_plan_configured"}


# --- check_and_consume: token deduction -----------------------------------------

def test_check_and_consume_deducts_tokens_when_balance_covers_cost(db_session):
    _plan(db_session)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=15)
    user = _user(db_session)
    _give_tokens(db_session, user, 100)

    result = check_and_consume(db_session, user, "ai_resume_builder")
    assert result["allowed"] is True
    assert result["usedVia"] == "tokens"
    assert result["creditCost"] == 15
    assert result["creditBalance"] == 85
    assert get_credit_balance(db_session, user.id) == 85


def test_check_and_consume_denies_with_insufficient_tokens(db_session):
    _plan(db_session)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=15)
    user = _user(db_session)
    _give_tokens(db_session, user, 5)

    with pytest.raises(FeatureAccessDenied) as exc_info:
        check_and_consume(db_session, user, "ai_resume_builder")
    payload = exc_info.value.payload
    assert payload["error"] == "insufficient_credits"
    assert payload["creditBalance"] == 5
    assert payload["creditCost"] == 15
    assert payload["canUpgrade"] is True
    assert payload["canBuyCredits"] is True
    assert get_credit_balance(db_session, user.id) == 5  # unchanged


def test_check_and_consume_denial_includes_next_refresh_for_free_plan(db_session):
    _app_settings(db_session, free_signup_credits=10, free_credit_refresh_hours=24)
    _plan(db_session)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=999)
    user = _user(db_session)

    with pytest.raises(FeatureAccessDenied) as exc_info:
        check_and_consume(db_session, user, "ai_resume_builder")
    assert exc_info.value.payload["nextRefreshAt"] is not None


def test_check_and_consume_records_usage_counter_on_success(db_session):
    _plan(db_session)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=10)
    user = _user(db_session)
    adjust_credits(db_session, user.id, 50, reason="purchase")

    check_and_consume(db_session, user, "ai_resume_builder")
    monthly_key = datetime.now(timezone.utc).strftime("%Y-%m")
    assert get_usage_count(db_session, user.id, "ai_resume_builder", "monthly", monthly_key) == 1


# --- free-plan periodic refresh --------------------------------------------------

def test_free_plan_balance_refreshes_after_interval_elapses(db_session):
    _app_settings(db_session, free_signup_credits=10, free_credit_refresh_hours=24)
    _plan(db_session)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=10)
    user = _user(db_session)
    grant_signup_credits(db_session, user)  # balance = 10

    check_and_consume(db_session, user, "ai_resume_builder")  # spends the 10 -> balance 0
    assert get_credit_balance(db_session, user.id) == 0

    # Simulate the refresh interval having elapsed.
    balance_row = db_session.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
    balance_row.last_free_refresh_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db_session.commit()

    result = check_and_consume(db_session, user, "ai_resume_builder")  # refresh fires, then spends 10
    assert result["allowed"] is True
    assert get_credit_balance(db_session, user.id) == 0  # refreshed to 10, then spent 10


def test_free_plan_balance_does_not_refresh_before_interval_elapses(db_session):
    _app_settings(db_session, free_signup_credits=10, free_credit_refresh_hours=24)
    _plan(db_session)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=10)
    user = _user(db_session)
    grant_signup_credits(db_session, user)

    check_and_consume(db_session, user, "ai_resume_builder")  # balance -> 0
    with pytest.raises(FeatureAccessDenied):
        check_and_consume(db_session, user, "ai_resume_builder")  # still 0, interval hasn't elapsed
    assert get_credit_balance(db_session, user.id) == 0


def test_paid_plan_never_gets_the_free_refresh(db_session):
    _app_settings(db_session, free_signup_credits=999, free_credit_refresh_hours=24)
    plan = _plan(db_session, slug="premium", name="Premium", monthly_credits=100)
    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=10)
    user = _user(db_session)

    subscription = Subscription(
        user_id=user.id, plan_id=plan.id, status="active",
        current_period_start=datetime.now(timezone.utc), current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(subscription)
    db_session.commit()

    with pytest.raises(FeatureAccessDenied):
        check_and_consume(db_session, user, "ai_resume_builder")  # no free refresh on a paid plan
    assert get_credit_balance(db_session, user.id) == 0


def test_next_free_refresh_at_is_none_for_a_paid_plan(db_session):
    plan = _plan(db_session, slug="premium", name="Premium")
    user = _user(db_session)
    subscription = Subscription(user_id=user.id, plan_id=plan.id, status="active")
    db_session.add(subscription)
    db_session.commit()

    assert next_free_refresh_at(db_session, user, subscription) is None


# --- subscription expiration -----------------------------------------------------

def test_expired_paid_subscription_reverts_to_free_plan(db_session):
    _plan(db_session, slug="free", name="Free")
    premium = _plan(db_session, slug="premium", name="Premium", monthly_credits=500)
    _feature_setting(db_session, "resume_analysis", is_paid=False)  # unmetered, just to trigger the gate path cheaply
    user = _user(db_session)

    subscription = Subscription(
        user_id=user.id, plan_id=premium.id, status="active",
        current_period_start=datetime.now(timezone.utc) - timedelta(days=60),
        current_period_end=datetime.now(timezone.utc) - timedelta(days=30),  # expired a month ago
    )
    db_session.add(subscription)
    db_session.commit()

    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=10)
    check_and_consume(db_session, user, "ai_resume_builder")  # triggers the lazy expiry check

    db_session.refresh(subscription)
    free_plan = db_session.query(Plan).filter(Plan.slug == "free").first()
    assert subscription.plan_id == free_plan.id


def test_active_paid_subscription_does_not_expire_early(db_session):
    _plan(db_session, slug="free", name="Free")
    premium = _plan(db_session, slug="premium", name="Premium", monthly_credits=500)
    user = _user(db_session)
    subscription = Subscription(
        user_id=user.id, plan_id=premium.id, status="active",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(subscription)
    db_session.commit()

    _feature_setting(db_session, "ai_resume_builder", is_paid=True, credit_cost=10)
    adjust_credits(db_session, user.id, 100, reason="purchase")
    check_and_consume(db_session, user, "ai_resume_builder")

    db_session.refresh(subscription)
    assert subscription.plan_id == premium.id  # unchanged


# --- get_feature_usage_summary --------------------------------------------------

def test_get_feature_usage_summary_reflects_settings_and_plan(db_session):
    plan = _plan(db_session, name="Premium", slug="premium")
    _plan(db_session, slug="free_unused", name="unused")
    _feature_setting(db_session, "interview_practice", is_paid=True, credit_cost=15)
    user = _user(db_session)

    subscription = Subscription(user_id=user.id, plan_id=plan.id, status="active")
    db_session.add(subscription)
    db_session.commit()

    summary = get_feature_usage_summary(db_session, user, "interview_practice")
    assert summary["isPaid"] is True
    assert summary["creditCostPerUse"] == 15
    assert summary["planName"] == "Premium"
