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
    """A completed (or failed) money movement — subscription charge or a
    credit-package purchase. Deliberately holds NO card data: amount,
    currency, method, and status only. See app/services/payment_gateway.py
    for the (currently mocked, pending real provider credentials) processor
    this is written by; the schema itself makes storing a card number
    impossible since there's no column for one."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)  # set for kind="subscription", null for credit purchases
    kind = Column(String, nullable=False, default="subscription")  # "subscription" | "credit_purchase"
    stripe_invoice_id = Column(String, nullable=True, unique=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="usd")
    status = Column(String, nullable=False)  # "paid" | "pending" | "failed" | "refunded"
    billing_reason = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)  # "credit_card" | "debit_card" | "paypal" | "bitcoin"
    credits_purchased = Column(Integer, nullable=True)  # set only for kind="credit_purchase"
    external_reference = Column(String, nullable=True)  # the mock/real payment provider's transaction ref (never a card token)
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


class AiFeatureSetting(Base):
    """Admin-controlled, platform-wide config for one AI feature — whether it
    requires payment at all, and its credit cost. Independent of Plan/
    PlanLimit: PlanLimit says how many uses a given plan *includes* for
    free; this table says what happens once that included allowance runs
    out (nothing further, or pay-per-use via credits) and lets the admin
    flip a feature between free and paid without touching any plan."""
    __tablename__ = "ai_feature_settings"

    id = Column(Integer, primary_key=True, index=True)
    feature_key = Column(String, unique=True, nullable=False)
    feature_label = Column(String, nullable=False)
    is_paid = Column(Boolean, nullable=False, default=False)
    credit_cost_per_use = Column(Integer, nullable=False, default=0)
    is_enabled = Column(Boolean, nullable=False, default=True)  # master kill-switch: False = gating off entirely
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CreditBalance(Base):
    """One row per user — kept as an explicit running total (rather than
    summed from CreditLedgerEntry on every read) the same way UsageCounter
    avoids re-aggregating on every check; CreditLedgerEntry below is still
    the full audit trail."""
    __tablename__ = "credit_balances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CreditLedgerEntry(Base):
    """Append-only audit trail of every credit movement — positive for a
    purchase/admin grant, negative for a feature use. Powers both the
    user-facing "Usage History" and the admin "Credits Consumed" analytics."""
    __tablename__ = "credit_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    delta = Column(Integer, nullable=False)  # positive = credited, negative = spent
    reason = Column(String, nullable=False)  # "purchase" | "usage" | "admin_grant" | "refund"
    feature_key = Column(String, nullable=True)  # set when reason="usage"
    reference_id = Column(String, nullable=True)  # e.g. the related Transaction id
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class CreditPackage(Base):
    """Admin-managed purchasable credit bundles (e.g. "100 Credits" for
    $9.99). Deactivating one hides it from new purchases without breaking
    historical Transactions that already reference its credit amount."""
    __tablename__ = "credit_packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    credits = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="usd")
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PaymentMethodConfig(Base):
    """Admin on/off switch per payment method — purely a display/availability
    toggle for the checkout flow; it does not itself integrate with any
    provider (see app/services/payment_gateway.py)."""
    __tablename__ = "payment_method_configs"

    id = Column(Integer, primary_key=True, index=True)
    method_key = Column(String, unique=True, nullable=False)  # "credit_card" | "debit_card" | "paypal" | "bitcoin"
    label = Column(String, nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
