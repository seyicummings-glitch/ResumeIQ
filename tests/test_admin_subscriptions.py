from unittest.mock import patch

import pytest

from app.models.models import User
from app.models.subscription_models import Plan, PlanLimit, Subscription, Transaction, CreditPackage
from app.routes import admin_subscriptions as routes


@pytest.fixture(autouse=True)
def _no_real_stripe_calls():
    """Every test in this file exercises route handlers directly; none of
    them should ever reach the real Stripe network — sync_plan_to_stripe is
    replaced with a no-op unless a test explicitly wants to assert on it."""
    with patch("app.routes.admin_subscriptions.sync_plan_to_stripe") as mock_sync:
        yield mock_sync


def _admin(db_session):
    user = User(email="admin@example.com", hashed_password="x", role="admin")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_plan_persists_and_serializes(db_session):
    admin = _admin(db_session)
    data = routes.PlanCreateInput(name="Basic", slug="basic", description="desc", monthlyPriceCents=999, yearlyPriceCents=9999)

    result = routes.create_plan(data, db_session, admin)

    assert result["name"] == "Basic"
    assert result["slug"] == "basic"
    assert result["monthlyPriceCents"] == 999
    assert result["isActive"] is True
    assert db_session.query(Plan).filter(Plan.slug == "basic").count() == 1


def test_create_plan_rejects_duplicate_slug(db_session):
    admin = _admin(db_session)
    db_session.add(Plan(name="Basic", slug="basic", monthly_price_cents=999))
    db_session.commit()

    data = routes.PlanCreateInput(name="Basic 2", slug="basic", monthlyPriceCents=1999)
    with pytest.raises(Exception) as exc_info:
        routes.create_plan(data, db_session, admin)
    assert exc_info.value.status_code == 400


def test_update_plan_resyncs_stripe_only_when_price_or_identity_changes(db_session, _no_real_stripe_calls):
    admin = _admin(db_session)
    plan = Plan(name="Basic", slug="basic", monthly_price_cents=999)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    _no_real_stripe_calls.reset_mock()

    routes.update_plan(plan.id, routes.PlanUpdateInput(displayOrder=5), db_session, admin)
    _no_real_stripe_calls.assert_not_called()

    routes.update_plan(plan.id, routes.PlanUpdateInput(monthlyPriceCents=1999), db_session, admin)
    _no_real_stripe_calls.assert_called_once()


def test_set_plan_status_toggles_active_flag(db_session):
    admin = _admin(db_session)
    plan = Plan(name="Basic", slug="basic", monthly_price_cents=999, is_active=True)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    result = routes.set_plan_status(plan.id, routes.PlanStatusInput(isActive=False), db_session, admin)
    assert result["isActive"] is False


def test_delete_plan_removes_plan_and_its_limits(db_session):
    admin = _admin(db_session)
    plan = Plan(name="Basic", slug="basic", monthly_price_cents=999)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    db_session.add(PlanLimit(plan_id=plan.id, feature_key="resume_analysis", daily_limit=5, monthly_limit=50))
    db_session.commit()

    routes.delete_plan(plan.id, db_session, admin)

    assert db_session.query(Plan).filter(Plan.id == plan.id).count() == 0
    assert db_session.query(PlanLimit).filter(PlanLimit.plan_id == plan.id).count() == 0


def test_get_plan_limits_fills_in_missing_feature_keys(db_session):
    from app.services.subscription_limits import FEATURE_KEYS

    admin = _admin(db_session)
    plan = Plan(name="Basic", slug="basic", monthly_price_cents=999)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    db_session.add(PlanLimit(plan_id=plan.id, feature_key="resume_analysis", daily_limit=5, monthly_limit=50))
    db_session.commit()

    limits = routes.get_plan_limits(plan.id, db_session, admin)

    assert len(limits) == len(FEATURE_KEYS)
    resume_limit = next(entry for entry in limits if entry["featureKey"] == "resume_analysis")
    assert resume_limit == {"featureKey": "resume_analysis", "dailyLimit": 5, "monthlyLimit": 50}
    other_limit = next(entry for entry in limits if entry["featureKey"] == "ai_chat")
    assert other_limit == {"featureKey": "ai_chat", "dailyLimit": None, "monthlyLimit": None}


