"""Admin-side aggregation and lazy-seeding for the Subscription & Credit
Management system. Mirrors admin_dashboard.py's separation: routes stay
thin, the actual queries live here.

"Lazy seed" pattern used for AiFeatureSetting/PaymentMethodConfig: rather
than a one-off migration script the admin has to remember to run, the first
GET that needs these rows creates any missing ones with safe defaults
(is_paid=False, is_enabled=True — nothing becomes gated or unavailable just
because the admin opened the settings page) and returns the full set. Every
subsequent call is a normal read.
"""
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import User
from app.models.subscription_models import (
    Plan, PlanLimit, Subscription, Transaction, UsageCounter,
    AiFeatureSetting, CreditLedgerEntry, PaymentMethodConfig,
)
from app.services.subscription_limits import FEATURE_KEYS, FEATURE_LABELS

DEFAULT_PAYMENT_METHODS = [
    ("credit_card", "Credit Card"),
    ("debit_card", "Debit Card"),
    ("paypal", "PayPal"),
    ("bitcoin", "Bitcoin"),
]

NEAR_LIMIT_THRESHOLD = 0.8


def get_or_seed_feature_settings(db: Session) -> list[AiFeatureSetting]:
    existing_keys = {row.feature_key for row in db.query(AiFeatureSetting).all()}
    created = False
    for key in FEATURE_KEYS:
        if key not in existing_keys:
            db.add(AiFeatureSetting(
                feature_key=key, feature_label=FEATURE_LABELS.get(key, key),
                is_paid=False, credit_cost_per_use=0, is_enabled=True,
            ))
            created = True
    if created:
        db.commit()
    return db.query(AiFeatureSetting).order_by(AiFeatureSetting.feature_key).all()


def get_or_seed_payment_methods(db: Session) -> list[PaymentMethodConfig]:
    existing_keys = {row.method_key for row in db.query(PaymentMethodConfig).all()}
    created = False
    for key, label in DEFAULT_PAYMENT_METHODS:
        if key not in existing_keys:
            db.add(PaymentMethodConfig(method_key=key, label=label, is_enabled=True))
            created = True
    if created:
        db.commit()
    return db.query(PaymentMethodConfig).order_by(PaymentMethodConfig.method_key).all()


def is_plan_free(db: Session, plan_id: int) -> bool:
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    return bool(plan and plan.slug == "free")


def count_paid_active_subscribers(db: Session) -> int:
    return (
        db.query(func.count(Subscription.id))
        .join(Plan, Plan.id == Subscription.plan_id)
        .filter(Subscription.status == "active", Plan.slug != "free")
        .scalar() or 0
    )


def compute_credit_totals(db: Session) -> dict:
    total_purchased = (
        db.query(func.coalesce(func.sum(CreditLedgerEntry.delta), 0))
        .filter(CreditLedgerEntry.reason == "purchase")
        .scalar() or 0
    )
    total_consumed = (
        db.query(func.coalesce(func.sum(CreditLedgerEntry.delta), 0))
        .filter(CreditLedgerEntry.reason == "usage")
        .scalar() or 0
    )
    return {"totalCreditsPurchased": total_purchased, "creditsConsumed": abs(total_consumed)}


def compute_most_used_features(db: Session, top_n: int = 10) -> list[dict]:
    """Summed over `monthly` UsageCounter rows only (not `daily` too — every
    use increments both, so summing both would double-count); a monthly
    counter's period_key changes each month, so summing across all of them
    gives a lifetime total per feature."""
    rows = (
        db.query(UsageCounter.feature_key, func.sum(UsageCounter.count))
        .filter(UsageCounter.period_type == "monthly")
        .group_by(UsageCounter.feature_key)
        .order_by(func.sum(UsageCounter.count).desc())
        .limit(top_n)
        .all()
    )
    return [{"featureKey": key, "label": FEATURE_LABELS.get(key, key), "count": int(count)} for key, count in rows]


def compute_revenue_by_plan(db: Session) -> list[dict]:
    rows = (
        db.query(Plan.name, func.coalesce(func.sum(Transaction.amount_cents), 0))
        .join(Transaction, Transaction.plan_id == Plan.id)
        .filter(Transaction.status == "paid", Transaction.kind == "subscription")
        .group_by(Plan.name)
        .order_by(func.coalesce(func.sum(Transaction.amount_cents), 0).desc())
        .all()
    )
    return [{"plan": name, "revenueCents": int(cents)} for name, cents in rows]


