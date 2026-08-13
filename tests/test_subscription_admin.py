from datetime import datetime, timezone

from app.models.models import User
from app.models.subscription_models import (
    Plan, PlanLimit, Subscription, Transaction, UsageCounter, CreditLedgerEntry,
)
from app.services.subscription_limits import FEATURE_KEYS
from app.services.subscription_admin import (
    get_or_seed_feature_settings,
    get_or_seed_payment_methods,
    count_paid_active_subscribers,
    compute_credit_totals,
    compute_most_used_features,
    compute_revenue_by_plan,
    compute_revenue_by_feature_estimated,
    get_users_near_limit,
    compute_subscription_analytics,
)

NOW = datetime.now(timezone.utc)


def _user(db_session, email="user@example.com"):
    user = User(email=email, hashed_password="x", full_name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _plan(db_session, slug, name):
    plan = Plan(name=name, slug=slug, monthly_price_cents=1999)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


# --- lazy seeding -----------------------------------------------------------

def test_get_or_seed_feature_settings_creates_a_row_per_known_feature(db_session):
    settings = get_or_seed_feature_settings(db_session)
    assert {s.feature_key for s in settings} == set(FEATURE_KEYS)
    assert all(s.is_paid is False and s.is_enabled is True for s in settings)


def test_get_or_seed_feature_settings_is_idempotent(db_session):
    get_or_seed_feature_settings(db_session)
    second = get_or_seed_feature_settings(db_session)
    assert len(second) == len(FEATURE_KEYS)


def test_get_or_seed_payment_methods_creates_four_defaults(db_session):
    methods = get_or_seed_payment_methods(db_session)
    assert {m.method_key for m in methods} == {"credit_card", "debit_card", "paypal", "bitcoin"}
    assert all(m.is_enabled for m in methods)


# --- subscriber counting -----------------------------------------------------

def test_count_paid_active_subscribers_excludes_free_plan(db_session):
    free_plan = _plan(db_session, "free", "Free")
    premium_plan = _plan(db_session, "premium", "Premium")
    user_a = _user(db_session, "a@example.com")
    user_b = _user(db_session, "b@example.com")
    db_session.add(Subscription(user_id=user_a.id, plan_id=free_plan.id, status="active"))
    db_session.add(Subscription(user_id=user_b.id, plan_id=premium_plan.id, status="active"))
    db_session.commit()

    assert count_paid_active_subscribers(db_session) == 1


# --- credit totals ------------------------------------------------------------

def test_compute_credit_totals(db_session):
    user = _user(db_session)
    db_session.add_all([
        CreditLedgerEntry(user_id=user.id, delta=100, reason="purchase"),
        CreditLedgerEntry(user_id=user.id, delta=500, reason="purchase"),
        CreditLedgerEntry(user_id=user.id, delta=-30, reason="usage", feature_key="ai_resume_builder"),
    ])
    db_session.commit()

    totals = compute_credit_totals(db_session)
    assert totals == {"totalCreditsPurchased": 600, "creditsConsumed": 30}


# --- most used features --------------------------------------------------------

def test_compute_most_used_features_sums_monthly_not_daily_to_avoid_double_counting(db_session):
    user = _user(db_session)
    db_session.add_all([
        UsageCounter(user_id=user.id, feature_key="resume_analysis", period_type="monthly", period_key="2026-08", count=5),
        UsageCounter(user_id=user.id, feature_key="resume_analysis", period_type="daily", period_key="2026-08-01", count=5),
        UsageCounter(user_id=user.id, feature_key="ai_resume_builder", period_type="monthly", period_key="2026-08", count=2),
    ])
    db_session.commit()

    result = compute_most_used_features(db_session)
    lookup = {r["featureKey"]: r["count"] for r in result}
    assert lookup["resume_analysis"] == 5  # not 10
    assert lookup["ai_resume_builder"] == 2


# --- revenue --------------------------------------------------------------------

def test_compute_revenue_by_plan_only_counts_paid_subscription_transactions(db_session):
    plan = _plan(db_session, "premium", "Premium")
    user = _user(db_session)
    db_session.add_all([
        Transaction(user_id=user.id, plan_id=plan.id, kind="subscription", amount_cents=1999, currency="usd", status="paid"),
        Transaction(user_id=user.id, plan_id=plan.id, kind="subscription", amount_cents=1999, currency="usd", status="failed"),
        Transaction(user_id=user.id, kind="credit_purchase", amount_cents=999, currency="usd", status="paid"),
    ])
    db_session.commit()

    result = compute_revenue_by_plan(db_session)
    assert result == [{"plan": "Premium", "revenueCents": 1999}]


def test_compute_revenue_by_feature_estimated_uses_blended_rate(db_session):
    user = _user(db_session)
    # $10 for 100 credits purchased -> $0.10/credit blended rate
    db_session.add(Transaction(user_id=user.id, kind="credit_purchase", amount_cents=1000, currency="usd", status="paid", credits_purchased=100))
    db_session.add(CreditLedgerEntry(user_id=user.id, delta=100, reason="purchase"))
    db_session.add(CreditLedgerEntry(user_id=user.id, delta=-40, reason="usage", feature_key="ai_resume_builder"))
    db_session.commit()

    result = compute_revenue_by_feature_estimated(db_session)
    assert result == [{"featureKey": "ai_resume_builder", "label": "AI Resume Builder", "creditsConsumed": 40, "estimatedRevenueCents": 400}]


def test_compute_revenue_by_feature_estimated_handles_zero_credits_purchased(db_session):
    result = compute_revenue_by_feature_estimated(db_session)
    assert result == []


# --- users near limit -----------------------------------------------------------

def test_get_users_near_limit_flags_users_above_threshold(db_session):
    plan = _plan(db_session, "premium", "Premium")
    db_session.add(PlanLimit(plan_id=plan.id, feature_key="ai_resume_builder", monthly_limit=10))
    user = _user(db_session, "near@example.com")
    db_session.add(Subscription(user_id=user.id, plan_id=plan.id, status="active"))
    monthly_key = NOW.strftime("%Y-%m")
    db_session.add(UsageCounter(user_id=user.id, feature_key="ai_resume_builder", period_type="monthly", period_key=monthly_key, count=9))
    db_session.commit()

    result = get_users_near_limit(db_session, threshold=0.8)
    assert len(result) == 1
    assert result[0]["userId"] == user.id
    assert result[0]["used"] == 9
    assert result[0]["limit"] == 10


def test_get_users_near_limit_excludes_users_below_threshold(db_session):
    plan = _plan(db_session, "premium", "Premium")
    db_session.add(PlanLimit(plan_id=plan.id, feature_key="ai_resume_builder", monthly_limit=10))
    user = _user(db_session, "safe@example.com")
    db_session.add(Subscription(user_id=user.id, plan_id=plan.id, status="active"))
    monthly_key = NOW.strftime("%Y-%m")
    db_session.add(UsageCounter(user_id=user.id, feature_key="ai_resume_builder", period_type="monthly", period_key=monthly_key, count=2))
    db_session.commit()

    result = get_users_near_limit(db_session, threshold=0.8)
    assert result == []


# --- full analytics bundle -------------------------------------------------------

def test_compute_subscription_analytics_returns_all_expected_keys(db_session):
    result = compute_subscription_analytics(db_session)
    assert set(result.keys()) == {
        "totalCreditsPurchased", "creditsConsumed", "mostUsedFeatures",
        "revenueByPlan", "revenueByFeatureEstimated", "activeSubscribers", "usersNearLimit",
    }
