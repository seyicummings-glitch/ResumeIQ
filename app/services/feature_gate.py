"""Usage gating for AI features — the enforcement layer behind the
Subscription & Credit Management system. check_and_consume() is called at
the start of every gated feature's route handler (before the actual AI work
runs, so a denied user never burns AI quota/cost); on success it also
records the usage. No FastAPI import here (mirrors this codebase's
service-layer convention) — routes catch FeatureAccessDenied and convert it
to an HTTPException themselves.

Two independent allowances, checked in order:
  1. The user's current plan's included allowance for this feature
     (PlanLimit.daily_limit/monthly_limit — None means unlimited under the
     plan). UsageCounter's period_key naturally changing each day/month IS
     the "resets at the next billing cycle" behavior — no reset job needed,
     a new period just starts a fresh counter at 0.
  2. If the plan allowance is exhausted AND the admin has marked this
     feature as paid (AiFeatureSetting.is_paid) with a non-zero credit
     cost, the user's credit balance is charged automatically instead of
     being blocked outright.

A feature with no AiFeatureSetting row, or an account with no Subscription
yet (e.g. Plans haven't been seeded on a fresh install), fails OPEN
(unrestricted) rather than silently blocking every AI feature platform-wide
over incomplete admin setup — the admin has to explicitly configure a
feature as paid for gating to ever deny anyone.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.models import User
from app.models.subscription_models import (
    Plan, PlanLimit, Subscription, UsageCounter, AiFeatureSetting, CreditBalance, CreditLedgerEntry,
)


class FeatureAccessDenied(Exception):
    """Raised by check_and_consume() when a feature use is denied. `payload`
    has everything the frontend needs to render an "Upgrade Plan / Buy
    Credits" prompt — callers should catch this and raise
    HTTPException(402, detail=exc.payload)."""

    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("message", "Access denied"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_keys(now: datetime | None = None) -> dict:
    now = now or _now()
    return {"daily": now.strftime("%Y-%m-%d"), "monthly": now.strftime("%Y-%m")}


def get_or_create_subscription(db: Session, user: User) -> Subscription | None:
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if subscription:
        return subscription

    free_plan = db.query(Plan).filter(Plan.slug == "free").first()
    if not free_plan:
        return None  # Plans haven't been seeded yet -- caller fails open, see module docstring.

    now = _now()
    subscription = Subscription(
        user_id=user.id, plan_id=free_plan.id, billing_cycle="monthly", status="active",
        current_period_start=now, current_period_end=now + timedelta(days=30),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_feature_setting(db: Session, feature_key: str) -> AiFeatureSetting | None:
    return db.query(AiFeatureSetting).filter(AiFeatureSetting.feature_key == feature_key).first()


def get_plan_limit(db: Session, plan_id: int, feature_key: str) -> PlanLimit | None:
    return db.query(PlanLimit).filter(PlanLimit.plan_id == plan_id, PlanLimit.feature_key == feature_key).first()


def get_usage_count(db: Session, user_id: int, feature_key: str, period_type: str, period_key: str) -> int:
    row = (
        db.query(UsageCounter)
        .filter(
            UsageCounter.user_id == user_id, UsageCounter.feature_key == feature_key,
            UsageCounter.period_type == period_type, UsageCounter.period_key == period_key,
        )
        .first()
    )
    return row.count if row else 0


def _increment_usage(db: Session, user_id: int, feature_key: str, period_type: str, period_key: str) -> None:
    row = (
        db.query(UsageCounter)
        .filter(
            UsageCounter.user_id == user_id, UsageCounter.feature_key == feature_key,
            UsageCounter.period_type == period_type, UsageCounter.period_key == period_key,
        )
        .first()
    )
    if row:
        row.count += 1
    else:
        db.add(UsageCounter(user_id=user_id, feature_key=feature_key, period_type=period_type, period_key=period_key, count=1))
    db.commit()


def get_credit_balance(db: Session, user_id: int) -> int:
    row = db.query(CreditBalance).filter(CreditBalance.user_id == user_id).first()
    return row.balance if row else 0


def adjust_credits(
    db: Session, user_id: int, delta: int, reason: str, feature_key: str | None = None, reference_id: str | None = None
) -> int:
    """Applies `delta` (positive to credit, negative to spend) to the user's
    balance and appends a CreditLedgerEntry. Raises ValueError rather than
    letting the balance go negative — callers spending credits must check
    get_credit_balance() first (check_and_consume() always does)."""
    row = db.query(CreditBalance).filter(CreditBalance.user_id == user_id).first()
    if not row:
        row = CreditBalance(user_id=user_id, balance=0)
        db.add(row)
        db.flush()

    new_balance = row.balance + delta
    if new_balance < 0:
        raise ValueError("Insufficient credit balance.")

    row.balance = new_balance
    db.add(CreditLedgerEntry(
        user_id=user_id, delta=delta, reason=reason, feature_key=feature_key,
        reference_id=str(reference_id) if reference_id is not None else None,
    ))
    db.commit()
    return new_balance


def get_feature_usage_summary(db: Session, user: User, feature_key: str) -> dict:
    """Read-only snapshot of where a user stands on one feature — used both
    internally and by GET /subscriptions/me."""
    setting = get_feature_setting(db, feature_key)
    subscription = get_or_create_subscription(db, user)
    periods = _period_keys()

    plan_limit = get_plan_limit(db, subscription.plan_id, feature_key) if subscription else None
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first() if subscription else None

    return {
        "featureKey": feature_key,
        "isPaid": setting.is_paid if setting else False,
        "isEnabled": setting.is_enabled if setting else True,
        "creditCostPerUse": setting.credit_cost_per_use if setting else 0,
        "dailyUsed": get_usage_count(db, user.id, feature_key, "daily", periods["daily"]),
        "dailyLimit": plan_limit.daily_limit if plan_limit else None,
        "monthlyUsed": get_usage_count(db, user.id, feature_key, "monthly", periods["monthly"]),
        "monthlyLimit": plan_limit.monthly_limit if plan_limit else None,
        "planName": plan.name if plan else None,
    }


def check_and_consume(db: Session, user: User, feature_key: str) -> dict:
    """The gate. Call before doing the actual AI work for a gated feature.
    Returns a result dict on success; raises FeatureAccessDenied on denial."""
    setting = get_feature_setting(db, feature_key)
    if setting is not None and not setting.is_enabled:
        return {"allowed": True, "usedVia": "unrestricted", "reason": "gating_disabled"}

    subscription = get_or_create_subscription(db, user)
    if subscription is None:
        return {"allowed": True, "usedVia": "unrestricted", "reason": "no_plan_configured"}

    periods = _period_keys()
    plan_limit = get_plan_limit(db, subscription.plan_id, feature_key)

    daily_used = get_usage_count(db, user.id, feature_key, "daily", periods["daily"])
    monthly_used = get_usage_count(db, user.id, feature_key, "monthly", periods["monthly"])
    daily_limit = plan_limit.daily_limit if plan_limit else None
    monthly_limit = plan_limit.monthly_limit if plan_limit else None

    within_daily = daily_limit is None or daily_used < daily_limit
    within_monthly = monthly_limit is None or monthly_used < monthly_limit

    if within_daily and within_monthly:
        _increment_usage(db, user.id, feature_key, "daily", periods["daily"])
        _increment_usage(db, user.id, feature_key, "monthly", periods["monthly"])
        return {
            "allowed": True, "usedVia": "plan",
            "dailyUsed": daily_used + 1, "dailyLimit": daily_limit,
            "monthlyUsed": monthly_used + 1, "monthlyLimit": monthly_limit,
        }

    is_paid = setting.is_paid if setting else False
    credit_cost = setting.credit_cost_per_use if setting else 0

    if is_paid and credit_cost > 0:
        balance = get_credit_balance(db, user.id)
        if balance >= credit_cost:
            new_balance = adjust_credits(db, user.id, -credit_cost, reason="usage", feature_key=feature_key)
            # Still recorded for usage stats/display, even though enforcement passed via credits
            # rather than the plan allowance.
            _increment_usage(db, user.id, feature_key, "daily", periods["daily"])
            _increment_usage(db, user.id, feature_key, "monthly", periods["monthly"])
            return {"allowed": True, "usedVia": "credits", "creditCost": credit_cost, "creditBalance": new_balance}

        raise FeatureAccessDenied({
            "error": "insufficient_credits",
            "message": "You have reached your monthly limit and don't have enough credits to continue.",
            "featureKey": feature_key,
            "creditCost": credit_cost,
            "creditBalance": balance,
            "dailyUsed": daily_used, "dailyLimit": daily_limit,
            "monthlyUsed": monthly_used, "monthlyLimit": monthly_limit,
            "canUpgrade": True, "canBuyCredits": True,
        })

    raise FeatureAccessDenied({
        "error": "limit_reached",
        "message": "You have reached your monthly limit.",
        "featureKey": feature_key,
        "dailyUsed": daily_used, "dailyLimit": daily_limit,
        "monthlyUsed": monthly_used, "monthlyLimit": monthly_limit,
        "canUpgrade": True, "canBuyCredits": is_paid,
    })
