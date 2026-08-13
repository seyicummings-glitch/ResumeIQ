import pytest

from app.models.models import User
from app.models.subscription_models import Plan, PlanLimit, Subscription, Transaction, CreditPackage, CreditLedgerEntry
from app.routes import subscriptions as routes


def _user(db_session, email="user@example.com"):
    user = User(email=email, hashed_password="x", full_name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _free_plan(db_session):
    plan = Plan(name="Free", slug="free", monthly_price_cents=0, yearly_price_cents=0, is_active=True)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def _premium_plan(db_session):
    plan = Plan(name="Premium", slug="premium", monthly_price_cents=1999, yearly_price_cents=19999, is_active=True)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


# --- GET /subscriptions/me -------------------------------------------------------

def test_get_my_subscription_lazily_creates_free_subscription(db_session):
    _free_plan(db_session)
    user = _user(db_session)

    result = routes.get_my_subscription(db_session, user)
    assert result["plan"]["slug"] == "free"
    assert result["creditBalance"] == 0
    assert len(result["usage"]) == 8  # one entry per FEATURE_KEYS


def test_get_my_subscription_reflects_credit_balance(db_session):
    _free_plan(db_session)
    user = _user(db_session)
    db_session.add(CreditLedgerEntry(user_id=user.id, delta=50, reason="purchase"))
    from app.models.subscription_models import CreditBalance
    db_session.add(CreditBalance(user_id=user.id, balance=50))
    db_session.commit()

    result = routes.get_my_subscription(db_session, user)
    assert result["creditBalance"] == 50


# --- GET /subscriptions/plans ------------------------------------------------------

def test_list_public_plans_only_returns_active_plans_with_limits(db_session):
    active = _premium_plan(db_session)
    db_session.add(PlanLimit(plan_id=active.id, feature_key="ai_resume_builder", monthly_limit=20))
    db_session.add(Plan(name="Retired", slug="retired", monthly_price_cents=999, is_active=False))
    db_session.commit()

    result = routes.list_public_plans(db_session)
    assert len(result) == 1
    assert result[0]["slug"] == "premium"
    assert result[0]["limits"][0] == {"featureKey": "ai_resume_builder", "dailyLimit": None, "monthlyLimit": 20}


# --- payment methods ----------------------------------------------------------------

def test_list_available_payment_methods_hides_disabled_ones(db_session):
    from app.services.subscription_admin import get_or_seed_payment_methods
    from app.models.subscription_models import PaymentMethodConfig

    get_or_seed_payment_methods(db_session)
    bitcoin = db_session.query(PaymentMethodConfig).filter(PaymentMethodConfig.method_key == "bitcoin").first()
    bitcoin.is_enabled = False
    db_session.commit()

    result = routes.list_available_payment_methods(db_session)
    keys = {m["methodKey"] for m in result}
    assert "bitcoin" not in keys
    assert "credit_card" in keys


# --- upgrade ------------------------------------------------------------------------

def test_upgrade_plan_succeeds_and_records_transaction(db_session):
    _free_plan(db_session)
    premium = _premium_plan(db_session)
    user = _user(db_session)

    result = routes.upgrade_plan(
        routes.UpgradeInput(planId=premium.id, billingCycle="monthly", paymentMethod="credit_card"), db_session, user,
    )
    assert result["planId"] == premium.id

    subscription = db_session.query(Subscription).filter(Subscription.user_id == user.id).first()
    assert subscription.plan_id == premium.id
    assert subscription.status == "active"

    transaction = db_session.query(Transaction).filter(Transaction.user_id == user.id).first()
    assert transaction.status == "paid"
    assert transaction.amount_cents == 1999
    assert transaction.kind == "subscription"


def test_upgrade_plan_to_free_skips_payment_gateway(db_session):
    free = _free_plan(db_session)
    user = _user(db_session)

    routes.upgrade_plan(routes.UpgradeInput(planId=free.id, billingCycle="monthly", paymentMethod="credit_card"), db_session, user)
    assert db_session.query(Transaction).count() == 0  # no charge for a $0 plan


def test_upgrade_plan_rejects_inactive_or_missing_plan(db_session):
    user = _user(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.upgrade_plan(routes.UpgradeInput(planId=999, billingCycle="monthly", paymentMethod="credit_card"), db_session, user)
    assert exc_info.value.status_code == 404


def test_upgrade_plan_rejects_invalid_billing_cycle(db_session):
    premium = _premium_plan(db_session)
    user = _user(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.upgrade_plan(routes.UpgradeInput(planId=premium.id, billingCycle="weekly", paymentMethod="credit_card"), db_session, user)
    assert exc_info.value.status_code == 400


def test_upgrade_plan_rejects_unsupported_payment_method(db_session):
    premium = _premium_plan(db_session)
    user = _user(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.upgrade_plan(routes.UpgradeInput(planId=premium.id, billingCycle="monthly", paymentMethod="check"), db_session, user)
    assert exc_info.value.status_code == 402
    failed_tx = db_session.query(Transaction).filter(Transaction.status == "failed").first()
    assert failed_tx is not None


# --- credit purchase -----------------------------------------------------------------

def _package(db_session, credits=100, price_cents=999):
    package = CreditPackage(name=f"{credits} Credits", credits=credits, price_cents=price_cents, is_active=True)
    db_session.add(package)
    db_session.commit()
    db_session.refresh(package)
    return package


def test_purchase_credits_success_adds_balance_and_transaction(db_session):
    package = _package(db_session, credits=100, price_cents=999)
    user = _user(db_session)

    result = routes.purchase_credits(routes.CreditPurchaseInput(packageId=package.id, paymentMethod="paypal"), db_session, user)
    assert result["creditsAdded"] == 100
    assert result["status"] == "Completed"
    assert result["transactionId"].startswith("TX-")
    assert "do not store" in result["disclosure"].lower()

    from app.services.feature_gate import get_credit_balance
    assert get_credit_balance(db_session, user.id) == 100

    transaction = db_session.query(Transaction).filter(Transaction.user_id == user.id).first()
    assert transaction.kind == "credit_purchase"
    assert transaction.credits_purchased == 100
    assert transaction.status == "paid"


def test_purchase_credits_rejects_inactive_package(db_session):
    package = _package(db_session)
    package.is_active = False
    db_session.commit()
    user = _user(db_session)

    with pytest.raises(Exception) as exc_info:
        routes.purchase_credits(routes.CreditPurchaseInput(packageId=package.id, paymentMethod="paypal"), db_session, user)
    assert exc_info.value.status_code == 404


def test_purchase_credits_failure_does_not_add_balance(db_session):
    package = _package(db_session)
    user = _user(db_session)

    with pytest.raises(Exception) as exc_info:
        routes.purchase_credits(routes.CreditPurchaseInput(packageId=package.id, paymentMethod="check"), db_session, user)
    assert exc_info.value.status_code == 402

    from app.services.feature_gate import get_credit_balance
    assert get_credit_balance(db_session, user.id) == 0


# --- history endpoints -----------------------------------------------------------------

def test_get_my_transactions_only_returns_own_transactions(db_session):
    user_a = _user(db_session, "a@example.com")
    user_b = _user(db_session, "b@example.com")
    db_session.add_all([
        Transaction(user_id=user_a.id, kind="credit_purchase", amount_cents=999, currency="usd", status="paid"),
        Transaction(user_id=user_b.id, kind="credit_purchase", amount_cents=999, currency="usd", status="paid"),
    ])
    db_session.commit()

    result = routes.get_my_transactions(page=1, pageSize=20, db=db_session, current_user=user_a)
    assert result["total"] == 1


def test_get_my_usage_history_only_returns_own_entries(db_session):
    user_a = _user(db_session, "a@example.com")
    user_b = _user(db_session, "b@example.com")
    db_session.add_all([
        CreditLedgerEntry(user_id=user_a.id, delta=100, reason="purchase"),
        CreditLedgerEntry(user_id=user_b.id, delta=100, reason="purchase"),
    ])
    db_session.commit()

    result = routes.get_my_usage_history(page=1, pageSize=20, db=db_session, current_user=user_a)
    assert result["total"] == 1
