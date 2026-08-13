"""Usage gating for AI features — the enforcement layer behind the AI token economy
(ChatGPT/Claude/Midjourney-style: one shared token balance, drained by a configurable
per-feature cost, refilled by a signup grant, a periodic free-plan refresh, and paid-plan
monthly grants). check_and_consume() is called at the start of every gated feature's route
handler (before the actual AI work runs, so a denied user never burns AI quota/cost); on
success it also records the usage. No FastAPI import here (mirrors this codebase's
service-layer convention) — routes catch FeatureAccessDenied and convert it to an
HTTPException(402, ...) themselves.

How a use is paid for, checked in order:
  1. The feature must be both enabled (AiFeatureSetting.is_enabled) and marked paid with a
     positive credit_cost_per_use — otherwise it's unmetered and always allowed (usage is still
     counted for admin "most used features" analytics).
  2. Before checking the balance, two lazy, no-cron-job-needed maintenance steps run (the same
     "a new period just starts fresh" pattern UsageCounter already uses):
       - _maybe_expire_subscription: a paid plan whose current_period_end has passed reverts the
         account to the Free plan (this project's mocked payment gateway has no real recurring
         billing to auto-renew it).
       - _maybe_refresh_free_credits: a Free-plan account whose last refresh is older than the
         admin-configured interval gets topped up by the admin-configured free amount again.
  3. If the balance covers the cost, it's deducted and the use proceeds. Otherwise
     FeatureAccessDenied carries everything the frontend's upgrade modal needs: cost, balance,
     and when the free tier will next refresh.

A feature with no AiFeatureSetting row, or an account with no Subscription yet (e.g. Plans
haven't been seeded on a fresh install), fails OPEN (unrestricted) rather than silently blocking
every AI feature platform-wide over incomplete admin setup — the admin has to explicitly
configure a feature as paid (with a real cost) for gating to ever deny anyone.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.models import User
from app.models.admin_models import AppSetting
from app.models.subscription_models import (
    Plan, PlanLimit, Subscription, UsageCounter, AiFeatureSetting, CreditBalance, CreditLedgerEntry,
)
from app.services.subscription_limits import FEATURE_LABELS

DEFAULT_FREE_SIGNUP_CREDITS = 100
DEFAULT_FREE_REFRESH_HOURS = 720  # 30 days


class FeatureAccessDenied(Exception):
    """Raised by check_and_consume() when a feature use is denied. `payload`
    has everything the frontend needs to render the upgrade modal — callers
    should catch this and raise HTTPException(402, detail=exc.payload)."""

    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("message", "Access denied"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    """SQLite (used in tests, and by anyone running this app without Postgres) doesn't actually
    preserve timezone info on a DateTime(timezone=True) column — a value written as UTC-aware
    can come back naive on read. Treat a naive value as UTC (this codebase's convention
    everywhere else) rather than letting the comparison below raise."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _period_keys(now: datetime | None = None) -> dict:
    now = now or _now()
    return {"daily": now.strftime("%Y-%m-%d"), "monthly": now.strftime("%Y-%m")}


def _token_settings(db: Session) -> tuple[int, int]:
    """(free_signup_credits, free_credit_refresh_hours), admin-configurable via
    PUT /admin/settings, falling back to sane defaults if no settings row exists yet."""
    row = db.query(AppSetting).first()
    if not row:
        return DEFAULT_FREE_SIGNUP_CREDITS, DEFAULT_FREE_REFRESH_HOURS
    return (row.free_signup_credits or 0), (row.free_credit_refresh_hours or DEFAULT_FREE_REFRESH_HOURS)


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
    """Retained for the legacy per-plan daily/monthly allowance table — no longer consulted by
    check_and_consume() (superseded by the shared token balance below), but the table/endpoints
    still exist and this stays available for anything still reading it."""
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


def _record_usage(db: Session, user_id: int, feature_key: str) -> None:
    periods = _period_keys()
    _increment_usage(db, user_id, feature_key, "daily", periods["daily"])
    _increment_usage(db, user_id, feature_key, "monthly", periods["monthly"])


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


def grant_signup_credits(db: Session, user: User) -> None:
    """Called once at registration (app/routes/auth.py) — every new account starts with the
    admin-configured free token amount, matching the ChatGPT/Claude/Midjourney "free tier"
    pattern this whole system is modeled on. Always stamps last_free_refresh_at (even when the
    admin has set the signup grant to 0) so _maybe_refresh_free_credits never mistakes a
    properly-onboarded account for a legacy one that's "never refreshed" and owes it a bonus
    the moment the admin turns the signup grant back on."""
    row = db.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
    if not row:
        row = CreditBalance(user_id=user.id, balance=0)
        db.add(row)
        db.flush()

    free_amount, _ = _token_settings(db)
    if free_amount > 0:
        adjust_credits(db, user.id, free_amount, reason="signup_grant")

    row.last_free_refresh_at = _now()
    db.commit()