def compute_revenue_by_feature_estimated(db: Session, top_n: int = 10) -> list[dict]:
    """Credits are a fungible currency purchased in bundles and spent across
    features — there's no exact per-feature revenue to attribute (a single
    credit purchase might fund uses across five different features). This
    estimates it via a blended cents-per-credit rate (total paid credit-
    purchase revenue / total credits ever purchased) applied to how many
    credits each feature actually consumed. Explicitly labeled "estimated"
    in the response for that reason."""
    total_purchase_revenue_cents = (
        db.query(func.coalesce(func.sum(Transaction.amount_cents), 0))
        .filter(Transaction.status == "paid", Transaction.kind == "credit_purchase")
        .scalar() or 0
    )
    total_purchased = compute_credit_totals(db)["totalCreditsPurchased"]
    blended_cents_per_credit = (total_purchase_revenue_cents / total_purchased) if total_purchased else 0

    rows = (
        db.query(CreditLedgerEntry.feature_key, func.sum(CreditLedgerEntry.delta))
        .filter(CreditLedgerEntry.reason == "usage", CreditLedgerEntry.feature_key.isnot(None))
        .group_by(CreditLedgerEntry.feature_key)
        .all()
    )
    estimated = [
        {
            "featureKey": key,
            "label": FEATURE_LABELS.get(key, key),
            "creditsConsumed": abs(int(delta_sum)),
            "estimatedRevenueCents": round(abs(delta_sum) * blended_cents_per_credit),
        }
        for key, delta_sum in rows
    ]
    estimated.sort(key=lambda row: row["estimatedRevenueCents"], reverse=True)
    return estimated[:top_n]


def compute_top_paying_users(db: Session, top_n: int = 10) -> list[dict]:
    """Lifetime paid amount per user, across both subscription charges and credit-package
    purchases — the "Top Paying Users" admin view."""
    rows = (
        db.query(User.id, User.full_name, User.email, func.coalesce(func.sum(Transaction.amount_cents), 0))
        .join(Transaction, Transaction.user_id == User.id)
        .filter(Transaction.status == "paid")
        .group_by(User.id, User.full_name, User.email)
        .order_by(func.coalesce(func.sum(Transaction.amount_cents), 0).desc())
        .limit(top_n)
        .all()
    )
    return [
        {"userId": uid, "userName": name or email, "userEmail": email, "totalPaidCents": int(total)}
        for uid, name, email, total in rows
    ]


def get_users_near_limit(db: Session, threshold: float = NEAR_LIMIT_THRESHOLD, limit: int = 20) -> list[dict]:
    """Flags (user, feature) pairs where the user is close to their plan's
    monthly allowance for the current period — a natural upsell moment.
    O(active subscribers x plan features with a limit) — fine at this
    product's scale; would need a batched/SQL-side rewrite at a much larger
    subscriber count."""
    now = datetime.now(timezone.utc)
    monthly_key = now.strftime("%Y-%m")

    subscriptions = db.query(Subscription).filter(Subscription.status == "active").all()
    results = []
    for subscription in subscriptions:
        plan_limits = (
            db.query(PlanLimit)
            .filter(PlanLimit.plan_id == subscription.plan_id, PlanLimit.monthly_limit.isnot(None))
            .all()
        )
        if not plan_limits:
            continue
        user = db.query(User).filter(User.id == subscription.user_id).first()
        if not user:
            continue
        for plan_limit in plan_limits:
            usage = (
                db.query(UsageCounter)
                .filter(
                    UsageCounter.user_id == subscription.user_id, UsageCounter.feature_key == plan_limit.feature_key,
                    UsageCounter.period_type == "monthly", UsageCounter.period_key == monthly_key,
                )
                .first()
            )
            used = usage.count if usage else 0
            ratio = used / plan_limit.monthly_limit if plan_limit.monthly_limit else 0
            if ratio >= threshold:
                results.append({
                    "userId": user.id,
                    "userName": user.full_name or user.email,
                    "featureKey": plan_limit.feature_key,
                    "featureLabel": FEATURE_LABELS.get(plan_limit.feature_key, plan_limit.feature_key),
                    "used": used,
                    "limit": plan_limit.monthly_limit,
                    "ratio": round(ratio, 2),
                })

    results.sort(key=lambda row: row["ratio"], reverse=True)
    return results[:limit]


def compute_total_revenue_cents(db: Session) -> int:
    return (
        db.query(func.coalesce(func.sum(Transaction.amount_cents), 0))
        .filter(Transaction.status == "paid")
        .scalar() or 0
    )


def compute_subscription_analytics(db: Session) -> dict:
    credit_totals = compute_credit_totals(db)
    return {
        **credit_totals,
        "totalRevenueCents": compute_total_revenue_cents(db),
        "mostUsedFeatures": compute_most_used_features(db),
        "revenueByPlan": compute_revenue_by_plan(db),
        "revenueByFeatureEstimated": compute_revenue_by_feature_estimated(db),
        "activeSubscribers": count_paid_active_subscribers(db),
        "usersNearLimit": get_users_near_limit(db),
        "topPayingUsers": compute_top_paying_users(db),
    }