def test_update_plan_limits_upserts_and_rejects_unknown_feature_keys(db_session):
    admin = _admin(db_session)
    plan = Plan(name="Basic", slug="basic", monthly_price_cents=999)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    routes.update_plan_limits(
        plan.id,
        routes.PlanLimitsUpdateInput(limits=[routes.PlanLimitInput(featureKey="resume_analysis", dailyLimit=10, monthlyLimit=100)]),
        db_session,
        admin,
    )
    saved = db_session.query(PlanLimit).filter(PlanLimit.plan_id == plan.id, PlanLimit.feature_key == "resume_analysis").first()
    assert saved.daily_limit == 10 and saved.monthly_limit == 100

    # Upsert again with a different value — should update the same row, not create a duplicate
    routes.update_plan_limits(
        plan.id,
        routes.PlanLimitsUpdateInput(limits=[routes.PlanLimitInput(featureKey="resume_analysis", dailyLimit=20, monthlyLimit=200)]),
        db_session,
        admin,
    )
    assert db_session.query(PlanLimit).filter(PlanLimit.plan_id == plan.id, PlanLimit.feature_key == "resume_analysis").count() == 1

    with pytest.raises(Exception) as exc_info:
        routes.update_plan_limits(
            plan.id,
            routes.PlanLimitsUpdateInput(limits=[routes.PlanLimitInput(featureKey="not_a_real_feature", dailyLimit=1)]),
            db_session,
            admin,
        )
    assert exc_info.value.status_code == 400


def test_list_plans_paginates_and_filters_by_status(db_session):
    admin = _admin(db_session)
    db_session.add_all([
        Plan(name="Free", slug="free", monthly_price_cents=0, is_active=True, display_order=0),
        Plan(name="Basic", slug="basic", monthly_price_cents=999, is_active=True, display_order=1),
        Plan(name="Retired", slug="retired", monthly_price_cents=999, is_active=False, display_order=2),
    ])
    db_session.commit()

    active_only = routes.list_plans(page=1, pageSize=20, search=None, status="active", db=db_session, current_user=admin)
    assert active_only["total"] == 2
    assert {p["slug"] for p in active_only["items"]} == {"free", "basic"}

    all_plans = routes.list_plans(page=1, pageSize=20, search=None, status=None, db=db_session, current_user=admin)
    assert all_plans["total"] == 3