def _maybe_expire_subscription(db: Session, subscription: Subscription) -> None:
    """A paid plan whose billing period has passed reverts the account to the Free plan — this
    project's payment gateway is a test-mode mock with no real recurring billing to renew it
    automatically, so lazy expiry-on-access is the honest behavior rather than pretending an
    unpaid renewal succeeded."""
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if not plan or plan.slug == "free":
        return
    if subscription.current_period_end and _now() > _as_aware(subscription.current_period_end):
        free_plan = db.query(Plan).filter(Plan.slug == "free").first()
        if free_plan:
            subscription.plan_id = free_plan.id
            subscription.status = "active"
            subscription.cancel_at_period_end = False
            db.commit()


def _maybe_refresh_free_credits(db: Session, user: User, subscription: Subscription) -> None:
    """Tops up a Free-plan account's balance by the admin-configured free amount once the
    admin-configured refresh interval has elapsed since the last refresh (or since signup, for
    an account that predates this feature and has never had one)."""
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if not plan or plan.slug != "free":
        return

    free_amount, refresh_hours = _token_settings(db)
    if free_amount <= 0 or refresh_hours <= 0:
        return

    balance_row = db.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
    now = _now()

    if balance_row is None or balance_row.last_free_refresh_at is None:
        # No CreditBalance row (predates this feature, or the signup grant is disabled) — treat
        # as due immediately so a real refresh happens on this check rather than never.
        adjust_credits(db, user.id, free_amount, reason="free_refresh")
        db.query(CreditBalance).filter(CreditBalance.user_id == user.id).update({"last_free_refresh_at": now})
        db.commit()
        return

    if now - _as_aware(balance_row.last_free_refresh_at) >= timedelta(hours=refresh_hours):
        adjust_credits(db, user.id, free_amount, reason="free_refresh")
        balance_row.last_free_refresh_at = now
        db.commit()


def next_free_refresh_at(db: Session, user: User, subscription: Subscription | None) -> datetime | None:
    """When a Free-plan account's balance will next be topped up — None if the account isn't on
    the Free plan (paid plans don't get this; they're granted tokens per billing period instead)
    or the admin has disabled the free refresh entirely."""
    if subscription is None:
        return None
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if not plan or plan.slug != "free":
        return None

    _, refresh_hours = _token_settings(db)
    if refresh_hours <= 0:
        return None

    balance_row = db.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
    last = _as_aware(balance_row.last_free_refresh_at) if balance_row and balance_row.last_free_refresh_at else _now()
    return last + timedelta(hours=refresh_hours)


def get_feature_usage_summary(db: Session, user: User, feature_key: str) -> dict:
    """Read-only snapshot of where a user stands on one feature — used both
    internally and by GET /subscriptions/me."""
    setting = get_feature_setting(db, feature_key)
    subscription = get_or_create_subscription(db, user)
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first() if subscription else None

    return {
        "featureKey": feature_key,
        "featureLabel": setting.feature_label if setting else FEATURE_LABELS.get(feature_key, feature_key),
        "isPaid": setting.is_paid if setting else False,
        "isEnabled": setting.is_enabled if setting else True,
        "creditCostPerUse": setting.credit_cost_per_use if setting else 0,
        "planName": plan.name if plan else None,
    }


def check_and_consume(db: Session, user: User, feature_key: str) -> dict:
    """The gate. Call before doing the actual AI work for a gated feature.
    Returns a result dict on success; raises FeatureAccessDenied on denial."""
    setting = get_feature_setting(db, feature_key)

    if setting is not None and not setting.is_enabled:
        return {"allowed": True, "usedVia": "unrestricted", "reason": "gating_disabled"}

    if setting is None or not setting.is_paid or setting.credit_cost_per_use <= 0:
        # Unmetered feature -- still counted for admin "most used features" analytics, but never
        # touches the token balance.
        _record_usage(db, user.id, feature_key)
        return {"allowed": True, "usedVia": "unrestricted", "reason": "free_feature"}

    subscription = get_or_create_subscription(db, user)
    if subscription is None:
        _record_usage(db, user.id, feature_key)
        return {"allowed": True, "usedVia": "unrestricted", "reason": "no_plan_configured"}

    _maybe_expire_subscription(db, subscription)
    _maybe_refresh_free_credits(db, user, subscription)

    cost = setting.credit_cost_per_use
    balance = get_credit_balance(db, user.id)

    if balance >= cost:
        new_balance = adjust_credits(db, user.id, -cost, reason="usage", feature_key=feature_key)
        _record_usage(db, user.id, feature_key)
        return {"allowed": True, "usedVia": "tokens", "creditCost": cost, "creditBalance": new_balance}

    next_refresh = next_free_refresh_at(db, user, subscription)
    raise FeatureAccessDenied({
        "error": "insufficient_credits",
        "message": f"You've used all your available tokens for {setting.feature_label}.",
        "featureKey": feature_key,
        "featureLabel": setting.feature_label,
        "creditCost": cost,
        "creditBalance": balance,
        "nextRefreshAt": next_refresh.isoformat() if next_refresh else None,
        "canUpgrade": True,
        "canBuyCredits": True,
    })
