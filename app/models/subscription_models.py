from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    monthly_price_cents = Column(Integer, nullable=False, default=0)
    yearly_price_cents = Column(Integer, nullable=True)
    currency = Column(String, nullable=False, default="usd")
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    stripe_product_id = Column(String, nullable=True)
    stripe_monthly_price_id = Column(String, nullable=True)
    stripe_yearly_price_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PlanLimit(Base):
    """One row per (plan, feature) — daily_limit/monthly_limit of None means
    unlimited. Kept as a separate table rather than fixed columns on Plan so
    admins can configure limits generically without a schema change every
    time a new billable feature is added."""
    __tablename__ = "plan_limits"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    feature_key = Column(String, nullable=False)
    daily_limit = Column(Integer, nullable=True)
    monthly_limit = Column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("plan_id", "feature_key", name="uq_plan_limit_feature"),)


class Subscription(Base):
    """A user's current subscription state — one row per user, upserted by
    the Stripe webhook handler (app/routes/stripe_webhooks.py) as Stripe
    events arrive. Lazily get-or-created on the Free plan the first time it's
    needed rather than backfilled, to avoid racing with concurrent signups."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    billing_cycle = Column(String, nullable=False, default="monthly")  # "monthly" | "yearly"
    status = Column(String, nullable=False, default="active")  # "active" | "trialing" | "past_due" | "canceled" | "incomplete"
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, unique=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    stripe_invoice_id = Column(String, nullable=True, unique=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="usd")
    status = Column(String, nullable=False)  # "paid" | "pending" | "failed" | "refunded"
    billing_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feature_key = Column(String, nullable=False)
    period_type = Column(String, nullable=False)  # "daily" | "monthly"
    period_key = Column(String, nullable=False)  # "2026-08-10" | "2026-08"
    count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "feature_key", "period_type", "period_key", name="uq_usage_counter"),
    )