def test_delete_plan_rejects_when_plan_has_subscribers(db_session):
    admin = _admin(db_session)
    plan = Plan(name="Premium", slug="premium", monthly_price_cents=1999)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    user = User(email="subscriber@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.add(Subscription(user_id=user.id, plan_id=plan.id, status="active"))
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        routes.delete_plan(plan.id, db_session, admin)
    assert exc_info.value.status_code == 400
    assert db_session.query(Plan).filter(Plan.id == plan.id).count() == 1


# --- AI feature settings ---------------------------------------------------------

def test_list_feature_settings_seeds_all_known_features(db_session):
    from app.services.subscription_limits import FEATURE_KEYS

    admin = _admin(db_session)
    result = routes.list_feature_settings(db_session, admin)
    assert {r["featureKey"] for r in result} == set(FEATURE_KEYS)
    assert all(r["isPaid"] is False for r in result)


def test_update_feature_setting_persists_changes(db_session):
    admin = _admin(db_session)
    result = routes.update_feature_setting(
        "ai_resume_builder", routes.FeatureSettingUpdateInput(isPaid=True, creditCostPerUse=10, isEnabled=True),
        db_session, admin,
    )
    assert result == {"featureKey": "ai_resume_builder", "featureLabel": "AI Resume Builder", "isPaid": True, "creditCostPerUse": 10, "isEnabled": True}


def test_update_feature_setting_rejects_unknown_feature_key(db_session):
    admin = _admin(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.update_feature_setting("not_real", routes.FeatureSettingUpdateInput(isPaid=True, creditCostPerUse=5), db_session, admin)
    assert exc_info.value.status_code == 400


def test_update_feature_setting_rejects_negative_credit_cost(db_session):
    admin = _admin(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.update_feature_setting("ai_resume_builder", routes.FeatureSettingUpdateInput(isPaid=True, creditCostPerUse=-5), db_session, admin)
    assert exc_info.value.status_code == 400


# --- Credit packages --------------------------------------------------------------

def test_create_and_list_credit_packages(db_session):
    admin = _admin(db_session)
    routes.create_credit_package(routes.CreditPackageInput(name="100 Credits", credits=100, priceCents=999), db_session, admin)
    routes.create_credit_package(routes.CreditPackageInput(name="500 Credits", credits=500, priceCents=3999, displayOrder=1), db_session, admin)

    result = routes.list_credit_packages(db_session, admin)
    assert len(result) == 2
    assert result[0]["name"] == "100 Credits"


def test_create_credit_package_rejects_non_positive_values(db_session):
    admin = _admin(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.create_credit_package(routes.CreditPackageInput(name="Bad", credits=0, priceCents=999), db_session, admin)
    assert exc_info.value.status_code == 400


def test_update_and_toggle_credit_package(db_session):
    admin = _admin(db_session)
    created = routes.create_credit_package(routes.CreditPackageInput(name="100 Credits", credits=100, priceCents=999), db_session, admin)

    updated = routes.update_credit_package(created["id"], routes.CreditPackageInput(name="150 Credits", credits=150, priceCents=1299), db_session, admin)
    assert updated["credits"] == 150

    toggled = routes.set_credit_package_status(created["id"], routes.PackageStatusInput(isActive=False), db_session, admin)
    assert toggled["isActive"] is False


def test_delete_credit_package(db_session):
    admin = _admin(db_session)
    created = routes.create_credit_package(routes.CreditPackageInput(name="100 Credits", credits=100, priceCents=999), db_session, admin)
    routes.delete_credit_package(created["id"], db_session, admin)
    assert db_session.query(CreditPackage).count() == 0


# --- Payment methods ---------------------------------------------------------------

def test_list_payment_methods_seeds_defaults(db_session):
    admin = _admin(db_session)
    result = routes.list_payment_methods(db_session, admin)
    assert {m["methodKey"] for m in result} == {"credit_card", "debit_card", "paypal", "bitcoin"}


def test_set_payment_method_status_toggles(db_session):
    admin = _admin(db_session)
    routes.list_payment_methods(db_session, admin)  # seed first
    result = routes.set_payment_method_status("bitcoin", routes.PaymentMethodStatusInput(isEnabled=False), db_session, admin)
    assert result["isEnabled"] is False


def test_set_payment_method_status_rejects_unknown_method(db_session):
    admin = _admin(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.set_payment_method_status("carrier_pigeon", routes.PaymentMethodStatusInput(isEnabled=True), db_session, admin)
    assert exc_info.value.status_code == 404


# --- Subscribers & transactions ---------------------------------------------------

def test_list_subscribers_returns_joined_user_and_plan_info(db_session):
    admin = _admin(db_session)
    plan = Plan(name="Premium", slug="premium", monthly_price_cents=1999)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    user = User(email="jane@example.com", hashed_password="x", full_name="Jane Doe")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.add(Subscription(user_id=user.id, plan_id=plan.id, status="active"))
    db_session.commit()

    result = routes.list_subscribers(page=1, pageSize=20, planId=None, status=None, db=db_session, current_user=admin)
    assert result["total"] == 1
    assert result["items"][0]["userName"] == "Jane Doe"
    assert result["items"][0]["planName"] == "Premium"


def test_list_transactions_filters_by_status_and_kind(db_session):
    admin = _admin(db_session)
    user = User(email="jane@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.add_all([
        Transaction(user_id=user.id, kind="credit_purchase", amount_cents=999, currency="usd", status="paid", credits_purchased=100),
        Transaction(user_id=user.id, kind="subscription", amount_cents=1999, currency="usd", status="failed"),
    ])
    db_session.commit()

    paid_only = routes.list_transactions(page=1, pageSize=20, status="paid", kind=None, db=db_session, current_user=admin)
    assert paid_only["total"] == 1
    assert paid_only["items"][0]["kind"] == "credit_purchase"
    assert paid_only["items"][0]["creditsPurchased"] == 100


def test_get_subscription_analytics_route_returns_a_dict(db_session):
    admin = _admin(db_session)
    result = routes.get_subscription_analytics(db_session, admin)
    assert "totalCreditsPurchased" in result
    assert "usersNearLimit" in result
